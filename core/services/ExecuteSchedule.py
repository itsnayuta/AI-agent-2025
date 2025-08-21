import sqlite3
import datetime
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from core.services.google_calendar_service import GoogleCalendarService

class ExecuteSchedule:
    def __init__(self, db_path='database/schedule.db', smtp_config=None, enable_google_calendar=True):
        load_dotenv()
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()
        self._ensure_schema_migrations()
        self.enable_google_calendar = enable_google_calendar
        self.smtp_config = smtp_config or {
            'host': 'smtp.gmail.com',
            'port': 587,
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'to': os.getenv('SMTP_TO', '')
        }
        self.google_creds = None
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'core/OAuth/credentials.json')
        self.calendar_service = GoogleCalendarService(db_path=self.db_path) if enable_google_calendar else None

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                start_time TEXT,
                end_time TEXT,
                created_at TEXT
            )
        ''')
        self.conn.commit()

    def _ensure_schema_migrations(self):
        """Đảm bảo các cột mới phục vụ đồng bộ Google tồn tại."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(schedules)")
        cols = {row[1] for row in cursor.fetchall()}
        to_add = []
        if 'google_event_id' not in cols:
            to_add.append("ALTER TABLE schedules ADD COLUMN google_event_id TEXT")
        if 'google_etag' not in cols:
            to_add.append("ALTER TABLE schedules ADD COLUMN google_etag TEXT")
        if 'google_updated' not in cols:
            to_add.append("ALTER TABLE schedules ADD COLUMN google_updated TEXT")
        if 'deleted' not in cols:
            to_add.append("ALTER TABLE schedules ADD COLUMN deleted INTEGER DEFAULT 0")
        for stmt in to_add:
            try:
                cursor.execute(stmt)
            except Exception:
                pass
        self.conn.commit()

    def add_schedule(self, title, description, start_time, end_time):
        try:
            if not self.validate_time(start_time, end_time):
                return "❌ Thời gian không hợp lệ hoặc bị trùng với lịch khác."
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (title, description, start_time, end_time, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, description, start_time, end_time, datetime.datetime.now().isoformat()))
            self.conn.commit()
            new_id = cursor.lastrowid
            self.send_notification(f"Lịch mới: {title} lúc {start_time}")
            if self.enable_google_calendar and self.calendar_service:
                event_id = self.calendar_service.create_event(title, description, start_time, end_time)
                if event_id:
                    cursor.execute('UPDATE schedules SET google_event_id = ? WHERE id = ?', (event_id, new_id))
                    self.conn.commit()
            else:
                print("📋 Google Calendar sync đã bị tắt - chỉ lưu vào database local")
            return "✅ Đã thêm lịch thành công."
        except Exception as e:
            return f"❌ Lỗi khi thêm lịch: {e}"

    def update_schedule(self, schedule_id, title=None, description=None, start_time=None, end_time=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM schedules WHERE id=?', (schedule_id,))
            row = cursor.fetchone()
            if not row:
                return "❌ Không tìm thấy lịch để cập nhật."
            if start_time and end_time and not self.validate_time(start_time, end_time, exclude_id=schedule_id):
                return "❌ Thời gian cập nhật bị trùng với lịch khác."
            cursor.execute('''
                UPDATE schedules SET title=?, description=?, start_time=?, end_time=? WHERE id=?
            ''', (
                title or row[1],
                description or row[2],
                start_time or row[3],
                end_time or row[4],
                schedule_id
            ))
            self.conn.commit()
            self.send_notification(f"Đã cập nhật lịch: {title or row[1]} lúc {start_time or row[3]}")
            # Đồng bộ Google nếu có
            if self.enable_google_calendar and self.calendar_service:
                cursor.execute('SELECT google_event_id FROM schedules WHERE id=?', (schedule_id,))
                ev_row = cursor.fetchone()
                google_event_id = ev_row[0] if ev_row else None
                final_title = title or row[1]
                final_desc = description or row[2]
                final_start = start_time or row[3]
                final_end = end_time or row[4]
                if google_event_id:
                    self.calendar_service.update_event(google_event_id, final_title, final_desc, final_start, final_end)
                else:
                    new_event_id = self.calendar_service.create_event(final_title, final_desc, final_start, final_end)
                    if new_event_id:
                        cursor.execute('UPDATE schedules SET google_event_id = ? WHERE id = ?', (new_event_id, schedule_id))
                        self.conn.commit()
            return "✅ Đã cập nhật lịch thành công."
        except Exception as e:
            return f"❌ Lỗi khi cập nhật lịch: {e}"

    def delete_schedule(self, schedule_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM schedules WHERE id=?', (schedule_id,))
            row = cursor.fetchone()
            if not row:
                return "❌ Không tìm thấy lịch để xóa."
            # Xóa khỏi Google nếu có
            if self.enable_google_calendar and self.calendar_service:
                cursor.execute('SELECT google_event_id FROM schedules WHERE id=?', (schedule_id,))
                ev_row = cursor.fetchone()
                google_event_id = ev_row[0] if ev_row else None
                if google_event_id:
                    self.calendar_service.delete_event(google_event_id)
            cursor.execute('DELETE FROM schedules WHERE id=?', (schedule_id,))
            self.conn.commit()
            self.send_notification(f"Đã xóa lịch: {row[1]} lúc {row[3]}")
            return "✅ Đã xóa lịch thành công."
        except Exception as e:
            return f"❌ Lỗi khi xóa lịch: {e}"

    def get_schedules(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE COALESCE(deleted, 0) = 0 ORDER BY start_time')
        return cursor.fetchall()

    def get_schedules_by_date(self, date_str):
        """Lấy lịch theo ngày (YYYY-MM-DD)"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE COALESCE(deleted, 0) = 0 AND start_time LIKE ? ORDER BY start_time', (f'{date_str}%',))
        return cursor.fetchall()

    def get_schedules_by_month(self, year, month):
        """Lấy lịch theo tháng"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE COALESCE(deleted, 0) = 0 AND strftime("%Y", start_time)=? AND strftime("%m", start_time)=? ORDER BY start_time', (str(year), f'{month:02d}'))
        return cursor.fetchall()

    def get_schedules_by_year(self, year):
        """Lấy lịch theo năm"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE COALESCE(deleted, 0) = 0 AND strftime("%Y", start_time)=? ORDER BY start_time', (str(year),))
        return cursor.fetchall()

    def validate_time(self, start_time, end_time, exclude_id=None):
        try:
            start_dt = datetime.datetime.fromisoformat(start_time)
            end_dt = datetime.datetime.fromisoformat(end_time)
            if start_dt >= end_dt:
                return False
        except Exception:
            return False
        cursor = self.conn.cursor()
        query = 'SELECT id, start_time, end_time FROM schedules'
        cursor.execute(query)
        for row in cursor.fetchall():
            if exclude_id and row[0] == exclude_id:
                continue
            exist_start = datetime.datetime.fromisoformat(row[1])
            exist_end = datetime.datetime.fromisoformat(row[2])
            # Kiểm tra trùng thời gian
            if (start_dt < exist_end and end_dt > exist_start):
                return False
        return True

    def send_notification(self, message):
        print(f"[Thông báo] {message}")
        # Gửi email nếu cấu hình đủ
        if self.smtp_config['user'] and self.smtp_config['password'] and self.smtp_config['to']:
            try:
                email = EmailMessage()
                email.set_content(message)
                email['Subject'] = 'Thông báo lịch mới'
                email['From'] = self.smtp_config['user']
                email['To'] = self.smtp_config['to']
                with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as smtp:
                    smtp.starttls()
                    smtp.login(self.smtp_config['user'], self.smtp_config['password'])
                    smtp.send_message(email)
            except Exception as e:
                print(f"Gửi email thất bại: {e}")

    # sync_google_calendar được thay thế bởi GoogleCalendarService trong các phương thức CRUD

    def close(self):
        self.conn.close()
