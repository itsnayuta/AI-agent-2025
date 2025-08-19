import sqlite3
import smtplib
import re
import os
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import List, Tuple, Optional, Dict, Any
from core.config import Config
from utils.timezone_utils import get_vietnam_now, get_vietnam_time, vietnam_isoformat, get_vietnam_date_display

class EmailService:
    def __init__(self):
        self.smtp_config = Config.SMTP_CONFIG
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        try:
            if not self._validate_email_config() or not to_email:
                return False

            email = EmailMessage()
            email.set_content(body)
            email['Subject'] = subject
            email['From'] = self.smtp_config['user']
            email['To'] = to_email
            
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as smtp:
                smtp.starttls()
                smtp.login(self.smtp_config['user'], self.smtp_config['password'])
                smtp.send_message(email)
            
            print(f"Đã gửi email thành công đến: {to_email}")
            return True
            
        except Exception as e:
            print(f"Lỗi khi gửi email: {e}")
            return False
    
    def _validate_email_config(self) -> bool:
        required_fields = ['host', 'port', 'user', 'password']
        for field in required_fields:
            if not self.smtp_config.get(field):
                return False
        return True

class EmailTemplateService:
    @staticmethod
    def create_reminder_email(schedule_data: Dict[str, Any]) -> Dict[str, str]:
        title = schedule_data.get('title', 'Lịch trình')
        description = schedule_data.get('description', '')
        start_time = schedule_data.get('start_time', '')
        end_time = schedule_data.get('end_time', '')
        
        start_display, end_display = EmailTemplateService._format_time(start_time, end_time)
        
        subject = f"Nhắc nhở: {title}"
        body = f"""Xin chào!
Bạn có lịch sắp diễn ra trong 15 phút tới:

Tiêu đề: {title}
Mô tả: {description}
Thời gian: {start_display} - {end_display}

Hãy chuẩn bị sẵn sàng!

---
Tin nhắn tự động từ AI Agent Schedule Management"""
        
        return {'subject': subject, 'body': body}
    
    @staticmethod
    def create_welcome_email(user_email: str) -> Dict[str, str]:
        subject = "Chào mừng đến với AI Agent Schedule Management"
        body = f"""Xin chào!
Email {user_email} đã được thiết lập để nhận thông báo lịch trình.
Bạn sẽ nhận được email nhắc nhở trước 15 phút khi có lịch sắp diễn ra.
Để thay đổi email nhận thông báo, bạn có thể sử dụng lệnh:
"Thay đổi email nhận thông báo thành [email_mới]"
Cảm ơn bạn đã sử dụng dịch vụ!
---
AI Agent Schedule Management"""
        
        return {'subject': subject, 'body': body}
    
    @staticmethod
    def _format_time(start_time: str, end_time: str) -> tuple:
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            start_display = start_dt.strftime('%d/%m/%Y lúc %H:%M')
            end_display = end_dt.strftime('%H:%M')
            return start_display, end_display
        except:
            return start_time, end_time


