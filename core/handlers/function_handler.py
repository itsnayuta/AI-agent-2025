from datetime import datetime, timedelta
import random
import re
from typing import Dict
from core.services.ScheduleAdvisor import ScheduleAdvisor
from core.services.ExecuteSchedule import ExecuteSchedule
from core.notification import get_notification_manager


def _handle_irrelevant_input(user_input: str) -> str | None:
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


class FunctionCallHandler:
    def __init__(self, advisor: ScheduleAdvisor = None):  # cho phép inject advisor có LLM
        self.advisor = advisor or ScheduleAdvisor()
        self.notification_manager = get_notification_manager()

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
            elif name == "setup_notification_email":
                return self._handle_setup_notification_email(args)
            else:
                return "Chức năng không hỗ trợ."
        except Exception as e:
            return f"Lỗi khi thực hiện: {str(e)}"
        finally:
            executor.close()

    def _handle_advise_schedule(self, args: Dict, user_input: str) -> str:
        # irrelevant_response = _handle_irrelevant_input(user_input)
        # if irrelevant_response:
        #     return f"[Trợ lý]: {irrelevant_response}"

        """Xử lý tư vấn lịch"""
        user_request = args.get('user_request', user_input)
        preferred_time_of_day = args.get('preferred_time_of_day')
        duration = args.get('duration')
        priority = args.get('priority')
        preferreddate = args.get('preferred_date')
        preferred_weekday = args.get('preferred_weekday')

        print(f"DEBUG advise_schedule:")
        print(f"user_request: {user_request}")  
        print(f"preferred_time_of_day: {preferred_time_of_day}")
        print(f"duration: {duration}")
        print(f"priority: {priority}")
        print(f"preferred_date: {preferreddate}")
        print(f"preferred_weekday: {preferred_weekday}")

        # Ủy quyền cho advisor quyết định hỏi thêm hay tư vấn
        result = self.advisor.advise_schedule(
            user_request=user_request,
            preferred_time_of_day=preferred_time_of_day,
            duration=duration,
            priority=priority,
            preferred_date=preferreddate,
            preferred_weekday=preferred_weekday
        )
        print(f"DEBUG advise_schedule result: {result} \n")
        return self.advisor.format_response(result)

    def _handle_smart_add_schedule(self, args: Dict, user_input: str, executor: ExecuteSchedule) -> str:
        """Xử lý thêm lịch thông minh"""
        user_request = args.get('user_request', user_input)

        print(f"DEBUG smart_add_schedule:")
        print(f"user_request: {user_request}")
        print(f"args: {args}")

        # 1. Ưu tiên sử dụng thời gian từ Gemini nếu có
        start_time_str = args.get('start_time')
        end_time_str = args.get('end_time')

        if start_time_str:
            # Gemini đã parse được thời gian
            print(f"Using Gemini parsed time: {start_time_str}")
            
            # Kiểm tra và sửa năm nếu cần
            from utils.timezone_utils import parse_time_to_vietnam, vietnam_isoformat, get_vietnam_now
            from datetime import datetime
            
            try:
                start_time_vn = parse_time_to_vietnam(start_time_str)
                current_year = get_vietnam_now().year
                
                # Nếu năm không đúng, sửa lại
                if start_time_vn.year != current_year:
                    print(f"⚠️ WARNING: Gemini returned wrong year {start_time_vn.year}, correcting to {current_year}")
                    start_time_vn = start_time_vn.replace(year=current_year)
                    start_time_str = vietnam_isoformat(start_time_vn)
                    print(f"✅ Corrected time: {start_time_str}")
                
                if not end_time_str:
                    # Tính toán end_time dựa trên start_time
                    end_time_vn = start_time_vn + timedelta(hours=1)  # Default 1 hour
                    end_time_str = vietnam_isoformat(end_time_vn)
                else:
                    # Kiểm tra end_time cũng
                    end_time_vn = parse_time_to_vietnam(end_time_str)
                    if end_time_vn.year != current_year:
                        end_time_vn = end_time_vn.replace(year=current_year)
                        end_time_str = vietnam_isoformat(end_time_vn)
                        
            except Exception as e:
                print(f"⚠️ Error parsing time: {e}, falling back to advisor")
                start_time_str = None
        else:
            # Fallback: Phân tích thời gian từ input thông qua ScheduleAdvisor
            advisor_result = self.advisor.advise_schedule(user_request)

            if 'suggested_time' not in advisor_result:
                return "Không thể phân tích thời gian từ yêu cầu của bạn."

            suggested_time = advisor_result['suggested_time']
            print(f"ScheduleAdvisor parsed time: {suggested_time}")

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

        print(f"Final: {title} | {start_time_str} - {end_time_str}")

        # 3. Thêm vào database
        result = executor.add_schedule(title, description, start_time_str, end_time_str)
        return result

    def _handle_get_schedules(self, executor: 'ExecuteSchedule') -> dict:
        """Xử lý yêu cầu lấy danh sách lịch và trả về dưới dạng JSON."""
        schedules = executor.get_schedules()

        if not schedules:
            return {
                "message": "Hiện tại chưa có lịch nào được lưu.",
                "schedules": []
            }

        schedule_list = []
        for schedule in schedules:
            schedule_item = {
                "id": schedule[0],
                "title": schedule[1],
                "description": schedule[2],
                "start_time": schedule[3],
                "end_time": schedule[4]
            }
            schedule_list.append(schedule_item)

        return {
            "message": "Danh sách lịch đã được lấy thành công.",
            "schedules": schedule_list
        }

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

    def _extract_title(self, user_request: str) -> str:
        """Trích xuất thông tin từ yêu cầu của người dùng"""
        title_match = re.search(r'(khám răng|học|họp|đi|mua|gặp|làm)', user_request, re.IGNORECASE)
        return title_match.group(0) if title_match else "Lịch mới"

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