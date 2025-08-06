import re
from datetime import datetime, timedelta
from typing import Optional

def parse_weekday(match, current_time, weekday_map):
    weekday_str = match.group(1).lower().replace(' ', '')
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (current_time + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_weekday_this_week(match, current_time, weekday_map):
    weekday_str = match.group(1).lower().replace(' ', '')
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return (current_time + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_weekday_next_week(match, current_time, weekday_map):
    weekday_str = match.group(1).lower().replace(' ', '')
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday() + 7
    return (current_time + timedelta(days=days_ahead)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_time_period_day(match, current_time):
    period = match.group(1).lower()
    day_ref = match.group(2).lower().replace(' ', '')
    if 'hômnay' in day_ref or 'today' in day_ref:
        base_date = current_time
    elif 'mai' in day_ref or 'tomorrow' in day_ref:
        base_date = current_time + timedelta(days=1)
    elif 'ngàykia' in day_ref:
        base_date = current_time + timedelta(days=2)
    else:
        return None
    if period == 'sáng':
        hour = 8
    elif period == 'chiều':
        hour = 14
    elif period == 'tối':
        hour = 19
    else:
        hour = 8
    return base_date.replace(hour=hour, minute=0, second=0, microsecond=0)

def parse_time_period_weekday(match, current_time, weekday_map):
    period = match.group(1).lower()
    weekday_str = match.group(2).lower().replace(' ', '')
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    base_date = current_time + timedelta(days=days_ahead)
    if period == 'sáng':
        hour = 8
    elif period == 'chiều':
        hour = 14
    elif period == 'tối':
        hour = 19
    else:
        hour = 8
    return base_date.replace(hour=hour, minute=0, second=0, microsecond=0)

def parse_after_days(match, current_time):
    days = int(match.group(1))
    return (current_time + timedelta(days=days)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_after_weeks(match, current_time):
    weeks = int(match.group(1))
    return (current_time + timedelta(weeks=weeks)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_after_months(match, current_time):
    months = int(match.group(1))
    target_month = current_time.month + months
    target_year = current_time.year
    while target_month > 12:
        target_month -= 12
        target_year += 1
    return datetime(target_year, target_month, current_time.day, 8, 0)

def parse_time_period_weekday_with_hour(match, current_time, weekday_map):
    period = match.group(1).lower()
    weekday_str = match.group(2).lower().replace(' ', '')
    hour = int(match.group(3)) if match.group(3) else 8
    minute = int(match.group(4)) if match.group(4) else 0
    
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    
    days_ahead = target_weekday - current_time.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    base_date = current_time + timedelta(days=days_ahead)
    
    if period == 'sáng':
        final_hour = hour if 6 <= hour <= 11 else 8
    elif period == 'chiều':
        if 12 <= hour <= 17:
            final_hour = hour
        elif hour < 12:
            final_hour = hour + 12 if hour + 12 <= 17 else 14 
            final_hour = 14  
    elif period == 'tối':
        if 18 <= hour <= 23:
            final_hour = hour 
        elif 6 <= hour <= 11:
            final_hour = hour + 12 
        elif 12 <= hour <= 17:
            final_hour = hour + 6 if hour + 6 <= 23 else 19
        else:
            final_hour = 19
    else:
        final_hour = hour
    
    final_hour = max(0, min(23, final_hour))
    
    return base_date.replace(hour=final_hour, minute=minute, second=0, microsecond=0)

def parse_weekday_time(match, current_time, weekday_map):
    weekday_str = match.group(1).lower().replace(' ', '')
    hour = int(match.group(2)) if match.group(2) else 8
    minute = int(match.group(3)) if match.group(3) else 0
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday()
    if days_ahead < 0:
        days_ahead += 7
    target_date = current_time + timedelta(days=days_ahead)
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

def parse_time_weekday_this_week(match, current_time, weekday_map):
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    weekday_str = match.group(3).lower().replace(' ', '')
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday()
    if days_ahead < 0:
        days_ahead += 7
    target_date = current_time + timedelta(days=days_ahead)
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

def parse_time_weekday_next_week(match, current_time, weekday_map):
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    weekday_str = match.group(3).lower().replace(' ', '')
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday() + 7
    target_date = current_time + timedelta(days=days_ahead)
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

def parse_time_weekday(match, current_time, weekday_map):
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    weekday_str = match.group(3).lower().replace(' ', '')
    target_weekday = weekday_map.get(weekday_str)
    if target_weekday is None:
        return None
    days_ahead = target_weekday - current_time.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    target_date = current_time + timedelta(days=days_ahead)
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
def parse_specific_date(match, current_time):
    try:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else current_time.year
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return None
        target_date = datetime(year, month, day, 8, 0)
        if target_date < current_time:
            target_date = target_date.replace(year=year + 1)
        return target_date
    except (ValueError, TypeError):
        return None

def parse_time(match, current_time):
    try:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        target_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_time <= current_time:
            target_time += timedelta(days=1)
        return target_time
    except (ValueError, TypeError):
        return None

def parse_today(match, current_time):
    return current_time.replace(hour=8, minute=0, second=0, microsecond=0)

def parse_tomorrow(match, current_time):
    return (current_time + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_day_after_tomorrow(match, current_time):
    return (current_time + timedelta(days=2)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_next_week(match, current_time):
    return (current_time + timedelta(days=7)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_this_week(match, current_time):
    days_until_monday = 7 - current_time.weekday()
    if days_until_monday == 7:
        days_until_monday = 0
    return (current_time + timedelta(days=days_until_monday)).replace(hour=8, minute=0, second=0, microsecond=0)

def parse_next_month(match, current_time):
    next_month = current_time.month + 1
    year = current_time.year
    if next_month > 12:
        next_month = 1
        year += 1
    return datetime(year, next_month, 1, 8, 0)

def get_time_patterns(current_time):
    return [
        (r"ngày\s*(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{4}))?", lambda m: parse_specific_date(m, current_time)),
        (r"(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{4}))?", lambda m: parse_specific_date(m, current_time)),
        (r"(\d{1,2})(?:h|:)(\d{2})?(?:\s*(?:sáng|chiều|tối))?", lambda m: parse_time(m, current_time)),
        (r"(\d{1,2})\s*giờ\s*(\d{2})?\s*phút?", lambda m: parse_time(m, current_time)),
        (r"(?:hôm\s*nay|today)", lambda m: parse_today(m, current_time)),
        (r"(?:ngày\s*mai|mai|tomorrow)", lambda m: parse_tomorrow(m, current_time)),
        (r"(?:ngày\s*kia|послезавтра)", lambda m: parse_day_after_tomorrow(m, current_time)),
        (r"(?:tuần\s*sau|next\s*week)", lambda m: parse_next_week(m, current_time)),
        (r"(?:tuần\s*này|this\s*week)", lambda m: parse_this_week(m, current_time)),
        (r"(?:tháng\s*sau|next\s*month)", lambda m: parse_next_month(m, current_time)),
    ]
