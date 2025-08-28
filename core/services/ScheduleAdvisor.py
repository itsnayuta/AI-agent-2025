import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
import sqlite3
import pytz

# Import các hàm kiểm tra lịch độc lập và các hàm tiện ích khác
from utils.time_patterns import (
    get_time_patterns,
    parse_weekday, parse_weekday_this_week, parse_weekday_next_week,
    parse_time_period_day, parse_time_period_weekday, parse_time_period_weekday_with_hour,
    parse_after_days, parse_after_weeks, parse_after_months,
    parse_weekday_time, parse_time_weekday_this_week, parse_time_weekday_next_week, parse_time_weekday
)
from utils.task_categories import task_categories

def check_schedule_overlap(conn: sqlite3.Connection, start_time: datetime, end_time: datetime) -> bool:
    """
    Kiểm tra xem một khoảng thời gian có bị trùng với lịch đã có trong cơ sở dữ liệu hay không.
    Trả về True nếu KHÔNG có trùng lặp, False nếu có.
    """
    cursor = conn.cursor()
    # Database lưu thời gian với timezone, nên ta giữ nguyên timezone để so sánh
    start_str = start_time.isoformat()
    end_str = end_time.isoformat()
    
    query = """
        SELECT COUNT(*) FROM schedules
        WHERE NOT (? <= start_time OR ? >= end_time)
    """
    cursor.execute(query, (end_str, start_str))
    # Nếu số lượng lịch trình trùng lặp > 0, trả về False
    count = cursor.fetchone()[0]
    return count == 0

