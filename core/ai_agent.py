from core.handlers.function_handler import FunctionCallHandler
from core.models.function_definitions import get_function_definitions
from core.notification import get_notification_manager
from core.services.ScheduleAdvisor import ScheduleAdvisor
from core.services.gemini_service import GeminiService
from core.services.conversation_service import ConversationService
from core.config import Config
from core.exceptions import GeminiAPIError
from datetime import datetime, timedelta

class AIAgent:
    def __init__(self, session_id: str = 'default'):
        self.session_id = session_id
        self.gemini_service = GeminiService()
        self.advisor = ScheduleAdvisor(llm=self.gemini_service)
        self.function_handler = FunctionCallHandler(self.advisor)
        self.functions = get_function_definitions()
        self.notification_manager = get_notification_manager()
        self.conversation_service = ConversationService()

        self._load_conversation_context()

    def _load_conversation_context(self):
        """Load conversation context khi agent khởi động."""
        stats = self.conversation_service.get_session_stats(self.session_id)
        if stats['total_messages'] > 0:
            print(f"[AI Agent] Đã tải {stats['total_messages']} tin nhắn từ session trước")
        else:
            print(f"[AI Agent] Bắt đầu session mới: {self.session_id}")

    async def process_user_input(self, user_input: str) -> str | dict[str, str]:
        """Main processing loop for user input."""
        print(f"\n[Người dùng]: {user_input}")
        print("---------------------------------")
        print("[Hệ thống]: Đang xử lý yêu cầu...")

        # 1. Lưu user input vào conversation history
        self.conversation_service.add_user_message(user_input, self.session_id)

        # 2. Handle special commands (e.g., email setup)
        email_command_result = self.notification_manager.process_user_input(user_input)
        if email_command_result['is_email_command']:
            response = "[Trợ lý]: Lệnh email đã được xử lý."
            self.conversation_service.add_assistant_message(response, session_id=self.session_id)
            return response

        try:
            # 2.5. Check if question can be answered from context
            if self._can_answer_from_context(user_input):
                context_response = self._answer_from_context(user_input)
                if context_response:
                    self.conversation_service.add_assistant_message(context_response, session_id=self.session_id)
                    return context_response

            # 3. Call Gemini to analyze complex requests
            system_prompt = self._build_system_prompt(user_input)
            response = self.gemini_service.generate_with_timeout(system_prompt, self.functions)
            function_call = self.gemini_service.extract_function_call(response)

            if function_call:
                # Kiểm tra lại dữ liệu quan trọng trước khi gọi FunctionCallHandler
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
                if function_call.name in ["update_schedule", "delete_schedule"]:
                    args = function_call.args or {}
                    schedule_id = function_call.args.get("schedule_id") if function_call.args else None
                    if schedule_id is None or str(schedule_id) == "123.0":
                    # Trả về câu hỏi yêu cầu người dùng cung cấp ID
                        args.pop("schedule_id", None)
                        function_call.args = args
                        response = "[Trợ lý]: Xin vui lòng cung cấp ID của lịch trình bạn muốn cập nhật/xóa."
                        self.conversation_service.add_assistant_message(response, session_id=self.session_id)
                        return response

                function_response = await self.function_handler.handle_function_call(function_call, user_input)
                
                # Xử lý hành động thoát
                if isinstance(function_response, dict) and function_response.get('action') == 'exit':
                    # Lưu exit message vào conversation history
                    self.conversation_service.add_assistant_message(
                        content=function_response.get('message', 'Tạm biệt!'),
                        session_id=self.session_id
                    )
                    return function_response
                
                # Chuyển đổi function_call thành dict có thể serialize
                function_call_dict = {
                    'name': function_call.name,
                    'args': dict(function_call.args) if function_call.args else {}
                }
                
                # Xử lý các kiểu phản hồi khác nhau
                response_content = function_response
                if isinstance(function_response, dict):
                    response_content = function_response.get('message', str(function_response))
                
                self.conversation_service.add_assistant_message(
                    content=str(response_content),
                    function_call=function_call_dict,
                    session_id=self.session_id
                )
                
                return function_response
            else:
                response = self._handle_direct_response(user_input)

                self.conversation_service.add_assistant_message(str(response), session_id=self.session_id)
                return response

        except GeminiAPIError as e:
            error_msg = f"Lỗi Gemini API: {e}"
            self.conversation_service.add_assistant_message(error_msg, session_id=self.session_id)
            return error_msg
        except Exception as e:
            error_msg = f"Lỗi hệ thống: {e}"
            self.conversation_service.add_assistant_message(error_msg, session_id=self.session_id)
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

        # Lấy conversation context
        conversation_context = self.conversation_service.get_recent_context(
            session_id=self.session_id, 
            last_n_messages=Config.CONTEXT_WINDOW_SIZE
        )

        return f"""QUAN TRỌNG: Hôm nay là {current_date} (Thứ {current_weekday_index + 1}) - NĂM {current_year} 🚨

        LƯU Ý QUAN TRỌNG VỀ THỜI GIAN:
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

        LỊCH SỬ TRÒ CHUYỆN VÀ NGỮ CẢNH:
        {conversation_context}

        HƯỚNG DẪN QUAN TRỌNG VỀ TRÍ NHỚ:
        - BẠN LÀ AI AGENT CÓ TRÍ NHỚ LIÊN TỤC - KHÔNG PHẢI CUỘC TRÒ CHUYỆN MỚI!
        - HÃY ĐỌC KỸ toàn bộ lịch sử trò chuyện ở trên trước khi trả lời
        - QUAN TRỌNG: Nếu trong lịch sử có "👤 Người dùng: xin chào tôi tên là [TÊN]" thì BẠN ĐÃ BIẾT TÊN ĐÓ!
        - Nếu user đã giới thiệu TÊN, SỞ THÍCH, THÓI QUEN → HÃY NHỚ và SỬ DỤNG NGAY
        - Nếu có cuộc trò chuyện trước → TIẾP TỤC từ ngữ cảnh đó, ĐỪNG hỏi lại thông tin đã biết
        - Trả lời như một người BẠN ĐÃ QUEN BIẾT, không phải người lạ
        - Tham chiếu đến các lịch trình đã tạo hoặc thảo luận trước đó

        VÍ DỤ CÁCH ĐỌC NGỮ CẢNH:
        - Nếu thấy "Người dùng: xin chào tôi tên là Long" → TÊN LÀ LONG
        - Nếu thấy "Người dùng: tôi thích đọc sách" → SỞ THÍCH LÀ ĐỌC SÁCH
        - Nếu thấy "Tiêu đề: Họp team" → ĐÃ TẠO LỊCH HỌP TEAM

        QUY TẮC GỌI CHỨC NĂNG:
        - CHỈ gọi chức năng khi THỰC SỰ CẦN thiết để thực hiện hành động cụ thể
        - VÍ DỤ: "bạn biết tên tôi không?" → TRẢ LỜI TRỰC TIẾP từ lịch sử, KHÔNG gọi chức năng
        - CHỈ gọi chức năng khi cần thực hiện hành động: thêm/xóa/sửa lịch, tư vấn thời gian, v.v.

        Phân tích yêu cầu và gọi chức năng phù hợp:
        - Nếu người dùng muốn THOÁT/KẾT THÚC (exit, quit, thoát, bye) → handle_greeting_goodbye với is_exit=true
        - Nếu người dùng CHÀO HỎI LẦN ĐẦU, CẢM ƠN → handle_greeting_goodbye
        - Nếu người dùng HỎI THÔNG TIN ĐÃ CÓ TRONG NGỮ CẢNH → TRẢ LỜI TRỰC TIẾP, không gọi chức năng
        - Nếu người dùng muốn TƯ VẤN/KIỂM TRA thời gian → advise_schedule
        - Nếu người dùng muốn THÊM LỊCH với thời gian cụ thể → smart_add_schedule 
        - Nếu người dùng muốn THÊM LỊCH nhưng chưa rõ thời gian → advise_schedule TRƯỚC
        - Xem danh sách lịch → get_schedules
        - Cập nhật lịch → update_schedule (cần schedule_id)
        - Xóa lịch → delete_schedule (cần schedule_id)

        QUY TẮC XỬ LÝ:
        - LUÔN sử dụng các mốc tham chiếu thời gian ở trên
        - KHÔNG BAO GIỜ tự tạo thời gian năm 2024!
        - Ưu tiên dùng smart_add_schedule cho yêu cầu thêm lịch
        - QUAN TRỌNG: Dựa vào lịch sử trò chuyện để hiểu người dùng tốt hơn
        - Sử dụng thông tin cá nhân đã biết (tên, thói quen, sở thích)
        - Đề cập đến các cuộc trò chuyện hoặc lịch trình trước nếu liên quan

        Yêu cầu hiện tại: {user_input}"""

    def _can_answer_from_context(self, user_input: str) -> bool:
        """Kiểm tra xem câu hỏi có thể trả lời từ context không."""
        context_questions = [
            "biết tên tôi", "tên tôi là gì", "tôi tên gì", 
            "nhớ tên", "tên của tôi", "ai tôi là",
            "nhớ kĩ tên", "hãy nhớ tên", "tên tôi là"
        ]
        
        return any(q in user_input.lower() for q in context_questions)

    def _answer_from_context(self, user_input: str) -> str:
        """Trả lời câu hỏi dựa trên context có sẵn."""
        # Lấy context từ conversation history
        context = self.conversation_service.get_recent_context(
            session_id=self.session_id, 
            last_n_messages=Config.CONTEXT_WINDOW_SIZE
        )
        
        # Nếu user đang giới thiệu hoặc nhắc nhở về tên
        if any(phrase in user_input.lower() for phrase in ["tên tôi là", "nhớ kĩ tên", "hãy nhớ tên"]):
            import re
            # Tìm tên trong câu hiện tại
            name_match = re.search(r"tên (?:tôi là|là) (\w+)", user_input, re.IGNORECASE)
            if name_match:
                name = name_match.group(1)
                return f"Dạ, tôi đã ghi nhớ tên của bạn là {name}! Rất vui được làm quen với bạn, {name}. Tôi có thể giúp gì về lập lịch cho bạn không?"
        
        # Tìm tên trong context cho câu hỏi về tên
        if "biết tên" in user_input.lower() or "tên tôi" in user_input.lower():
            # Tìm pattern "tên là [Tên]" trong context
            import re
            name_patterns = [
                r"tên (?:là|tôi là) (\w+)",
                r"tôi (?:là|tên) (\w+)",
                r"chào (?:tôi tên là|mình là) (\w+)",
                r"nhớ (?:kĩ )?tên (?:tôi là|là) (\w+)"
            ]
            
            for pattern in name_patterns:
                matches = re.findall(pattern, context, re.IGNORECASE)
                if matches:
                    name = matches[-1]  # Lấy tên gần nhất
                    return f"Dạ, tôi nhớ bạn tên là {name}! Bạn cần giúp gì về lập lịch không?"
            
            return "Xin lỗi, tôi chưa thấy bạn giới thiệu tên trong cuộc trò chuyện này. Bạn có thể cho tôi biết tên của bạn không?"
        
        return None

    def _handle_direct_response(self, user_input: str) -> str:
        result = self.advisor.advise_schedule(user_input)
        formatted_response = self.advisor.format_response(result)
        return formatted_response

    def get_conversation_history(self, limit: int = None) -> list:
        """Lấy lịch sử conversation của session hiện tại."""
        return self.conversation_service.get_conversation_history(self.session_id, limit)
    
    def clear_conversation_history(self) -> int:
        """Xóa toàn bộ lịch sử conversation của session hiện tại."""
        deleted_count = self.conversation_service.clear_session(self.session_id)
        print(f"[AI Agent] Đã xóa {deleted_count} tin nhắn khỏi session {self.session_id}")
        return deleted_count
    
    def get_conversation_stats(self) -> dict:
        """Lấy thống kê conversation của session hiện tại."""
        return self.conversation_service.get_session_stats(self.session_id)
    
    def search_conversation(self, query: str, limit: int = 10) -> list:
        """Tìm kiếm trong lịch sử conversation."""
        return self.conversation_service.search_conversations(query, self.session_id, limit)
    
    def switch_session(self, new_session_id: str):
        """Chuyển sang session khác."""
        old_session = self.session_id
        self.session_id = new_session_id
        self._load_conversation_context()
        print(f"[AI Agent] Đã chuyển từ session '{old_session}' sang '{new_session_id}'")
    
    def export_conversation(self) -> str:
        """Export conversation history thành text."""
        history = self.get_conversation_history()
        if not history:
            return "Chưa có lịch sử conversation nào."
        
        lines = []
        lines.append(f"=== LỊCH SỬ CUỘC TRÒ CHUYỆN - SESSION: {self.session_id} ===")
        lines.append("")
        
        for msg in history:
            role = "Người dùng" if msg['role'] == 'user' else "Trợ lý"
            timestamp = msg['created_at']
            lines.append(f"[{timestamp}] {role}:")
            lines.append(f"{msg['content']}")
            
            if msg['function_call']:
                func_name = msg['function_call'].get('name', 'Unknown')
                lines.append(f"Function: {func_name}")
            
            lines.append("")
        
        return "\n".join(lines)