class UserConfigService:
    def __init__(self, db_path: str = 'database/user_config.db'):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def set_notification_email(self, email: str) -> bool:
        return self._set_config('notification_email', email)
    
    def get_notification_email(self) -> Optional[str]:
        return self._get_config('notification_email')
    
    def set_email_setup_completed(self, completed: bool = True) -> bool:
        return self._set_config('email_setup_completed', str(completed))
    
    def is_email_setup_completed(self) -> bool:
        result = self._get_config('email_setup_completed')
        return result == 'True' if result else False
    
    def _set_config(self, key: str, value: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_config (config_key, config_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Lỗi khi thiết lập cấu hình {key}: {e}")
            return False
    
    def _get_config(self, key: str) -> Optional[str]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT config_value FROM user_config WHERE config_key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Lỗi khi lấy cấu hình {key}: {e}")
            return None


class NotificationDatabaseService:
    def __init__(self, db_path: str = 'database/schedule.db'):
        self.db_path = db_path
        self._ensure_notification_columns()
    
    def _ensure_notification_columns(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(schedules)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'notified' not in columns:
                cursor.execute('ALTER TABLE schedules ADD COLUMN notified INTEGER DEFAULT 0')
                print("Đã thêm cột 'notified' vào bảng schedules")
            
            if 'notification_sent_at' not in columns:
                cursor.execute('ALTER TABLE schedules ADD COLUMN notification_sent_at TEXT')
                print("Đã thêm cột 'notification_sent_at' vào bảng schedules")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Lỗi khi cập nhật cấu trúc database: {e}")
    
    def get_upcoming_schedules(self, reminder_minutes: int = 15) -> List[Tuple]:
        try:
            current_time = get_vietnam_now()
            reminder_time = current_time + timedelta(minutes=reminder_minutes)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, title, description, start_time, end_time
                FROM schedules 
                WHERE start_time <= ? 
                AND start_time > ? 
                AND (notified IS NULL OR notified = 0)
            '''
            
            cursor.execute(query, (
                reminder_time.strftime('%Y-%m-%dT%H:%M:%S'),
                current_time.strftime('%Y-%m-%dT%H:%M:%S')
            ))
            
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"Lỗi khi truy vấn lịch sắp tới: {e}")
            return []
    
    def mark_notification_sent(self, schedule_id: int) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE schedules 
                SET notified = 1, notification_sent_at = ? 
                WHERE id = ?
            ''', (vietnam_isoformat(get_vietnam_now()), schedule_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Lỗi khi cập nhật trạng thái thông báo: {e}")
            return False
    
    def get_notification_stats(self) -> dict:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM schedules')
            total_schedules = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM schedules WHERE notified = 1')
            notified_schedules = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM schedules WHERE notified = 0 OR notified IS NULL')
            pending_schedules = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_schedules': total_schedules,
                'notified_schedules': notified_schedules,
                'pending_schedules': pending_schedules
            }
        except Exception as e:
            print(f"Lỗi khi lấy thống kê: {e}")
            return {}


class UserInteractionService:
    def __init__(self):
        self.user_config = UserConfigService()
        self.email_service = EmailService()
        self.template_service = EmailTemplateService()
    
    def setup_user_email_on_startup(self) -> Dict[str, Any]:
        if self.user_config.is_email_setup_completed():
            current_email = self.user_config.get_notification_email()
            return {
                'setup_required': False,
                'current_email': current_email,
                'message': f"Email hiện tại để nhận thông báo: {current_email}"
            }
        
        return {
            'setup_required': True,
            'message': "Chưa có email được thiết lập. Vui lòng cung cấp email để nhận thông báo lịch trình."
        }
    
    def process_email_setup_command(self, user_input: str) -> Dict[str, Any]:
        if not self._is_email_setup_command(user_input):
            return {
                'is_email_command': False,
                'message': 'Không phải lệnh thiết lập email'
            }
        
        email = self._extract_email_from_input(user_input)
        
        if not email:
            return {
                'is_email_command': True,
                'success': False,
                'message': 'Không tìm thấy email hợp lệ trong lệnh. Ví dụ: "Thiết lập email example@gmail.com"'
            }
        
        return self.setup_notification_email(email)
    
    def setup_notification_email(self, email: str) -> Dict[str, Any]:
        if not self._validate_email(email):
            return {
                'success': False,
                'message': f'Email không hợp lệ: {email}'
            }
        
        if self.user_config.set_notification_email(email):
            self.user_config.set_email_setup_completed(True)
            
            welcome_content = self.template_service.create_welcome_email(email)
            email_sent = self.email_service.send_email(
                to_email=email,
                subject=welcome_content['subject'],
                body=welcome_content['body']
            )
            
            return {
                'success': True,
                'email': email,
                'welcome_email_sent': email_sent,
                'message': f'Đã thiết lập email nhận thông báo: {email}'
            }
        else:
            return {
                'success': False,
                'message': 'Có lỗi khi lưu email vào hệ thống'
            }
    
    def get_current_email_info(self) -> Dict[str, Any]:
        current_email = self.user_config.get_notification_email()
        setup_completed = self.user_config.is_email_setup_completed()
        
        return {
            'current_email': current_email,
            'setup_completed': setup_completed,
            'message': f'Email hiện tại: {current_email}' if current_email else 'Chưa thiết lập email'
        }
    
    def _is_email_setup_command(self, user_input: str) -> bool:
        keywords = [
            'thiết lập email', 'setup email', 'đặt email',
            'thay đổi email', 'change email', 'email mới',
            'cấu hình email', 'config email'
        ]
        
        user_input_lower = user_input.lower()
        return any(keyword in user_input_lower for keyword in keywords)
    
    def _extract_email_from_input(self, user_input: str) -> Optional[str]:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, user_input)
        return matches[0] if matches and self._validate_email(matches[0]) else None
    
    def _validate_email(self, email: str) -> bool:
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return bool(re.match(pattern, email))
