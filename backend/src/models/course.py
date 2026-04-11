from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Course:
    course_id: str
    course_name: str
    instructor_name: str
    max_seats: int
    credits: int
    category: str  # Core / Elective
    branch: str
    enrolled_students: List[str] = field(default_factory=list)
    waiting_list: List[str] = field(default_factory=list)

    @property
    def available_seats(self) -> int:
        return max(self.max_seats - len(self.enrolled_students), 0)

    def is_full(self) -> bool:
        return len(self.enrolled_students) >= self.max_seats

    def to_dict(self) -> Dict:
        return {
            "course_id": self.course_id,
            "course_name": self.course_name,
            "instructor_name": self.instructor_name,
            "max_seats": self.max_seats,
            "credits": self.credits,
            "category": self.category,
            "branch": self.branch,
            "enrolled_students": self.enrolled_students,
            "waiting_list": self.waiting_list,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Course":
        return cls(
            course_id=data["course_id"],
            course_name=data["course_name"],
            instructor_name=data["instructor_name"],
            max_seats=int(data["max_seats"]),
            credits=int(data["credits"]),
            category=data["category"],
            branch=data.get("branch", "General"),
            enrolled_students=data.get("enrolled_students", []),
            waiting_list=data.get("waiting_list", []),
        )
