from __future__ import annotations

import io
from collections import defaultdict
from datetime import datetime
from functools import wraps
from typing import Callable, Dict, List

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for  # type: ignore
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from src.core.auth_manager import AuthManager
from src.core.registration_manager import MAX_COURSE_SEATS
from src.core.registration_manager import RegistrationManager
from src.core.storage import StorageManager
from src.models.course import Course
from src.models.student import Student


class WebSystem:
    def __init__(self) -> None:
        self.storage = StorageManager(data_dir="backend/data")
        courses = [Course.from_dict(item) for item in self.storage.load_courses()]
        students = [Student.from_dict(item) for item in self.storage.load_students()]
        users = self.storage.load_users()
        self.enrollment_log = self.storage.load_enrollment_log()

        self.manager = RegistrationManager(courses, students)
        self.auth = AuthManager(users)
        created_accounts = self._ensure_student_login_accounts()
        if created_accounts:
            self.save()

    def _ensure_student_login_accounts(self) -> int:
        """Create login accounts for student profiles that do not have one yet."""
        created = 0
        default_password = "student123"

        for student in self.manager.get_all_students():
            if self.auth.has_student_account(student.student_id):
                continue

            base_username = student.student_id.strip().lower()
            username = base_username
            suffix = 1
            while self.auth.has_username(username):
                suffix += 1
                username = f"{base_username}{suffix}"

            if self.auth.signup_student(
                username=username,
                password=default_password,
                email=student.email,
                student_id=student.student_id,
            ):
                created += 1

        return created

    def save(self) -> None:
        self.storage.save_courses(self.manager.export_courses())
        self.storage.save_students(self.manager.export_students())
        self.storage.save_users(self.auth.users)
        self.storage.save_enrollment_log(self.enrollment_log)

    def add_enrollment_event(self, student_id: str, course_id: str, status: str) -> None:
        self.enrollment_log.append(
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "student_id": student_id,
                "course_id": course_id,
                "status": status,
            }
        )

    def enrollment_trend_data(self) -> Dict[str, List]:
        grouped = defaultdict(int)
        for event in self.enrollment_log:
            if event.get("status") == "enrolled":
                grouped[event.get("date", "Unknown")] += 1

        labels = sorted(grouped.keys())
        values = [grouped[label] for label in labels]
        return {"labels": labels, "values": values}

    def student_registration_report(self, student_id: str) -> Dict:
        student = self.manager.get_student(student_id)
        if not student:
            return {
                "student": None,
                "registered_courses": [],
                "total_registered_courses": 0,
                "total_credits": 0,
                "enrollment_events": [],
                "last_enrollment_date": "N/A",
            }

        courses = {
            course.course_id: course for course in self.manager.get_all_courses()
        }
        registered_courses = [
            courses[course_id]
            for course_id in student.registered_courses
            if course_id in courses
        ]

        enrollment_events = [
            event
            for event in self.enrollment_log
            if event.get("student_id") == student_id
        ]
        enrollment_events.sort(key=lambda event: event.get("date", ""), reverse=True)

        return {
            "student": student,
            "registered_courses": registered_courses,
            "total_registered_courses": len(registered_courses),
            "total_credits": sum(course.credits for course in registered_courses),
            "enrollment_events": enrollment_events,
            "last_enrollment_date": (
                enrollment_events[0].get("date", "N/A") if enrollment_events else "N/A"
            ),
        }


