from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class Role(str, Enum):
    STUDENT = "student"
    ORGANIZER = "organizer"
    ADMIN = "admin"


class AuthError(Exception):
    pass


class PermissionError(Exception):
    pass


class ValidationError(Exception):
    pass


def _now_ts() -> float:
    return time.time()


def _normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email must be a string.")
    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValidationError("Invalid email.")
    return email


def _hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("Password must be a string with at least 8 characters.")
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt, dk


def _verify_password(password: str, salt: bytes, digest: bytes) -> bool:
    _, dk = _hash_password(password, salt=salt)
    return hmac.compare_digest(dk, digest)


@dataclass(frozen=True)
class StudentProgress:
    completed_modules: int = 0
    total_modules: int = 0

    def __post_init__(self) -> None:
        if self.completed_modules < 0 or self.total_modules < 0:
            raise ValidationError("Module counts must be non-negative.")
        if self.completed_modules > self.total_modules:
            raise ValidationError("Completed modules cannot exceed total modules.")

    @property
    def completion_rate(self) -> float:
        if self.total_modules == 0:
            return 0.0
        return self.completed_modules / self.total_modules


@dataclass(frozen=True)
class StudentOutcome:
    status: str = "unknown"
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValidationError("Outcome status must be a non-empty string.")
        if not isinstance(self.notes, str):
            raise ValidationError("Outcome notes must be a string.")


class Account:
    def __init__(self, email: str, password: str, role: Role) -> None:
        self._email: str = _normalize_email(email)
        self._role: Role = role
        self._salt, self._password_digest = _hash_password(password)
        self._created_at: float = _now_ts()
        self._last_login_at: Optional[float] = None
        self._active: bool = True

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> Role:
        return self._role

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def last_login_at(self) -> Optional[float]:
        return self._last_login_at

    @property
    def is_active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def activate(self) -> None:
        self._active = True

    def check_password(self, password: str) -> bool:
        return _verify_password(password, self._salt, self._password_digest)

    def set_password(self, new_password: str) -> None:
        self._salt, self._password_digest = _hash_password(new_password)

    def _mark_login(self) -> None:
        self._last_login_at = _now_ts()


class Student(Account):
    def __init__(self, email: str, password: str, full_name: str) -> None:
        super().__init__(email=email, password=password, role=Role.STUDENT)
        if not isinstance(full_name, str) or not full_name.strip():
            raise ValidationError("Full name must be a non-empty string.")
        self._full_name: str = full_name.strip()
        self._progress: StudentProgress = StudentProgress()
        self._outcome: StudentOutcome = StudentOutcome()
        self._profile_private: bool = True

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def progress(self) -> StudentProgress:
        return self._progress

    @property
    def outcome(self) -> StudentOutcome:
        return self._outcome

    @property
    def profile_private(self) -> bool:
        return self._profile_private

    def set_profile_private(self, private: bool) -> None:
        if not isinstance(private, bool):
            raise ValidationError("Private flag must be boolean.")
        self._profile_private = private

    def update_progress(self, completed_modules: int, total_modules: int) -> None:
        self._progress = StudentProgress(completed_modules=completed_modules, total_modules=total_modules)

    def update_outcome(self, status: str, notes: str = "") -> None:
        self._outcome = StudentOutcome(status=status, notes=notes)


class Organizer(Account):
    def __init__(self, email: str, password: str, display_name: str) -> None:
        super().__init__(email=email, password=password, role=Role.ORGANIZER)
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValidationError("Display name must be a non-empty string.")
        self._display_name: str = display_name.strip()

    @property
    def display_name(self) -> str:
        return self._display_name


class Admin(Account):
    def __init__(self, email: str, password: str, display_name: str) -> None:
        super().__init__(email=email, password=password, role=Role.ADMIN)
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValidationError("Display name must be a non-empty string.")
        self._display_name: str = display_name.strip()

    @property
    def display_name(self) -> str:
        return self._display_name


@dataclass(frozen=True)
class Volunteer:
    email: str
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "email", _normalize_email(self.email))
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Volunteer name must be a non-empty string.")
        object.__setattr__(self, "name", self.name.strip())


