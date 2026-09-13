from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class Role(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"


class AuthError(Exception):
    pass


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


def _constant_time_equals(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)


@dataclass(frozen=True)
class Session:
    token: str
    user_id: int
    role: Role
    created_at: datetime
    expires_at: datetime

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        now = now or _utcnow()
        return now >= self.expires_at


class User:
    __slots__ = ("_id", "_username", "_role", "_salt", "_password_hash", "_created_at", "_last_login_at")

    def __init__(self, user_id: int, username: str, role: Role, password: str) -> None:
        if not username or not username.strip():
            raise ValidationError("username is required")
        if role not in (Role.STUDENT, Role.ADMIN):
            raise ValidationError("invalid role")
        if not password or len(password) < 8:
            raise ValidationError("password must be at least 8 characters")

        self._id = user_id
        self._username = username.strip()
        self._role = role
        self._salt = os.urandom(16)
        self._password_hash = _hash_password(password, self._salt)
        self._created_at = _utcnow()
        self._last_login_at: Optional[datetime] = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def username(self) -> str:
        return self._username

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
        if password is None:
            return False
        candidate = _hash_password(password, self._salt)
        return _constant_time_equals(candidate, self._password_hash)

    def set_last_login(self, when: Optional[datetime] = None) -> None:
        self._last_login_at = when or _utcnow()


class StudentProfile:
    __slots__ = ("_user_id", "_full_name", "_email", "_created_at", "_updated_at")

    def __init__(self, user_id: int, full_name: str, email: str) -> None:
        if not full_name or not full_name.strip():
            raise ValidationError("full_name is required")
        if not email or "@" not in email or email.strip().startswith("@") or email.strip().endswith("@"):
            raise ValidationError("valid email is required")

        self._user_id = user_id
        self._full_name = full_name.strip()
        self._email = email.strip()
        self._created_at = _utcnow()
        self._updated_at = self._created_at

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def email(self) -> str:
        return self._email

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(self, *, full_name: Optional[str] = None, email: Optional[str] = None) -> None:
        changed = False
        if full_name is not None:
            if not full_name.strip():
                raise ValidationError("full_name cannot be empty")
            self._full_name = full_name.strip()
            changed = True
        if email is not None:
            if not email or "@" not in email or email.strip().startswith("@") or email.strip().endswith("@"):
                raise ValidationError("valid email is required")
            self._email = email.strip()
            changed = True
        if changed:
            self._updated_at = _utcnow()


class StudentProgress:
    __slots__ = ("_user_id", "_outcomes", "_created_at", "_updated_at")

    def __init__(self, user_id: int) -> None:
        self._user_id = user_id
        self._outcomes: List[str] = []
        self._created_at = _utcnow()
        self._updated_at = self._created_at

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def outcomes(self) -> Tuple[str, ...]:
        return tuple(self._outcomes)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def add_outcome(self, outcome: str) -> None:
        if not outcome or not outcome.strip():
            raise ValidationError("outcome is required")
        self._outcomes.append(outcome.strip())
        self._updated_at = _utcnow()


class Volunteer:
    __slots__ = ("_id", "_name", "_email", "_created_at", "_active")

    def __init__(self, volunteer_id: int, name: str, email: str) -> None:
        if not name or not name.strip():
            raise ValidationError("name is required")
        if not email or "@" not in email or email.strip().startswith("@") or email.strip().endswith("@"):
            raise ValidationError("valid email is required")
        self._id = volunteer_id
        self._name = name.strip()
        self._email = email.strip()
        self._created_at = _utcnow()
        self._active = True

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def activate(self) -> None:
        self._active = True


class Waitlist:
    __slots__ = ("_queue", "_set", "_created_at")

    def __init__(self) -> None:
        self._queue: List[int] = []
        self._set: Set[int] = set()
        self._created_at = _utcnow()

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def add(self, student_user_id: int) -> None:
        if student_user_id in self._set:
            return
        self._queue.append(student_user_id)
        self._set.add(student_user_id)

    def remove(self, student_user_id: int) -> None:
        if student_user_id not in self._set:
            return
        self._set.remove(student_user_id)
        self._queue = [sid for sid in self._queue if sid != student_user_id]

    def pop_next(self) -> Optional[int]:
        while self._queue:
            sid = self._queue.pop(0)
            if sid in self._set:
                self._set.remove(sid)
                return sid
        return None

    def list(self) -> Tuple[int, ...]:
        return tuple([sid for sid in self._queue if sid in self._set])

    def contains(self, student_user_id: int) -> bool:
        return student_user_id in self._set


class StudentManagementSystem:
    def __init__(self, *, session_ttl_minutes: int = 60) -> None:
        if session_ttl_minutes <= 0:
            raise ValidationError("session_ttl_minutes must be positive")
        self._session_ttl = timedelta(minutes=session_ttl_minutes)

        self._next_user_id = 1
        self._next_volunteer_id = 1

        self._users_by_id: Dict[int, User] = {}
        self._users_by_username: Dict[str, int] = {}

        self._profiles_by_user_id: Dict[int, StudentProfile] = {}
        self._progress_by_user_id: Dict[int, StudentProgress] = {}

        self._volunteers_by_id: Dict[int, Volunteer] = {}

        self._waitlist = Waitlist()

        self._sessions_by_token: Dict[str, Session] = {}

    @property
    def waitlist(self) -> Waitlist:
        return self._waitlist

    def _create_user(self, username: str, password: str, role: Role) -> User:
        uname = (username or "").strip()
        if not uname:
            raise ValidationError("username is required")
        key = uname.lower()
        if key in self._users_by_username:
            raise ValidationError("username already exists")

        user = User(self._next_user_id, uname, role, password)
        self._users_by_id[user.id] = user
        self._users_by_username[key] = user.id
        self._next_user_id += 1
        return user

    def register_student(self, *, username: str, password: str, full_name: str, email: str) -> int:
        user = self._create_user(username, password, Role.STUDENT)
        self._profiles_by_user_id[user.id] = StudentProfile(user.id, full_name, email)
        self._progress_by_user_id[user.id] = StudentProgress(user.id)
        return user.id

    def register_admin(self, *, username: str, password: str) -> int:
        user = self._create_user(username, password, Role.ADMIN)
        return user.id

    def login(self, *, username: str, password: str) -> str:
        uname = (username or "").strip().lower()
        if not uname:
            raise AuthError("invalid credentials")
        user_id = self._users_by_username.get(uname)
        if user_id is None:
            raise AuthError("invalid credentials")
        user = self._users_by_id[user_id]
        if not user.verify_password(password):
            raise AuthError("invalid credentials")

        now = _utcnow()
        user.set_last_login(now)

        token = secrets.token_urlsafe(32)
        session = Session(
            token=token,
            user_id=user.id,
            role=user.role,
            created_at=now,
            expires_at=now + self._session_ttl,
        )
        self._sessions_by_token[token] = session
        return token

    def logout(self, token: str) -> None:
        if token in self._sessions_by_token:
            del self._sessions_by_token[token]

    def _get_session(self, token: str) -> Session:
        session = self._sessions_by_token.get(token)
        if session is None:
            raise AuthError("not authenticated")
        if session.is_expired():
            del self._sessions_by_token[token]
            raise AuthError("session expired")
        return session

    def _require_admin(self, token: str) -> Session:
        session = self._get_session(token)
        if session.role != Role.ADMIN:
            raise AuthError("admin privileges required")
        return session

    def _require_student_or_admin(self, token: str) -> Session:
        session = self._get_session(token)
        if session.role not in (Role.STUDENT, Role.ADMIN):
            raise AuthError("not authorized")
        return session

    def get_own_student_profile(self, token: str) -> StudentProfile:
        session = self._get_session(token)
        if session.role != Role.STUDENT:
            raise AuthError("student privileges required")
        profile = self._profiles_by_user_id.get(session.user_id)
        if profile is None:
            raise NotFoundError("student profile not found")
        return profile

    def get_student_profile(self, token: str, student_user_id: int) -> StudentProfile:
        session = self._get_session(token)
        if session.role == Role.STUDENT and session.user_id != student_user_id:
            raise AuthError("not authorized to view this profile")
        if session.role not in (Role.STUDENT, Role.ADMIN):
            raise AuthError("not authorized")
        profile = self._profiles_by_user_id.get(student_user_id)
        if profile is None:
            raise NotFoundError("student profile not found")
        return profile

    def update_own_student_profile(
        self,
        token: str,
        *,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> None:
        profile = self.get_own_student_profile(token)
        profile.update(full_name=full_name, email=email)

    def add_student_outcome(self, token: str, student_user_id: int, outcome: str) -> None:
        self._require_admin(token)
        progress = self._progress_by_user_id.get(student_user_id)
        if progress is None:
            raise NotFoundError("student progress not found")
        progress.add_outcome(outcome)

    def get_student_progress(self, token: str, student_user_id: int) -> StudentProgress:
        session = self._get_session(token)
        if session.role == Role.STUDENT and session.user_id != student_user_id:
            raise AuthError("not authorized to view this progress")
        if session.role not in (Role.STUDENT, Role.ADMIN):
            raise AuthError("not authorized")
        progress = self._progress_by_user_id.get(student_user_id)
        if progress is None:
            raise NotFoundError("student progress not found")
        return progress

    def list_students(self, token: str) -> Tuple[int, ...]:
        self._require_admin(token)
        return tuple(sorted(self._profiles_by_user_id.keys()))

    def create_volunteer(self, token: str, *, name: str, email: str) -> int:
        self._require_admin(token)
        volunteer = Volunteer(self._next_volunteer_id, name, email)
        self._volunteers_by_id[volunteer.id] = volunteer
        self._next_volunteer_id += 1
        return volunteer.id

    def list_volunteers(self, token: str, *, active_only: bool = False) -> Tuple[Volunteer, ...]:
        self._require_admin(token)
        vols = list(self._volunteers_by_id.values())
        if active_only:
            vols = [v for v in vols if v.active]
        vols.sort(key=lambda v: v.id)
        return tuple(vols)

    def set_volunteer_active(self, token: str, volunteer_id: int, *, active: bool) -> None:
        self._require_admin(token)
        v = self._volunteers_by_id.get(volunteer_id)
        if v is None:
            raise NotFoundError("volunteer not found")
        if active:
            v.activate()
        else:
            v.deactivate()

    def add_student_to_waitlist(self, token: str, student_user_id: int) -> None:
        self._require_admin(token)
        if student_user_id not in self._profiles_by_user_id:
            raise NotFoundError("student not found")
        self._waitlist.add(student_user_id)

    def remove_student_from_waitlist(self, token: str, student_user_id: int) -> None:
        self._require_admin(token)
        self._waitlist.remove(student_user_id)

    def view_waitlist(self, token: str) -> Tuple[int, ...]:
        self._require_admin(token)
        return self._waitlist.list()

    def admin_dashboard_summary(self, token: str) -> Dict[str, int]:
        self._require_admin(token)
        total_students = len(self._profiles_by_user_id)
        total_volunteers = len(self._volunteers_by_id)
        active_volunteers = sum(1 for v in self._volunteers_by_id.values() if v.active)
        waitlist_count = len(self._waitlist.list())
        return {
            "students": total_students,
            "volunteers": total_volunteers,
            "active_volunteers": active_volunteers,
            "waitlist": waitlist_count,
        }


def _demo() -> None:
    sms = StudentManagementSystem()
    admin_id = sms.register_admin(username="admin", password="adminpass1")
    _ = admin_id

    s1 = sms.register_student(username="alice", password="password123", full_name="Alice A", email="alice@example.com")
    s2 = sms.register_student(username="bob", password="password123", full_name="Bob B", email="bob@example.com")

    admin_token = sms.login(username="admin", password="adminpass1")
    student_token = sms.login(username="alice", password="password123")

    sms.add_student_outcome(admin_token, s1, "Completed onboarding")
    sms.add_student_to_waitlist(admin_token, s2)
    _ = sms.get_own_student_profile(student_token)
    _ = sms.get_student_progress(student_token, s1)
    _ = sms.admin_dashboard_summary(admin_token)


if __name__ == "__main__":
    _demo()