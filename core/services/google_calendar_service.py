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


class GoogleCalendarService:
    def __init__(self, db_path: str = 'database/schedule.db', credentials_path_env: str = 'GOOGLE_CREDENTIALS_PATH'):
        self.db_path = db_path
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials_path = os.getenv(credentials_path_env, 'core/OAuth/credentials.json')
        self.token_path = 'token.pickle'

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
        return build('calendar', 'v3', credentials=creds)

    # ------------- DB Helpers -------------
    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_sync_tables(self):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
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
        Kéo thay đổi từ Google về local bằng syncToken.
        Nếu chưa có token → lần đầu sẽ lấy tất cả (có thể giới hạn thời gian bằng updatedMin nếu muốn).
        """
        state = self._get_sync_state()
        token = state.get('next_sync_token')
        service = self._build_service()

        changes: List[Dict[str, Any]] = []
        page_token = None
        try:
            while True:
                kwargs: Dict[str, Any] = {'calendarId': calendar_id, 'showDeleted': True, 'singleEvents': False, 'maxResults': 2500}
                if token:
                    kwargs['syncToken'] = token
                else:
                    updated_min = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + 'Z'
                    kwargs['updatedMin'] = updated_min
                if page_token:
                    kwargs['pageToken'] = page_token

                resp = service.events().list(**kwargs).execute()
                items = resp.get('items', [])
                for ev in items:
                    self._upsert_local_from_google_event(ev)
                    changes.append({'id': ev.get('id'), 'status': ev.get('status')})

                page_token = resp.get('nextPageToken')
                if not page_token:
                    new_token = resp.get('nextSyncToken')
                    if new_token:
                        self._update_sync_state(next_sync_token=new_token, last_sync_at=datetime.datetime.utcnow().isoformat())
                    break
        except HttpError as e:
            if e.resp is not None and e.resp.status in (410,):
                self._update_sync_state(next_sync_token=None)
                return self.sync_from_google(calendar_id=calendar_id)
            print(f"[GoogleCalendar] Lỗi khi sync: {e}")
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
        start_dt = start_obj.get('dateTime') or (start_obj.get('date') + 'T00:00:00' if start_obj.get('date') else None)
        end_dt = end_obj.get('dateTime') or (end_obj.get('date') + 'T23:59:59' if end_obj.get('date') else None)

        conn = self._get_conn()
        try:
            cur = conn.cursor()
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

            cur.execute('SELECT id, deleted FROM schedules WHERE google_event_id = ?', (google_id,))
            row = cur.fetchone()

            if status == 'cancelled':
                if row:
                    cur.execute('UPDATE schedules SET deleted = 1 WHERE id = ?', (row[0],))

                conn.commit()
                return

            if row:
                # Update existing row
                cur.execute('''
                    UPDATE schedules
                    SET title = ?, description = ?, start_time = ?, end_time = ?, google_etag = ?, google_updated = ?, deleted = 0
                    WHERE google_event_id = ?
                ''', (summary, description, start_dt, end_dt, etag, updated, google_id))
            else:
                # Create new row
                cur.execute('''
                    INSERT INTO schedules (title, description, start_time, end_time, created_at, google_event_id, google_etag, google_updated, deleted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ''', (summary, description, start_dt, end_dt, datetime.datetime.utcnow().isoformat(), google_id, etag, updated))
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


