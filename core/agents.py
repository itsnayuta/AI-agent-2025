import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from utils.time_patterns import (
            get_time_patterns,
            parse_weekday,
            parse_weekday_this_week,
            parse_weekday_next_week,
            parse_time_period_day,
            parse_time_period_weekday,
            parse_after_days,
            parse_after_weeks,
            parse_after_months
        )
from utils.task_categories import task_categories

class ScheduleAdvisor:
    def __init__(self):
        self.current_time = datetime.now()
        self.business_hours = (8, 17)
        self.lunch_time = (12, 13)
        self.weekday_map = {
            'chủ nhật': 6, 'cn': 6, 'chủnhật': 6,
            'thứ hai': 0, 't2': 0, 'thứ 2': 0, 'thứhai': 0, 'thứ2': 0,
            'thứ ba': 1, 't3': 1, 'thứ 3': 1, 'thứba': 1, 'thứ3': 1,
            'thứ tư': 2, 't4': 2, 'thứ 4': 2, 'thứtư': 2, 'thứ4': 2,
            'thứ năm': 3, 't5': 3, 'thứ 5': 3, 'thứnăm': 3, 'thứ5': 3,
            'thứ sáu': 4, 't6': 4, 'thứ 6': 4, 'thứsáu': 4, 'thứ6': 4,
            'thứ bảy': 5, 't7': 5, 'thứ 7': 5, 'thứbảy': 5, 'thứ7': 5
        }
        self.time_patterns = [
            # Ưu tiên nhận diện 'thứ ... (tuần ...) (lúc|vào) ...h' với khoảng trắng linh hoạt
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*(?:tuần\s*này|tuần\s*sau)?\s*(?:lúc|vào)?\s*(\d{1,2})(?:h|:)?(\d{2})?", lambda m: self._parse_weekday_time(m)),
            (r"(\d{1,2})(?:h|:)?(\d{2})?\s*(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*này", lambda m: self._parse_time_weekday_this_week(m)),
            (r"(\d{1,2})(?:h|:)?(\d{2})?\s*(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*sau", lambda m: self._parse_time_weekday_next_week(m)),
            (r"(\d{1,2})(?:h|:)?(\d{2})?\s*(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])", lambda m: self._parse_time_weekday(m)),
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*này", lambda m: parse_weekday_this_week(m, self.current_time, self.weekday_map)),
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])\s*tuần\s*sau", lambda m: parse_weekday_next_week(m, self.current_time, self.weekday_map)),
            (r"(thứ\s*[2-7]|chủ\s*nhật|cn|t[2-7])", lambda m: parse_weekday(m, self.current_time, self.weekday_map)),
            (r"(sáng|chiều|tối)\s*(hôm\s*nay|mai|ngày\s*kia)", lambda m: parse_time_period_day(m, self.current_time)),
            (r"(sáng|chiều|tối)\s*(thứ\s*[2-7]|chủ\s*nhật)", lambda m: parse_time_period_weekday(m, self.current_time, self.weekday_map)),
            (r"sau\s*(\d+)\s*ngày", lambda m: parse_after_days(m, self.current_time)),
            (r"sau\s*(\d+)\s*tuần", lambda m: parse_after_weeks(m, self.current_time)),
            (r"sau\s*(\d+)\s*tháng", lambda m: parse_after_months(m, self.current_time)),
        ] + get_time_patterns(self.current_time)
        
        self.task_categories = task_categories

    def _parse_weekday_time(self, match):
        """Parse pattern: thứ 2 lúc 14h, thứ 7 lúc 12h"""
        weekday_str = match.group(1).lower().replace(' ', '')
        hour = int(match.group(2)) if match.group(2) else 8
        minute = int(match.group(3)) if match.group(3) else 0
        target_weekday = self.weekday_map.get(weekday_str)
        if target_weekday is None:
            return None
        days_ahead = target_weekday - self.current_time.weekday()
        if days_ahead < 0:
            # Nếu ngày đã qua trong tuần này thì hiểu là tuần sau
            days_ahead += 7
        target_date = self.current_time + timedelta(days=days_ahead)
        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _parse_time_weekday_this_week(self, match):
        """Parse pattern: 12h thứ 7 tuần này"""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        weekday_str = match.group(3).lower().replace(' ', '')
        
        target_weekday = self.weekday_map.get(weekday_str)
        if target_weekday is None:
            return None
            
        days_ahead = target_weekday - self.current_time.weekday()
        if days_ahead < 0:
            days_ahead += 7
            
        target_date = self.current_time + timedelta(days=days_ahead)
        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _parse_time_weekday_next_week(self, match):
        """Parse pattern: 12h thứ 7 tuần sau"""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        weekday_str = match.group(3).lower().replace(' ', '')
        
        target_weekday = self.weekday_map.get(weekday_str)
        if target_weekday is None:
            return None
            
        days_ahead = target_weekday - self.current_time.weekday() + 7
        target_date = self.current_time + timedelta(days=days_ahead)
        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _parse_time_weekday(self, match):
        """Parse pattern: 12h thứ 7"""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        weekday_str = match.group(3).lower().replace(' ', '')
        
        target_weekday = self.weekday_map.get(weekday_str)
        if target_weekday is None:
            return None
            
        days_ahead = target_weekday - self.current_time.weekday()
        if days_ahead <= 0:
            days_ahead += 7
            
        target_date = self.current_time + timedelta(days=days_ahead)
        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _extract_time(self, text: str) -> Optional[datetime]:
        text_lower = text.lower()
        for pattern, parser in self.time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    result = parser(match)
                    if result:
                        # Nếu kết quả là quá khứ thì không trả về
                        if result > self.current_time:
                            return result
                        else:
                            return None
                except Exception:
                    continue
        return None

    def _categorize_task(self, text: str) -> Dict[str, Union[str, int, Tuple[int, int]]]:
        text_lower = text.lower()
        for category, info in self.task_categories.items():
            if any(keyword in text_lower for keyword in info['keywords']):
                return info
        return {
            'duration': 60,
            'priority': 'Bình thường',
            'best_time': (9, 17)
        }

    def _analyze_priority(self, text: str) -> str:
        text_lower = text.lower()
        high_priority_keywords = ['gấp', 'urgent', 'quan trọng', 'important', 'khẩn cấp', 'deadline', 'hạn chót']
        low_priority_keywords = ['không gấp', 'có thể', 'nếu được', 'tùy ý']
        if any(keyword in text_lower for keyword in high_priority_keywords):
            return 'Cao'
        elif any(keyword in text_lower for keyword in low_priority_keywords):
            return 'Thấp'
        else:
            return 'Bình thường'

    def _validate_business_time(self, suggested_time: datetime) -> Tuple[datetime, List[str]]:
        warnings = []
        adjusted_time = suggested_time
        if suggested_time.weekday() >= 5:
            warnings.append("⚠️ Thời gian rơi vào cuối tuần")
        hour = suggested_time.hour
        if hour < self.business_hours[0]:
            warnings.append("⚠️ Trước giờ làm việc, gợi ý điều chỉnh về 8h")
            adjusted_time = suggested_time.replace(hour=8, minute=0)
        elif hour > self.business_hours[1]:
            warnings.append("⚠️ Sau giờ làm việc, gợi ý điều chỉnh về 9h ngày hôm sau")
            adjusted_time = (suggested_time + timedelta(days=1)).replace(hour=9, minute=0)
        if self.lunch_time[0] <= hour < self.lunch_time[1]:
            warnings.append("⚠️ Trùng giờ ăn trưa, gợi ý điều chỉnh về 13h")
            adjusted_time = suggested_time.replace(hour=13, minute=0)
        return adjusted_time, warnings

    def _generate_alternative_times(self, base_time: datetime, task_info: Dict) -> List[str]:
        alternatives = []
        best_start, best_end = task_info.get('best_time', (9, 17))
        for hour in [best_start, (best_start + best_end) // 2, best_end - 1]:
            alt_time = base_time.replace(hour=hour, minute=0)
            if alt_time > self.current_time:
                alternatives.append(alt_time.strftime('%d/%m/%Y %H:%M'))
        next_day = base_time + timedelta(days=1)
        alternatives.append(next_day.replace(hour=9, minute=0).strftime('%d/%m/%Y %H:%M'))
        return alternatives[:3]

    def advise_schedule(self, user_input: str) -> Dict[str, Union[str, List[str]]]:
        try:
            suggested_time = self._extract_time(user_input)
            task_info = self._categorize_task(user_input)
            priority = self._analyze_priority(user_input)
            if suggested_time:
                adjusted_time, warnings = self._validate_business_time(suggested_time)
                alternatives = self._generate_alternative_times(adjusted_time, task_info)
                main_suggestion = f"📅 **Đề xuất chính:** {adjusted_time.strftime('%A, %d/%m/%Y lúc %H:%M') }"
                duration_info = f"⏱️ **Thời lượng gợi ý:** {task_info['duration']} phút"
                priority_info = f"🎯 **Mức độ ưu tiên:** {priority}"
                response = {
                    'main_suggestion': main_suggestion,
                    'duration': duration_info,
                    'priority': priority_info,
                    'warnings': warnings,
                    'alternatives': alternatives,
                    'status': 'success'
                }
            else:
                response = {
                    'main_suggestion': "❌ **Không nhận diện được thời gian cụ thể**",
                    'duration': f"⏱️ **Thời lượng gợi ý:** {task_info['duration']} phút",
                    'priority': f"🎯 **Mức độ ưu tiên:** {priority}",
                    'suggestions': [
                        "Hãy thử các cách diễn đạt như:",
                        "• 'ngày mai lúc 9h'",
                        "• 'thứ 3 tuần sau'",
                        "• 'chiều thứ 5'",
                        "• '15/8 lúc 14h'"
                    ],
                    'status': 'need_more_info'
                }
        except Exception as e:
            response = {
                'main_suggestion': "❌ **Có lỗi xảy ra khi phân tích**",
                'error': str(e),
                'status': 'error'
            }
        return response

    def format_response(self, response: Dict) -> str:
        if response['status'] == 'success':
            result = f"{response['main_suggestion']}\n"
            result += f"{response['duration']}\n"
            result += f"{response['priority']}\n"
            if response.get('warnings'):
                result += "\n⚠️ **Lưu ý:**\n"
                for warning in response['warnings']:
                    result += f"  {warning}\n"
            if response.get('alternatives'):
                result += "\n🔄 **Thời gian thay thế:**\n"
                for alt in response['alternatives']:
                    result += f"  • {alt}\n"
        elif response['status'] == 'need_more_info':
            result = f"{response['main_suggestion']}\n"
            result += f"{response['duration']}\n"
            result += f"{response['priority']}\n\n"
            if response.get('suggestions'):
                for suggestion in response['suggestions']:
                    result += f"{suggestion}\n"
        else:
            result = f"{response['main_suggestion']}\n"
            result += f"Chi tiết lỗi: {response.get('error', 'Không xác định')}"
        return result