web_system = WebSystem()
app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
app.config["SECRET_KEY"] = "smart-college-registration-secret-key"


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("landing"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles: str) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("dashboard_router"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def _draw_pdf_shell(pdf: canvas.Canvas, title: str, subtitle: str, page_no: int) -> float:
    width, height = A4

    # White background and border frame.
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#0b4f7a"))
    pdf.setLineWidth(1.3)
    pdf.rect(20, 20, width - 40, height - 40, fill=0, stroke=1)

    # Watermark background "SRU".
    pdf.saveState()
    pdf.setFillColor(colors.Color(0.75, 0.85, 0.95, alpha=0.15))
    pdf.setFont("Helvetica-Bold", 96)
    pdf.translate(width / 2, height / 2)
    pdf.rotate(35)
    pdf.drawCentredString(0, 0, "SRU")
    pdf.restoreState()

    # Header bar.
    pdf.setFillColor(colors.HexColor("#0b4f7a"))
    pdf.rect(20, height - 110, width - 40, 90, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(34, height - 58, "SRU COURSE REGISTRATION")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(34, height - 80, title)
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - 34, height - 56, subtitle)
    pdf.drawRightString(width - 34, height - 74, f"Page {page_no}")

    # Footer note for document validity.
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(colors.HexColor("#333333"))
    pdf.drawCentredString(
        width / 2,
        30,
        "This is an  Automated Document, There Is No Need Of Signature",
    )

    return height - 128


def _draw_kv_box(pdf: canvas.Canvas, y: float, items: List[tuple]) -> float:
    """Draw key-value items in a neat two-column bordered block."""
    width, _ = A4
    row_h = 18
    total_rows = (len(items) + 1) // 2
    box_h = (total_rows * row_h) + 18

    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor("#9bb8cc"))
    pdf.rect(34, y - box_h, width - 68, box_h, fill=1, stroke=1)

    x_left = 42
    x_right = width / 2 + 8
    line_y = y - 22
    index = 0
    for _ in range(total_rows):
        for col_x in (x_left, x_right):
            if index >= len(items):
                break
            label, value = items[index]
            pdf.setFont("Helvetica-Bold", 9)
            pdf.setFillColor(colors.HexColor("#0b4f7a"))
            pdf.drawString(col_x, line_y, f"{label}:")
            pdf.setFont("Helvetica", 9)
            pdf.setFillColor(colors.black)
            pdf.drawString(col_x + 95, line_y, str(value))
            index += 1
        line_y -= row_h

    return y - box_h - 14


def _draw_table_header(pdf: canvas.Canvas, y: float, columns: List[str], col_widths: List[float]) -> float:
    x = 34
    pdf.setFillColor(colors.HexColor("#e3f0fa"))
    pdf.setStrokeColor(colors.HexColor("#8baec4"))
    pdf.rect(x, y - 18, sum(col_widths), 18, fill=1, stroke=1)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(colors.HexColor("#0b4f7a"))

    draw_x = x + 4
    for idx, col in enumerate(columns):
        pdf.drawString(draw_x, y - 12, col)
        draw_x += col_widths[idx]
    return y - 18


def _draw_table_row(pdf: canvas.Canvas, y: float, row: List[str], col_widths: List[float]) -> float:
    x = 34
    row_h = 16
    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor("#c3d7e7"))
    pdf.rect(x, y - row_h, sum(col_widths), row_h, fill=1, stroke=1)

    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.black)
    draw_x = x + 4
    for idx, cell in enumerate(row):
        text = str(cell)
        if len(text) > 30:
            text = text[:27] + "..."
        pdf.drawString(draw_x, y - 11, text)
        draw_x += col_widths[idx]

    return y - row_h


