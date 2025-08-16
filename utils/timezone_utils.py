"""
Timezone utilities for Vietnam timezone (UTC+7)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# Vietnam timezone (UTC+7)
VIETNAM_TZ = timezone(timedelta(hours=7))

def get_vietnam_now() -> datetime:
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    return datetime.now(VIETNAM_TZ)

def get_vietnam_time(dt: Optional[datetime] = None) -> datetime:
    """Chuyển đổi datetime sang múi giờ Việt Nam"""
    if dt is None:
        return get_vietnam_now()
    
    if dt.tzinfo is None:
        # Nếu datetime không có timezone, coi như local time
        return dt.replace(tzinfo=VIETNAM_TZ)
    else:
        # Chuyển đổi sang múi giờ Việt Nam
        return dt.astimezone(VIETNAM_TZ)

def format_vietnam_time(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime theo múi giờ Việt Nam"""
    vietnam_dt = get_vietnam_time(dt)
    return vietnam_dt.strftime(format_str)

def parse_time_to_vietnam(time_str: str) -> datetime:
    """Parse time string và chuyển sang múi giờ Việt Nam"""
    try:
        # Parse ISO format
        if 'T' in time_str:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(time_str)
        
        return get_vietnam_time(dt)
    except:
        raise ValueError(f"Không thể parse thời gian: {time_str}")

def vietnam_isoformat(dt: datetime) -> str:
    """Chuyển datetime sang ISO format với timezone Việt Nam"""
    vietnam_dt = get_vietnam_time(dt)
    return vietnam_dt.isoformat()

def get_vietnam_timestamp() -> str:
    """Lấy timestamp hiện tại theo múi giờ Việt Nam"""
    return get_vietnam_now().isoformat()

def is_vietnam_business_hours(dt: Optional[datetime] = None) -> bool:
    """Kiểm tra có phải giờ làm việc ở Việt Nam (8h-17h)"""
    vietnam_time = get_vietnam_time(dt) if dt else get_vietnam_now()
    hour = vietnam_time.hour
    return 8 <= hour < 17

def get_vietnam_date_display(dt: datetime) -> str:
    """Hiển thị ngày theo định dạng Việt Nam"""
    vietnam_dt = get_vietnam_time(dt)
    return vietnam_dt.strftime("%d/%m/%Y lúc %H:%M")