class Session:
    def __init__(self, token: str, account_email: str, created_at: float) -> None:
        self._token = token
        self._account_email = account_email
        self._created_at = created_at
        self._revoked = False

    @property
    def token(self) -> str:
        return self._token

    @property
    def account_email(self) -> str:
        return self._account_email

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def revoked(self) -> bool:
        return self._revoked

    def revoke(self) -> None:
        self._revoked = True


class StudentManagementSystem:
    def __init__(self) -> None:
        self._accounts_by_email: Dict[str, Account] = {}
        self._students_by_email: Dict[str, Student] = {}
        self._sessions_by_token: Dict[str, Session] = {}
        self._volunteers_by_email: Dict[str, Volunteer] = {}
        self._waitlist: List[str] = []

    def register_student(self, email: str, password: str, full_name: str) -> Student:
        email_n = _normalize_email(email)
        if email_n in self._accounts_by_email:
            raise ValidationError("Account already exists.")
        student = Student(email=email_n, password=password, full_name=full_name)
        self._accounts_by_email[email_n] = student
        self._students_by_email[email_n] = student
        return student

    def register_organizer(self, email: str, password: str, display_name: str) -> Organizer:
        email_n = _normalize_email(email)
        if email_n in self._accounts_by_email:
            raise ValidationError("Account already exists.")
        organizer = Organizer(email=email_n, password=password, display_name=display_name)
        self._accounts_by_email[email_n] = organizer
        return organizer

    def register_admin(self, email: str, password: str, display_name: str) -> Admin:
        email_n = _normalize_email(email)
        if email_n in self._accounts_by_email:
            raise ValidationError("Account already exists.")
        admin = Admin(email=email_n, password=password, display_name=display_name)
        self._accounts_by_email[email_n] = admin
        return admin

    def login(self, email: str, password: str) -> str:
        email_n = _normalize_email(email)
        account = self._accounts_by_email.get(email_n)
        if account is None or not account.is_active:
            raise AuthError("Invalid credentials.")
        if not account.check_password(password):
            raise AuthError("Invalid credentials.")
        token = secrets.token_urlsafe(32)
        session = Session(token=token, account_email=email_n, created_at=_now_ts())
        self._sessions_by_token[token] = session
        account._mark_login()
        return token

    def logout(self, token: str) -> None:
        session = self._sessions_by_token.get(token)
        if session is None or session.revoked:
            return
        session.revoke()

    def _require_session(self, token: str) -> Account:
        session = self._sessions_by_token.get(token)
        if session is None or session.revoked:
            raise AuthError("Not authenticated.")
        account = self._accounts_by_email.get(session.account_email)
        if account is None or not account.is_active:
            raise AuthError("Not authenticated.")
        return account

    def _is_staff(self, account: Account) -> bool:
        return account.role in (Role.ORGANIZER, Role.ADMIN)

    def _require_staff(self, token: str) -> Account:
        account = self._require_session(token)
        if not self._is_staff(account):
            raise PermissionError("Insufficient permissions.")
        return account

    def _require_admin(self, token: str) -> Account:
        account = self._require_session(token)
        if account.role != Role.ADMIN:
            raise PermissionError("Insufficient permissions.")
        return account

    def get_my_student_profile(self, token: str) -> Student:
        account = self._require_session(token)
        if account.role != Role.STUDENT:
            raise PermissionError("Only students can access their own student profile via this method.")
        student = self._students_by_email.get(account.email)
        if student is None:
            raise ValidationError("Student profile not found.")
        return student

    def get_student_profile(self, token: str, student_email: str) -> Student:
        requester = self._require_session(token)
        student_email_n = _normalize_email(student_email)
        student = self._students_by_email.get(student_email_n)
        if student is None:
            raise ValidationError("Student profile not found.")

        if requester.role == Role.STUDENT:
            if requester.email != student_email_n:
                raise PermissionError("Students can only view their own profile.")
            return student

        if self._is_staff(requester):
            return student

        raise PermissionError("Insufficient permissions.")

    def list_students_for_admin_dashboard(self, token: str) -> List[Student]:
        self._require_staff(token)
        return list(self._students_by_email.values())

    def update_student_progress(self, token: str, student_email: str, completed_modules: int, total_modules: int) -> None:
        self._require_staff(token)
        student = self._students_by_email.get(_normalize_email(student_email))
        if student is None:
            raise ValidationError("Student profile not found.")
        student.update_progress(completed_modules=completed_modules, total_modules=total_modules)

    def update_student_outcome(self, token: str, student_email: str, status: str, notes: str = "") -> None:
        self._require_staff(token)
        student = self._students_by_email.get(_normalize_email(student_email))
        if student is None:
            raise ValidationError("Student profile not found.")
        student.update_outcome(status=status, notes=notes)

    def set_student_profile_privacy(self, token: str, private: bool) -> None:
        student = self.get_my_student_profile(token)
        student.set_profile_private(private)

    def add_volunteer(self, token: str, email: str, name: str) -> Volunteer:
        self._require_staff(token)
        v = Volunteer(email=email, name=name)
        if v.email in self._volunteers_by_email:
            raise ValidationError("Volunteer already exists.")
        self._volunteers_by_email[v.email] = v
        return v

    def remove_volunteer(self, token: str, email: str) -> None:
        self._require_staff(token)
        email_n = _normalize_email(email)
        if email_n in self._volunteers_by_email:
            del self._volunteers_by_email[email_n]

    def list_volunteers(self, token: str) -> List[Volunteer]:
        self._require_staff(token)
        return list(self._volunteers_by_email.values())

    def add_to_waitlist(self, token: str, student_email: str) -> None:
        self._require_staff(token)
        email_n = _normalize_email(student_email)
        if email_n not in self._students_by_email:
            raise ValidationError("Student profile not found.")
        if email_n in self._waitlist:
            return
        self._waitlist.append(email_n)

    def remove_from_waitlist(self, token: str, student_email: str) -> None:
        self._require_staff(token)
        email_n = _normalize_email(student_email)
        try:
            self._waitlist.remove(email_n)
        except ValueError:
            return

    def get_waitlist(self, token: str) -> List[str]:
        self._require_staff(token)
        return list(self._waitlist)

    def admin_deactivate_account(self, token: str, email: str) -> None:
        self._require_admin(token)
        email_n = _normalize_email(email)
        account = self._accounts_by_email.get(email_n)
        if account is None:
            raise ValidationError("Account not found.")
        account.deactivate()
        for sess in self._sessions_by_token.values():
            if sess.account_email == email_n:
                sess.revoke()

    def admin_activate_account(self, token: str, email: str) -> None:
        self._require_admin(token)
        email_n = _normalize_email(email)
        account = self._accounts_by_email.get(email_n)
        if account is None:
            raise ValidationError("Account not found.")
        account.activate()

    def admin_list_accounts(self, token: str) -> List[Account]:
        self._require_admin(token)
        return list(self._accounts_by_email.values())

    def admin_get_account(self, token: str, email: str) -> Account:
        self._require_admin(token)
        email_n = _normalize_email(email)
        account = self._accounts_by_email.get(email_n)
        if account is None:
            raise ValidationError("Account not found.")
        return account

    def admin_list_active_sessions(self, token: str) -> List[Session]:
        self._require_admin(token)
        return [s for s in self._sessions_by_token.values() if not s.revoked]

    def admin_revoke_session(self, token: str, session_token: str) -> None:
        self._require_admin(token)
        sess = self._sessions_by_token.get(session_token)
        if sess is None:
            raise ValidationError("Session not found.")
        sess.revoke()

    def get_public_student_directory(self, token: str) -> List[Student]:
        requester = self._require_session(token)
        if self._is_staff(requester):
            return list(self._students_by_email.values())
        if requester.role == Role.STUDENT:
            return [s for s in self._students_by_email.values() if not s.profile_private]
        raise PermissionError("Insufficient permissions.")

    def export_admin_dashboard_snapshot(self, token: str) -> Dict[str, object]:
        self._require_staff(token)
        students = list(self._students_by_email.values())
        snapshot = {
            "student_count": len(students),
            "students": [
                {
                    "email": s.email,
                    "full_name": s.full_name,
                    "progress": {
                        "completed_modules": s.progress.completed_modules,
                        "total_modules": s.progress.total_modules,
                        "completion_rate": s.progress.completion_rate,
                    },
                    "outcome": {"status": s.outcome.status, "notes": s.outcome.notes},
                    "profile_private": s.profile_private,
                }
                for s in students
            ],
            "volunteer_count": len(self._volunteers_by_email),
            "waitlist": list(self._waitlist),
        }
        return snapshot