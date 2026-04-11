from __future__ import annotations

from typing import List

from src.core.auth_manager import AuthManager
from src.core.registration_manager import RegistrationManager
from src.models.course import Course
from src.models.student import Student

try:
    from rich.console import Console  # type: ignore
    from rich.panel import Panel  # type: ignore
    from rich.prompt import Prompt  # type: ignore
    from rich.table import Table  # type: ignore
    from rich.text import Text  # type: ignore

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class SmartUI:
    def __init__(self, manager: RegistrationManager, auth: AuthManager) -> None:
        self.manager = manager
        self.auth = auth
        self.console = Console() if RICH_AVAILABLE else None

    def run(self) -> None:
        while True:
            self._show_welcome()
            if self._login_flow():
                self._main_menu_loop()
            else:
                break

    def _show_welcome(self) -> None:
        if RICH_AVAILABLE and self.console:
            title = Text("SRU COURSE REGISTRATION", style="bold cyan")
            subtitle = Text("Fast. Smart. Modular. Student-first.", style="bold magenta")
            self.console.print(Panel.fit(f"{title}\n{subtitle}", border_style="bright_blue"))
        else:
            print("\n=== SRU COURSE REGISTRATION ===")

    def _login_flow(self) -> bool:
        while True:
            username = self._input("Username (or 'exit')").strip()
            if username.lower() == "exit":
                return False
            password = self._input("Password").strip()

            if self.auth.login(username, password):
                self._success(f"Login successful. Welcome {username}.")
                return True
            self._error("Invalid credentials. Try again.")

    def _main_menu_loop(self) -> None:
        while self.auth.is_logged_in():
            self._render_main_menu()
            choice = self._input("Select an option").strip()

            if choice == "1":
                self._add_course()
            elif choice == "2":
                self._register_student()
            elif choice == "3":
                self._enroll_student()
            elif choice == "4":
                self._view_all_courses()
            elif choice == "5":
                self._search_course()
            elif choice == "6":
                self._generate_report()
            elif choice == "7":
                self._advanced_course_tools()
            elif choice == "8":
                self.auth.logout()
                self._success("Logged out successfully.")
            elif choice == "9":
                self.auth.logout()
                self._success("Goodbye.")
                raise SystemExit(0)
            else:
                self._error("Invalid option. Please choose from the menu.")

    def _render_main_menu(self) -> None:
        menu_text = (
            "1. Add Course\n"
            "2. Register Student\n"
            "3. Enroll Student in Course\n"
            "4. View All Courses\n"
            "5. Search Course\n"
            "6. Generate Reports\n"
            "7. Advanced Tools (Update/Delete/Filter/View Student)\n"
            "8. Logout\n"
            "9. Exit"
        )
        if RICH_AVAILABLE and self.console:
            self.console.print(Panel(menu_text, title="Main Menu", border_style="green"))
        else:
            print("\n" + menu_text)

    def _add_course(self) -> None:
        course_id = self._input("Course ID").strip()
        course_name = self._input("Course Name").strip()
        instructor_name = self._input("Instructor Name").strip()
        max_seats = self._input_int("Maximum Seats")
        credits = self._input_int("Credits")
        category = self._input("Category (Core/Elective)").strip().title()
        branch = self._input("Branch").strip()

        course = Course(
            course_id=course_id,
            course_name=course_name,
            instructor_name=instructor_name,
            max_seats=max_seats,
            credits=credits,
            category=category,
            branch=branch,
        )
        if self.manager.add_course(course):
            self._success("Course added successfully.")
        else:
            self._error("Course ID already exists.")

    def _register_student(self) -> None:
        student = Student(
            student_id=self._input("Student ID").strip(),
            student_name=self._input("Student Name").strip(),
            branch=self._input("Branch").strip(),
            semester=self._input_int("Semester"),
            email=self._input("Email").strip(),
        )

        ok, message = self.manager.register_student(student)
        if ok:
            self._success(message)
        else:
            self._error(message)

    def _enroll_student(self) -> None:
        student_id = self._input("Student ID").strip()
        course_id = self._input("Course ID").strip()
        ok, message = self.manager.enroll_student_in_course(student_id, course_id)
        if ok:
            self._success(message)
        else:
            self._error(message)

    def _view_all_courses(self) -> None:
        courses = self.manager.get_all_courses()
        if not courses:
            self._error("No courses available.")
            return

        if RICH_AVAILABLE and self.console:
            table = Table(title="Course Catalog", show_lines=True)
            table.add_column("Course ID", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Instructor")
            table.add_column("Credits")
            table.add_column("Category")
            table.add_column("Branch")
            table.add_column("Seats")
            table.add_column("Wait List")

            for course in courses:
                seat_view = f"{course.available_seats}/{course.max_seats}"
                table.add_row(
                    course.course_id,
                    course.course_name,
                    course.instructor_name,
                    str(course.credits),
                    course.category,
                    course.branch,
                    seat_view,
                    str(len(course.waiting_list)),
                )
            self.console.print(table)
        else:
            for c in courses:
                print(
                    f"{c.course_id} | {c.course_name} | {c.instructor_name} | "
                    f"Credits: {c.credits} | Seats: {c.available_seats}/{c.max_seats}"
                )

    def _search_course(self) -> None:
        query = self._input("Enter Course ID or Course Name").strip()
        results = self.manager.search_course(query)
        if not results:
            self._error("No matching courses found.")
            return
        self._display_courses(results)

    def _advanced_course_tools(self) -> None:
        submenu = (
            "1. Update Course\n"
            "2. Delete Course\n"
            "3. Filter Courses\n"
            "4. View Student Profile\n"
            "5. Back"
        )

        while True:
            if RICH_AVAILABLE and self.console:
                self.console.print(Panel(submenu, title="Advanced Tools", border_style="yellow"))
            else:
                print("\n" + submenu)

            choice = self._input("Choose tool").strip()
            if choice == "1":
                self._update_course()
            elif choice == "2":
                self._delete_course()
            elif choice == "3":
                self._filter_courses()
            elif choice == "4":
                self._view_student_profile()
            elif choice == "5":
                break
            else:
                self._error("Invalid choice.")

    def _update_course(self) -> None:
        course_id = self._input("Course ID to update").strip()
        max_seats_raw = self._input("New max seats (blank to skip)").strip()
        credits_raw = self._input("New credits (blank to skip)").strip()

        updates = {
            "course_name": self._input("New name (blank to skip)").strip() or None,
            "instructor_name": self._input("New instructor (blank to skip)").strip() or None,
            "category": self._input("New category (blank to skip)").strip() or None,
            "branch": self._input("New branch (blank to skip)").strip() or None,
            "max_seats": int(max_seats_raw) if max_seats_raw else None,
            "credits": int(credits_raw) if credits_raw else None,
        }

        if self.manager.update_course(course_id, **updates):
            self._success("Course updated successfully.")
        else:
            self._error("Course not found.")

    def _delete_course(self) -> None:
        course_id = self._input("Course ID to delete").strip()
        if self.manager.delete_course(course_id):
            self._success("Course deleted successfully.")
        else:
            self._error("Course not found.")

    def _filter_courses(self) -> None:
        branch = self._input("Filter by branch (blank to skip)").strip()
        instructor = self._input("Filter by instructor (blank to skip)").strip()
        category = self._input("Filter by category (blank to skip)").strip()

        results = self.manager.filter_courses(
            branch=branch or None,
            instructor=instructor or None,
            category=category or None,
        )
        if results:
            self._display_courses(results)
        else:
            self._error("No courses match your filters.")

    def _view_student_profile(self) -> None:
        student_id = self._input("Student ID").strip()
        student = self.manager.get_student(student_id)
        if not student:
            self._error("Student not found.")
            return

        lines = [
            f"Student ID: {student.student_id}",
            f"Name: {student.student_name}",
            f"Branch: {student.branch}",
            f"Semester: {student.semester}",
            f"Email: {student.email}",
            f"Registered Courses: {', '.join(student.registered_courses) or 'None'}",
        ]
        self._block("Student Profile", "\n".join(lines), style="bright_cyan")

    def _generate_report(self) -> None:
        report = self.manager.generate_report()
        report_lines = [
            f"Total courses offered: {report['total_courses']}",
            f"Total students registered: {report['total_students']}",
            f"Most popular course: {report['most_popular_course']}",
            f"Courses with available seats: {', '.join(report['courses_with_available_seats']) or 'None'}",
            f"Courses with waiting list: {', '.join(report['courses_with_waiting_list']) or 'None'}",
            f"Average enrollment per course: {report['average_enrollment_per_course']}",
        ]
        self._block("Analytics Report", "\n".join(report_lines), style="bright_green")

    def _display_courses(self, courses: List[Course]) -> None:
        if RICH_AVAILABLE and self.console:
            table = Table(title="Course Results")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Instructor")
            table.add_column("Category")
            table.add_column("Branch")
            table.add_column("Seats")
            for c in courses:
                table.add_row(
                    c.course_id,
                    c.course_name,
                    c.instructor_name,
                    c.category,
                    c.branch,
                    f"{c.available_seats}/{c.max_seats}",
                )
            self.console.print(table)
        else:
            for c in courses:
                print(f"{c.course_id} - {c.course_name} ({c.category})")

    def _input(self, label: str) -> str:
        if RICH_AVAILABLE:
            return Prompt.ask(f"[bold blue]{label}[/bold blue]")
        return input(f"{label}: ")

    def _input_int(self, label: str) -> int:
        while True:
            raw = self._input(label).strip()
            if raw.isdigit():
                return int(raw)
            self._error("Please enter a valid number.")

    def _block(self, title: str, body: str, style: str = "white") -> None:
        if RICH_AVAILABLE and self.console:
            self.console.print(Panel(body, title=title, border_style=style))
        else:
            print(f"\n--- {title} ---\n{body}")

    def _success(self, message: str) -> None:
        if RICH_AVAILABLE and self.console:
            self.console.print(f"[bold green]{message}[/bold green]")
        else:
            print(f"[SUCCESS] {message}")

    def _error(self, message: str) -> None:
        if RICH_AVAILABLE and self.console:
            self.console.print(f"[bold red]{message}[/bold red]")
        else:
            print(f"[ERROR] {message}")
