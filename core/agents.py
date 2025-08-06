def advise_schedule(user_info):
    import re
    from datetime import datetime, timedelta

    time_patterns = [
        (r"chiều mai", lambda: (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0)),
        (r"sáng mai", lambda: (datetime.now() + timedelta(days=1)).replace(hour=8, minute=0)),
        (r"sáng thứ ([2-7])", lambda m: datetime.now() + timedelta(days=(int(m.group(1)) - datetime.now().isoweekday()))),
        (r"chiều thứ ([2-7])", lambda m: (datetime.now() + timedelta(days=(int(m.group(1)) - datetime.now().isoweekday()))).replace(hour=14, minute=0)),
    ]

    suggested_time = None
    for pattern, func in time_patterns:
        match = re.search(pattern, user_info, re.IGNORECASE)
        if match:
            if callable(func):
                try:
                    suggested_time = func(match) if match.groups() else func()
                except Exception:
                    suggested_time = None
            break

    priority = "Bình thường"
    if re.search(r"quan trọng|gấp|ưu tiên", user_info, re.IGNORECASE):
        priority = "Cao"

    # Đề xuất lịch trình
    if suggested_time:
        time_str = suggested_time.strftime('%A, %d/%m/%Y %H:%M')
        return f"Đề xuất: Bạn nên đặt lịch vào {time_str} (Ưu tiên: {priority})"
    else:
        return f"Không nhận diện được thời gian cụ thể. Vui lòng cung cấp thêm thông tin. (Ưu tiên: {priority})"