class ScheduleAdvisor:
    """
    Lớp ScheduleAdvisor cung cấp các chức năng gợi ý lịch trình thông minh:
    - Phân tích yêu cầu của người dùng
    - Kiểm tra lịch trống, đề xuất thời gian
    - Nếu thông tin chưa đủ (đặc biệt là thời gian), sinh câu hỏi làm rõ (ưu tiên dùng LLM nếu có)
    """
    def __init__(self, db_path='database/schedule.db', llm=None):
        # Lấy múi giờ Việt Nam
        self.vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        self.current_time = datetime.now(self.vietnam_tz)
        # Thiết lập giờ làm việc và giờ nghỉ trưa
        self.business_hours = (8, 17)
        self.lunch_time = (12, 13)
        # Ánh xạ các từ khóa ngày trong tuần sang số
        self.weekday_map = {
            'chủ nhật': 6, 'cn': 6, 'chủnhật': 6,
            'thứ hai': 0, 't2': 0, 'thứ 2': 0, 'thứhai': 0, 'thứ2': 0,
            'thứ ba': 1, 't3': 1, 'thứ 3': 1, 'thứba': 1, 'thứ3': 1,
            'thứ tư': 2, 't4': 2, 'thứ 4': 2, 'thứtư': 2, 'thứ4': 2,
            'thứ năm': 3, 't5': 3, 'thứ 5': 3, 'thứnăm': 3, 'thứ5': 3,
            'thứ sáu': 4, 't6': 4, 'thứ 6': 4, 'thứsáu': 4, 'thứ6': 4,
            'thứ bảy': 5, 't7': 5, 'thứ 7': 5, 'thứbảy': 5, 'thứ7': 5
        }
        # Danh sách các pattern regex để trích xuất thời gian
        # Ưu tiên pattern ngày cụ thể trước pattern thứ trong tuần
        date_patterns = get_time_patterns(self.current_time)
        self.time_patterns = date_patterns + [
            (r"(\d{1,2})(?:h|:)?(\d{2})?\s*(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*này",
            lambda m: parse_time_weekday_this_week(m, self.current_time, self.weekday_map)),
            (r"(\d{1,2})(?:h|:)?(\d{2})?\s*(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*sau",
            lambda m: parse_time_weekday_next_week(m, self.current_time, self.weekday_map)),
            (r"(sáng|chiều|tối)\s*(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*(?:lúc|vào)?\s*(\d{1,2})(?:h|:)?(\d{2})?",
            lambda m: parse_time_period_weekday_with_hour(m, self.current_time, self.weekday_map)),
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*(?:tuần\s*này|tuần\s*sau)?\s*(?:lúc|vào)?\s*(\d{1,2})(?:h|:)?(\d{2})?",
            lambda m: parse_weekday_time(m, self.current_time, self.weekday_map)),
            (r"(\d{1,2})(?:h|:)?(\d{2})?\s*(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])",
            lambda m: parse_time_weekday(m, self.current_time, self.weekday_map)),
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*này",
            lambda m: parse_weekday_this_week(m, self.current_time, self.weekday_map)),
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*sau",
            lambda m: parse_weekday_next_week(m, self.current_time, self.weekday_map)),
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])",
            lambda m: parse_weekday(m, self.current_time, self.weekday_map)),
            (r"(sáng|chiều|tối)\s*(hôm\s*nay|mai|ngày\s*kia)", lambda m: parse_time_period_day(m, self.current_time)),
            (r"(sáng|chiều|tối)\s*(thứ\s*[2-7]|chủ\s*nhật)",
            lambda m: parse_time_period_weekday(m, self.current_time, self.weekday_map)),
            (r"sau\s*(\d+)\s*ngày", lambda m: parse_after_days(m, self.current_time)),
            (r"sau\s*(\d+)\s*tuần", lambda m: parse_after_weeks(m, self.current_time)),
            (r"sau\s*(\d+)\s*tháng", lambda m: parse_after_months(m, self.current_time)),
        ]
        # Danh mục công việc và từ khóa ưu tiên
        self.task_categories = task_categories
        self.high_priority_keywords = ['gấp', 'urgent', 'quan trọng', 'important', 'khẩn cấp', 'deadline', 'hạn chót']
        self.low_priority_keywords = ['không gấp', 'có thể', 'nếu được', 'tùy ý']
        # giữ reference đến LLM/Gemini (nếu có) để sinh câu hỏi tự nhiên
        self.llm = llm
        # Import google_calendar_service để sử dụng các tính năng mới
        try:
            from core.services.google_calendar_service import GoogleCalendarService
            self.calendar_service = GoogleCalendarService()
        except Exception:
            self.calendar_service = None
        # Tạo kết nối DB
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        """Tạo bảng schedules nếu chưa tồn tại."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                start_time TEXT,
                end_time TEXT,
                created_at TEXT
            )
        ''')
        self.conn.commit()

    def _extract_time(self, text: str) -> Optional[datetime]:
        """Trích xuất thời gian từ văn bản người dùng."""
        text_lower = text.lower()
        for pattern, parser in self.time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    result = parser(match)
                    if result:
                        # Gán múi giờ nếu chưa có
                        if result.tzinfo is None or result.tzinfo.utcoffset(result) is None:
                            result = self.vietnam_tz.localize(result)
                        
                        if result > self.current_time:
                            return result
                except (ValueError, TypeError):
                    continue
        return None

    def _resolve_preferred_date(self, preferred_date: Optional[str], preferred_weekday: Optional[str]) -> Optional[datetime]:
        """Ưu tiên preferred_date, nếu không có thì dùng preferred_weekday."""
        if preferred_date:
            try:
                dt = datetime.strptime(preferred_date, "%Y-%m-%d").replace(tzinfo=self.vietnam_tz)
                if dt >= self.current_time:
                    return dt
            except ValueError:
                pass
        if preferred_weekday:
            wd = self.weekday_map.get(preferred_weekday.lower())
            if wd is not None:
                days_ahead = (wd - self.current_time.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return (self.current_time + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
        return None
        
    def _default_time_from_tod(self, preferred_time_of_day: str) -> Optional[datetime]:
        """
        Tạo đối tượng datetime mặc định dựa trên khung giờ ưa thích (sáng/chiều/tối).
        Nếu thời gian gợi ý trong quá khứ, đẩy nó sang ngày hôm sau.
        """
        base = self.current_time
        suggested_time = None
        
        if preferred_time_of_day.lower() == 'sáng':
            suggested_time = base.replace(hour=9, minute=0, second=0, microsecond=0)
        elif preferred_time_of_day.lower() == 'chiều':
            suggested_time = base.replace(hour=14, minute=0, second=0, microsecond=0)
        elif preferred_time_of_day.lower() == 'tối':
            suggested_time = base.replace(hour=19, minute=0, second=0, microsecond=0)
        
        # Nếu thời gian gợi ý đã qua, chuyển sang ngày hôm sau
        if suggested_time and suggested_time <= self.current_time:
            suggested_time += timedelta(days=1)
            
        return suggested_time

    def advise_schedule(self, user_request: str,
                        preferred_time_of_day: Optional[str] = None,
                        preferred_date: Optional[str] = None,
                        preferred_weekday: Optional[str] = None,
                        duration: Optional[Union[int, str]] = None,
                        priority: Optional[str] = None) -> Dict[str, Union[str, List[str]]]:

        try:
            task_info = self._categorize_task_and_priority(user_request)
            duration_minutes, duration_provided = self._normalize_duration(duration, user_request, task_info['duration'])
            priority_norm, priority_provided = self._normalize_priority(priority, user_request)
            priority = priority_norm

            # 1. Ưu tiên parse từ text trước (có thời gian cụ thể)
            suggested_time = self._extract_time(user_request)

            # 2. Nếu chưa có, dùng preferred_date/weekday nhưng cần có thời gian cụ thể
            if suggested_time is None:
                date_time = self._resolve_preferred_date(preferred_date, preferred_weekday)
                if date_time and preferred_time_of_day:
                    # Combine date with time of day
                    suggested_time = self._default_time_from_tod(preferred_time_of_day)
                    if suggested_time and date_time:
                        suggested_time = suggested_time.replace(
                            year=date_time.year, 
                            month=date_time.month, 
                            day=date_time.day
                        )
                elif date_time:
                    suggested_time = date_time

            # 3. Nếu vẫn chưa có, fallback dựa trên preferred_time_of_day
            if suggested_time is None and preferred_time_of_day:
                suggested_time = self._default_time_from_tod(preferred_time_of_day)

            # 4. Nếu vẫn không có, yêu cầu thêm thông tin
            if suggested_time is None:
                return self._ask_for_more_info(user_request, duration_minutes, priority, duration_provided, priority_provided, preferred_time_of_day)

            # 5. Kiểm tra trùng lịch với thời gian gốc trước khi validate
            original_time = suggested_time
            if original_time.tzinfo is None or original_time.tzinfo.utcoffset(original_time) is None:
                original_time = self.vietnam_tz.localize(original_time)
            
            original_end_time = original_time + timedelta(minutes=duration_minutes)
            has_conflict = not check_schedule_overlap(self.conn, original_time, original_end_time)
            
            # Lấy lịch hiện có để hiển thị
            existing_schedules = self._get_schedules_for_day(original_time)
            conflict_details = []
            
            if has_conflict:
                # Tìm lịch trùng cụ thể để thông báo
                for schedule in existing_schedules:
                    schedule_start = datetime.fromisoformat(schedule['start_time'])
                    schedule_end = datetime.fromisoformat(schedule['end_time'])
                    if schedule_start.tzinfo is None:
                        schedule_start = self.vietnam_tz.localize(schedule_start)
                    if schedule_end.tzinfo is None:
                        schedule_end = self.vietnam_tz.localize(schedule_end)
                    
                    # Kiểm tra overlap
                    if not (original_end_time <= schedule_start or original_time >= schedule_end):
                        # Convert to Vietnam time for display
                        display_start = schedule_start.astimezone(self.vietnam_tz)
                        display_end = schedule_end.astimezone(self.vietnam_tz)
                        conflict_details.append(f"**{schedule['title']}** ({display_start.strftime('%H:%M')}-{display_end.strftime('%H:%M')})")

            # 6. Validate và tìm thời gian thay thế
            adjusted_time, warnings = self._validate_business_time(suggested_time, duration_minutes, priority)
            alternatives = self._generate_alternative_times(adjusted_time, task_info)

            # 7. Tạo response với thông báo trùng lịch rõ ràng
            if has_conflict:
                conflict_message = f"⚠️ Thời gian {original_time.strftime('%H:%M')} đã trùng với: {', '.join(conflict_details)}"
                warnings.insert(0, conflict_message)  # Thêm vào đầu danh sách warnings
                
                return {
                    'main_suggestion': f"Đề xuất thay thế: {adjusted_time.strftime('%A, %d/%m/%Y lúc %H:%M')}",
                    'duration': f"Thời lượng gợi ý: {duration_minutes} phút",
                    'priority': f"Mức độ ưu tiên: {priority}",
                    'warnings': warnings,
                    'alternatives': alternatives,
                    'existing_schedules': existing_schedules,
                    'suggested_time': suggested_time,
                    'adjusted_time': adjusted_time,
                    'original_time': original_time,
                    'has_conflict': True,
                    'status': 'success'
                }
            else:
                return {
                    'main_suggestion': f"Đề xuất chính: {adjusted_time.strftime('%A, %d/%m/%Y lúc %H:%M')}",
                    'duration': f"Thời lượng gợi ý: {duration_minutes} phút",
                    'priority': f"Mức độ ưu tiên: {priority}",
                    'warnings': warnings,
                    'alternatives': alternatives,
                    'existing_schedules': existing_schedules,
                    'suggested_time': suggested_time,
                    'adjusted_time': adjusted_time,
                    'has_conflict': False,
                    'status': 'success'
                }

        except Exception as e:
            return {'main_suggestion': "Có lỗi xảy ra khi phân tích.", 'error': str(e), 'status': 'error'}
            
    def _ask_for_more_info(self, user_request, duration_minutes, priority, duration_provided, priority_provided, preferred_time_of_day):
        missing_fields: List[str] = []
        if not duration_provided:
            missing_fields.append('duration')
        if not priority_provided:
            missing_fields.append('priority')
        if not preferred_time_of_day:
            missing_fields.append('preferred_time_of_day')
        
        # Luôn cần thời gian cụ thể nếu chưa có
        missing_fields.insert(0, 'time')
        
        question = self._generate_followup_question(missing_fields, user_request)
        return {
            'status': 'need_more_info',
            'main_suggestion': "Chưa đủ thông tin để tư vấn.",
            'duration': f"Thời lượng mặc định hiện tại: {duration_minutes} phút",
            'priority': f"Mức độ ưu tiên hiện tại: {priority}",
            'question': question,
            'missing_fields': missing_fields
        }

    def _extract_duration_from_text(self, text: str) -> Tuple[Optional[int], bool]:
        text_lower = text.lower()
        m = re.search(r'(\d{1,2})\s*(tiếng|giờ)\s*(\d{1,2})?\s*(phút)?', text_lower)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(3) or 0)
            return hours * 60 + minutes, True
        m = re.search(r'(\d{1,3})\s*phút', text_lower)
        if m:
            return int(m.group(1)), True
        return None, False

    def _detect_preferred_tod_in_text(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if 'sáng' in text_lower:
            return 'sáng'
        if 'chiều' in text_lower:
            return 'chiều'
        if 'tối' in text_lower:
            return 'tối'
        return None

    def _normalize_priority(self, p: Optional[str], text: str) -> Tuple[str, bool]:
        provided = False
        if p:
            provided = True
            v = p.strip().lower()
        else:
            v = ''
        if not v:
            t = text.lower()
            if any(k in t for k in self.high_priority_keywords):
                return 'Cao', True
            if any(k in t for k in self.low_priority_keywords):
                return 'Thấp', True
            return 'Bình thường', False
        if v in ['cao', 'high', 'urgent']:
            return 'Cao', True
        if v in ['trung bình', 'binh thuong', 'bình thường', 'medium', 'normal']:
            return 'Bình thường', True
        if v in ['thấp', 'low']:
            return 'Thấp', True
        return 'Bình thường', provided

    def _normalize_duration(self, duration_arg: Optional[Union[int, str]], user_request: str, default_minutes: int) -> Tuple[int, bool]:
        if isinstance(duration_arg, int):
            return duration_arg, True
        if isinstance(duration_arg, str):
            dur_text = duration_arg.lower().strip()
            m = re.search(r'(\d{1,2})\s*(tiếng|giờ)\s*(\d{1,2})?\s*(phút)?', dur_text)
            if m:
                hours = int(m.group(1))
                minutes = int(m.group(3) or 0)
                return hours * 60 + minutes, True
            m = re.search(r'(\d{1,3})\s*phút', dur_text)
            if m:
                return int(m.group(1)), True
        parsed, provided = self._extract_duration_from_text(user_request)
        if parsed is not None:
            return parsed, provided
        return default_minutes, False

    def _generate_followup_question(self, missing_fields: List[str], user_request: str) -> str:
        base_question = "Để tư vấn lịch chính xác hơn, mình cần thêm: "
        mapping = {
            'time': "thời gian cụ thể (vd: 'thứ 5 tuần sau lúc 14:00' hoặc 'ngày mai 9h')",
            'preferred_time_of_day': "khung giờ ưa thích (sáng/chiều/tối)",
            'duration': "thời lượng dự kiến (vd: 30, 60, 90 phút)",
            'priority': "mức độ ưu tiên (Cao/ Bình thường/ Thấp)"
        }
        items = [mapping[f] for f in missing_fields if f in mapping]
        template = (
            f"{base_question}{'; '.join(items)}.\n"
            f"Bạn trả lời tự nhiên được nhé. Ví dụ: 'Sáng thứ 3 tuần sau, 60 phút, ưu tiên Cao'."
        )
        if self.llm:
            try:
                prompt = (
                    "Người dùng đang yêu cầu tư vấn lịch trình.\n"
                    f"Yêu cầu người dùng: {user_request}\n"
                    f"Các trường còn thiếu: {', '.join(missing_fields)}\n"
                    "Hãy viết 1-2 câu hỏi ngắn gọn, thân thiện bằng tiếng Việt để hỏi thêm thông tin, "
                    "kèm 2-3 ví dụ câu trả lời mẫu theo đúng ngữ cảnh (không dùng bullet nếu không cần).\n"
                )
                if hasattr(self.llm, "generate_text"):
                    out = self.llm.generate_text(prompt)
                elif hasattr(self.llm, "generate"):
                    out = self.llm.generate(prompt)
                elif hasattr(self.llm, "chat"):
                    out = self.llm.chat(prompt)
                elif hasattr(self.llm, "generate_with_timeout"):
                    out = self.llm.generate_with_timeout(prompt, functions=None)
                else:
                    out = None
                if isinstance(out, str) and out.strip():
                    return out.strip()
                if hasattr(out, "text"):
                    return str(out.text).strip()
            except Exception:
                pass
        return template

    def _categorize_task_and_priority(self, text: str) -> Dict[str, Union[str, int, Tuple[int, int]]]:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in self.high_priority_keywords):
            priority = 'Cao'
        elif any(keyword in text_lower for keyword in self.low_priority_keywords):
            priority = 'Thấp'
        else:
            priority = 'Bình thường'
        for category, info in self.task_categories.items():
            if any(keyword in text_lower for keyword in info['keywords']):
                info = dict(info)
                info['priority'] = priority
                return info
        return {
            'duration': 60,
            'priority': priority,
            'best_time': (9, 17)
        }

    def _validate_business_time(self, suggested_time: datetime, duration: int, priority: str) -> Tuple[datetime, List[str]]:
        """
        Kiểm tra và điều chỉnh thời gian đề xuất để phù hợp với giờ làm việc và lịch trống.
        Thêm tham số 'priority' để xét mức độ ưu tiên.
        """
        warnings = []
        
        # Gán múi giờ Việt Nam nếu suggested_time chưa có
        if suggested_time.tzinfo is None or suggested_time.tzinfo.utcoffset(suggested_time) is None:
            suggested_time = self.vietnam_tz.localize(suggested_time)

        adjusted_time = suggested_time
        end_time = adjusted_time + timedelta(minutes=duration)

        business_start, business_end = self.business_hours

        # Điều chỉnh nếu thời gian nằm ngoài giờ làm việc
        if adjusted_time.hour < business_start:
            warnings.append(f"Thời gian trước giờ làm việc. Đã điều chỉnh về {business_start}h.")
            adjusted_time = adjusted_time.replace(hour=business_start, minute=0)
            end_time = adjusted_time + timedelta(minutes=duration)
        elif end_time.hour >= business_end:
            warnings.append(f"Thời gian sau giờ làm việc. Đã điều chỉnh về 9h sáng hôm sau.")
            adjusted_time = (adjusted_time + timedelta(days=1)).replace(hour=9, minute=0)
            end_time = adjusted_time + timedelta(minutes=duration)

        # Điều chỉnh nếu thời gian trùng giờ ăn trưa
        lunch_start, lunch_end = self.lunch_time
        if (lunch_start <= adjusted_time.hour < lunch_end) or (lunch_start < end_time.hour <= lunch_end):
            warnings.append(f"Thời gian trùng giờ ăn trưa. Đã điều chỉnh về {lunch_end}h.")
            adjusted_time = adjusted_time.replace(hour=lunch_end, minute=0)
            end_time = adjusted_time + timedelta(minutes=duration)

        # QUAN TRỌNG: Kiểm tra trùng lịch - LUÔN tìm thời gian trống nếu bị trùng
        max_attempts = 5  # Giới hạn số lần thử để tránh vòng lặp vô hạn
        attempts = 0
        
        while not check_schedule_overlap(self.conn, adjusted_time, end_time) and attempts < max_attempts:
            warnings.append(f"Thời gian {adjusted_time.strftime('%H:%M')} đã có lịch, đang tìm thời gian khác...")
            try:
                adjusted_time = self._find_next_available_slot(adjusted_time, duration, priority)
                end_time = adjusted_time + timedelta(minutes=duration)
                attempts += 1
            except Exception as e:
                warnings.append(f"Không thể tìm thấy thời gian trống phù hợp: {str(e)}")
                break

        return adjusted_time, warnings

    def _find_next_available_slot(self, start_time: datetime, duration: int, priority: str) -> datetime:
        """
        Tìm kiếm khung giờ trống gần nhất trong vòng 7 ngày tới.
        Đã tích hợp logic dựa trên mức độ ưu tiên.
        """
        # Đảm bảo start_time có múi giờ
        if start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None:
            start_time = self.vietnam_tz.localize(start_time)
        
        # Bắt đầu tìm từ ngày hiện tại
        search_date = start_time.date()
        max_search_days = 2 if priority == 'Cao' else 7
        
        # Tạo danh sách các khung giờ ưu tiên trong ngày (tránh giờ ăn trưa)
        preferred_hours = []
        business_start, business_end = self.business_hours
        lunch_start, lunch_end = self.lunch_time
        
        for hour in range(business_start, business_end):
            if hour < lunch_start or hour >= lunch_end:
                preferred_hours.append(hour)
        
        for i in range(max_search_days):
            current_date = search_date + timedelta(days=i)
            
            # Bỏ qua cuối tuần
            if current_date.weekday() >= 5:
                continue
            
            # Nếu là ngày hiện tại, chỉ tìm từ giờ hiện tại trở đi
            if current_date == self.current_time.date():
                current_hour = max(self.current_time.hour, business_start)
                preferred_hours = [h for h in preferred_hours if h >= current_hour]
            
            # Thử từng khung giờ ưu tiên
            for hour in preferred_hours:
                for minute in [0, 30]:  # Thử cả giờ tròn và 30 phút
                    candidate_time = datetime.combine(current_date, datetime.min.time()).replace(
                        hour=hour, minute=minute, tzinfo=self.vietnam_tz
                    )
                    candidate_end = candidate_time + timedelta(minutes=duration)
                    
                    # Kiểm tra không vượt quá giờ làm việc
                    if candidate_end.hour > business_end:
                        continue
                    
                    # Kiểm tra không trùng với lịch hiện có
                    if check_schedule_overlap(self.conn, candidate_time, candidate_end):
                        return candidate_time
            
            # Nếu không tìm được trong các khung giờ ưu tiên, tìm bất kỳ khoảng trống nào
            schedules_on_day = self._get_schedules_for_day(datetime.combine(current_date, datetime.min.time()).replace(tzinfo=self.vietnam_tz))
            
            if not schedules_on_day:
                # Không có lịch nào trong ngày, trả về giờ bắt đầu làm việc
                return datetime.combine(current_date, datetime.min.time()).replace(
                    hour=business_start, minute=0, tzinfo=self.vietnam_tz
                )
            
            # Sắp xếp lịch theo thời gian bắt đầu
            sorted_schedules = sorted(schedules_on_day, key=lambda x: datetime.fromisoformat(x['start_time']))
            
            # Tìm khoảng trống giữa các lịch
            last_end_time = datetime.combine(current_date, datetime.min.time()).replace(
                hour=business_start, minute=0, tzinfo=self.vietnam_tz
            )
            
            for schedule in sorted_schedules:
                current_start = datetime.fromisoformat(schedule['start_time'])
                if current_start.tzinfo is None:
                    current_start = self.vietnam_tz.localize(current_start)
                
                # Kiểm tra khoảng trống trước lịch này
                if (current_start - last_end_time).total_seconds() >= duration * 60:
                    # Kiểm tra không trùng giờ ăn trưa
                    if not (lunch_start <= last_end_time.hour < lunch_end):
                        return last_end_time
                
                # Cập nhật thời gian kết thúc cuối cùng
                last_end_time = datetime.fromisoformat(schedule['end_time'])
                if last_end_time.tzinfo is None:
                    last_end_time = self.vietnam_tz.localize(last_end_time)
                
                # Nếu kết thúc trong giờ ăn trưa, chuyển đến sau giờ ăn trưa
                if lunch_start <= last_end_time.hour < lunch_end:
                    last_end_time = last_end_time.replace(hour=lunch_end, minute=0)
            
            # Kiểm tra khoảng trống cuối ngày
            end_of_business_day = datetime.combine(current_date, datetime.min.time()).replace(
                hour=business_end, minute=0, tzinfo=self.vietnam_tz
            )
            
            if (end_of_business_day - last_end_time).total_seconds() >= duration * 60:
                return last_end_time
        
        # Nếu không tìm thấy trong khoảng thời gian cho phép, ném exception
        raise Exception(f"Không tìm thấy khung giờ trống phù hợp trong vòng {max_search_days} ngày tới.")

    def _generate_alternative_times(self, base_time: datetime, task_info: Dict) -> List[str]:
        """Tạo các gợi ý thời gian thay thế không trùng với lịch hiện có."""
        alternatives = []
        duration = task_info.get('duration', 60)
        best_start, best_end = task_info.get('best_time', self.business_hours)
        
        # Đảm bảo base_time có timezone
        if base_time.tzinfo is None or base_time.tzinfo.utcoffset(base_time) is None:
            base_time = self.vietnam_tz.localize(base_time)
        
        # Tạo danh sách các khung giờ gợi ý trong cùng ngày
        suggestion_hours = []
        business_start, business_end = self.business_hours
        lunch_start, lunch_end = self.lunch_time
        
        # Thêm các khung giờ phổ biến (tránh giờ ăn trưa)
        for hour in [8, 9, 10, 11, 14, 15, 16]:
            if business_start <= hour < business_end and (hour < lunch_start or hour >= lunch_end):
                suggestion_hours.append(hour)
        
        # Thử các khung giờ trong cùng ngày
        for hour in suggestion_hours:
            alt_time = base_time.replace(hour=hour, minute=0)
            if alt_time > self.current_time:
                alt_end = alt_time + timedelta(minutes=duration)
                if check_schedule_overlap(self.conn, alt_time, alt_end):
                    alternatives.append(alt_time.strftime('%H:%M %A, %d/%m/%Y'))
        
        # Thử ngày hôm sau và các ngày tiếp theo
        for days_ahead in [1, 2, 3]:
            next_day = base_time + timedelta(days=days_ahead)
            
            # Bỏ qua cuối tuần
            if next_day.weekday() >= 5:
                continue
            
            # Thử một vài khung giờ phổ biến trong ngày mới
            for hour in [8, 9, 14, 15]:
                if business_start <= hour < business_end:
                    alt_time = next_day.replace(hour=hour, minute=0)
                    alt_end = alt_time + timedelta(minutes=duration)
                    
                    if check_schedule_overlap(self.conn, alt_time, alt_end):
                        alternatives.append(alt_time.strftime('%H:%M %A, %d/%m/%Y'))
                        break  # Chỉ lấy 1 thời gian mỗi ngày
        
        # Loại bỏ trùng lặp và giới hạn số lượng
        unique_alternatives = list(dict.fromkeys(alternatives))  # Giữ thứ tự và loại bỏ trùng
        return unique_alternatives[:3]

    def _get_schedules_for_day(self, target_date: datetime) -> List[Dict[str, str]]:
        """Lấy tất cả các lịch hẹn trong một ngày cụ thể."""
        cursor = self.conn.cursor()
        date_str = target_date.strftime('%Y-%m-%d')
        cursor.execute(
            'SELECT title, start_time, end_time FROM schedules WHERE strftime("%Y-%m-%d", start_time) = ?',
            (date_str,)
        )
        schedules = []
        for row in cursor.fetchall():
            schedules.append({
                'title': row[0],
                'start_time': row[1],
                'end_time': row[2]
            })
        return schedules

    def format_response(self, response: Dict) -> str:
        if response['status'] == 'success':
            # Kiểm tra nếu có trùng lịch
            if response.get('has_conflict', False):
                result = f"### ⚠️ Phát hiện trùng lịch\n---\n"
                result += f"**{response['main_suggestion']}**\n"
                result += f"**{response['duration']}**\n"
                result += f"**{response['priority']}**\n"
                
                # Hiển thị thông báo trùng lịch trước
                if response.get('warnings'):
                    result += "\n### 🚨 Thông báo trùng lịch\n---\n"
                    for i, warning in enumerate(response['warnings']):
                        if i == 0:  # Warning đầu tiên là thông báo trùng lịch
                            result += f"  - {warning}\n"
                        else:
                            break
                
                # Hiển thị lịch hiện có
                if response.get('existing_schedules'):
                    result += "\n### 📅 Lịch trình hiện có trong ngày\n---\n"
                    for schedule in response['existing_schedules']:
                        start_dt = datetime.fromisoformat(schedule['start_time'])
                        end_dt = datetime.fromisoformat(schedule['end_time'])
                        
                        # Convert to Vietnam timezone for display
                        if start_dt.tzinfo is not None:
                            start_dt = start_dt.astimezone(self.vietnam_tz)
                        if end_dt.tzinfo is not None:
                            end_dt = end_dt.astimezone(self.vietnam_tz)
                            
                        start_time_str = start_dt.strftime('%H:%M')
                        end_time_str = end_dt.strftime('%H:%M')
                        result += f"  - **{schedule['title']}**: từ {start_time_str} đến {end_time_str}\n"
                
                # Hiển thị các lưu ý khác (ngoài trừ thông báo trùng lịch đầu tiên)
                other_warnings = response.get('warnings', [])[1:] if response.get('warnings') else []
                if other_warnings:
                    result += "\n### ⚡ Lưu ý khác\n---\n"
                    for warning in other_warnings:
                        result += f"  - {warning}\n"
                
                # Hiển thị thời gian thay thế
                if response.get('alternatives'):
                    result += "\n### 🔄 Thời gian thay thế khác\n---\n"
                    for alt in response['alternatives']:
                        result += f"  - {alt}\n"
            else:
                # Trường hợp không có trùng lịch
                result = f"### Gợi ý Lịch trình\n---\n"
                result += f"**{response['main_suggestion']}**\n"
                result += f"**{response['duration']}**\n"
                result += f"**{response['priority']}**\n"
                
                if response.get('existing_schedules'):
                    result += "\n### Lịch trình đã có trong ngày\n---\n"
                    for schedule in response['existing_schedules']:
                        start_dt = datetime.fromisoformat(schedule['start_time'])
                        end_dt = datetime.fromisoformat(schedule['end_time'])
                        
                        # Convert to Vietnam timezone for display
                        if start_dt.tzinfo is not None:
                            start_dt = start_dt.astimezone(self.vietnam_tz)
                        if end_dt.tzinfo is not None:
                            end_dt = end_dt.astimezone(self.vietnam_tz)
                            
                        start_time_str = start_dt.strftime('%H:%M')
                        end_time_str = end_dt.strftime('%H:%M')
                        result += f"  - **{schedule['title']}**: từ {start_time_str} đến {end_time_str}\n"
                        
                if response.get('warnings'):
                    result += "\n### Lưu ý\n---\n"
                    for warning in response['warnings']:
                        result += f"  - {warning}\n"
                        
                if response.get('alternatives'):
                    result += "\n### Thời gian thay thế\n---\n"
                    for alt in response['alternatives']:
                        result += f"  - {alt}\n"
        elif response['status'] == 'need_more_info':
            result = f"### Cần thêm thông tin\n---\n"
            result += f"**{response['main_suggestion']}**\n"
            if 'question' in response:
                result += f"\n{response['question']}\n"
                result += "\nVí dụ nhanh: 'Ngày mai 9h, 60 phút, ưu tiên Cao' hoặc 'Chiều thứ 5 tuần sau, 30 phút'.\n"
            else:
                result += f"**{response.get('duration','')}**\n"
                result += f"**{response.get('priority','')}**\n\n"
                if response.get('suggestions'):
                    result += "**Gợi ý diễn đạt:**\n"
                    for suggestion in response['suggestions']:
                        result += f"{suggestion}\n"
        else:
            result = f"### Lỗi\n---\n"
            result += f"**{response['main_suggestion']}**\n"
            result += f"Chi tiết lỗi: {response.get('error', 'Không xác định')}"
        return result

    def find_available_slots(self, target_date: datetime, duration_minutes: int, preferred_start_hour: int = None, preferred_end_hour: int = None) -> List[str]:
        """
        Tìm các khung giờ trống trong ngày cụ thể
        """
        available_slots = []
        
        # Thiết lập khung giờ tìm kiếm
        start_hour = preferred_start_hour or self.business_hours[0]  # 8h
        end_hour = preferred_end_hour or self.business_hours[1]      # 17h
        
        # Tạo các slot 30 phút
        current_time = target_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = target_date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Bỏ qua giờ ăn trưa
            if not (current_time.hour == 12 and current_time.minute == 0):
                # Kiểm tra xung đột với database
                is_free = check_schedule_overlap(self.conn, current_time, slot_end)
                
                if is_free:
                    available_slots.append(f"{current_time.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}")
                    
            # Chuyển sang slot tiếp theo (15 phút)
            current_time += timedelta(minutes=15)
            
            # Giới hạn tối đa 10 slots để không quá nhiều
            if len(available_slots) >= 10:
                break
                
        return available_slots

    async def intelligent_schedule_advice(self, user_input: str, context: Dict = None) -> str:
        """
        Tư vấn lịch trình thông minh với tìm kiếm khung giờ trống
        """
        if not self.llm:
            # Fallback về phương thức cũ nếu không có Gemini
            result = self.advise_schedule(user_input)
            return self.format_response(result)
        
        try:
            # Trích xuất thông tin từ yêu cầu người dùng
            extracted_time = self._extract_time(user_input)
            duration_minutes = self._extract_duration_minutes(user_input)
            
            if extracted_time and duration_minutes:
                # Tìm khung giờ trống cho ngày được yêu cầu
                target_date = extracted_time.date()
                target_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=self.vietnam_tz)
                
                available_slots = self.find_available_slots(
                    target_datetime, 
                    duration_minutes,
                    preferred_start_hour=8,
                    preferred_end_hour=17
                )
                
                if available_slots:
                    # Trích xuất loại lịch từ user input
                    schedule_type = self._extract_schedule_type(user_input)
                    response = f"📅 **{schedule_type} {target_date.strftime('%d/%m/%Y')} - Thời lượng: {duration_minutes} phút**\n\n"
                    response += "🕒 **Các khung giờ trống:**\n"
                    for i, slot in enumerate(available_slots[:8], 1):  # Hiển thị tối đa 8 slots
                        response += f"{i}. {slot}\n"
                    response += f"\nVui lòng chọn khung giờ phù hợp!"
                    return response
                else:
                    return f"❌ **Không có khung giờ trống nào trong ngày {target_date.strftime('%d/%m/%Y')}**\n\nBạn có muốn tôi đề xuất ngày khác không?"
            
            # Nếu không đủ thông tin, dùng Gemini để hỏi làm rõ
            gemini_prompt = f"""TƯ VẤN LỊCH TRÌNH NGẮN GỌN