def _build_student_report_pdf(student: Student, report: Dict) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, _ = A4
    page_no = 1

    y = _draw_pdf_shell(
        pdf,
        "Student Course Registration Report",
        datetime.now().strftime("Generated: %Y-%m-%d %H:%M"),
        page_no,
    )

    y = _draw_kv_box(
        pdf,
        y,
        [
            ("Student ID", student.student_id),
            ("Student Name", student.student_name),
            ("Branch", student.branch),
            ("Semester", student.semester),
            ("Email", student.email),
            ("Total Registered", report["total_registered_courses"]),
            ("Total Credits", report["total_credits"]),
            ("Last Enrollment", report["last_enrollment_date"]),
        ],
    )

    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.HexColor("#0b4f7a"))
    pdf.drawString(34, y, "REGISTERED COURSES")
    y -= 10

    columns = ["Course ID", "Course Name", "Instructor", "Category", "Branch", "Credits"]
    col_widths = [62, 130, 110, 70, 80, 45]
    y = _draw_table_header(pdf, y, columns, col_widths)

    courses = report["registered_courses"]
    if not courses:
        y = _draw_table_row(pdf, y, ["-", "No registered courses", "-", "-", "-", "-"], col_widths)
    else:
        for course in courses:
            if y < 70:
                pdf.showPage()
                page_no += 1
                y = _draw_pdf_shell(
                    pdf,
                    "Student Course Registration Report",
                    datetime.now().strftime("Generated: %Y-%m-%d %H:%M"),
                    page_no,
                )
                y = _draw_table_header(pdf, y - 8, columns, col_widths)
            y = _draw_table_row(
                pdf,
                y,
                [
                    course.course_id,
                    course.course_name,
                    course.instructor_name,
                    course.category,
                    course.branch,
                    str(course.credits),
                ],
                col_widths,
            )

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def _build_course_report_pdf(course: Course, students: List[Student]) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_no = 1

    y = _draw_pdf_shell(
        pdf,
        "Course Registration Report",
        datetime.now().strftime("Generated: %Y-%m-%d %H:%M"),
        page_no,
    )

    y = _draw_kv_box(
        pdf,
        y,
        [
            ("Course ID", course.course_id),
            ("Course Name", course.course_name),
            ("Instructor", course.instructor_name),
            ("Category", course.category),
            ("Branch", course.branch),
            ("Credits", course.credits),
            ("Enrollment", f"{len(course.enrolled_students)}/{course.max_seats}"),
            ("Available Seats", course.available_seats),
            ("Waiting List Count", len(course.waiting_list)),
        ],
    )

    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.HexColor("#0b4f7a"))
    pdf.drawString(34, y, "ENROLLED STUDENT DETAILS")
    y -= 10

    columns = ["Student ID", "Name", "Branch", "Semester", "Email"]
    col_widths = [70, 130, 90, 60, 160]
    y = _draw_table_header(pdf, y, columns, col_widths)

    if not students:
        y = _draw_table_row(pdf, y, ["-", "No students enrolled", "-", "-", "-"], col_widths)
    else:
        for student in students:
            if y < 70:
                pdf.showPage()
                page_no += 1
                y = _draw_pdf_shell(
                    pdf,
                    "Course Registration Report",
                    datetime.now().strftime("Generated: %Y-%m-%d %H:%M"),
                    page_no,
                )
                y = _draw_table_header(pdf, y - 8, columns, col_widths)
            y = _draw_table_row(
                pdf,
                y,
                [
                    student.student_id,
                    student.student_name,
                    student.branch,
                    str(student.semester),
                    student.email,
                ],
                col_widths,
            )

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


@app.route("/")
def landing():
    if session.get("username"):
        return redirect(url_for("dashboard_router"))

    report = web_system.manager.generate_report()
    featured_courses = web_system.manager.get_all_courses()[:3]
    return render_template(
        "landing.html",
        report=report,
        featured_courses=featured_courses,
    )


