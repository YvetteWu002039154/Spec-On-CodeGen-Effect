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


class AuthError(Exception):
    pass


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class PermissionError(Exception):
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
        raise ValidationError("Password must be at least 8 characters.")
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
class StudentOutcomes:
    graduated: bool = False
    placed: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.notes, str):
            raise ValidationError("Notes must be a string.")


@dataclass(frozen=True)
class VolunteerRecord:
    name: str
    email: str
    active: bool = True
    joined_at: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Volunteer name is required.")
        object.__setattr__(self, "email", _normalize_email(self.email))
        if self.joined_at.tzinfo is None:
            raise ValidationError("joined_at must be timezone-aware.")


@dataclass(frozen=True)
class WaitlistEntry:
    name: str
    email: str
    created_at: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("Waitlist name is required.")
        object.__setattr__(self, "email", _normalize_email(self.email))
        if self.created_at.tzinfo is None:
            raise ValidationError("created_at must be timezone-aware.")


class User:
    def __init__(self, user_id: int, email: str, role: Role, password: str) -> None:
        self._id: int = user_id
        self._email: str = _normalize_email(email)
        self._role: Role = role
        self._salt: bytes = os.urandom(16)
        self._password_hash: bytes = _hash_password(password, self._salt)
        self._created_at: datetime = _utcnow()
        self._last_login_at: Optional[datetime] = None

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
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def last_login_at(self) -> Optional[datetime]:
        return self._last_login_at

    def verify_password(self, password: str) -> bool:
        candidate = _hash_password(password, self._salt)
        return _constant_time_equals(candidate, self._password_hash)

    def set_password(self, new_password: str) -> None:
        self._salt = os.urandom(16)
        self._password_hash = _hash_password(new_password, self._salt)

    def mark_login(self) -> None:
        self._last_login_at = _utcnow()


class StudentProfile:
    def __init__(
        self,
        user_id: int,
        full_name: str,
        progress: Optional[StudentProgress] = None,
        outcomes: Optional[StudentOutcomes] = None,
    ) -> None:
        if not isinstance(full_name, str) or not full_name.strip():
            raise ValidationError("Student full_name is required.")
        self._user_id: int = user_id
        self._full_name: str = full_name.strip()
        self._progress: StudentProgress = progress or StudentProgress()
        self._outcomes: StudentOutcomes = outcomes or StudentOutcomes()
        self._updated_at: datetime = _utcnow()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def progress(self) -> StudentProgress:
        return self._progress

    @property
    def outcomes(self) -> StudentOutcomes:
        return self._outcomes

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_full_name(self, full_name: str) -> None:
        if not isinstance(full_name, str) or not full_name.strip():
            raise ValidationError("Student full_name is required.")
        self._full_name = full_name.strip()
        self._updated_at = _utcnow()

    def update_progress(self, completed_modules: int, total_modules: int) -> None:
        self._progress = StudentProgress(completed_modules=completed_modules, total_modules=total_modules)
        self._updated_at = _utcnow()

    def update_outcomes(self, graduated: bool, placed: bool, notes: str = "") -> None:
        self._outcomes = StudentOutcomes(graduated=bool(graduated), placed=bool(placed), notes=notes)
        self._updated_at = _utcnow()


@dataclass(frozen=True)
class Session:
    token: str
    user_id: int
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.token or not isinstance(self.token, str):
            raise ValidationError("Invalid session token.")
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValidationError("Session timestamps must be timezone-aware.")
        if self.expires_at <= self.created_at:
            raise ValidationError("Session expires_at must be after created_at.")

    @property
    def is_expired(self) -> bool:
        return _utcnow() >= self.expires_at


class AuthService:
    def __init__(self, user_store: "UserStore", session_ttl: timedelta = timedelta(hours=8)) -> None:
        if session_ttl <= timedelta(0):
            raise ValidationError("session_ttl must be positive.")
        self._user_store = user_store
        self._session_ttl = session_ttl
        self._sessions: Dict[str, Session] = {}

    def login(self, email: str, password: str) -> Session:
        email_n = _normalize_email(email)
        user = self._user_store.get_by_email(email_n)
        if user is None or not user.verify_password(password):
            raise AuthError("Invalid credentials.")
        user.mark_login()
        token = secrets.token_urlsafe(32)
        created = _utcnow()
        sess = Session(token=token, user_id=user.id, created_at=created, expires_at=created + self._session_ttl)
        self._sessions[token] = sess
        return sess

    def logout(self, token: str) -> None:
        if token in self._sessions:
            del self._sessions[token]

    def authenticate(self, token: str) -> User:
        sess = self._sessions.get(token)
        if sess is None:
            raise AuthError("Invalid session.")
        if sess.is_expired:
            del self._sessions[token]
            raise AuthError("Session expired.")
        user = self._user_store.get_by_id(sess.user_id)
        if user is None:
            del self._sessions[token]
            raise AuthError("Invalid session.")
        return user

    def cleanup_expired(self) -> int:
        now = _utcnow()
        expired = [t for t, s in self._sessions.items() if now >= s.expires_at]
        for t in expired:
            del self._sessions[t]
        return len(expired)


