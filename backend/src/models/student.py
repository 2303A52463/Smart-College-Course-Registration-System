from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Student:
    student_id: str
    student_name: str
    branch: str
    semester: int
    email: str
    registered_courses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "branch": self.branch,
            "semester": self.semester,
            "email": self.email,
            "registered_courses": self.registered_courses,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Student":
        return cls(
            student_id=data["student_id"],
            student_name=data["student_name"],
            branch=data["branch"],
            semester=int(data["semester"]),
            email=data["email"],
            registered_courses=data.get("registered_courses", []),
        )
