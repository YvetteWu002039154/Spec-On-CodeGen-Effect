from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 200_000) -> Tuple[bytes, bytes, int]:
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt, dk, iterations


def _verify_password(password: str, salt: bytes, expected_hash: bytes, iterations: int) -> bool:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk, expected_hash)


def _normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email must be a string.")
    e = email.strip().lower()
    if "@" not in e or e.startswith("@") or e.endswith("@"):
        raise ValidationError("Invalid email.")
    return e


def _validate_nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} is required.")
    return value.strip()


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
    def percent_complete(self) -> float:
        if self.total_modules == 0:
            return 0.0
        return (self.completed_modules / self.total_modules) * 100.0


@dataclass(frozen=True)
class StudentOutcome:
    status: str
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.updated_at.tzinfo is None:
            raise ValidationError("updated_at must be timezone-aware.")
        _validate_nonempty(self.status, "status")


class Account:
    def __init__(self, account_id: int, email: str, role: Role) -> None:
        self._id = account_id
        self._email = _normalize_email(email)
        self._role = role
        self._is_active = True
        self._created_at = _utcnow()
        self._last_login_at: Optional[datetime] = None
        self._password_salt: Optional[bytes] = None
        self._password_hash: Optional[bytes] = None
        self._password_iterations: Optional[int] = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> Role:
        return self._role

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def last_login_at(self) -> Optional[datetime]:
        return self._last_login_at

    def set_password(self, password: str) -> None:
        salt, pw_hash, iters = _hash_password(password)
        self._password_salt = salt
        self._password_hash = pw_hash
        self._password_iterations = iters

    def check_password(self, password: str) -> bool:
        if self._password_salt is None or self._password_hash is None or self._password_iterations is None:
            return False
        return _verify_password(password, self._password_salt, self._password_hash, self._password_iterations)

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True

    def _mark_login(self) -> None:
        self._last_login_at = _utcnow()


class Student(Account):
    def __init__(self, account_id: int, email: str, full_name: str) -> None:
        super().__init__(account_id, email, Role.STUDENT)
        self._full_name = _validate_nonempty(full_name, "full_name")
        self._profile_private = True
        self._progress = StudentProgress(0, 0)
        self._outcome: Optional[StudentOutcome] = None

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def profile_private(self) -> bool:
        return self._profile_private

    @property
    def progress(self) -> StudentProgress:
        return self._progress

    @property
    def outcome(self) -> Optional[StudentOutcome]:
        return self._outcome

    def set_full_name(self, full_name: str) -> None:
        self._full_name = _validate_nonempty(full_name, "full_name")

    def set_progress(self, completed_modules: int, total_modules: int) -> None:
        self._progress = StudentProgress(completed_modules=completed_modules, total_modules=total_modules)

    def set_outcome(self, status: str) -> None:
        self._outcome = StudentOutcome(status=_validate_nonempty(status, "status"), updated_at=_utcnow())


class Organizer(Account):
    def __init__(self, account_id: int, email: str, full_name: str, role: Role = Role.ORGANIZER) -> None:
        if role not in (Role.ORGANIZER, Role.ADMIN):
            raise ValidationError("Organizer role must be organizer or admin.")
        super().__init__(account_id, email, role)
        self._full_name = _validate_nonempty(full_name, "full_name")

    @property
    def full_name(self) -> str:
        return self._full_name

    def set_full_name(self, full_name: str) -> None:
        self._full_name = _validate_nonempty(full_name, "full_name")


@dataclass(frozen=True)
class Volunteer:
    volunteer_id: int
    full_name: str
    email: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValidationError("created_at must be timezone-aware.")
        _validate_nonempty(self.full_name, "full_name")
        _normalize_email(self.email)


@dataclass(frozen=True)
class WaitlistEntry:
    entry_id: int
    full_name: str
    email: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValidationError("created_at must be timezone-aware.")
        _validate_nonempty(self.full_name, "full_name")
        _normalize_email(self.email)


@dataclass(frozen=True)
class Session:
    token: str
    account_id: int
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValidationError("Session timestamps must be timezone-aware.")
        if self.expires_at <= self.created_at:
            raise ValidationError("Session expires_at must be after created_at.")

    @property
    def is_expired(self) -> bool:
        return _utcnow() >= self.expires_at


