from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class StorageManager:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_path = Path(data_dir)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.courses_file = self.data_path / "courses.json"
        self.students_file = self.data_path / "students.json"
        self.users_file = self.data_path / "users.json"
        self.enrollment_log_file = self.data_path / "enrollment_log.json"
        self._ensure_files_exist()

    def _ensure_files_exist(self) -> None:
        defaults = {
            self.courses_file: [],
            self.students_file: [],
            self.users_file: [
                {
                    "username": "admin",
                    "password": "admin123",
                    "role": "admin",
                    "email": "admin@college.edu",
                }
            ],
            self.enrollment_log_file: [],
        }
        for file_path, default_content in defaults.items():
            if not file_path.exists():
                with file_path.open("w", encoding="utf-8") as f:
                    json.dump(default_content, f, indent=2)

    def _read_json(self, file_path: Path) -> List[Dict]:
        if not file_path.exists():
            return []
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _write_json(self, file_path: Path, data: List[Dict]) -> None:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_courses(self) -> List[Dict]:
        return self._read_json(self.courses_file)

    def save_courses(self, data: List[Dict]) -> None:
        self._write_json(self.courses_file, data)

    def load_students(self) -> List[Dict]:
        return self._read_json(self.students_file)

    def save_students(self, data: List[Dict]) -> None:
        self._write_json(self.students_file, data)

    def load_users(self) -> List[Dict]:
        return self._read_json(self.users_file)

    def save_users(self, data: List[Dict]) -> None:
        self._write_json(self.users_file, data)

    def load_enrollment_log(self) -> List[Dict]:
        return self._read_json(self.enrollment_log_file)

    def save_enrollment_log(self, data: List[Dict]) -> None:
        self._write_json(self.enrollment_log_file, data)