Yêu cầu: {user_input}
Thời gian hiện tại: {self.current_time.strftime('%Y-%m-%d %H:%M')} (Việt Nam)

Hãy phân tích yêu cầu và hỏi NGẮN GỌN những thông tin còn thiếu:
- Ngày cụ thể (nếu chưa rõ)
- Thời lượng (nếu chưa có)
- Khung giờ ưu tiên (nếu cần)

Chỉ hỏi tối đa 2 câu, không dài dòng.
Ví dụ: "Bạn muốn khám vào ngày nào? Thời lượng khoảng bao lâu?"
"""
            
            gemini_response = await self.llm.process_message(gemini_prompt)
            return gemini_response
            
        except Exception as e:
            print(f"Lỗi khi sử dụng tư vấn thông minh: {e}")
            # Fallback về phương thức truyền thống
            response = self.advise_schedule(user_input)
            return self.format_response(response)

    def _extract_schedule_type(self, text: str) -> str:
        """Trích xuất loại lịch từ user input"""
        text_lower = text.lower()
        
        # Mapping các từ khóa với loại lịch
        schedule_types = {
            'họp': 'Lịch họp',
            'meeting': 'Lịch họp',
            'khám': 'Lịch khám',
            'appointment': 'Lịch hẹn',
            'đi ăn': 'Lịch ăn uống',
            'ăn': 'Lịch ăn uống',
            'học': 'Lịch học',
            'study': 'Lịch học',
            'làm việc': 'Lịch làm việc',
            'work': 'Lịch làm việc',
            'du lịch': 'Lịch du lịch',
            'travel': 'Lịch du lịch',
            'thể thao': 'Lịch thể thao',
            'sport': 'Lịch thể thao',
            'yoga': 'Lịch yoga',
            'gym': 'Lịch tập gym',
            'chơi game': 'Lịch giải trí',
            'game': 'Lịch giải trí',
            'xem phim': 'Lịch giải trí',
            'movie': 'Lịch giải trí'
        }
        
        # Tìm loại lịch phù hợp nhất
        for keyword, schedule_type in schedule_types.items():
            if keyword in text_lower:
                return schedule_type
        
        # Nếu không tìm thấy, dùng từ đầu tiên trong câu hoặc mặc định
        words = text_lower.split()
        if words:
            first_word = words[0]
            # Loại bỏ các từ không phù hợp
            if first_word not in ['tôi', 'muốn', 'cần', 'xin', 'vui', 'lòng', 'hãy', 'làm', 'cho', 'về']:
                return f"Lịch {first_word.capitalize()}"
        
        # Mặc định
        return "Lịch trình"

    def _extract_duration_minutes(self, text: str) -> int:
        """Trích xuất thời lượng từ text và trả về số phút"""
        # Tìm các pattern thời lượng
        patterns = [
            r'(\d+)\s*phút',
            r'(\d+)\s*ph',
            r'(\d+)\s*minutes?',
            r'(\d+)\s*mins?',
            r'(\d+)\s*tiếng',
            r'(\d+)\s*giờ',
            r'(\d+)\s*hours?',
            r'(\d+)\s*hrs?'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                duration = int(match.group(1))
                # Chuyển giờ thành phút
                if any(word in pattern for word in ['tiếng', 'giờ', 'hours?', 'hrs?']):
                    duration *= 60
                return duration
        
        # Mặc định 30 phút nếu không tìm thấy
        return 30

    def _format_schedules_for_gemini(self, schedules: List[Dict]) -> str:
        """Định dạng lịch trình để cung cấp context cho Gemini"""
        if not schedules:
            return "Không có lịch trình nào trong 3 ngày tới."
        
        formatted = []
        for schedule in schedules[:10]:  # Giới hạn 10 lịch để tránh context quá dài
            try:
                start = datetime.fromisoformat(schedule['start_time']).strftime('%d/%m %H:%M')
                end = datetime.fromisoformat(schedule['end_time']).strftime('%H:%M')
                formatted.append(f"- {schedule['title']}: {start} - {end}")
            except Exception:
                continue
        
        return "\n".join(formatted) if formatted else "Không có lịch trình nào."

    def __del__(self):
        if getattr(self, 'conn', None):
            self.conn.close()