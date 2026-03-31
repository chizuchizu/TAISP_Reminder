from dataclasses import dataclass
from typing import Optional


@dataclass
class Module:
    id: int
    name: str
    description: Optional[str]


@dataclass
class Deadline:
    id: int
    module_id: int
    module_name: str
    title: str
    due_date: str        # YYYY-MM-DD
    due_time: Optional[str]  # HH:MM or None
    notes: Optional[str]
    created_by: int
