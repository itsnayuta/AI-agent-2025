from typing import Dict, Any, Optional
from datetime import datetime

from .NotificationScheduler import NotificationScheduler
from .NotificationCore import UserInteractionService, NotificationDatabaseService, EmailService


class NotificationManager:
    def __init__(self):
        self.scheduler = NotificationScheduler()
        self.user_interaction = UserInteractionService()
        self.db_service = NotificationDatabaseService()
        self.email_service = EmailService()
        self._is_initialized = False
    
    def initialize(self) -> Dict[str, Any]:
        try:
            email_setup = self.user_interaction.setup_user_email_on_startup()
            scheduler_started = self.scheduler.start()
            self._is_initialized = scheduler_started
            
            return {
                'success': scheduler_started,
                'email_setup': email_setup,
                'scheduler_status': self.scheduler.get_status(),
                'message': 'Hệ thống notification đã được khởi tạo' if scheduler_started else 'Có lỗi khi khởi tạo'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Lỗi khi khởi tạo hệ thống notification: {e}'
            }
    
    def shutdown(self) -> Dict[str, Any]:
        try:
            scheduler_stopped = self.scheduler.stop()
            self._is_initialized = False
            
            return {
                'success': scheduler_stopped,
                'message': 'Hệ thống notification đã được tắt' if scheduler_stopped else 'Có lỗi khi tắt'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Lỗi khi tắt hệ thống notification: {e}'
            }
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        return self.user_interaction.process_email_setup_command(user_input)
    
    def get_system_status(self) -> Dict[str, Any]:
        return {
            'initialized': self._is_initialized,
            'scheduler': self.scheduler.get_status(),
            'email_info': self.user_interaction.get_current_email_info(),
            'notification_stats': self.db_service.get_notification_stats()
        }
    
    def setup_email(self, email: str) -> Dict[str, Any]:
        return self.user_interaction.setup_notification_email(email)

    def test_email_send(self, test_email: str) -> Dict[str, Any]:
        """Test gửi email để kiểm tra cấu hình SMTP"""
        try:
            subject = "Test Email - AI Agent Schedule Management"
            body = f"""Test
Thời gian test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Email nhận: {test_email}"""

            success = self.email_service.send_email(test_email, subject, body)
            
            return {
                'success': success,
                'message': f'Email test đã được gửi thành công đến {test_email}' if success 
                        else 'Không thể gửi email test. Kiểm tra lại cấu hình SMTP.',
                'email': test_email
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Lỗi khi gửi email test: {e}'
            }


_notification_manager = None

def get_notification_manager() -> NotificationManager:
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
