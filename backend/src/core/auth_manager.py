from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from werkzeug.security import check_password_hash, generate_password_hash  # type: ignore


@dataclass
class SessionUser:
    username: str
    role: str
    student_id: Optional[str] = None


class AuthManager:
    def __init__(self, users_data: List[Dict]) -> None:
        self.users = users_data
        self.current_user: Optional[SessionUser] = None

    def _find_user(self, username: str) -> Optional[Dict]:
        normalized_username = username.strip().lower()
        normalized_student_id = username.strip().upper()
        for user in self.users:
            if user.get("username", "").strip().lower() == normalized_username:
                return user
            if user.get("email", "").strip().lower() == normalized_username:
                return user
            if user.get("student_id", "").strip().upper() == normalized_student_id:
                return user
        return None

    def has_username(self, username: str) -> bool:
        return self._find_user(username) is not None

    def has_student_account(self, student_id: str) -> bool:
        normalized_student_id = student_id.strip().upper()
        for user in self.users:
            if user.get("student_id", "").strip().upper() == normalized_student_id:
                return True
        return False

    def has_email(self, email: str) -> bool:
        normalized_email = email.strip().lower()
        for user in self.users:
            if user.get("email", "").strip().lower() == normalized_email:
                return True
        return False

    def _verify_password(self, user: Dict, password: str) -> bool:
        stored_hash = user.get("password_hash")
        if stored_hash:
            return check_password_hash(stored_hash, password)
        plain_password = user.get("password")
        return plain_password == password

    def _upgrade_plain_password_if_needed(self, user: Dict, password: str) -> bool:
        if user.get("password_hash"):
            return False
        if user.get("password") == password:
            user["password_hash"] = generate_password_hash(password)
            user.pop("password", None)
            return True
        return False

    def login(self, username: str, password: str) -> bool:
        user = self._find_user(username)
        if not user:
            return False

        if self._verify_password(user, password):
            self._upgrade_plain_password_if_needed(user, password)
            self.current_user = SessionUser(
                username=user.get("username", "unknown"),
                role=user.get("role", "user"),
                student_id=user.get("student_id"),
            )
            return True
        return False

    def signup_student(
        self,
        username: str,
        password: str,
        email: str,
        student_id: str,
    ) -> bool:
        if self.has_username(username):
            return False
        if self.has_student_account(student_id):
            return False
        if self.has_email(email):
            return False

        self.users.append(
            {
                "username": username,
                "password_hash": generate_password_hash(password),
                "role": "student",
                "email": email,
                "student_id": student_id,
            }
        )
        return True

    def reset_password(self, username: str, email: str, new_password: str) -> bool:
        user = self._find_user(username)
        if not user:
            return False
        if user.get("email", "").lower() != email.lower():
            return False

        user["password_hash"] = generate_password_hash(new_password)
        user.pop("password", None)
        return True

    def logout(self) -> None:
        self.current_user = None

    def is_logged_in(self) -> bool:
        return self.current_user is not None
