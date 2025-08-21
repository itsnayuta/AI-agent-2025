import random
from datetime import datetime, timedelta


# --- Mock-up Classes (Giả lập các dịch vụ bên ngoài để code có thể chạy) ---
# Trong dự án thật, bạn sẽ import các lớp này từ các file tương ứng.

class MockFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class GeminiService:
    def generate_with_timeout(self, prompt, functions):
        if any(keyword in prompt.lower() for keyword in ["thêm", "đặt lịch", "tạo"]):
            print("DEBUG: Gemini is generating a function call...")
            # Trích xuất title và description một cách đơn giản để giả lập
            parts = prompt.split("vào lúc")[0].replace("Yêu cầu:", "").strip().split(" ")
            title = " ".join(parts[:2])  # Giả sử 2 từ đầu là title
            description = " ".join(parts[2:])  # Phần còn lại là description
            return {
                "function_call": MockFunctionCall("smart_add_schedule", {"title": title, "description": description})}
        # Mặc định không gọi function
        print("DEBUG: Gemini is not generating a function call.")
        return {"text": "Đây là phản hồi văn bản từ Gemini."}

    def extract_function_call(self, response):
        return response.get("function_call")


class FunctionCallHandler:
    def handle_function_call(self, function_call, user_input):
        if function_call.name == "smart_add_schedule":
            title = function_call.args.get('title', 'Không có tiêu đề')
            description = function_call.args.get('description', '')
            # Giả lập thêm lịch thành công
            return f"✓ Đã thêm lịch thành công: '{title}' với mô tả '{description}'."
        return f"Đã thực thi hàm {function_call.name}."


class ScheduleAdvisor:
    def advise_schedule(self, user_input):
        return f"Đây là lời khuyên cho yêu cầu: '{user_input}'"

    def format_response(self, result):
        return f"🤖 Lời khuyên của Trợ lý: {result}"


class NotificationManager:
    def process_user_input(self, user_input):
        if "thiết lập email" in user_input.lower():
            # Giả lập xử lý thành công
            return {'is_email_command': True, 'success': True, 'message': 'Đã thiết lập email thành công.'}
        return {'is_email_command': False}


def get_function_definitions():
    # Trả về một danh sách các định nghĩa hàm (giả lập)
    return ["smart_add_schedule", "get_schedules", "update_schedule", "delete_schedule"]


def get_notification_manager():
    return NotificationManager()


class GeminiAPIError(Exception):
    pass


# --- Main AI Agent Class ---

class AIAgent:
    def __init__(self):
        """Khởi tạo các dịch vụ cần thiết cho Agent."""
        self.gemini_service = GeminiService()
        self.function_handler = FunctionCallHandler()
        self.functions = get_function_definitions()
        self.advisor = ScheduleAdvisor()
        self.notification_manager = get_notification_manager()

    def process_user_input(self, user_input: str) -> str:
        """
        Luồng xử lý chính cho mọi đầu vào của người dùng.
        """
        print(f"\n[Người dùng]: {user_input}")
        print("---------------------------------")
        print("[Hệ thống]: Đang xử lý yêu cầu...")

        # 1. Xử lý các câu giao tiếp cơ bản để phản hồi nhanh
        basic_response = self._handle_basic_greetings(user_input)
        if basic_response:
            return f"[Trợ lý]: {basic_response}"

        # 2. Kiểm tra xem có phải lệnh đặc biệt (ví dụ: thiết lập email) không
        email_command_result = self.notification_manager.process_user_input(user_input)
        if email_command_result['is_email_command']:
            if email_command_result['success']:
                return f"[Trợ lý]: ✓ {email_command_result['message']}"
            else:
                return f"[Trợ lý]: {email_command_result['message']}"

        try:
            # 3. Gọi Gemini để xử lý các yêu cầu phức tạp cần phân tích
            system_prompt = self._build_system_prompt(user_input)
            response = self.gemini_service.generate_with_timeout(system_prompt, self.functions)
            function_call = self.gemini_service.extract_function_call(response)

            if function_call:
                print(f"DEBUG: Gemini function call detected.")
                print(f"  - Function: {function_call.name}")
                print(f"  - Args: {dict(function_call.args) if hasattr(function_call, 'args') else 'No args'}")

                function_response = self.function_handler.handle_function_call(function_call, user_input)
                return f"[Trợ lý]: {function_response}"
            else:
                print("DEBUG: Gemini không gọi function, kiểm tra tính liên quan...")
                irrelevant_response = self._handle_irrelevant_input(user_input)
                if irrelevant_response:
                    return f"[Trợ lý]: {irrelevant_response}"

                print("DEBUG: Input có vẻ liên quan, sử dụng logic tư vấn trực tiếp...")
                return self._handle_direct_response(user_input)

        except GeminiAPIError as e:
            error_msg = f"Lỗi Gemini API: {e}"
            print(f"[Lỗi]: {error_msg}")
            return f"[Trợ lý]: Rất tiếc, đã có lỗi xảy ra với dịch vụ AI. Vui lòng thử lại sau."
        except Exception as e:
            error_msg = f"Lỗi hệ thống không xác định: {e}"
            print(f"[Lỗi]: {error_msg}")
            return f"[Trợ lý]: Rất tiếc, hệ thống đã gặp lỗi. Vui lòng thử lại."

    def _build_system_prompt(self, user_input: str) -> str:
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')

        return f"""QUAN TRỌNG: Hôm nay là {current_date}.
        Phân tích yêu cầu và gọi function phù hợp.
        Yêu cầu: {user_input}"""

    def _handle_direct_response(self, user_input: str) -> str:
        result = self.advisor.advise_schedule(user_input)
        formatted_response = self.advisor.format_response(result)
        return formatted_response

    def _handle_basic_greetings(self, user_input: str) -> str | None:
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

    def _handle_irrelevant_input(self, user_input: str) -> str | None:
        user_input_lower = user_input.lower().strip()

        scheduling_keywords = [
            "lịch", "lịch trình", "cuộc hẹn", "sự kiện", "công việc", "kế hoạch",
            "nhắc", "đặt", "tạo", "thêm", "xóa", "sửa", "cập nhật", "hủy",
            "kiểm tra", "xem", "tìm", "liệt kê", "tư vấn", "gợi ý",
            "hôm nay", "ngày mai", "ngày kia", "tuần này", "tuần sau", "tháng này",
            "thứ hai", "thứ ba", "giờ", "phút"
        ]

        is_relevant = any(word in user_input_lower for word in scheduling_keywords)

        if not is_relevant:
            irrelevant_responses = [
                "Xin lỗi, tôi chưa hiểu rõ yêu cầu của bạn. Chuyên môn của tôi là hỗ trợ quản lý lịch trình. Bạn có muốn đặt một lịch hẹn không?",
                "Tôi có thể chưa được lập trình để xử lý yêu cầu này. Bạn có thể thử yêu cầu tôi 'thêm lịch đi khám răng vào 3 giờ chiều mai' không?",
                "Rất tiếc, tôi chỉ có thể giúp bạn các vấn đề liên quan đến lịch trình, cuộc hẹn và công việc. Bạn cần tôi giúp gì trong phạm vi này không?"
            ]
            return random.choice(irrelevant_responses)
        return None

