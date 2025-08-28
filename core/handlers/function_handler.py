from datetime import datetime, timedelta
import re
from typing import Dict

from core.models.function_definitions import get_function_definitions
from core.services.ScheduleAdvisor import ScheduleAdvisor
from core.services.ExecuteSchedule import ExecuteSchedule
from core.notification import get_notification_manager
from core.services.gemini_service import GeminiService
from utils.timezone_utils import parse_time_to_vietnam, vietnam_isoformat, get_vietnam_now

class FunctionCallHandler:
    def __init__(self, advisor: ScheduleAdvisor = None):
        self.advisor = advisor or ScheduleAdvisor()
        self.notification_manager = get_notification_manager()
        self.functions = get_function_definitions()
        self.agent = GeminiService()

    async def handle_function_call(self, call, user_input: str) -> str | dict:
        """Xử lý các hàm cho Agent AI"""
        name = call.name
        args = call.args if hasattr(call, 'args') else {}

        executor = None

        try:
            if name == "advise_schedule":
                return await self._handle_advise_schedule(args, user_input)
            elif name == "handle_greeting_goodbye":
                return self._handle_greeting_goodbye(args)
            elif name == "handle_off_topic_query":
                return self._handle_off_topic_query(args)

            # Cho tất cả các chức năng khác tương tác với database
            executor = ExecuteSchedule()
            if name == "smart_add_schedule":
                return self._handle_smart_add_schedule(args, user_input, executor)
            elif name == "get_schedules":
                return self._handle_get_schedules(args,executor)
            elif name == "update_schedule":
                return self._handle_update_schedule(args, executor)
            elif name == "delete_schedule":
                return self._handle_delete_schedule(args, executor)
            elif name == "setup_notification_email":
                return self._handle_setup_notification_email(args)
            else:
                return "Chức năng không hỗ trợ."
        except Exception as e:
            return f"Lỗi khi thực hiện: {str(e)}"
        finally:
            if executor:
                executor.close()

    def _handle_greeting_goodbye(self, args: Dict) -> str:
        """Handles basic conversational turns by generating a dynamic AI response."""
        user_message = args.get('message', 'chào bạn')

        prompt = f"""You are a friendly scheduling assistant. 
        The user has said something conversational (like a greeting, thanks, or a simple question). 
        Respond naturally, briefly, and in Vietnamese.
        User's message: "{user_message}"
        """
        try:
            # Call the LLM for a text-only response
            response = self.agent.get_ai_response(prompt)
            text_response = self.agent.format_response(response)
            return text_response or "Chào bạn, tôi có thể giúp gì cho bạn?"
        except Exception as e:
            print(f"Error in _handle_greeting_goodbye: {e}")
            return "Chào bạn! Tôi sẵn sàng giúp bạn lập lịch."

    # **MODIFIED METHOD**
    def _handle_off_topic_query(self, args: Dict) -> str:
        """Handles off-topic queries by generating a polite, redirecting AI response."""
        user_query = args.get('query', '')

        prompt = f"""You are a helpful AI assistant focused on scheduling tasks. 
        The user has asked something off-topic. 
        Politely state that you can only handle scheduling-related requests and gently guide them back. 
        Respond briefly and in Vietnamese.
        User's off-topic query: "{user_query}"
        """
        try:
            # Call the LLM for a text-only response
            response = self.agent.get_ai_response(prompt)
            text_response = self.agent.format_response(response)
            return text_response or "Xin lỗi, tôi chỉ có thể hỗ trợ các vấn đề liên quan đến lịch trình."
        except Exception as e:
            print(f"Error in _handle_off_topic_query: {e}")
            return "Xin lỗi, chuyên môn của tôi là về lịch trình. Bạn cần giúp gì về việc đó không?"

    async def _handle_advise_schedule(self, args: Dict, user_input: str) -> str:
        """Xử lý tư vấn lịch với Gemini AI thông minh"""
        user_request = args.get('user_request', user_input)
        
        # Enable tính năng mới
        if True:
            try:
                # Đảm bảo advisor có llm
                if not self.advisor.llm and hasattr(self, 'agent'):
                    self.advisor.llm = self.agent
                
                # Sử dụng tư vấn thông minh mới
                intelligent_response = await self.advisor.intelligent_schedule_advice(user_request)
                if intelligent_response and len(intelligent_response.strip()) > 0:
                    return intelligent_response
            except Exception as e:
                print(f"Lỗi khi sử dụng tư vấn thông minh: {e}")
        
        try:
            preferred_time_of_day = args.get('preferred_time_of_day')
            duration = args.get('duration')
            priority = args.get('priority')
            preferreddate = args.get('preferred_date')
            preferred_weekday = args.get('preferred_weekday')
            result = self.advisor.advise_schedule(
                user_request=user_request,
                preferred_time_of_day=preferred_time_of_day,
                duration=duration,
                priority=priority,
                preferred_date=preferreddate,
                preferred_weekday=preferred_weekday
            )
            return self.advisor.format_response(result)
        except Exception as e:
            return f"Lỗi: {str(e)}"

    def _handle_smart_add_schedule(self, args: Dict, user_input: str, executor: ExecuteSchedule) -> str:
        """Xử lý thêm lịch thông minh"""
        user_request = args.get('user_request', user_input)

        # 1. Ưu tiên sử dụng thời gian từ Gemini nếu có
        start_time_str = args.get('start_time')
        end_time_str = args.get('end_time')

        if start_time_str:
            # Gemini đã parse được thời gian

            try:
                start_time_vn = parse_time_to_vietnam(start_time_str)
                current_year = get_vietnam_now().year

                # Nếu năm không đúng, sửa lại
                if start_time_vn.year != current_year:
                    start_time_vn = start_time_vn.replace(year=current_year)
                    start_time_str = vietnam_isoformat(start_time_vn)

                if not end_time_str:
                    # Tính toán end_time dựa trên start_time
                    end_time_vn = start_time_vn + timedelta(hours=1)  # Mặc định 1 giờ
                    end_time_str = vietnam_isoformat(end_time_vn)
                else:
                    # Kiểm tra end_time cũng
                    end_time_vn = parse_time_to_vietnam(end_time_str)
                    if end_time_vn.year != current_year:
                        end_time_vn = end_time_vn.replace(year=current_year)
                        end_time_str = vietnam_isoformat(end_time_vn)

            except Exception as e:
                start_time_str = None
        else:
            # Fallback: Phân tích thời gian từ input thông qua ScheduleAdvisor
            advisor_result = self.advisor.advise_schedule(user_request)

            if 'suggested_time' not in advisor_result:
                return "Không thể phân tích thời gian từ yêu cầu của bạn."

            suggested_time = advisor_result['suggested_time']

            from utils.timezone_utils import get_vietnam_time, vietnam_isoformat
            suggested_time_vn = get_vietnam_time(suggested_time)
            end_time = self._calculate_end_time(user_request, suggested_time_vn)
            end_time_vn = get_vietnam_time(end_time)

            start_time_str = vietnam_isoformat(suggested_time_vn)
            end_time_str = vietnam_isoformat(end_time_vn)

        # 2. Trích xuất thông tin khác
        title = args.get('title', user_request)
        description = args.get('description', '')
        if not description:
            description = title

        # 3. Thêm vào database
        result = executor.add_schedule(title, description, start_time_str, end_time_str)
        return result

    def _handle_get_schedules(self, args: Dict, executor: 'ExecuteSchedule') -> dict:
        """Xử lý yêu cầu lấy danh sách lịch theo ngày, tháng, năm hoặc tất cả."""
        date_str = args.get('date')  # YYYY-MM-DD
        month = args.get('month')  # 1-12
        year = args.get('year')  # YYYY

        try:
            if date_str:
                schedules = executor.get_schedules_by_date(date_str)
                message = f"Danh sách lịch cho ngày {date_str}:"
            elif year and month:
                schedules = executor.get_schedules_by_month(year, int(month))
                message = f"Danh sách lịch cho tháng {month}/{year}:"
            elif year:
                schedules = executor.get_schedules_by_year(year)
                message = f"Danh sách lịch cho năm {year}:"
            else:
                schedules = executor.get_schedules()
                message = "Đây là tất cả các lịch của bạn:"

            if not schedules:
                return {
                    "message": "Không tìm thấy lịch nào phù hợp.",
                    "schedules": []
                }

            schedule_list = [
                {
                    "id": s[0],
                    "title": s[1],
                    "description": s[2],
                    "start_time": s[3],
                    "end_time": s[4]
                } for s in schedules
            ]

            return {
                "message": message,
                "schedules": schedule_list
            }
        except Exception as e:
            return {"message": f"Đã xảy ra lỗi khi lấy lịch: {e}", "schedules": []}

    def _handle_update_schedule(self, args: Dict, executor: 'ExecuteSchedule') -> str:
        """Xử lý yêu cầu cập nhật lịch"""
        schedule_id = args.get('schedule_id')
        if not schedule_id:
            return "Thiếu ID lịch cần cập nhật."

        title = args.get('title')
        description = args.get('description')
        start_time = args.get('start_time')
        end_time = args.get('end_time')

        result = executor.update_schedule(schedule_id, title, description, start_time, end_time)
        return result

    def _handle_delete_schedule(self, args: Dict, executor: 'ExecuteSchedule') -> str:
        """Xử lý yêu cầu xóa lịch"""
        schedule_id = args.get('schedule_id')
        if not schedule_id:
            return "Thiếu ID lịch cần xóa."

        result = executor.delete_schedule(schedule_id)
        return result

    def _handle_setup_notification_email(self, args: Dict) -> str:
        """Xử lý thiết lập email nhận thông báo"""
        email = args.get('email')
        if not email:
            return "Thiếu địa chỉ email."

        result = self.notification_manager.setup_email(email)
        if result['success']:
            return f"Đã thiết lập email nhận thông báo: {email}"
        else:
            return f"Lỗi khi thiết lập email: {result['message']}"

    def _calculate_end_time(self, user_request: str, suggested_time: datetime):
        """Tính toán thời gian kết thúc dựa trên thời lượng trong yêu cầu"""
        duration_match = re.search(r'(\d+)\s*(tiếng|giờ|phút)', user_request)
        if duration_match:
            duration_num = int(duration_match.group(1))
            duration_unit = duration_match.group(2)
            if 'tiếng' in duration_unit or 'giờ' in duration_unit:
                return suggested_time + timedelta(hours=duration_num)
            else:
                return suggested_time + timedelta(minutes=duration_num)
        else:
            return suggested_time + timedelta(hours=1)