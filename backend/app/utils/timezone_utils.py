"""
Timezone-aware business hours utility.

Returns typical active hours (local time, 0-23) for a given role type
in the specified IANA timezone. These are used as fallback defaults when
the LLM fails to generate agent activity configs.

The logic is intentionally simple — we just shift well-known "social media
active hours" patterns by the UTC offset of the target timezone so they
land in plausible local-time windows regardless of region.
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime
from typing import List


def _utc_offset_hours(iana_tz: str) -> int:
    """Return the current UTC offset in whole hours for the given IANA timezone."""
    try:
        tz = ZoneInfo(iana_tz)
    except (ZoneInfoNotFoundError, Exception):
        return 0  # fall back to UTC
    now = datetime.now(tz)
    offset_seconds = now.utcoffset().total_seconds()
    return int(offset_seconds // 3600)


def _shift_hours(hours: List[int], shift: int) -> List[int]:
    """Shift a list of hours by `shift` and wrap around 24h."""
    return sorted({(h + shift) % 24 for h in hours})


def get_business_hours(iana_tz: str, role_type: str) -> List[int]:
    """
    Return appropriate active hours (0-23 local time) for a role in a timezone.

    Args:
        iana_tz:   IANA timezone string, e.g. "America/New_York", "UTC", "Asia/Tokyo"
        role_type: One of 'institution', 'media', 'expert', 'student', 'alumni', 'person'

    Returns:
        Sorted list of active hours in local time.
    """
    shift = _utc_offset_hours(iana_tz)

    # Base patterns defined in UTC — shift to local time
    patterns = {
        "institution": list(range(9, 18)),           # 09:00-17:59 UTC
        "media":       list(range(7, 24)),            # 07:00-23:59 UTC
        "expert":      list(range(8, 22)),            # 08:00-21:59 UTC
        "student":     [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],
        "alumni":      [12, 13, 19, 20, 21, 22, 23],
        "person":      [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],
    }

    base = patterns.get(role_type.lower(), patterns["person"])
    return _shift_hours(base, shift)
