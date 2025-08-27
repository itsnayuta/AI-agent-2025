import os
import sqlite3
import uuid
import datetime
import pickle
from typing import Optional, Dict, Any, List

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import time
import socket


class GoogleCalendarService:
    def __init__(self, db_path: str = 'database/schedule.db', credentials_path_env: str = 'GOOGLE_CREDENTIALS_PATH'):
        self.db_path = db_path
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials_path = os.getenv(credentials_path_env, 'core/OAuth/credentials.json')
        self.token_path = 'token.pickle'
        self._last_sync_ts: float = 0.0
        self._sync_debounce_interval = 30  # seconds
        
        # Timeout settings
        self._api_timeout = 30  # seconds for API calls
        self._max_retries = 3

        self._ensure_sync_tables()

    # ------------- Auth / Service -------------
    def _load_credentials(self):
        creds = None
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        return creds

    def _build_service(self):
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Không tìm thấy file credentials: {self.credentials_path}")
        creds = self._load_credentials()
        
        # Configure socket timeout để tránh hanging
        socket.setdefaulttimeout(self._api_timeout)
        
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)

    # ------------- DB Helpers -------------
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)

        conn.execute("PRAGMA journal_mode=WAL;")

        conn.execute("PRAGMA busy_timeout = 30000;")

        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_sync_tables(self):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            # trạng thái sync/watch
            cur.execute('''
                CREATE TABLE IF NOT EXISTS google_sync_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    calendar_id TEXT DEFAULT 'primary',
                    next_sync_token TEXT,
                    channel_id TEXT,
                    resource_id TEXT,
                    resource_uri TEXT,
                    channel_expiration TEXT,
                    last_sync_at TEXT
                )
            ''')
            cur.execute('SELECT id FROM google_sync_state WHERE id = 1')
            if cur.fetchone() is None:
                cur.execute('INSERT INTO google_sync_state (id) VALUES (1)')

            # bảng schedules (tạo tập trung, cùng lúc tạo index hiệu năng)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    created_at TEXT,
                    google_event_id TEXT,
                    google_etag TEXT,
                    google_updated TEXT,
                    deleted INTEGER DEFAULT 0
                )
            ''')
            # index để kiểm tra xung đột và truy vấn nhanh
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_schedules_google_event_id ON schedules(google_event_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_schedules_start_end ON schedules(start_time, end_time)')

            conn.commit()
        finally:
            conn.close()

    def _get_sync_state(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute('SELECT calendar_id, next_sync_token, channel_id, resource_id, resource_uri, channel_expiration, last_sync_at FROM google_sync_state WHERE id = 1')
            row = cur.fetchone()
            keys = ['calendar_id', 'next_sync_token', 'channel_id', 'resource_id', 'resource_uri', 'channel_expiration', 'last_sync_at']
            return dict(zip(keys, row)) if row else {}
        finally:
            conn.close()

    def get_sync_state(self) -> Dict[str, Any]:
        """Public: lấy trạng thái watch/sync hiện tại."""
        return self._get_sync_state()

    def _update_sync_state(self, **kwargs):
        if not kwargs:
            return
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            columns = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values())
            cur.execute(f"UPDATE google_sync_state SET {columns} WHERE id = 1", values)
            conn.commit()
        finally:
            conn.close()

    # ------------- CRUD event to Google Calendar -------------
    def create_event(self, summary: str, description: str, start_iso: str, end_iso: str, calendar_id: str = 'primary') -> Optional[str]:
        try:
            service = self._build_service()
            event_body = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_iso, 'timeZone': 'Asia/Ho_Chi_Minh'},
                'end': {'dateTime': end_iso, 'timeZone': 'Asia/Ho_Chi_Minh'},
            }
            event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            return event.get('id')
        except HttpError as e:
            print(f"[GoogleCalendar] Lỗi tạo event: {e}")
            return None

    def update_event(self, event_id: str, summary: str, description: str, start_iso: str, end_iso: str, calendar_id: str = 'primary') -> bool:
        try:
            service = self._build_service()
            event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            event['summary'] = summary
            event['description'] = description
            event['start'] = {'dateTime': start_iso, 'timeZone': 'Asia/Ho_Chi_Minh'}
            event['end'] = {'dateTime': end_iso, 'timeZone': 'Asia/Ho_Chi_Minh'}
            service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
            return True
        except HttpError as e:
            print(f"[GoogleCalendar] Lỗi cập nhật event: {e}")
            return False

    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        try:
            service = self._build_service()
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return True
        except HttpError as e:
            if e.resp is not None and e.resp.status in (404, 410):
                return True
            print(f"[GoogleCalendar] Lỗi xóa event: {e}")
            return False

    # ------------- Incremental Sync -------------
    def sync_from_google(self, calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        Kéo thay đổi từ Google về local bằng syncToken với retry mechanism.
        """
        current_time = time.time()
        if current_time - self._last_sync_ts < self._sync_debounce_interval:
            return {'synced': 0, 'changes': [], 'skipped': 'debounce'}
        
        for attempt in range(self._max_retries):
            try:
                result = self._do_sync_from_google(calendar_id)
                self._last_sync_ts = current_time
                return result
                
            except (socket.timeout, socket.error, ConnectionError) as e:
                if attempt < self._max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    print(f"[Sync] Network timeout after {self._max_retries} attempts")
                    return {'synced': 0, 'changes': [], 'error': 'network_timeout'}
                    
            except HttpError as e:
                if e.resp is not None and e.resp.status in (410,):
                    self._update_sync_state(next_sync_token=None)
                    return self.sync_from_google(calendar_id=calendar_id)
                else:
                    print(f"[Sync] HTTP Error: {e}")
                    return {'synced': 0, 'changes': [], 'error': str(e)}
                    
            except Exception as e:
                print(f"[Sync] Error: {e}")
                return {'synced': 0, 'changes': [], 'error': str(e)}

    def _do_sync_from_google(self, calendar_id: str = 'primary') -> Dict[str, Any]:
        """Thực hiện sync thực tế"""
        state = self._get_sync_state()
        token = state.get('next_sync_token')
        service = self._build_service()

        changes: List[Dict[str, Any]] = []
        page_token = None
        
        while True:
            kwargs: Dict[str, Any] = {
                'calendarId': calendar_id, 
                'showDeleted': True, 
                'singleEvents': True,
                'maxResults': 250
            }
            if token:
                kwargs['syncToken'] = token
            else:
                updated_min = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat() + 'Z'
                kwargs['updatedMin'] = updated_min

            if page_token:
                kwargs['pageToken'] = page_token

            resp = service.events().list(**kwargs).execute()
            items = resp.get('items', [])
            
            for ev in items:
                try:
                    self._upsert_local_from_google_event(ev)
                    changes.append({
                        'id': ev.get('id'), 
                        'status': ev.get('status'),
                        'summary': ev.get('summary', '')[:30]
                    })
                except Exception as ev_error:
                    print(f"[Sync] Event error {ev.get('id')}: {ev_error}")

            page_token = resp.get('nextPageToken')
            if not page_token:
                new_token = resp.get('nextSyncToken')
                if new_token:
                    from utils.timezone_utils import get_vietnam_timestamp
                    self._update_sync_state(next_sync_token=new_token, last_sync_at=get_vietnam_timestamp())
                break
                
        return {'synced': len(changes), 'changes': changes}

    # ------------- Webhook -------------
    def start_watch(self, callback_url: str, calendar_id: str = 'primary') -> Dict[str, Any]:
        service = self._build_service()
        channel_id = str(uuid.uuid4())
        body = {
            'id': channel_id,
            'type': 'web_hook',
            'address': callback_url,
        }
        watch = service.events().watch(calendarId=calendar_id, body=body).execute()
        resource_id = watch.get('resourceId')
        resource_uri = watch.get('resourceUri')
        expiration = watch.get('expiration')

        self._update_sync_state(calendar_id=calendar_id, channel_id=channel_id, resource_id=resource_id, resource_uri=resource_uri, channel_expiration=expiration)
        return {
            'channel_id': channel_id,
            'resource_id': resource_id,
            'resource_uri': resource_uri,
            'expiration': expiration,
        }

    def stop_watch(self) -> bool:
        state = self._get_sync_state()
        channel_id = state.get('channel_id')
        resource_id = state.get('resource_id')
        if not channel_id or not resource_id:
            return True
        service = self._build_service()
        try:
            service.channels().stop(body={'id': channel_id, 'resourceId': resource_id}).execute()
            self._update_sync_state(channel_id=None, resource_id=None, resource_uri=None, channel_expiration=None)
            return True
        except HttpError as e:
            print(f"[GoogleCalendar] Lỗi stop watch: {e}")
            return False

    # ------------- Local Upsert from Google Event -------------
    def _upsert_local_from_google_event(self, event: Dict[str, Any]):
        google_id = event.get('id')
        status = event.get('status')
        summary = event.get('summary') or ''
        description = event.get('description') or ''
        etag = event.get('etag')
        updated = event.get('updated')

        start_obj = event.get('start', {})
        end_obj = event.get('end', {})
        
        # Chuẩn hóa thời gian về múi giờ Việt Nam
        from utils.timezone_utils import parse_time_to_vietnam, vietnam_isoformat
        
        start_time_raw = start_obj.get('dateTime') or (start_obj.get('date') + 'T00:00:00+07:00' if start_obj.get('date') else None)
        end_time_raw = end_obj.get('dateTime') or (end_obj.get('date') + 'T23:59:59+07:00' if end_obj.get('date') else None)
        
        try:
            start_dt = vietnam_isoformat(parse_time_to_vietnam(start_time_raw)) if start_time_raw else None
            end_dt = vietnam_isoformat(parse_time_to_vietnam(end_time_raw)) if end_time_raw else None
        except:
            # Fallback to raw strings if parsing fails
            start_dt = start_time_raw
            end_dt = end_time_raw

        conn = self._get_conn()
        try:
            cur = conn.cursor()
            # Bảng schedules đã được tạo trong _ensure_sync_tables với UNIQUE index
            # Nếu sự kiện bị huỷ
            if status == 'cancelled':
                cur.execute('SELECT id FROM schedules WHERE google_event_id = ?', (google_id,))
                row = cur.fetchone()
                if row:
                    cur.execute('UPDATE schedules SET deleted = 1 WHERE id = ?', (row['id'],))
                conn.commit()
                return

            # Sử dụng UPSERT (ON CONFLICT) để tránh race/duplicate và cập nhật an toàn
            from utils.timezone_utils import get_vietnam_timestamp
            cur.execute('''
                INSERT INTO schedules (title, description, start_time, end_time, created_at, google_event_id, google_etag, google_updated, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(google_event_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    start_time=excluded.start_time,
                    end_time=excluded.end_time,
                    google_etag=excluded.google_etag,
                    google_updated=excluded.google_updated,
                    deleted=0
            ''', (
                summary, description, start_dt, end_dt,
                get_vietnam_timestamp(),
                google_id, etag, updated
            ))
            conn.commit()
        finally:
            conn.close()

    # ------------- Backfill & Sync Control -------------
    def backfill_range(self, time_min_iso: str, time_max_iso: str, calendar_id: str = 'primary') -> Dict[str, Any]:
        service = self._build_service()
        page_token = None
        total = 0
        while True:
            kwargs: Dict[str, Any] = {
                'calendarId': calendar_id,
                'timeMin': time_min_iso,
                'timeMax': time_max_iso,
                'singleEvents': True,
                'showDeleted': True,
                'maxResults': 2500,
            }
            if page_token:
                kwargs['pageToken'] = page_token
            resp = service.events().list(**kwargs).execute()
            items = resp.get('items', [])
            for ev in items:
                self._upsert_local_from_google_event(ev)
                total += 1
            page_token = resp.get('nextPageToken')
            if not page_token:
                break
        return {'backfilled': total, 'timeMin': time_min_iso, 'timeMax': time_max_iso}

    def reset_sync_token(self):
        self._update_sync_state(next_sync_token=None)

    def backfill_upcoming_days(self, days: int = 30, calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        Backfill tất cả sự kiện từ thời điểm hiện tại đến N ngày tới.
        """
        now_utc = datetime.datetime.utcnow().replace(microsecond=0)
        time_min_iso = now_utc.isoformat() + 'Z'
        time_max_iso = (now_utc + datetime.timedelta(days=days)).isoformat() + 'Z'
        return self.backfill_range(time_min_iso, time_max_iso, calendar_id=calendar_id)

    # ------------- Conflict Detection & Time Slot Helpers -------------
    def is_time_slot_free(self, start_iso: str, end_iso: str, exclude_google_id: Optional[str] = None) -> bool:
        """
        Kiểm tra khoảng thời gian [start_iso, end_iso) có trùng event local (deleted=0).
        Trả về True nếu trống.
        """
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            query = '''
                SELECT 1 FROM schedules
                WHERE deleted = 0
                AND NOT (end_time <= ? OR start_time >= ?)
            '''
            params = (start_iso, end_iso)
            if exclude_google_id:
                query += ' AND (google_event_id IS NULL OR google_event_id != ?)'
                params = (start_iso, end_iso, exclude_google_id)
            cur.execute(query, params)
            return cur.fetchone() is None
        finally:
            conn.close()

    def find_conflicts(self, start_iso: str, end_iso: str) -> List[Dict[str, Any]]:
        """
        Trả về danh sách event local xung đột với khoảng thời gian.
        """
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute('''
                SELECT id, title, start_time, end_time, google_event_id FROM schedules
                WHERE deleted = 0
                AND NOT (end_time <= ? OR start_time >= ?)
                ORDER BY start_time
            ''', (start_iso, end_iso))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def propose_time_slots(self, desired_start_iso: str, desired_end_iso: str, alternatives: int = 3, shifts_minutes: List[int] = None) -> List[Dict[str, str]]:
        """
        Nếu slot mong muốn conflict, trả về tối đa `alternatives` phương án thay thế.
        Mặc định thử shifts: +30, -30, +60, -60, +1440 (ngày kế).
        Trả về list các dict {start, end, note}.
        """
        import datetime as _dt
        if shifts_minutes is None:
            shifts_minutes = [30, -30, 60, -60, 1440]

        # nếu slot trống => trả về chính nó
        if self.is_time_slot_free(desired_start_iso, desired_end_iso):
            return [{"start": desired_start_iso, "end": desired_end_iso, "note": "Trống"}]

        results: List[Dict[str, str]] = []
        try:
            base_start = _dt.datetime.fromisoformat(desired_start_iso)
            base_end = _dt.datetime.fromisoformat(desired_end_iso)
        except Exception:
            # nếu không parse được thì không propose
            return results

        for minutes in shifts_minutes:
            if len(results) >= alternatives:
                break
            alt_start = (base_start + _dt.timedelta(minutes=minutes)).isoformat()
            alt_end = (base_end + _dt.timedelta(minutes=minutes)).isoformat()
            if self.is_time_slot_free(alt_start, alt_end):
                results.append({"start": alt_start, "end": alt_end, "note": f"Đề xuất (dịch {minutes} phút)"})

        return results


