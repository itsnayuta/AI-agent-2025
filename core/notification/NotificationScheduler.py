import threading
import time
from datetime import datetime
from typing import Optional

from .NotificationCore import EmailService, EmailTemplateService, UserConfigService, NotificationDatabaseService
from core.config import Config


class NotificationScheduler:
    def __init__(self):
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.scan_interval = Config.SCAN_INTERVAL
        self.reminder_minutes = Config.REMINDER_MINUTES
        
        self.email_service = EmailService()
        self.template_service = EmailTemplateService()
        self.user_config_service = UserConfigService()
        self.db_service = NotificationDatabaseService()
    
    def start(self) -> bool:
        if self.is_running:
            return True
        
        try:
            self.is_running = True
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, 
                daemon=True,
                name="NotificationScheduler"
            )
            self.scheduler_thread.start()
            print("NotificationScheduler đã được khởi động")
            return True
        except Exception as e:
            print(f"Lỗi khi khởi động NotificationScheduler: {e}")
            self.is_running = False
            return False
    
    def stop(self) -> bool:
        if not self.is_running:
            return True
        
        try:
            self.is_running = False
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
            print("NotificationScheduler đã được dừng")
            return True
        except Exception as e:
            print(f"Lỗi khi dừng NotificationScheduler: {e}")
            return False
    
    def _scheduler_loop(self):
        while self.is_running:
            try:
                self._check_and_send_notifications()
            except Exception as e:
                print(f"Lỗi trong vòng lặp scheduler: {e}")
            
            time.sleep(self.scan_interval)
    
    def _check_and_send_notifications(self):
        recipient_email = self.user_config_service.get_notification_email()
        if not recipient_email:
            return
        
        upcoming_schedules = self.db_service.get_upcoming_schedules(self.reminder_minutes)
        
        if not upcoming_schedules:
            return
        
        print(f"Tìm thấy {len(upcoming_schedules)} lịch cần gửi thông báo")
        
        for schedule in upcoming_schedules:
            schedule_id, title, description, start_time, end_time = schedule
            
            schedule_data = {
                'title': title,
                'description': description,
                'start_time': start_time,
                'end_time': end_time
            }
            
            email_content = self.template_service.create_reminder_email(schedule_data)
            
            if self.email_service.send_email(
                to_email=recipient_email,
                subject=email_content['subject'],
                body=email_content['body']
            ):
                self.db_service.mark_notification_sent(schedule_id)
                print(f"Đã gửi thông báo cho lịch: {title} (ID: {schedule_id})")
            else:
                print(f"Không thể gửi thông báo cho lịch: {title} (ID: {schedule_id})")
    
    def get_status(self) -> dict:
        return {
            'is_running': self.is_running,
            'scan_interval': self.scan_interval,
            'reminder_minutes': self.reminder_minutes,
            'thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False,
            'recipient_email': self.user_config_service.get_notification_email(),
            'email_setup_completed': self.user_config_service.is_email_setup_completed()
        }