class UserStore:
    def __init__(self) -> None:
        self._by_id: Dict[int, User] = {}
        self._by_email: Dict[str, User] = {}
        self._next_id: int = 1

    def create_user(self, email: str, role: Role, password: str) -> User:
        email_n = _normalize_email(email)
        if email_n in self._by_email:
            raise ValidationError("Email already exists.")
        user = User(user_id=self._next_id, email=email_n, role=role, password=password)
        self._next_id += 1
        self._by_id[user.id] = user
        self._by_email[user.email] = user
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self._by_email.get(_normalize_email(email))

    def all_users(self) -> List[User]:
        return list(self._by_id.values())


class StudentStore:
    def __init__(self) -> None:
        self._profiles_by_user_id: Dict[int, StudentProfile] = {}

    def create_profile(self, user_id: int, full_name: str) -> StudentProfile:
        if user_id in self._profiles_by_user_id:
            raise ValidationError("Student profile already exists.")
        profile = StudentProfile(user_id=user_id, full_name=full_name)
        self._profiles_by_user_id[user_id] = profile
        return profile

    def get_profile(self, user_id: int) -> Optional[StudentProfile]:
        return self._profiles_by_user_id.get(user_id)

    def all_profiles(self) -> List[StudentProfile]:
        return list(self._profiles_by_user_id.values())


class VolunteerStore:
    def __init__(self) -> None:
        self._by_email: Dict[str, VolunteerRecord] = {}

    def upsert(self, name: str, email: str, active: bool = True) -> VolunteerRecord:
        email_n = _normalize_email(email)
        existing = self._by_email.get(email_n)
        if existing is None:
            rec = VolunteerRecord(name=name.strip(), email=email_n, active=bool(active), joined_at=_utcnow())
        else:
            rec = VolunteerRecord(
                name=name.strip() if isinstance(name, str) and name.strip() else existing.name,
                email=email_n,
                active=bool(active),
                joined_at=existing.joined_at,
            )
        self._by_email[email_n] = rec
        return rec

    def set_active(self, email: str, active: bool) -> VolunteerRecord:
        email_n = _normalize_email(email)
        rec = self._by_email.get(email_n)
        if rec is None:
            raise NotFoundError("Volunteer not found.")
        updated = VolunteerRecord(name=rec.name, email=rec.email, active=bool(active), joined_at=rec.joined_at)
        self._by_email[email_n] = updated
        return updated

    def list_all(self) -> List[VolunteerRecord]:
        return list(self._by_email.values())


class WaitlistStore:
    def __init__(self) -> None:
        self._entries_by_email: Dict[str, WaitlistEntry] = {}

    def add(self, name: str, email: str) -> WaitlistEntry:
        email_n = _normalize_email(email)
        if email_n in self._entries_by_email:
            raise ValidationError("Already on waitlist.")
        entry = WaitlistEntry(name=name.strip(), email=email_n, created_at=_utcnow())
        self._entries_by_email[email_n] = entry
        return entry

    def remove(self, email: str) -> None:
        email_n = _normalize_email(email)
        if email_n not in self._entries_by_email:
            raise NotFoundError("Waitlist entry not found.")
        del self._entries_by_email[email_n]

    def list_all(self) -> List[WaitlistEntry]:
        return sorted(self._entries_by_email.values(), key=lambda e: e.created_at)


class AccessControl:
    @staticmethod
    def is_admin_or_organizer(user: User) -> bool:
        return user.role in (Role.ADMIN, Role.ORGANIZER)

    @staticmethod
    def can_view_student_profile(requester: User, student_user_id: int) -> bool:
        if requester.id == student_user_id:
            return True
        return AccessControl.is_admin_or_organizer(requester)

    @staticmethod
    def require_admin_or_organizer(user: User) -> None:
        if not AccessControl.is_admin_or_organizer(user):
            raise PermissionError("Insufficient permissions.")

    @staticmethod
    def require_student(user: User) -> None:
        if user.role != Role.STUDENT:
            raise PermissionError("Insufficient permissions.")