def _login_for_role(expected_role: str):
    if session.get("username"):
        return redirect(url_for("dashboard_router"))

    role_title = "Admin" if expected_role == "admin" else "Student"
    role_route = "admin_login" if expected_role == "admin" else "student_login"

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        login_identifier = username
        if expected_role == "student":
            # Support student-name login by resolving a unique name to student ID.
            normalized_name = "".join(username.split()).lower()
            matched_students = [
                student
                for student in web_system.manager.get_all_students()
                if "".join(student.student_name.split()).lower() == normalized_name
            ]
            if len(matched_students) == 1:
                matched_student_id = matched_students[0].student_id
                if not web_system.auth.has_student_account(matched_student_id):
                    flash(
                        "Student profile found, but no login account exists yet. Please create a student account first.",
                        "error",
                    )
                    return redirect(url_for("signup"))
                login_identifier = matched_student_id
            elif len(matched_students) > 1:
                flash(
                    "Multiple students share this name. Please login with student ID or email.",
                    "error",
                )
                return redirect(url_for(role_route))

        if web_system.auth.login(login_identifier, password):
            current_user = web_system.auth.current_user
            if not current_user or current_user.role != expected_role:
                web_system.auth.logout()
                session.clear()
                flash(f"This login page is only for {role_title.lower()} accounts.", "error")
                return redirect(url_for(role_route))

            session["username"] = current_user.username
            session["role"] = current_user.role
            session["student_id"] = current_user.student_id

            # Persist automatic migration from plain password to hash.
            web_system.save()
            flash("Welcome back, {}.".format(username), "success")
            if expected_role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("student_dashboard"))

        flash("Invalid username or password.", "error")


    return render_template(
        "login.html",
        login_role=expected_role,
        login_role_title=role_title,
    )


@app.route("/login")
def login():
    return redirect(url_for("landing"))


@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    return _login_for_role("admin")


@app.route("/login/student", methods=["GET", "POST"])
def student_login():
    return _login_for_role("student")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        email = request.form.get("email", "").strip().lower()
        student_id = request.form.get("student_id", "").strip().upper()
        student_name = request.form.get("student_name", "").strip()
        branch = request.form.get("branch", "").strip()
        semester_raw = request.form.get("semester", "").strip()

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("signup"))

        if not username or not password or not email or not student_id:
            flash("Username, password, email, and student ID are required.", "error")
            return redirect(url_for("signup"))

        if not student_name or not branch:
            flash("Student name and branch are required.", "error")
            return redirect(url_for("signup"))

        try:
            semester = int(semester_raw)
        except ValueError:
            flash("Semester must be a valid number.", "error")
            return redirect(url_for("signup"))

        if semester < 1 or semester > 12:
            flash("Semester must be between 1 and 12.", "error")
            return redirect(url_for("signup"))

        if web_system.auth.has_username(username):
            flash("Username already exists.", "error")
            return redirect(url_for("signup"))

        if web_system.auth.has_email(email):
            flash("Email already exists.", "error")
            return redirect(url_for("signup"))

        if web_system.auth.has_student_account(student_id):
            flash("This student ID already has a login account.", "error")
            return redirect(url_for("signup"))

        existing_student = web_system.manager.get_student(student_id)
        if existing_student:
            if existing_student.email.strip().lower() != email:
                flash("Email does not match the existing student profile.", "error")
                return redirect(url_for("signup"))
            if existing_student.student_name.strip().lower() != student_name.lower():
                flash("Student name does not match the existing student profile.", "error")
                return redirect(url_for("signup"))
            if existing_student.branch.strip().lower() != branch.lower():
                flash("Branch does not match the existing student profile.", "error")
                return redirect(url_for("signup"))
            if existing_student.semester != semester:
                flash("Semester does not match the existing student profile.", "error")
                return redirect(url_for("signup"))
        else:
            created, message = web_system.manager.register_student(
                Student(
                    student_id=student_id,
                    student_name=student_name,
                    branch=branch,
                    semester=semester,
                    email=email,
                )
            )
            if not created:
                flash(message, "error")
                return redirect(url_for("signup"))

        ok = web_system.auth.signup_student(
            username=username,
            password=password,
            email=email,
            student_id=student_id,
        )
        if not ok:
            flash("Could not create the student account.", "error")
            return redirect(url_for("signup"))

        web_system.save()
        flash("Signup successful. You can login now.", "success")
        return redirect(url_for("student_login"))

    return render_template("signup.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("reset_password"))

        if not username or not email or not new_password:
            flash("All fields are required.", "error")
            return redirect(url_for("reset_password"))

        if web_system.auth.reset_password(username, email, new_password):
            web_system.save()
            flash("Password reset successful. Please login.", "success")
            return redirect(url_for("student_login"))

        flash("Reset failed. Check username and email.", "error")

    return render_template("reset_password.html")


@app.route("/logout")
@login_required
def logout():
    web_system.save()
    web_system.auth.logout()
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("landing"))


