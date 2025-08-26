import random

from core.handlers.function_handler import FunctionCallHandler
from core.models.function_definitions import get_function_definitions
from core.notification import get_notification_manager
from core.services.ScheduleAdvisor import ScheduleAdvisor
from core.services.gemini_service import GeminiService
from core.exceptions import GeminiAPIError
from datetime import datetime, timedelta


def _handle_basic_greetings(user_input: str) -> str | None:
    """Xử lý các câu chào hỏi và phản hồi cơ bản một cách tự nhiên hơn."""
    user_input_lower = user_input.lower().strip()

    greetings = ["xin chào", "chào bạn", "chào", "hi", "hello", "alo"]
    how_are_you = ["bạn có khỏe không", "khỏe không", "how are you"]
    who_are_you = ["bạn là ai", "bạn tên gì", "who are you"]
    thanks = ["cảm ơn", "cám ơn", "thank you", "thanks"]
    goodbyes = ["tạm biệt", "bye", "hẹn gặp lại", "bai"]
    confirmations = ["ừ", "uk", "ok", "oke", "được rồi", "đúng rồi"]

    GREETING_RESPONSES = [
        "Chào bạn, tôi có thể giúp gì cho bạn hôm nay?",
        "Xin chào! Bạn cần hỗ trợ về lịch trình chứ?",
        "Chào bạn, tôi là trợ lý ảo sẵn sàng giúp bạn quản lý công việc."
    ]
    THANKS_RESPONSES = ["Không có gì, rất vui được hỗ trợ bạn!", "Rất hân hạnh được giúp đỡ!"]
    CONFIRMATION_RESPONSES = ["Tuyệt vời! Bạn có cần tôi hỗ trợ thêm gì không?",
                              "Đã rõ. Tôi có thể giúp gì khác cho bạn không?"]

    if any(word in user_input_lower for word in greetings):
        return random.choice(GREETING_RESPONSES)
    if any(phrase in user_input_lower for phrase in how_are_you):
        return "Cảm ơn bạn đã hỏi, tôi là một chương trình máy tính nên luôn 'khỏe'. Bạn cần giúp gì về lịch trình không?"
    if any(phrase in user_input_lower for phrase in who_are_you):
        return "Tôi là một trợ lý ảo thông minh, được tạo ra để giúp bạn quản lý lịch trình một cách hiệu quả."
    if any(word in user_input_lower for word in thanks):
        return random.choice(THANKS_RESPONSES)
    if any(word in user_input_lower for word in goodbyes):
        return "Tạm biệt bạn, hẹn gặp lại!"
    if any(word in user_input_lower for word in confirmations):
        return random.choice(CONFIRMATION_RESPONSES)
    return None


def _handle_irrelevant_input(user_input: str) -> str | None:
    user_input_lower = user_input.lower().strip()
    scheduling_keywords = [
        "lịch", "cuộc hẹn", "sự kiện", "công việc", "nhắc", "tạo", "thêm", "xóa", "sửa", "kiểm tra", "xem"
    ]
    if not any(word in user_input_lower for word in scheduling_keywords):
        return "Xin lỗi, tôi chỉ có thể hỗ trợ các vấn đề liên quan đến lịch trình."
    return None


