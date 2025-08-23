import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import sqlite3

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

    start_str = start_time.isoformat()
    end_str = end_time.isoformat()

    # Tìm kiếm các lịch trình mà khoảng thời gian của chúng giao nhau với khoảng thời gian đầu vào
    query = """
        SELECT COUNT(*) FROM schedules
        WHERE (? < end_time AND ? > start_time)
    """
    cursor.execute(query, (start_str, end_str))

    # Nếu số lượng lịch trình trùng lặp > 0, trả về False
    return cursor.fetchone()[0] == 0


class ScheduleAdvisor:
    """
    Lớp ScheduleAdvisor cung cấp các chức năng gợi ý lịch trình thông minh:
    - Phân tích yêu cầu của người dùng
    - Kiểm tra lịch trống, đề xuất thời gian
    - Nếu thông tin chưa đủ (đặc biệt là thời gian), sinh câu hỏi làm rõ (ưu tiên dùng LLM nếu có)
    """
    def __init__(self, db_path='database/schedule.db', llm=None):  # [CHANGED] thêm tham số llm
        # Thiết lập thời gian hiện tại theo múi giờ Việt Nam
        from utils.timezone_utils import get_vietnam_now
        self.current_time = get_vietnam_now()

        # Thiết lập giờ làm việc và giờ nghỉ trưa
        self.business_hours = (8, 17)  # 8h sáng đến 17h chiều
        self.lunch_time = (12, 13)     # 12h trưa đến 13h chiều

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
                    if result and result > self.current_time:
                        return result
                except (ValueError, TypeError):
                    continue
        return None

    # trích xuất thời lượng từ text, trả về (minutes, provided_by_user: bool)
    def _extract_duration_from_text(self, text: str) -> Tuple[Optional[int], bool]:
        text_lower = text.lower()
        # Ví dụ: "2 tiếng", "1 giờ 30", "90 phút"
        m = re.search(r'(\d{1,2})\s*(tiếng|giờ)\s*(\d{1,2})?\s*(phút)?', text_lower)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(3) or 0)
            return hours * 60 + minutes, True
        m = re.search(r'(\d{1,3})\s*phút', text_lower)
        if m:
            return int(m.group(1)), True
        return None, False

    # phát hiện "sáng/chiều/tối" trong text
    def _detect_preferred_tod_in_text(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if 'sáng' in text_lower:
            return 'sáng'
        if 'chiều' in text_lower:
            return 'chiều'
        if 'tối' in text_lower:
            return 'tối'
        return None

    # chuẩn hóa priority từ input (vd: "cao"/"Cao")
    def _normalize_priority(self, p: Optional[str], text: str) -> Tuple[str, bool]:
        provided = False
        if p:
            provided = True
            v = p.strip().lower()
        else:
            v = ''
        if not v:
            # suy từ text
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

    # chuẩn hóa duration: nhận int/phút hoặc chuỗi "2 tiếng"
    def _normalize_duration(self, duration_arg: Optional[Union[int, str]], user_request: str, default_minutes: int) -> Tuple[int, bool]:
        if isinstance(duration_arg, int):
            return duration_arg, True
        if isinstance(duration_arg, str):
            # parse chuỗi
            dur_text = duration_arg.lower().strip()
            m = re.search(r'(\d{1,2})\s*(tiếng|giờ)\s*(\d{1,2})?\s*(phút)?', dur_text)
            if m:
                hours = int(m.group(1))
                minutes = int(m.group(3) or 0)
                return hours * 60 + minutes, True
            m = re.search(r'(\d{1,3})\s*phút', dur_text)
            if m:
                return int(m.group(1)), True
        # không có trong arg => thử từ user_request
        parsed, provided = self._extract_duration_from_text(user_request)
        if parsed is not None:
            return parsed, provided
        return default_minutes, False

    # sinh câu hỏi làm rõ (ưu tiên dùng LLM, fallback template)
    def _generate_followup_question(self, missing_fields: List[str], user_request: str) -> str:
        # Mặc định: template ngắn gọn
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

        # Nếu có LLM thì yêu cầu LLM viết lại câu hỏi tự nhiên hơn
        if self.llm:
            try:
                prompt = (
                    "Người dùng đang yêu cầu tư vấn lịch trình.\n"
                    f"Yêu cầu người dùng: {user_request}\n"
                    f"Các trường còn thiếu: {', '.join(missing_fields)}\n"
                    "Hãy viết 1-2 câu hỏi ngắn gọn, thân thiện bằng tiếng Việt để hỏi thêm thông tin, "
                    "kèm 2-3 ví dụ câu trả lời mẫu theo đúng ngữ cảnh (không dùng bullet nếu không cần).\n"
                )
                # Tương thích nhiều kiểu client Gemini/LLM khác nhau
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
                # nếu client trả về object có .text
                if hasattr(out, "text"):
                    return str(out.text).strip()
            except Exception:
                pass
        return template

    def _categorize_task_and_priority(self, text: str) -> Dict[str, Union[str, int, Tuple[int, int]]]:
        """Phân loại công việc và xác định mức độ ưu tiên dựa trên từ khóa."""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in self.high_priority_keywords):
            priority = 'Cao'
        elif any(keyword in text_lower for keyword in self.low_priority_keywords):
            priority = 'Thấp'
        else:
            priority = 'Bình thường'

        for category, info in self.task_categories.items():
            if any(keyword in text_lower for keyword in info['keywords']):
                info = dict(info)  # tránh mutate gốc
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
        Đã thêm tham số 'priority' để xét mức độ ưu tiên.
        """
        warnings = []
        adjusted_time = suggested_time

        # Kiểm tra cuối tuần
        if suggested_time.weekday() >= 5:
            warnings.append("Thời gian này rơi vào cuối tuần.")

        start_hour = suggested_time.hour
        end_time = suggested_time + timedelta(minutes=duration)

        business_start, business_end = self.business_hours

        # Điều chỉnh nếu thời gian nằm ngoài giờ làm việc
        if start_hour < business_start:
            warnings.append(f"Thời gian trước giờ làm việc. Đã điều chỉnh về {business_start}h.")
            adjusted_time = suggested_time.replace(hour=business_start, minute=0)
        elif start_hour >= business_end:
            warnings.append(f"Thời gian sau giờ làm việc. Đã điều chỉnh về 9h sáng hôm sau.")
            adjusted_time = (suggested_time + timedelta(days=1)).replace(hour=9, minute=0)

        # Điều chỉnh nếu thời gian trùng giờ ăn trưa
        lunch_start, lunch_end = self.lunch_time
        if (lunch_start <= start_hour < lunch_end) or (lunch_start < end_time.hour <= lunch_end):
            warnings.append(f"Thời gian trùng giờ ăn trưa. Đã điều chỉnh về {lunch_end}h.")
            adjusted_time = suggested_time.replace(hour=lunch_end, minute=0)

        # Kiểm tra trùng lịch
        if not check_schedule_overlap(self.conn, adjusted_time, adjusted_time + timedelta(minutes=duration)):
            warnings.append("Thời gian này đã có lịch")
            # Gọi hàm tìm kiếm với mức độ ưu tiên
            adjusted_time = self._find_next_available_slot(adjusted_time, duration, priority)

        return adjusted_time, warnings

    def _find_next_available_slot(self, start_time: datetime, duration: int, priority: str) -> datetime:
        """
        Tìm kiếm khung giờ trống gần nhất trong vòng 7 ngày tới.
        Đã tích hợp logic dựa trên mức độ ưu tiên.
        """
        search_date = start_time.date()

        # Công việc ưu tiên cao sẽ được tìm kiếm trong 2 ngày đầu tiên
        # Công việc ưu tiên thấp sẽ được tìm kiếm trong 7 ngày
        max_search_days = 2 if priority == 'Cao' else 7

        for _ in range(max_search_days):
            schedules_on_day = self._get_schedules_for_day(datetime.combine(search_date, datetime.min.time()))

            if not schedules_on_day:
                # Nếu ngày không có lịch, đề xuất khung giờ mặc định
                return datetime.combine(search_date, datetime.min.time()).replace(hour=self.business_hours[0], minute=0)

            sorted_schedules = sorted(schedules_on_day, key=lambda x: datetime.fromisoformat(x['start_time']))

            # Khung giờ bắt đầu có thể là đầu giờ làm việc
            last_end_time = datetime.combine(search_date, datetime.min.time()).replace(hour=self.business_hours[0], minute=0)

            for schedule in sorted_schedules:
                current_start = datetime.fromisoformat(schedule['start_time'])

                # Tính khoảng trống giữa hai lịch
                if (current_start - last_end_time).total_seconds() >= duration * 60:
                    return last_end_time

                last_end_time = datetime.fromisoformat(schedule['end_time'])

            # Kiểm tra khoảng trống cuối cùng trong ngày làm việc
            end_of_business_day = datetime.combine(search_date, datetime.min.time()).replace(hour=self.business_hours[1], minute=0)
            if (end_of_business_day - last_end_time).total_seconds() >= duration * 60:
                return last_end_time

            # Chuyển sang ngày tiếp theo nếu không tìm thấy
            search_date += timedelta(days=1)
            # Bỏ qua cuối tuần
            if search_date.weekday() >= 5:
                search_date += timedelta(days=(7 - search_date.weekday()))

        # Xử lý trường hợp không tìm thấy khung giờ phù hợp
        raise Exception("Không tìm thấy khung giờ trống phù hợp trong vòng 7 ngày tới.")

    def _generate_alternative_times(self, base_time: datetime, task_info: Dict) -> List[str]:
        """Tạo các gợi ý thời gian thay thế."""
        alternatives = []
        best_start, best_end = task_info.get('best_time', self.business_hours)

        # Gợi ý các khung giờ khác trong cùng ngày
        suggestion_hours = sorted([best_start, best_start + 2, best_end - 1])

        for hour in suggestion_hours:
            alt_time = base_time.replace(hour=hour, minute=0)
            if alt_time > self.current_time and check_schedule_overlap(self.conn, alt_time, alt_time + timedelta(minutes=task_info['duration'])):
                alternatives.append(alt_time.strftime('%H:%M %A, %d/%m/%Y'))

        # Gợi ý thời gian vào ngày tiếp theo
        next_day = base_time + timedelta(days=1)
        # Bỏ qua cuối tuần
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

    def advise_schedule(self, user_request: str,
                        preferred_time_of_day: str = None,
                        duration: Optional[Union[int, str]] = None,
                        priority: Optional[str] = None) -> Dict[str, Union[str, List[str]]]:
        """
        - Nếu thiếu thông tin quan trọng (đặc biệt là thời gian) => sinh câu hỏi làm rõ (LLM nếu có).
        - Khi đã đủ thông tin => đề xuất như cũ.
        """
        try:
            # Lấy thông tin gợi ý mặc định theo category
            task_info = self._categorize_task_and_priority(user_request)

            # Chuẩn hóa duration: ưu tiên từ arg hoặc text, fallback category
            duration_minutes, duration_provided = self._normalize_duration(duration, user_request, task_info['duration'])
            task_info['duration'] = duration_minutes  # đồng bộ

            # Chuẩn hóa priority: ưu tiên arg, fallback text/category
            priority_norm, priority_provided = self._normalize_priority(priority, user_request)
            priority = priority_norm

            # Ưu tiên preferred_time_of_day từ arg hoặc text
            preferred_from_text = self._detect_preferred_tod_in_text(user_request)
            preferred_time_of_day = (preferred_time_of_day or preferred_from_text)

            # Lấy thời điểm cụ thể nếu có thể
            suggested_time = None
            if preferred_time_of_day:
                # Nếu người dùng chỉ nêu khung giờ, gợi thời điểm gần nhất trong tương lai theo khung đó
                base = self.current_time
                if preferred_time_of_day.lower() == 'sáng':
                    suggested_time = base.replace(hour=9, minute=0, second=0, microsecond=0)
                elif preferred_time_of_day.lower() == 'chiều':
                    suggested_time = base.replace(hour=14, minute=0, second=0, microsecond=0)
                elif preferred_time_of_day.lower() == 'tối':
                    suggested_time = base.replace(hour=19, minute=0, second=0, microsecond=0)
                if suggested_time and suggested_time <= self.current_time:
                    suggested_time += timedelta(days=1)

            # Nếu chưa có, thử extract thời gian cụ thể từ câu
            if suggested_time is None:
                suggested_time = self._extract_time(user_request)

            # Kiểm tra thiếu thông tin và hỏi làm rõ trước khi tư vấn
            missing_fields: List[str] = []
            if suggested_time is None:
                missing_fields.append('time')  # thiếu ngày/giờ cụ thể
            if not preferred_time_of_day:
                missing_fields.append('preferred_time_of_day')
            if not duration_provided:
                missing_fields.append('duration')
            if not priority_provided:
                missing_fields.append('priority')

            # Quy tắc quyết định: nếu thiếu 'time' => hỏi trước (bắt buộc)
            # Các trường khác có thể mặc định, nhưng vẫn hỏi gộp để nâng chất lượng tư vấn.
            if 'time' in missing_fields:
                question = self._generate_followup_question(missing_fields, user_request)  # ưu tiên dùng LLM
                return {
                    'status': 'need_more_info',
                    'main_suggestion': "Chưa đủ thông tin để tư vấn.",
                    'duration': f"Thời lượng mặc định hiện tại: {duration_minutes} phút",
                    'priority': f"Mức độ ưu tiên hiện tại: {priority}",
                    'question': question,                 # câu hỏi gợi ý gửi người dùng
                    'missing_fields': missing_fields       # để phía UI/agent biết cần thu thập gì
                }

            # --- Đủ để tư vấn ---
            adjusted_time, warnings = self._validate_business_time(suggested_time, duration_minutes, priority)
            alternatives = self._generate_alternative_times(adjusted_time, task_info)
            existing_schedules = self._get_schedules_for_day(adjusted_time)

            main_suggestion = f"Đề xuất chính: {adjusted_time.strftime('%A, %d/%m/%Y lúc %H:%M')}"
            duration_info = f"Thời lượng gợi ý: {duration_minutes} phút"
            priority_info = f"Mức độ ưu tiên: {priority}"

            response = {
                'main_suggestion': main_suggestion,
                'duration': duration_info,
                'priority': priority_info,
                'warnings': warnings,
                'alternatives': alternatives,
                'existing_schedules': existing_schedules,
                'suggested_time': suggested_time,
                'adjusted_time': adjusted_time,
                'status': 'success'
            }
        except Exception as e:
            response = {
                'main_suggestion': "Có lỗi xảy ra khi phân tích.",
                'error': str(e),
                'status': 'error'
            }
        return response

    def format_response(self, response: Dict) -> str:
        """Định dạng phản hồi thành chuỗi dễ đọc."""
        if response['status'] == 'success':
            result = f"### Gợi ý Lịch trình\n---\n"
            result += f"**{response['main_suggestion']}**\n"
            result += f"**{response['duration']}**\n"
            result += f"**{response['priority']}**\n"

            if response.get('existing_schedules'):
                result += "\n### Lịch trình đã có trong ngày\n---\n"
                for schedule in response['existing_schedules']:
                    # Lấy start_time và end_time từ chuỗi ISO 8601
                    start_time_str = datetime.fromisoformat(schedule['start_time']).strftime('%H:%M')
                    end_time_str = datetime.fromisoformat(schedule['end_time']).strftime('%H:%M')
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
            # [CHANGED] Nếu có 'question' thì hiển thị câu hỏi cá nhân hóa thay vì template cũ
            result = f"### Cần thêm thông tin\n---\n"
            result += f"**{response['main_suggestion']}**\n"
            if 'question' in response:
                result += f"\n{response['question']}\n"
                # gợi ý nhanh để user bấm lựa chọn (nếu muốn)
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
        """Đóng kết nối DB khi đối tượng bị hủy."""
        if getattr(self, 'conn', None):
            self.conn.close()
