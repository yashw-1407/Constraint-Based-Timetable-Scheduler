from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional

class CourseType:
    THEORY = "THEORY"
    LAB = "LAB"

class RoomType:
    THEORY_ROOM = "THEORY_ROOM"
    LAB = "LAB"

@dataclass
class WorkingConfig:
    working_days: List[str]
    start_time: str
    end_time: str
    slot_duration_minutes: int
    breaks: List[Dict[str, str]]
    lunch_start: str
    lunch_end: str

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**d)

@dataclass
class Room:
    id: str
    name: str
    room_type: str
    capacity: Optional[int] = None
    category: Optional[str] = None

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**d)

@dataclass
class Faculty:
    id: str
    name: str

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**d)

@dataclass
class Section:
    id: str
    name: str
    semester: int
    division: str
    strength: Optional[int] = None
    home_room_id: Optional[str] = None

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**d)

@dataclass
class Batch:
    id: str
    name: str
    section_id: str
    strength: Optional[int] = None
    home_room_id: Optional[str] = None

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**d)

@dataclass
class Course:
    """Raw Course Data (e.g. from Excel or manual entry)."""
    id: str
    name: str
    code: str
    section_id: str
    l: float
    t: float
    p: float
    faculty_ids: List[str] = field(default_factory=list)
    assistant_faculty_ids: List[str] = field(default_factory=list)
    room_type: str = RoomType.THEORY_ROOM  # Default theory room preference
    required_room_id: Optional[str] = None
    lab_batches: List[str] = field(default_factory=list) # List of batch IDs for practical component

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

@dataclass
class CourseComponent:
    """Generated Scheduling Component (Theory or Lab)."""
    id: str
    course_id: str
    name: str
    code: str
    section_id: str
    course_type: str  # 'THEORY' or 'LAB'
    weekly_hours: int
    faculty_ids: List[str]
    room_type: str
    required_room_id: Optional[str] = None
    batch_id: Optional[str] = None  # None = section-level

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class TimeSlot:
    index: int
    start_time: str
    end_time: str

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**d)

@dataclass
class ScheduleSession:
    id: str
    course_id: str
    course_name: str
    course_code: str
    course_type: str
    section_id: str
    faculty_ids: List[str]  # Changed to list
    room_type: str
    required_room_id: Optional[str]
    session_index: int
    duration_slots: int
    batch_id: Optional[str] = None

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

@dataclass
class Assignment:
    session_id: str
    day: str
    start_slot_index: int
    room_id: str

    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, d): return cls(**d)
