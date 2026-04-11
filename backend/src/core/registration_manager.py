from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.models.course import Course
from src.models.student import Student


MAX_COURSE_SEATS = 3


class RegistrationManager:
    def __init__(self, courses: List[Course], students: List[Student]) -> None:
        for course in courses:
            course.max_seats = min(max(course.max_seats, 1), MAX_COURSE_SEATS)
        self.courses: Dict[str, Course] = {c.course_id: c for c in courses}
        self.students: Dict[str, Student] = {s.student_id: s for s in students}

    def _normalize_student(self, student: Student) -> Student:
        student.student_id = student.student_id.strip().upper()
        student.student_name = student.student_name.strip()
        student.branch = student.branch.strip()
        student.email = student.email.strip().lower()
        return student

    def validate_student(self, student: Student) -> Tuple[bool, str]:
        student = self._normalize_student(student)

        if not student.student_id:
            return False, "Student ID is required"
        if not student.student_name:
            return False, "Student name is required"
        if not student.branch:
            return False, "Branch is required"
        if not student.email:
            return False, "Email is required"
        if student.semester < 1 or student.semester > 12:
            return False, "Semester must be between 1 and 12"
        if student.student_id in self.students:
            return False, "Student ID already exists"

        for existing in self.students.values():
            if existing.email.strip().lower() == student.email:
                return False, "Email already exists"

        return True, "Student details are valid"

    def add_course(self, course: Course) -> bool:
        if course.course_id in self.courses:
            return False
        for existing in self.courses.values():
            if existing.course_name.strip().lower() == course.course_name.strip().lower():
                return False
        if course.max_seats < 1 or course.max_seats > MAX_COURSE_SEATS:
            return False
        self.courses[course.course_id] = course
        return True

    def update_course(self, course_id: str, **updates) -> bool:
        course = self.courses.get(course_id)
        if not course:
            return False

        max_seats_value = updates.get("max_seats")
        if max_seats_value is not None:
            if max_seats_value < 1 or max_seats_value > MAX_COURSE_SEATS:
                return False

        for key, value in updates.items():
            if hasattr(course, key) and value is not None:
                setattr(course, key, value)
        return True

    def delete_course(self, course_id: str) -> bool:
        if course_id not in self.courses:
            return False

        for student in self.students.values():
            if course_id in student.registered_courses:
                student.registered_courses.remove(course_id)

        del self.courses[course_id]
        return True

    def get_all_courses(self) -> List[Course]:
        return sorted(self.courses.values(), key=lambda c: c.course_id)

    def register_student(self, student: Student) -> Tuple[bool, str]:
        is_valid, message = self.validate_student(student)
        if not is_valid:
            return False, message

        normalized_student = self._normalize_student(student)
        self.students[normalized_student.student_id] = normalized_student
        return True, "Student registered successfully"

    def get_student(self, student_id: str) -> Optional[Student]:
        return self.students.get(student_id)

    def get_all_students(self) -> List[Student]:
        return sorted(self.students.values(), key=lambda s: s.student_id)

    def enroll_student_in_course(self, student_id: str, course_id: str) -> Tuple[bool, str]:
        student = self.students.get(student_id)
        if not student:
            return False, "Student not found"

        course = self.courses.get(course_id)
        if not course:
            return False, "Course not found"

        if course_id in student.registered_courses:
            return False, "Duplicate registration prevented"

        if student.registered_courses:
            return False, "Student already enrolled in another course"

        if student_id in course.waiting_list:
            return False, "Student already in waiting list"

        if course.is_full():
            return False, "Course Full - Registration Rejected"

        course.enrolled_students.append(student_id)
        student.registered_courses.append(course_id)
        return True, "Enrollment successful"

    def search_course(self, query: str) -> List[Course]:
        q = query.strip().lower()
        return [
            c
            for c in self.courses.values()
            if c.course_id.lower() == q or q in c.course_name.lower()
        ]

    def filter_courses(
        self,
        branch: Optional[str] = None,
        instructor: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Course]:
        results = list(self.courses.values())

        if branch:
            results = [c for c in results if c.branch.lower() == branch.lower()]
        if instructor:
            results = [
                c for c in results if instructor.lower() in c.instructor_name.lower()
            ]
        if category:
            results = [c for c in results if c.category.lower() == category.lower()]

        return sorted(results, key=lambda c: c.course_id)

    def generate_report(self) -> Dict:
        total_courses = len(self.courses)
        total_students = len(self.students)
        enrollment_counts = {
            c.course_id: len(c.enrolled_students) for c in self.courses.values()
        }

        most_popular_course = None
        if enrollment_counts:
            popular_id = max(enrollment_counts, key=enrollment_counts.get)
            most_popular_course = self.courses[popular_id].course_name

        courses_with_available_seats = [
            c.course_id for c in self.courses.values() if c.available_seats > 0
        ]
        courses_with_waiting_list = [
            c.course_id for c in self.courses.values() if len(c.waiting_list) > 0
        ]

        average_enrollment = (
            sum(enrollment_counts.values()) / total_courses if total_courses else 0.0
        )

        return {
            "total_courses": total_courses,
            "total_students": total_students,
            "most_popular_course": most_popular_course or "N/A",
            "courses_with_available_seats": courses_with_available_seats,
            "courses_with_waiting_list": courses_with_waiting_list,
            "average_enrollment_per_course": round(average_enrollment, 2),
        }

    def export_courses(self) -> List[Dict]:
        return [course.to_dict() for course in self.courses.values()]

    def export_students(self) -> List[Dict]:
        return [student.to_dict() for student in self.students.values()]
