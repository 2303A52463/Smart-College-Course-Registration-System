from __future__ import annotations

from src.core.auth_manager import AuthManager
from src.core.registration_manager import RegistrationManager
from src.core.storage import StorageManager
from src.models.course import Course
from src.models.student import Student
from src.ui import SmartUI


def build_system() -> SmartUI:
    storage = StorageManager(data_dir="data")

    courses = [Course.from_dict(item) for item in storage.load_courses()]
    students = [Student.from_dict(item) for item in storage.load_students()]
    users = storage.load_users()

    manager = RegistrationManager(courses, students)
    auth = AuthManager(users)

    ui = SmartUI(manager, auth)

    original_logout = auth.logout

    def saving_logout() -> None:
        storage.save_courses(manager.export_courses())
        storage.save_students(manager.export_students())
        original_logout()

    auth.logout = saving_logout
    return ui


def main() -> None:
    ui = build_system()
    try:
        ui.run()
    except KeyboardInterrupt:
        ui.auth.logout()
        print("\nExiting... Saving data.")


if __name__ == "__main__":
    main()