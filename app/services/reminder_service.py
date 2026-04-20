"""
Reminder Service — replaces the old schedule_service.py.
Since users now define weekdays and times directly (like phone alarms),
this service only checks whether a given medication is active today/now.
"""
from datetime import time, datetime
from typing import List


# Maps Python weekday numbers (Monday=0) to our string codes
_WEEKDAY_MAP = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}


def get_today_weekday() -> str:
    """Return today's weekday code e.g. 'mon', 'tue', ..."""
    return _WEEKDAY_MAP[datetime.today().weekday()]


def is_dose_active_now(
    weekdays: List[str],
    times: List[str],
    buffer_minutes: int = 15,
) -> bool:
    """
    Check if any dose for this medication is active right now (within buffer_minutes window).
    weekdays: list of strings like ['mon', 'tue']
    times: list of time strings like ['08:00:00', '20:00:00']
    """
    today = get_today_weekday()
    if today not in weekdays:
        return False

    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    for t_str in times:
        dose_time = time.fromisoformat(t_str)
        dose_minutes = dose_time.hour * 60 + dose_time.minute
        if abs(now_minutes - dose_minutes) <= buffer_minutes:
            return True

    return False


def detect_conflicts(
    primary_weekdays: List[str],
    primary_times: List[str],
    secondary_weekdays: List[str],
    secondary_times: List[str],
    buffer_minutes: int = 30,
) -> List[dict]:
    """
    Detect scheduling conflicts between primary (chronic) and secondary (acute) medications.
    Compares (day, time) pairs — only flags conflicts on days where both medications are active.
    Returns a list of conflict dicts: {day, primary_time, secondary_time}
    """
    conflicts = []
    overlapping_days = set(primary_weekdays) & set(secondary_weekdays)

    for day in overlapping_days:
        for pt_str in primary_times:
            pt = time.fromisoformat(pt_str)
            pt_min = pt.hour * 60 + pt.minute
            for st_str in secondary_times:
                st = time.fromisoformat(st_str)
                st_min = st.hour * 60 + st.minute
                if abs(pt_min - st_min) < buffer_minutes:
                    conflicts.append({
                        "day": day,
                        "primary_time": str(pt),
                        "secondary_time": str(st),
                    })

    return conflicts