@app.route("/dashboard")
@login_required
def dashboard_router():
    role = session.get("role", "student")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("student_dashboard"))


@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    search_query = request.args.get("search", "").strip()
    branch = request.args.get("branch", "").strip()
    instructor = request.args.get("instructor", "").strip()
    category = request.args.get("category", "").strip()

    courses = web_system.manager.get_all_courses()
    if search_query:
        courses = web_system.manager.search_course(search_query)

    if branch or instructor or category:
        courses = web_system.manager.filter_courses(
            branch=branch or None,
            instructor=instructor or None,
            category=category or None,
        )

    all_students = web_system.manager.get_all_students()
    student_name_by_id = {student.student_id: student.student_name for student in all_students}
    student_by_id = {student.student_id: student for student in all_students}

    report = web_system.manager.generate_report()
    trend = web_system.enrollment_trend_data()
    course_labels = [course.course_id for course in courses]
    course_enrollment = [len(course.enrolled_students) for course in courses]
    waiting_counts = [len(course.waiting_list) for course in courses]
    has_courses = len(courses) > 0

    return render_template(
        "admin_dashboard.html",
        courses=courses,
        students=all_students,
        student_name_by_id=student_name_by_id,
        student_by_id=student_by_id,
        report=report,
        search_query=search_query,
        branch=branch,
        instructor=instructor,
        category=category,
        trend_labels=trend["labels"],
        trend_values=trend["values"],
        course_labels=course_labels,
        course_enrollment=course_enrollment,
        waiting_counts=waiting_counts,
        has_courses=has_courses,
    )


@app.route("/admin/course-report/<course_id>/download")
@login_required
@role_required("admin")
def download_course_report(course_id: str):
    course = web_system.manager.courses.get(course_id)
    if not course:
        flash("Course not found.", "error")
        return redirect(url_for("admin_dashboard"))

    enrolled_students = []
    for student_id in course.enrolled_students:
        student = web_system.manager.get_student(student_id)
        if student:
            enrolled_students.append(student)
        else:
            enrolled_students.append(
                Student(
                    student_id=student_id,
                    student_name="N/A",
                    branch="N/A",
                    semester=0,
                    email="N/A",
                )
            )

    pdf_bytes = _build_course_report_pdf(course, enrolled_students)

    response = Response(pdf_bytes, mimetype="application/pdf")
    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename=course_report_{course.course_id}.pdf"
    return response


@app.route("/student/dashboard")
@login_required
@role_required("student")
def student_dashboard():
    student_id = session.get("student_id")
    if not student_id:
        flash("Your account is missing a linked student profile.", "error")
        return redirect(url_for("logout"))

    student = web_system.manager.get_student(student_id)
    if not student:
        flash("Linked student profile not found.", "error")
        return redirect(url_for("logout"))

    all_courses = web_system.manager.get_all_courses()
    report = web_system.student_registration_report(student_id)
    return render_template(
        "student_dashboard.html",
        student=student,
        courses=all_courses,
        report=report,
    )


@app.route("/student/report/download")
@login_required
@role_required("student")
def download_student_report():
    student_id = session.get("student_id")
    if not student_id:
        flash("Your account is missing a linked student profile.", "error")
        return redirect(url_for("logout"))

    report = web_system.student_registration_report(student_id)
    student = report.get("student")
    if not student:
        flash("Linked student profile not found.", "error")
        return redirect(url_for("logout"))

    pdf_bytes = _build_student_report_pdf(student, report)

    response = Response(pdf_bytes, mimetype="application/pdf")
    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename=student_report_{student.student_id}.pdf"
    return response