class StudentManagementSystem:
    def __init__(self) -> None:
        self._users = UserStore()
        self._students = StudentStore()
        self._volunteers = VolunteerStore()
        self._waitlist = WaitlistStore()
        self._auth = AuthService(self._users)

    @property
    def auth(self) -> AuthService:
        return self._auth

    def register_student(self, email: str, password: str, full_name: str) -> Tuple[User, StudentProfile]:
        user = self._users.create_user(email=email, role=Role.STUDENT, password=password)
        profile = self._students.create_profile(user_id=user.id, full_name=full_name)
        return user, profile

    def register_admin(self, email: str, password: str) -> User:
        return self._users.create_user(email=email, role=Role.ADMIN, password=password)

    def register_organizer(self, email: str, password: str) -> User:
        return self._users.create_user(email=email, role=Role.ORGANIZER, password=password)

    def get_my_student_profile(self, token: str) -> StudentProfile:
        user = self._auth.authenticate(token)
        AccessControl.require_student(user)
        profile = self._students.get_profile(user.id)
        if profile is None:
            raise NotFoundError("Student profile not found.")
        return profile

    def get_student_profile(self, token: str, student_user_id: int) -> StudentProfile:
        requester = self._auth.authenticate(token)
        if not AccessControl.can_view_student_profile(requester, student_user_id):
            raise PermissionError("Insufficient permissions.")
        profile = self._students.get_profile(student_user_id)
        if profile is None:
            raise NotFoundError("Student profile not found.")
        return profile

    def update_my_profile_full_name(self, token: str, full_name: str) -> StudentProfile:
        user = self._auth.authenticate(token)
        AccessControl.require_student(user)
        profile = self._students.get_profile(user.id)
        if profile is None:
            raise NotFoundError("Student profile not found.")
        profile.update_full_name(full_name)
        return profile

    def admin_update_student_progress(
        self, token: str, student_user_id: int, completed_modules: int, total_modules: int
    ) -> StudentProfile:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        profile = self._students.get_profile(student_user_id)
        if profile is None:
            raise NotFoundError("Student profile not found.")
        profile.update_progress(completed_modules=completed_modules, total_modules=total_modules)
        return profile

    def admin_update_student_outcomes(
        self, token: str, student_user_id: int, graduated: bool, placed: bool, notes: str = ""
    ) -> StudentProfile:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        profile = self._students.get_profile(student_user_id)
        if profile is None:
            raise NotFoundError("Student profile not found.")
        profile.update_outcomes(graduated=graduated, placed=placed, notes=notes)
        return profile

    def admin_list_students(self, token: str) -> List[StudentProfile]:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        return self._students.all_profiles()

    def admin_dashboard_summary(self, token: str) -> Dict[str, object]:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)

        profiles = self._students.all_profiles()
        total_students = len(profiles)
        graduated = sum(1 for p in profiles if p.outcomes.graduated)
        placed = sum(1 for p in profiles if p.outcomes.placed)

        avg_completion = 0.0
        if total_students > 0:
            avg_completion = sum(p.progress.percent_complete for p in profiles) / total_students

        volunteers = self._volunteers.list_all()
        active_volunteers = sum(1 for v in volunteers if v.active)

        waitlist = self._waitlist.list_all()

        return {
            "students": {
                "total": total_students,
                "graduated": graduated,
                "placed": placed,
                "avg_percent_complete": avg_completion,
            },
            "volunteers": {
                "total": len(volunteers),
                "active": active_volunteers,
            },
            "waitlist": {
                "total": len(waitlist),
                "entries": waitlist,
            },
        }

    def admin_upsert_volunteer(self, token: str, name: str, email: str, active: bool = True) -> VolunteerRecord:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        return self._volunteers.upsert(name=name, email=email, active=active)

    def admin_set_volunteer_active(self, token: str, email: str, active: bool) -> VolunteerRecord:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        return self._volunteers.set_active(email=email, active=active)

    def admin_list_volunteers(self, token: str) -> List[VolunteerRecord]:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        return self._volunteers.list_all()

    def admin_add_waitlist(self, token: str, name: str, email: str) -> WaitlistEntry:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        return self._waitlist.add(name=name, email=email)

    def admin_remove_waitlist(self, token: str, email: str) -> None:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        self._waitlist.remove(email=email)

    def admin_list_waitlist(self, token: str) -> List[WaitlistEntry]:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        return self._waitlist.list_all()

    def get_user(self, token: str) -> User:
        return self._auth.authenticate(token)

    def list_users_admin(self, token: str) -> List[User]:
        requester = self._auth.authenticate(token)
        AccessControl.require_admin_or_organizer(requester)
        return self._users.all_users()

    def cleanup_sessions(self) -> int:
        return self._auth.cleanup_expired()