class AIAgent:
    def __init__(self):
        self.gemini_service = GeminiService()
        self.advisor = ScheduleAdvisor(llm=self.gemini_service)
        self.function_handler = FunctionCallHandler(self.advisor)
        self.functions = get_function_definitions()
        self.notification_manager = get_notification_manager()

    def process_user_input(self, user_input: str) -> str | dict[str, str]:
        """Main processing loop for user input."""
        print(f"\n[Người dùng]: {user_input}")
        print("---------------------------------")
        print("[Hệ thống]: Đang xử lý yêu cầu...")

        # 1. Handle basic greetings
        basic_response = _handle_basic_greetings(user_input)
        if basic_response:
            return f"[Trợ lý]: {basic_response}"

        # 2. Handle special commands (e.g., email setup)
        email_command_result = self.notification_manager.process_user_input(user_input)
        if email_command_result['is_email_command']:
            return "[Trợ lý]: Lệnh email đã được xử lý."

        try:
            # 3. Call Gemini to analyze complex requests
            system_prompt = self._build_system_prompt(user_input)
            response = self.gemini_service.generate_with_timeout(system_prompt, self.functions)
            function_call = self.gemini_service.extract_function_call(response)

            if function_call:
                print(f"DEBUG: Gemini function call detected: {function_call.name}")

                # **PATCH: Kiểm tra lại dữ liệu quan trọng trước khi gọi FunctionCallHandler**
                if function_call.name == "advise_schedule":
                    args = function_call.args or {}
                    # Nếu request gốc thiếu thông tin, bỏ qua giá trị "fill" cũ -> buộc advisor hỏi tiếp
                    if not any(keyword in user_input.lower() for keyword in ["sáng", "chiều", "tối", "hôm nay", "ngày", "lúc", "thứ"]):
                        args.pop("preferred_time_of_day", None)
                        args.pop("duration", None)
                        args.pop("priority", None)
                        args.pop("preferred_date", None)
                        args.pop("preferred_weekday", None)
                        function_call.args = args

                function_response = self.function_handler.handle_function_call(function_call, user_input)
                print("Function Response:", function_response)
                return function_response
            else:
                print("DEBUG: Input seems relevant, using direct response logic...")
                return self._handle_direct_response(user_input)

        except GeminiAPIError as e:
            error_msg = f"Lỗi Gemini API: {e}"
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Lỗi hệ thống: {e}"
            print(error_msg)
            return error_msg

    def _build_system_prompt(self, user_input: str) -> str:
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        current_year = now.year
        current_weekday_index = now.weekday()

        today = now.date()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)

        weekdays_map = {
            "Thứ 2": 0, "Thứ 3": 1, "Thứ 4": 2, "Thứ 5": 3,
            "Thứ 6": 4, "Thứ 7": 5, "Chủ nhật": 6
        }

        next_weekdays = {}
        for day_name, day_index in weekdays_map.items():
            days_to_add = (day_index - current_weekday_index + 7) % 7
            next_weekdays[day_name] = today + timedelta(days=days_to_add)

        return f"""🚨 QUAN TRỌNG: Hôm nay là {current_date} (Thứ {current_weekday_index + 1}) - NĂM {current_year} 🚨

        ⚠️ LƯU Ý QUAN TRỌNG VỀ THỜI GIAN:
        - NĂM HIỆN TẠI LÀ: {current_year}
        - KHÔNG BAO GIỜ sử dụng năm 2024 hoặc năm khác!
        - TẤT CẢ thời gian phải thuộc năm {current_year}

        Đây là các mốc thời gian quan trọng để tham chiếu (NĂM {current_year}):
        - Hôm nay: {current_date}
        - Ngày mai: {tomorrow.strftime('%Y-%m-%d')}
        - Ngày kia: {day_after_tomorrow.strftime('%Y-%m-%d')}
        - Thứ 2 gần nhất: {next_weekdays['Thứ 2'].strftime('%Y-%m-%d')}
        - Thứ 3 gần nhất: {next_weekdays['Thứ 3'].strftime('%Y-%m-%d')}
        - Thứ 4 gần nhất: {next_weekdays['Thứ 4'].strftime('%Y-%m-%d')}
        - Thứ 5 gần nhất: {next_weekdays['Thứ 5'].strftime('%Y-%m-%d')}
        - Thứ 6 gần nhất: {next_weekdays['Thứ 6'].strftime('%Y-%m-%d')}
        - Thứ 7 gần nhất: {next_weekdays['Thứ 7'].strftime('%Y-%m-%d')}
        - Chủ nhật gần nhất: {next_weekdays['Chủ nhật'].strftime('%Y-%m-%d')}

        Phân tích yêu cầu và gọi function phù hợp:
        - Nếu user muốn TƯ VẤN/KIỂM TRA thời gian → advise_schedule
        - Nếu user muốn THÊM LỊCH với thời gian cụ thể → smart_add_schedule 
        - Nếu user muốn THÊM LỊCH nhưng chưa rõ thời gian → advise_schedule TRƯỚC
        - Xem danh sách lịch → get_schedules
        - Cập nhật lịch → update_schedule (cần schedule_id)
        - Xóa lịch → delete_schedule (cần schedule_id)

        🎯 QUY TẮC XỬ LÝ THỜI GIAN:
        - LUÔN sử dụng các mốc tham chiếu ở trên
        - KHÔNG BAO GIỜ tự tạo thời gian năm 2024!
        - Ưu tiên dùng smart_add_schedule cho yêu cầu thêm lịch

        Yêu cầu: {user_input}"""

    def _handle_direct_response(self, user_input: str) -> str:
        result = self.advisor.advise_schedule(user_input)
        formatted_response = self.advisor.format_response(result)
        print("Direct Response:")
        print(formatted_response)
        return formatted_response
