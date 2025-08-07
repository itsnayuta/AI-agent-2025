# Function call handler
import re
from typing import Dict, Any, Optional
from core.services.ScheduleAdvisor import ScheduleAdvisor
from core.services.ExecuteSchedule import ExecuteSchedule
from core.exceptions import ValidationError, DatabaseError


class FunctionCallHandler:
    def __init__(self):
        self.advisor = ScheduleAdvisor()
    
    def handle_function_call(self, call, user_input: str) -> str:
        """Xử lý các hàm cho Agent AI"""
        name = call.name
        args = call.args if hasattr(call, 'args') else {}
        
        executor = ExecuteSchedule()
        
        try:
            if name == "advise_schedule":
                return self._handle_advise_schedule(args, user_input)
            elif name == "smart_add_schedule":
                return self._handle_smart_add_schedule(args, user_input, executor)
            elif name == "get_schedules":
                return self._handle_get_schedules(executor)
            elif name == "update_schedule":
                return self._handle_update_schedule(args, executor)
            elif name == "delete_schedule":
                return self._handle_delete_schedule(args, executor)
            else:
                return "❌ Chức năng không hỗ trợ."
        except Exception as e:
            return f"❌ Lỗi khi thực hiện: {str(e)}"
        finally:
            executor.close()
    
    def _handle_advise_schedule(self, args: Dict, user_input: str) -> str:
        """Xử lý tư vấn lịch"""
        user_request = args.get('user_request', user_input)
        result = self.advisor.advise_schedule(user_request)
        return self.advisor.format_response(result)
    
    def _handle_smart_add_schedule(self, args: Dict, user_input: str, executor: ExecuteSchedule) -> str:
        """Xử lý thêm lịch thông minh"""
        user_request = args.get('user_request', user_input)
        
        print(f"🔍 DEBUG smart_add_schedule:")
        print(f"   user_request: {user_request}")
        
        # 1. Phân tích thời gian từ input
        advisor_result = self.advisor.advise_schedule(user_request)
        
        if 'suggested_time' not in advisor_result:
            return "❌ Không thể phân tích thời gian từ yêu cầu của bạn."
        
        suggested_time = advisor_result['suggested_time']
        print(f"   ✅ Parsed time: {suggested_time}")
        
        # 2. Trích xuất thông tin từ yêu cầu
        #title = self._extract_title(user_request)
        title = args.get('title', user_request)
        
        # 3. Trích description từ yêu cầu (nếu có)
        description = args.get('description', user_request)
        if not description:
            description = title
        
        
        # 4. Trích xuất khoảng thời gian từ yêu cầu
        end_time = self._calculate_end_time(user_request, suggested_time)

        # 5. Định dạng thời gian
        start_time_str = suggested_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        print(f"   ✅ Final times: {start_time_str} - {end_time_str}")

        # 6. Thêm vào database
        result = executor.add_schedule(title, description, start_time_str, end_time_str)
        return result
    
    def _handle_get_schedules(self, executor: ExecuteSchedule) -> str:
        """Xử lý yêu cầu lấy danh sách lịch"""
        schedules = executor.get_schedules()
        if not schedules:
            return "📋 Hiện tại chưa có lịch nào được lưu."
        
        result = "📋 **Danh sách lịch:**\n"
        for schedule in schedules:
            result += f"ID: {schedule[0]} | {schedule[1]} | {schedule[3]} - {schedule[4]}\n"
            result += f"   Mô tả: {schedule[2]}\n\n"
        return result
    
    def _handle_update_schedule(self, args: Dict, executor: ExecuteSchedule) -> str:
        """Xử lý yêu cầu cập nhật lịch"""
        schedule_id = args.get('schedule_id')
        if not schedule_id:
            return "❌ Thiếu ID lịch cần cập nhật."
        
        title = args.get('title')
        description = args.get('description')
        start_time = args.get('start_time')
        end_time = args.get('end_time')
        
        result = executor.update_schedule(schedule_id, title, description, start_time, end_time)
        return result
    
    def _handle_delete_schedule(self, args: Dict, executor: ExecuteSchedule) -> str:
        """Xử lý yêu cầu xóa lịch"""
        schedule_id = args.get('schedule_id')
        if not schedule_id:
            return "❌ Thiếu ID lịch cần xóa."
        
        result = executor.delete_schedule(schedule_id)
        return result
    
    def _extract_title(self, user_request: str) -> str:
        """Trích xuất thông tin từ yêu cầu của người dùng"""
        title_match = re.search(r'(khám răng|học|họp|đi|mua|gặp|làm)', user_request, re.IGNORECASE)
        return title_match.group(0) if title_match else "Lịch mới"
    
    def _calculate_end_time(self, user_request: str, suggested_time):
        """Tính toán thời gian kết thúc dựa trên thời lượng trong yêu cầu"""
        duration_match = re.search(r'(\d+)\s*(tiếng|giờ|phút)', user_request)
        if duration_match:
            duration_num = int(duration_match.group(1))
            duration_unit = duration_match.group(2)
            if 'tiếng' in duration_unit or 'giờ' in duration_unit:
                return suggested_time.replace(hour=suggested_time.hour + duration_num)
            else:  # phút
                return suggested_time.replace(minute=suggested_time.minute + duration_num)
        else:
            return suggested_time.replace(hour=suggested_time.hour + 1)  # default 1h