@app.route("/courses/add", methods=["POST"])
@login_required
@role_required("admin")
def add_course():
    try:
        course = Course(
            course_id=request.form.get("course_id", "").strip(),
            course_name=request.form.get("course_name", "").strip(),
            instructor_name=request.form.get("instructor_name", "").strip(),
            max_seats=int(request.form.get("max_seats", "0")),
            credits=int(request.form.get("credits", "0")),
            category=request.form.get("category", "Elective").strip().title(),
            branch=request.form.get("branch", "General").strip(),
        )
    except ValueError:
        flash("Invalid number values for seats/credits.", "error")
        return redirect(url_for("admin_dashboard"))

    if not course.course_id or not course.course_name:
        flash("Course ID and Course Name are required.", "error")
        return redirect(url_for("admin_dashboard"))

    if course.max_seats < 1 or course.max_seats > MAX_COURSE_SEATS:
        flash("Maximum seats must be between 1 and 5.", "error")
        return redirect(url_for("admin_dashboard"))

    if web_system.manager.add_course(course):
        web_system.save()
        flash("Course added successfully.", "success")
    else:
        flash("Course rejected. Course ID/name may already exist or seats are invalid.", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/courses/update/<course_id>", methods=["POST"])
@login_required
@role_required("admin")
def update_course(course_id: str):
    max_seats_raw = request.form.get("max_seats", "").strip()
    credits_raw = request.form.get("credits", "").strip()

    try:
        updates: Dict = {
            "course_name": request.form.get("course_name", "").strip() or None,
            "instructor_name": request.form.get("instructor_name", "").strip() or None,
            "category": request.form.get("category", "").strip().title() or None,
            "branch": request.form.get("branch", "").strip() or None,
            "max_seats": int(max_seats_raw) if max_seats_raw else None,
            "credits": int(credits_raw) if credits_raw else None,
        }
    except ValueError:
        flash("Invalid number values for seats/credits.", "error")
        return redirect(url_for("admin_dashboard"))

    if updates.get("max_seats") is not None:
        if updates["max_seats"] < 1 or updates["max_seats"] > MAX_COURSE_SEATS:
            flash("Maximum seats must be between 1 and 5.", "error")
            return redirect(url_for("admin_dashboard"))

    if web_system.manager.update_course(course_id, **updates):
        web_system.save()
        flash("Course updated successfully.", "success")
    else:
        flash("Course not found.", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/courses/delete/<course_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_course(course_id: str):
    if web_system.manager.delete_course(course_id):
        web_system.save()
        flash("Course deleted successfully.", "success")
    else:
        flash("Course not found.", "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/students/add", methods=["POST"])
@login_required
@role_required("admin")
def add_student():
    try:
        student = Student(
            student_id=request.form.get("student_id", "").strip().upper(),
            student_name=request.form.get("student_name", "").strip(),
            branch=request.form.get("branch", "").strip(),
            semester=int(request.form.get("semester", "0")),
            email=request.form.get("email", "").strip().lower(),
        )
    except ValueError:
        flash("Semester must be a valid number.", "error")
        return redirect(url_for("admin_dashboard"))

    created, message = web_system.manager.register_student(student)
    if created:
        web_system.save()
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/enroll", methods=["POST"])
@login_required
def enroll():
    role = session.get("role")
    student_id = request.form.get("student_id", "").strip()
    if role == "student":
        student_id = session.get("student_id", "")
    course_id = request.form.get("course_id", "").strip()

    ok, message = web_system.manager.enroll_student_in_course(student_id, course_id)
    if ok:
        web_system.add_enrollment_event(student_id, course_id, "enrolled")
    elif "Waiting List" in message:
        web_system.add_enrollment_event(student_id, course_id, "waitlisted")

    web_system.save()

    flash(message, "success" if ok else "error")
    return redirect(url_for("dashboard_router"))


@app.route("/student/<student_id>")
@login_required
@role_required("admin")
def student_profile(student_id: str):
    student = web_system.manager.get_student(student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("admin_dashboard"))

    return render_template("student_profile.html", student=student)


if __name__ == "__main__":
    app.run(debug=True)