class AuthService:
    def __init__(self, session_ttl: timedelta = timedelta(hours=8)) -> None:
        if session_ttl.total_seconds() <= 0:
            raise ValidationError("session_ttl must be positive.")
        self._session_ttl = session_ttl
        self._sessions: Dict[str, Session] = {}

    def create_session(self, account: Account) -> Session:
        if not account.is_active:
            raise AuthError("Account is inactive.")
        token = secrets.token_urlsafe(32)
        now = _utcnow()
        session = Session(token=token, account_id=account.id, created_at=now, expires_at=now + self._session_ttl)
        self._sessions[token] = session
        account._mark_login()
        return session

    def get_session(self, token: str) -> Optional[Session]:
        s = self._sessions.get(token)
        if s is None:
            return None
        if s.is_expired:
            self._sessions.pop(token, None)
            return None
        return s

    def revoke_session(self, token: str) -> None:
        self._sessions.pop(token, None)

    def revoke_all_for_account(self, account_id: int) -> None:
        to_remove = [t for t, s in self._sessions.items() if s.account_id == account_id]
        for t in to_remove:
            self._sessions.pop(t, None)


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_account_id = 1
        self._next_volunteer_id = 1
        self._next_waitlist_id = 1

        self._accounts_by_id: Dict[int, Account] = {}
        self._account_id_by_email: Dict[str, int] = {}

        self._volunteers_by_id: Dict[int, Volunteer] = {}
        self._waitlist_by_id: Dict[int, WaitlistEntry] = {}

        self._auth = AuthService()

    @property
    def auth(self) -> AuthService:
        return self._auth

    def _allocate_account_id(self) -> int:
        aid = self._next_account_id
        self._next_account_id += 1
        return aid

    def _allocate_volunteer_id(self) -> int:
        vid = self._next_volunteer_id
        self._next_volunteer_id += 1
        return vid

    def _allocate_waitlist_id(self) -> int:
        wid = self._next_waitlist_id
        self._next_waitlist_id += 1
        return wid

    def _add_account(self, account: Account) -> None:
        if account.email in self._account_id_by_email:
            raise ValidationError("Email already exists.")
        self._accounts_by_id[account.id] = account
        self._account_id_by_email[account.email] = account.id

    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        return self._accounts_by_id.get(account_id)

    def get_account_by_email(self, email: str) -> Optional[Account]:
        e = _normalize_email(email)
        aid = self._account_id_by_email.get(e)
        if aid is None:
            return None
        return self._accounts_by_id.get(aid)

    def register_student(self, email: str, password: str, full_name: str) -> Student:
        account_id = self._allocate_account_id()
        student = Student(account_id=account_id, email=email, full_name=full_name)
        student.set_password(password)
        self._add_account(student)
        return student

    def register_organizer(self, email: str, password: str, full_name: str) -> Organizer:
        account_id = self._allocate_account_id()
        organizer = Organizer(account_id=account_id, email=email, full_name=full_name, role=Role.ORGANIZER)
        organizer.set_password(password)
        self._add_account(organizer)
        return organizer

    def register_admin(self, email: str, password: str, full_name: str) -> Organizer:
        account_id = self._allocate_account_id()
        admin = Organizer(account_id=account_id, email=email, full_name=full_name, role=Role.ADMIN)
        admin.set_password(password)
        self._add_account(admin)
        return admin

    def login(self, email: str, password: str) -> Session:
        account = self.get_account_by_email(email)
        if account is None:
            raise AuthError("Invalid credentials.")
        if not account.is_active:
            raise AuthError("Account is inactive.")
        if not account.check_password(password):
            raise AuthError("Invalid credentials.")
        return self._auth.create_session(account)

    def logout(self, token: str) -> None:
        self._auth.revoke_session(token)

    def _require_session(self, token: str) -> Account:
        session = self._auth.get_session(token)
        if session is None:
            raise AuthError("Invalid or expired session.")
        account = self.get_account_by_id(session.account_id)
        if account is None or not account.is_active:
            raise AuthError("Invalid session.")
        return account

    def _require_admin_or_organizer(self, account: Account) -> None:
        if account.role not in (Role.ORGANIZER, Role.ADMIN):
            raise PermissionError("Organizer or admin required.")

    def _require_admin(self, account: Account) -> None:
        if account.role != Role.ADMIN:
            raise PermissionError("Admin required.")

    def view_student_profile(self, token: str, student_id: int) -> Dict[str, object]:
        viewer = self._require_session(token)
        student = self.get_account_by_id(student_id)
        if not isinstance(student, Student):
            raise ValidationError("Student not found.")

        allowed = False
        if viewer.role in (Role.ORGANIZER, Role.ADMIN):
            allowed = True
        elif viewer.role == Role.STUDENT and viewer.id == student.id:
            allowed = True

        if not allowed:
            raise PermissionError("Not permitted to view this profile.")

        return {
            "id": student.id,
            "email": student.email,
            "full_name": student.full_name,
            "progress": {
                "completed_modules": student.progress.completed_modules,
                "total_modules": student.progress.total_modules,
                "percent_complete": student.progress.percent_complete,
            },
            "outcome": None
            if student.outcome is None
            else {"status": student.outcome.status, "updated_at": student.outcome.updated_at.isoformat()},
            "profile_private": student.profile_private,
        }

    def update_student_progress(self, token: str, student_id: int, completed_modules: int, total_modules: int) -> None:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)
        student = self.get_account_by_id(student_id)
        if not isinstance(student, Student):
            raise ValidationError("Student not found.")
        student.set_progress(completed_modules=completed_modules, total_modules=total_modules)

    def update_student_outcome(self, token: str, student_id: int, status: str) -> None:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)
        student = self.get_account_by_id(student_id)
        if not isinstance(student, Student):
            raise ValidationError("Student not found.")
        student.set_outcome(status=status)

    def list_students(self, token: str) -> List[Dict[str, object]]:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)
        students: List[Dict[str, object]] = []
        for acc in self._accounts_by_id.values():
            if isinstance(acc, Student):
                students.append(
                    {
                        "id": acc.id,
                        "email": acc.email,
                        "full_name": acc.full_name,
                        "progress_percent": acc.progress.percent_complete,
                        "outcome_status": None if acc.outcome is None else acc.outcome.status,
                    }
                )
        students.sort(key=lambda x: x["id"])
        return students

    def add_volunteer(self, token: str, full_name: str, email: str) -> Volunteer:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)
        vid = self._allocate_volunteer_id()
        v = Volunteer(volunteer_id=vid, full_name=_validate_nonempty(full_name, "full_name"), email=_normalize_email(email), created_at=_utcnow())
        self._volunteers_by_id[vid] = v
        return v

    def list_volunteers(self, token: str) -> List[Volunteer]:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)
        return [self._volunteers_by_id[k] for k in sorted(self._volunteers_by_id.keys())]

    def add_to_waitlist(self, token: str, full_name: str, email: str) -> WaitlistEntry:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)
        wid = self._allocate_waitlist_id()
        w = WaitlistEntry(entry_id=wid, full_name=_validate_nonempty(full_name, "full_name"), email=_normalize_email(email), created_at=_utcnow())
        self._waitlist_by_id[wid] = w
        return w

    def list_waitlist(self, token: str) -> List[WaitlistEntry]:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)
        return [self._waitlist_by_id[k] for k in sorted(self._waitlist_by_id.keys())]

    def admin_dashboard(self, token: str) -> Dict[str, object]:
        actor = self._require_session(token)
        self._require_admin_or_organizer(actor)

        students = [acc for acc in self._accounts_by_id.values() if isinstance(acc, Student)]
        total_students = len(students)
        avg_progress = 0.0
        if total_students > 0:
            avg_progress = sum(s.progress.percent_complete for s in students) / total_students

        outcomes: Dict[str, int] = {}
        for s in students:
            key = "unknown" if s.outcome is None else s.outcome.status
            outcomes[key] = outcomes.get(key, 0) + 1

        return {
            "students_total": total_students,
            "students_average_progress_percent": avg_progress,
            "outcomes": dict(sorted(outcomes.items(), key=lambda kv: kv[0])),
            "volunteers_total": len(self._volunteers_by_id),
            "waitlist_total": len(self._waitlist_by_id),
        }

    def deactivate_account(self, token: str, account_id: int) -> None:
        actor = self._require_session(token)
        self._require_admin(actor)
        acc = self.get_account_by_id(account_id)
        if acc is None:
            raise ValidationError("Account not found.")
        acc.deactivate()
        self._auth.revoke_all_for_account(account_id)

    def activate_account(self, token: str, account_id: int) -> None:
        actor = self._require_session(token)
        self._require_admin(actor)
        acc = self.get_account_by_id(account_id)
        if acc is None:
            raise ValidationError("Account not found.")
        acc.activate()