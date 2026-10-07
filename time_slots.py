"""
time_slots.py - Dynamic time-slot generation from working configuration.

Derives valid scheduling periods from:
  - working start time
  - working end time
  - break periods
  - lunch period
  - slot duration

Does NOT use a fixed slot matrix. Slots are computed dynamically.
"""

from typing import List, Dict
from models import WorkingConfig, TimeSlot


def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' to minutes since midnight.

    >>> time_to_minutes('09:00')
    540
    >>> time_to_minutes('13:30')
    810
    """
    h, m = map(int, time_str.strip().split(':'))
    return h * 60 + m


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to 'HH:MM'.

    >>> minutes_to_time(540)
    '09:00'
    >>> minutes_to_time(810)
    '13:30'
    """
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def generate_time_slots(config: WorkingConfig) -> List[TimeSlot]:
    """Generate valid scheduling periods from a WorkingConfig.

    Algorithm:
    1. Start cursor at config.start_time.
    2. Collect all blocked periods (breaks + lunch) sorted by start time.
    3. While cursor + slot_duration <= end_time:
       a. Compute the candidate period [cursor, cursor + duration).
       b. If it overlaps any blocked period, advance cursor to the end
          of that blocked period and retry.
       c. Otherwise, record the period and advance cursor to its end.

    This ensures:
    - No classes are scheduled during breaks or lunch.
    - Periods are contiguous within available windows.
    - Lab sessions can span consecutive periods only if those periods
      are temporally adjacent (no break between them).
    """
    start = time_to_minutes(config.start_time)
    end = time_to_minutes(config.end_time)
    duration = config.slot_duration_minutes

    # Collect all blocked intervals: lunch + explicit breaks
    blocked = []
    blocked.append((time_to_minutes(config.lunch_start),
                     time_to_minutes(config.lunch_end)))
    for b in config.breaks:
        b_start = b.get('start_time', b.get('start', ''))
        b_end = b.get('end_time', b.get('end', ''))
        if b_start and b_end:
            blocked.append((time_to_minutes(b_start), time_to_minutes(b_end)))
    blocked.sort()

    slots: List[TimeSlot] = []
    cursor = start

    while cursor + duration <= end:
        slot_end = cursor + duration

        # Check for overlap with any blocked period
        overlap = False
        skip_to = cursor
        for (b_start, b_end) in blocked:
            # Overlap condition: cursor < b_end AND slot_end > b_start
            if cursor < b_end and slot_end > b_start:
                overlap = True
                skip_to = max(skip_to, b_end)

        if overlap:
            cursor = skip_to
            continue

        slots.append(TimeSlot(
            index=len(slots),
            start_time=minutes_to_time(cursor),
            end_time=minutes_to_time(slot_end)
        ))
        cursor = slot_end

    return slots
