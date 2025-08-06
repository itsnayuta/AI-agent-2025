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

class ExecuteSchedule:
    def __init__(self, db_path='database/schedule.db', smtp_config=None, enable_google_calendar=True):
        load_dotenv()
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()
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
            self.send_notification(f"Lịch mới: {title} lúc {start_time}")
            if self.enable_google_calendar:
                self.sync_google_calendar(title, description, start_time, end_time)
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
            cursor.execute('DELETE FROM schedules WHERE id=?', (schedule_id,))
            self.conn.commit()
            self.send_notification(f"Đã xóa lịch: {row[1]} lúc {row[3]}")
            return "✅ Đã xóa lịch thành công."
        except Exception as e:
            return f"❌ Lỗi khi xóa lịch: {e}"

    def get_schedules(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules ORDER BY start_time')
        return cursor.fetchall()

    def get_schedules_by_date(self, date_str):
        """Lấy lịch theo ngày (YYYY-MM-DD)"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE start_time LIKE ? ORDER BY start_time', (f'{date_str}%',))
        return cursor.fetchall()

    def get_schedules_by_month(self, year, month):
        """Lấy lịch theo tháng"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE strftime("%Y", start_time)=? AND strftime("%m", start_time)=? ORDER BY start_time', (str(year), f'{month:02d}'))
        return cursor.fetchall()

    def get_schedules_by_year(self, year):
        """Lấy lịch theo năm"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM schedules WHERE strftime("%Y", start_time)=? ORDER BY start_time', (str(year),))
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

    def sync_google_calendar(self, title, description, start_time, end_time):
        try:
            if not os.path.exists(self.credentials_path):
                print(f"[Google Calendar] Không tìm thấy file credentials: {self.credentials_path}")
                return
                
            creds = None
            token_path = 'token.pickle'
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    print("[Google Calendar] Đang xác thực với Google...")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            service = build('calendar', 'v3', credentials=creds)
            event = {
                'summary': title,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'Asia/Ho_Chi_Minh'},
                'end': {'dateTime': end_time, 'timeZone': 'Asia/Ho_Chi_Minh'},
            }
            service.events().insert(calendarId='primary', body=event).execute()
            print(f"[Google Calendar] Đã đồng bộ lịch: {title} ({start_time} - {end_time})")
        except Exception as e:
            print(f"🔶 Đồng bộ Google Calendar thất bại: {e}")
            print("📋 Lịch đã được lưu thành công vào database local!")
            if "accessNotConfigured" in str(e) or "has not been used" in str(e):
                print("🛠️ CÁCH SỬA LỖI:")
                print("   1. Truy cập: https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview")
                print("   2. Chọn project của bạn")
                print("   3. Nhấn 'Enable' để kích hoạt Google Calendar API")
                print("   4. Chờ vài phút rồi thử lại")
            elif "access_denied" in str(e):
                print("🛠️ HƯỚNG DẪN: Kiểm tra OAuth consent screen và thêm email vào Test users trong Google Cloud Console")

    def close(self):
        self.conn.close()
