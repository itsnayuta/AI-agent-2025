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
    # Chuẩn hóa thời gian truyền vào về UTC trước khi so sánh,
    # vì database lưu ở định dạng này.
    start_utc = start_time.astimezone(pytz.utc)
    end_utc = end_time.astimezone(pytz.utc)
    start_str = start_utc.isoformat()
    end_str = end_utc.isoformat()
    # Tìm kiếm các lịch trình mà khoảng thời gian của chúng giao nhau với khoảng thời gian đầu vào
    query = """
        SELECT COUNT(*) FROM schedules
        WHERE (? < end_time AND ? > start_time)
    """
    cursor.execute(query, (end_str, start_str))
    # Nếu số lượng lịch trình trùng lặp > 0, trả về False
    return cursor.fetchone()[0] == 0

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
        self.time_patterns = [
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
        ] + get_time_patterns(self.current_time)
        # Danh mục công việc và từ khóa ưu tiên
        self.task_categories = task_categories
        self.high_priority_keywords = ['gấp', 'urgent', 'quan trọng', 'important', 'khẩn cấp', 'deadline', 'hạn chót']
        self.low_priority_keywords = ['không gấp', 'có thể', 'nếu được', 'tùy ý']
        # giữ reference đến LLM/Gemini (nếu có) để sinh câu hỏi tự nhiên
        self.llm = llm
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

            # 1. Ưu tiên LLM gửi preferred_date, preferred_weekday
            suggested_time = self._resolve_preferred_date(preferred_date, preferred_weekday)

            # 2. Nếu chưa có thì tự parse từ text
            if suggested_time is None:
                suggested_time = self._extract_time(user_request)

            # 3. Nếu vẫn chưa có, fallback dựa trên preferred_time_of_day
            if suggested_time is None and preferred_time_of_day:
                suggested_time = self._default_time_from_tod(preferred_time_of_day)

            # 4. Nếu vẫn không có, yêu cầu thêm thông tin
            if suggested_time is None:
                return self._ask_for_more_info(user_request, duration_minutes, priority, duration_provided, priority_provided, preferred_time_of_day)

            adjusted_time, warnings = self._validate_business_time(suggested_time, duration_minutes, priority)
            alternatives = self._generate_alternative_times(adjusted_time, task_info)
            existing_schedules = self._get_schedules_for_day(adjusted_time)

            return {
                'main_suggestion': f"Đề xuất chính: {adjusted_time.strftime('%A, %d/%m/%Y lúc %H:%M')}",
                'duration': f"Thời lượng gợi ý: {duration_minutes} phút",
                'priority': f"Mức độ ưu tiên: {priority}",
                'warnings': warnings,
                'alternatives': alternatives,
                'existing_schedules': existing_schedules,
                'suggested_time': suggested_time,
                'adjusted_time': adjusted_time,
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
        elif end_time.hour >= business_end:
            warnings.append(f"Thời gian sau giờ làm việc. Đã điều chỉnh về 9h sáng hôm sau.")
            adjusted_time = (adjusted_time + timedelta(days=1)).replace(hour=9, minute=0)

        # Điều chỉnh nếu thời gian trùng giờ ăn trưa
        lunch_start, lunch_end = self.lunch_time
        if (lunch_start <= adjusted_time.hour < lunch_end) or (lunch_start < end_time.hour <= lunch_end):
            warnings.append(f"Thời gian trùng giờ ăn trưa. Đã điều chỉnh về {lunch_end}h.")
            adjusted_time = adjusted_time.replace(hour=lunch_end, minute=0)

        # Kiểm tra trùng lịch
        if not check_schedule_overlap(self.conn, adjusted_time, adjusted_time + timedelta(minutes=duration)):
            warnings.append("Thời gian này đã có lịch")
            adjusted_time = self._find_next_available_slot(adjusted_time, duration, priority)

        return adjusted_time, warnings

    def _find_next_available_slot(self, start_time: datetime, duration: int, priority: str) -> datetime:
        """
        Tìm kiếm khung giờ trống gần nhất trong vòng 7 ngày tới.
        Đã tích hợp logic dựa trên mức độ ưu tiên.
        """
        # Đảm bảo start_time có múi giờ
        if start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None:
            start_time = self.vietnam_tz.localize(start_time)
        search_date = start_time.date()
        max_search_days = 2 if priority == 'Cao' else 7
        for i in range(max_search_days):
            current_date = search_date + timedelta(days=i)
            # Bỏ qua cuối tuần
            if current_date.weekday() >= 5:
                continue
            schedules_on_day = self._get_schedules_for_day(datetime.combine(current_date, datetime.min.time()).replace(tzinfo=self.vietnam_tz))
            if not schedules_on_day:
                return datetime.combine(current_date, datetime.min.time()).replace(hour=self.business_hours[0], minute=0, tzinfo=self.vietnam_tz)
            sorted_schedules = sorted(schedules_on_day, key=lambda x: datetime.fromisoformat(x['start_time']))
            last_end_time = datetime.combine(current_date, datetime.min.time()).replace(hour=self.business_hours[0], minute=0, tzinfo=self.vietnam_tz)
            for schedule in sorted_schedules:
                # Đọc từ DB và chuẩn hóa múi giờ
                current_start = datetime.fromisoformat(schedule['start_time'])
                if current_start.tzinfo is None:
                    current_start = self.vietnam_tz.localize(current_start)
                if (current_start - last_end_time).total_seconds() >= duration * 60:
                    return last_end_time
                last_end_time = datetime.fromisoformat(schedule['end_time'])
                if last_end_time.tzinfo is None:
                    last_end_time = self.vietnam_tz.localize(last_end_time)
            end_of_business_day = datetime.combine(current_date, datetime.min.time()).replace(hour=self.business_hours[1], minute=0, tzinfo=self.vietnam_tz)
            if (end_of_business_day - last_end_time).total_seconds() >= duration * 60:
                return last_end_time
        raise Exception("Không tìm thấy khung giờ trống phù hợp trong vòng 7 ngày tới.")

    def _generate_alternative_times(self, base_time: datetime, task_info: Dict) -> List[str]:
        """Tạo các gợi ý thời gian thay thế."""
        alternatives = []
        best_start, best_end = task_info.get('best_time', self.business_hours)
        suggestion_hours = sorted([best_start, best_start + 2, best_end - 1])
        for hour in suggestion_hours:
            alt_time = base_time.replace(hour=hour, minute=0)
            if alt_time > self.current_time and check_schedule_overlap(self.conn, alt_time, alt_time + timedelta(minutes=task_info['duration'])):
                alternatives.append(alt_time.strftime('%H:%M %A, %d/%m/%Y'))
        next_day = base_time + timedelta(days=1)
        if next_day.weekday() >= 5:
            days_to_add = 7 - next_day.weekday()
            next_day += timedelta(days=days_to_add)
        alt_time = next_day.replace(hour=self.business_hours[0], minute=0)
        if check_schedule_overlap(self.conn, alt_time, alt_time + timedelta(minutes=task_info['duration'])):
            alternatives.append(alt_time.strftime('%H:%M %A, %d/%m/%Y'))
        return list(set(alternatives))[:3]

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
            result = f"### Gợi ý Lịch trình\n---\n"
            result += f"**{response['main_suggestion']}**\n"
            result += f"**{response['duration']}**\n"
            result += f"**{response['priority']}**\n"
            if response.get('existing_schedules'):
                result += "\n### Lịch trình đã có trong ngày\n---\n"
                for schedule in response['existing_schedules']:
                    start_time_str = datetime.fromisoformat(schedule['start_time']).strftime('%H:%M')
                    end_time_str = datetime.fromisoformat(schedule['end_time']).strftime('%H:%M')
                    result += f"  - **{schedule['title']}**: từ {start_time_str} đến {end_time_str}\n"
            if response.get('warnings'):
                result += "\n### Lưu ý\n---\n"
                for warning in response['warnings']:
                    result += f"  - {warning}\n"
            if response.get('alternatives'):
                result += "\n### Thời gian thay thế\n---\n"
                for alt in response['alternatives']:
                    result += f"  - {alt}\n"
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

    def __del__(self):
        if getattr(self, 'conn', None):
            self.conn.close()