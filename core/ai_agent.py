# Main AI Agent class
from datetime import datetime
from core.services.gemini_service import GeminiService
from core.handlers.function_handler import FunctionCallHandler
from core.models.function_definitions import get_function_definitions
from core.services.ScheduleAdvisor import ScheduleAdvisor
from core.exceptions import GeminiAPIError


class AIAgent:
    def __init__(self):
        self.gemini_service = GeminiService()
        self.function_handler = FunctionCallHandler()
        self.functions = get_function_definitions()
        self.advisor = ScheduleAdvisor()
    
    def process_user_input(self, user_input: str) -> str:
        """Process user input and return response"""
        print("🔄 Đang xử lý yêu cầu...")
        
        try:
            system_prompt = self._build_system_prompt(user_input)
            response = self.gemini_service.generate_with_timeout(system_prompt, self.functions)
            
            function_call = self.gemini_service.extract_function_call(response)
            
            if function_call:
                print(f"🔍 DEBUG Gemini function call:")
                print(f"   Function: {function_call.name}")
                print(f"   Args: {dict(function_call.args) if hasattr(function_call, 'args') else 'No args'}")
                
                function_response = self.function_handler.handle_function_call(function_call, user_input)
                print("🤖 Gemini AI Response:")
                print(function_response)
                return function_response
            else:
                print("📋 Gemini không gọi function, sử dụng logic trực tiếp...")
                return self._handle_direct_response(user_input)
                
        except GeminiAPIError as e:
            error_msg = f"❌ Lỗi Gemini API: {e}"
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"❌ Lỗi hệ thống: {e}"
            print(error_msg)
            return error_msg
    
    def _build_system_prompt(self, user_input: str) -> str:
        """Build system prompt for Gemini AI"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        return f"""QUAN TRỌNG: Hôm nay là {current_date} (Thứ {datetime.now().weekday() + 1}).

            Phân tích yêu cầu và gọi function phù hợp:
            - Nếu user muốn TƯ VẤN/KIỂM TRA thời gian → advise_schedule
            - Nếu user muốn THÊM LỊCH với thời gian cụ thể → smart_add_schedule 
            - Nếu user muốn THÊM LỊCH nhưng chưa rõ thời gian → advise_schedule TRƯỚC
            - Xem danh sách lịch → get_schedules
            - Cập nhật lịch → update_schedule (cần schedule_id)
            - Xóa lịch → delete_schedule (cần schedule_id)

            LƯU Ý: 
            - Thứ 7 tuần này = 2025-08-09
            - Chủ nhật tuần này = 2025-08-10
            - KHÔNG tự tạo thời gian năm 2024!
            - Ưu tiên dùng smart_add_schedule cho yêu cầu thêm lịch

            Yêu cầu: {user_input}"""
    
    def _handle_direct_response(self, user_input: str) -> str:
        """Handle direct response when no function is called"""
        result = self.advisor.advise_schedule(user_input)
        formatted_response = self.advisor.format_response(result)
        print("🤖 Direct Response:")
        print(formatted_response)
        return formatted_response
