import random

from core.handlers.function_handler import FunctionCallHandler
from core.models.function_definitions import get_function_definitions
from core.notification import get_notification_manager
from core.services.ScheduleAdvisor import ScheduleAdvisor
from core.services.gemini_service import GeminiService


def _build_system_prompt(user_input: str) -> str:
    # This prompt is simplified for clarity
    return f"Phân tích yêu cầu và gọi function phù hợp. Yêu cầu: {user_input}"


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
        self.function_handler = FunctionCallHandler()
        self.functions = get_function_definitions()
        self.advisor = ScheduleAdvisor()
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
        # This part is simplified as it's not the main issue
        email_command_result = self.notification_manager.process_user_input(user_input)
        if email_command_result['is_email_command']:
            return "[Trợ lý]: Lệnh email đã được xử lý."

        try:
            # 3. Call Gemini to analyze complex requests
            system_prompt = _build_system_prompt(user_input)
            response = self.gemini_service.generate_with_timeout(system_prompt, self.functions)
            function_call = self.gemini_service.extract_function_call(response)

            if function_call:
                print(f"DEBUG: Gemini function call detected: {function_call.name}")
                function_response = self.function_handler.handle_function_call(function_call, user_input)
                return function_response
            else:
                print("DEBUG: Input seems relevant, using direct response logic...")
                return self._handle_direct_response(user_input)

        except Exception as e:
            error_msg = f"Lỗi hệ thống không xác định: {e}"
            print(f"[Lỗi]: {error_msg}")
            return f"[Trợ lý]: Rất tiếc, hệ thống đã gặp lỗi. Vui lòng thử lại."

    def _handle_direct_response(self, user_input: str) -> str:
        result = self.advisor.advise_schedule(user_input)
        return self.advisor.format_response(result)

