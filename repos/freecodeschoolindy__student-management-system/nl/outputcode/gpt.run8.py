from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class Role(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"
    ORGANIZER = "organizer"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AuthError(Exception):
    pass


class PermissionError(Exception):
    pass


class ValidationError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email must be a string.")
    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValidationError("Invalid email.")
    return email


def _hash_password(password: str, salt: bytes) -> bytes:
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("Password must be a string with at least 8 characters.")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


def _constant_time_equals(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)


@dataclass(frozen=True)
class StudentProgress:
    completed_modules: int = 0
    total_modules: int = 0

    def __post_init__(self) -> None:
        if self.completed_modules < 0 or self.total_modules < 0:
            raise ValidationError("Module counts cannot be negative.")
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
    notes: str = ""
    updated_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValidationError("Outcome status must be a non-empty string.")
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", _utcnow())


@dataclass(frozen=True)
class Volunteer:
    name: str
    email: str
    active: bool = True
    added_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Volunteer name must be a non-empty string.")
        object.__setattr__(self, "email", _normalize_email(self.email))
        if self.added_at is None:
            object.__setattr__(self, "added_at", _utcnow())


@dataclass(frozen=True)
class WaitlistEntry:
    student_id: int
    added_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.student_id <= 0:
            raise ValidationError("student_id must be positive.")
        if self.added_at is None:
            object.__setattr__(self, "added_at", _utcnow())


class Account:
    def __init__(self, account_id: int, email: str, role: Role, password: str) -> None:
        if account_id <= 0:
            raise ValidationError("account_id must be positive.")
        self._id: int = account_id
        self._email: str = _normalize_email(email)
        self._role: Role = role
        self._status: AccountStatus = AccountStatus.ACTIVE
        self._created_at: datetime = _utcnow()
        self._salt: bytes = os.urandom(16)
        self._password_hash: bytes = _hash_password(password, self._salt)

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
    def status(self) -> AccountStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def disable(self) -> None:
        self._status = AccountStatus.DISABLED

    def enable(self) -> None:
        self._status = AccountStatus.ACTIVE

    def set_password(self, new_password: str) -> None:
        self._salt = os.urandom(16)
        self._password_hash = _hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        if self._status != AccountStatus.ACTIVE:
            return False
        candidate = _hash_password(password, self._salt)
        return _constant_time_equals(candidate, self._password_hash)


class StudentProfile:
    def __init__(
        self,
        student_id: int,
        full_name: str,
        bio: str = "",
        progress: Optional[StudentProgress] = None,
        outcome: Optional[StudentOutcome] = None,
    ) -> None:
        if student_id <= 0:
            raise ValidationError("student_id must be positive.")
        if not isinstance(full_name, str) or not full_name.strip():
            raise ValidationError("full_name must be a non-empty string.")
        if not isinstance(bio, str):
            raise ValidationError("bio must be a string.")
        self._student_id: int = student_id
        self._full_name: str = full_name.strip()
        self._bio: str = bio
        self._progress: StudentProgress = progress if progress is not None else StudentProgress()
        self._outcome: Optional[StudentOutcome] = outcome
        self._updated_at: datetime = _utcnow()

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def bio(self) -> str:
        return self._bio

    @property
    def progress(self) -> StudentProgress:
        return self._progress

    @property
    def outcome(self) -> Optional[StudentOutcome]:
        return self._outcome

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_bio(self, bio: str) -> None:
        if not isinstance(bio, str):
            raise ValidationError("bio must be a string.")
        self._bio = bio
        self._updated_at = _utcnow()

    def update_progress(self, completed_modules: int, total_modules: int) -> None:
        self._progress = StudentProgress(completed_modules=completed_modules, total_modules=total_modules)
        self._updated_at = _utcnow()

    def set_outcome(self, status: str, notes: str = "") -> None:
        if not isinstance(notes, str):
            raise ValidationError("notes must be a string.")
        self._outcome = StudentOutcome(status=status, notes=notes, updated_at=_utcnow())
        self._updated_at = _utcnow()


class Session:
    def __init__(self, token: str, account_id: int, created_at: datetime, expires_at: datetime) -> None:
        self._token = token
        self._account_id = account_id
        self._created_at = created_at
        self._expires_at = expires_at

    @property
    def token(self) -> str:
        return self._token

    @property
    def account_id(self) -> int:
        return self._account_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def expires_at(self) -> datetime:
        return self._expires_at

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        now = now or _utcnow()
        return now >= self._expires_at


class AuthService:
    def __init__(self, session_ttl: timedelta = timedelta(hours=8)) -> None:
        if session_ttl.total_seconds() <= 0:
            raise ValidationError("session_ttl must be positive.")
        self._session_ttl = session_ttl
        self._sessions: Dict[str, Session] = {}

    def create_session(self, account: Account) -> Session:
        if account.status != AccountStatus.ACTIVE:
            raise AuthError("Account is not active.")
        token = secrets.token_urlsafe(32)
        now = _utcnow()
        session = Session(token=token, account_id=account.id, created_at=now, expires_at=now + self._session_ttl)
        self._sessions[token] = session
        return session

    def get_session(self, token: str) -> Optional[Session]:
        if not isinstance(token, str) or not token:
            return None
        session = self._sessions.get(token)
        if session is None:
            return None
        if session.is_expired():
            self._sessions.pop(token, None)
            return None
        return session

    def revoke_session(self, token: str) -> None:
        if not isinstance(token, str) or not token:
            return
        self._sessions.pop(token, None)

    def revoke_all_for_account(self, account_id: int) -> None:
        to_delete = [t for t, s in self._sessions.items() if s.account_id == account_id]
        for t in to_delete:
            self._sessions.pop(t, None)


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_account_id: int = 1
        self._accounts_by_id: Dict[int, Account] = {}
        self._accounts_by_email: Dict[str, int] = {}

        self._student_profiles: Dict[int, StudentProfile] = {}

        self._volunteers_by_email: Dict[str, Volunteer] = {}
        self._waitlist: List[WaitlistEntry] = []
        self._waitlist_set: Set[int] = set()

        self._auth: AuthService = AuthService()

    @property
    def auth(self) -> AuthService:
        return self._auth

    def _create_account(self, email: str, role: Role, password: str) -> Account:
        email_n = _normalize_email(email)
        if email_n in self._accounts_by_email:
            raise ValidationError("Email already exists.")
        account = Account(account_id=self._next_account_id, email=email_n, role=role, password=password)
        self._accounts_by_id[account.id] = account
        self._accounts_by_email[email_n] = account.id
        self._next_account_id += 1
        return account

    def register_student(self, email: str, password: str, full_name: str, bio: str = "") -> Account:
        account = self._create_account(email=email, role=Role.STUDENT, password=password)
        self._student_profiles[account.id] = StudentProfile(student_id=account.id, full_name=full_name, bio=bio)
        return account

    def register_admin(self, email: str, password: str) -> Account:
        return self._create_account(email=email, role=Role.ADMIN, password=password)

    def register_organizer(self, email: str, password: str) -> Account:
        return self._create_account(email=email, role=Role.ORGANIZER, password=password)

    def login(self, email: str, password: str) -> Session:
        email_n = _normalize_email(email)
        account_id = self._accounts_by_email.get(email_n)
        if account_id is None:
            raise AuthError("Invalid credentials.")
        account = self._accounts_by_id[account_id]
        if not account.verify_password(password):
            raise AuthError("Invalid credentials.")
        return self._auth.create_session(account)

    def logout(self, token: str) -> None:
        self._auth.revoke_session(token)

    def _require_session(self, token: str) -> Account:
        session = self._auth.get_session(token)
        if session is None:
            raise AuthError("Invalid or expired session.")
        account = self._accounts_by_id.get(session.account_id)
        if account is None or account.status != AccountStatus.ACTIVE:
            raise AuthError("Invalid session.")
        return account

    def _require_admin_or_organizer(self, account: Account) -> None:
        if account.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Admin/Organizer access required.")

    def _require_student(self, account: Account) -> None:
        if account.role != Role.STUDENT:
            raise PermissionError("Student access required.")

    def get_my_profile(self, token: str) -> StudentProfile:
        account = self._require_session(token)
        self._require_student(account)
        profile = self._student_profiles.get(account.id)
        if profile is None:
            raise ValidationError("Student profile not found.")
        return profile

    def get_student_profile(self, token: str, student_id: int) -> StudentProfile:
        account = self._require_session(token)
        if account.role == Role.STUDENT and account.id != student_id:
            raise PermissionError("Students can only view their own profile.")
        if account.role in (Role.ADMIN, Role.ORGANIZER) or account.id == student_id:
            profile = self._student_profiles.get(student_id)
            if profile is None:
                raise ValidationError("Student profile not found.")
            return profile
        raise PermissionError("Access denied.")

    def update_my_bio(self, token: str, bio: str) -> None:
        profile = self.get_my_profile(token)
        profile.update_bio(bio)

    def admin_update_student_progress(self, token: str, student_id: int, completed_modules: int, total_modules: int) -> None:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        profile = self._student_profiles.get(student_id)
        if profile is None:
            raise ValidationError("Student profile not found.")
        profile.update_progress(completed_modules=completed_modules, total_modules=total_modules)

    def admin_set_student_outcome(self, token: str, student_id: int, status: str, notes: str = "") -> None:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        profile = self._student_profiles.get(student_id)
        if profile is None:
            raise ValidationError("Student profile not found.")
        profile.set_outcome(status=status, notes=notes)

    def admin_list_students(self, token: str) -> List[StudentProfile]:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        return list(self._student_profiles.values())

    def admin_disable_account(self, token: str, account_id: int) -> None:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        target = self._accounts_by_id.get(account_id)
        if target is None:
            raise ValidationError("Account not found.")
        target.disable()
        self._auth.revoke_all_for_account(account_id)

    def admin_enable_account(self, token: str, account_id: int) -> None:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        target = self._accounts_by_id.get(account_id)
        if target is None:
            raise ValidationError("Account not found.")
        target.enable()

    def admin_add_volunteer(self, token: str, name: str, email: str, active: bool = True) -> Volunteer:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        email_n = _normalize_email(email)
        volunteer = Volunteer(name=name, email=email_n, active=active, added_at=_utcnow())
        self._volunteers_by_email[email_n] = volunteer
        return volunteer

    def admin_set_volunteer_active(self, token: str, email: str, active: bool) -> None:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        email_n = _normalize_email(email)
        v = self._volunteers_by_email.get(email_n)
        if v is None:
            raise ValidationError("Volunteer not found.")
        self._volunteers_by_email[email_n] = Volunteer(name=v.name, email=v.email, active=active, added_at=v.added_at)

    def admin_list_volunteers(self, token: str) -> List[Volunteer]:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        return list(self._volunteers_by_email.values())

    def admin_add_to_waitlist(self, token: str, student_id: int) -> None:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        if student_id not in self._student_profiles:
            raise ValidationError("Student profile not found.")
        if student_id in self._waitlist_set:
            return
        entry = WaitlistEntry(student_id=student_id, added_at=_utcnow())
        self._waitlist.append(entry)
        self._waitlist_set.add(student_id)

    def admin_remove_from_waitlist(self, token: str, student_id: int) -> None:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        if student_id not in self._waitlist_set:
            return
        self._waitlist = [e for e in self._waitlist if e.student_id != student_id]
        self._waitlist_set.discard(student_id)

    def admin_get_waitlist(self, token: str) -> List[WaitlistEntry]:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        return list(self._waitlist)

    def admin_dashboard_summary(self, token: str) -> Dict[str, int]:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        total_students = len(self._student_profiles)
        total_volunteers = len(self._volunteers_by_email)
        active_volunteers = sum(1 for v in self._volunteers_by_email.values() if v.active)
        waitlist_count = len(self._waitlist)
        return {
            "students": total_students,
            "volunteers": total_volunteers,
            "active_volunteers": active_volunteers,
            "waitlist": waitlist_count,
        }

    def admin_student_progress_overview(self, token: str) -> List[Tuple[int, float, Optional[str]]]:
        account = self._require_session(token)
        self._require_admin_or_organizer(account)
        overview: List[Tuple[int, float, Optional[str]]] = []
        for student_id, profile in self._student_profiles.items():
            outcome_status = profile.outcome.status if profile.outcome is not None else None
            overview.append((student_id, profile.progress.percent_complete, outcome_status))
        return overview