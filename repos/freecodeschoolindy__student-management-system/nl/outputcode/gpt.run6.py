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


def _normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email must be a string.")
    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValidationError("Invalid email.")
    return email


def _hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 200_000) -> str:
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, dk_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


@dataclass(frozen=True)
class Session:
    token: str
    user_id: int
    created_at: datetime
    expires_at: datetime

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        now = now or _utcnow()
        return now >= self.expires_at


class User:
    __slots__ = ("_id", "_email", "_password_hash", "_role", "_created_at", "_last_login_at", "_active")

    def __init__(self, user_id: int, email: str, password: str, role: Role) -> None:
        self._id = int(user_id)
        self._email = _normalize_email(email)
        self._password_hash = _hash_password(password)
        self._role = Role(role)
        self._created_at = _utcnow()
        self._last_login_at: Optional[datetime] = None
        self._active = True

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

    @property
    def is_active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def activate(self) -> None:
        self._active = True

    def set_password(self, new_password: str) -> None:
        self._password_hash = _hash_password(new_password)

    def check_password(self, password: str) -> bool:
        return _verify_password(password, self._password_hash)

    def _mark_login(self) -> None:
        self._last_login_at = _utcnow()


class StudentProfile:
    __slots__ = ("_student_user_id", "_full_name", "_progress", "_outcomes", "_created_at", "_updated_at")

    def __init__(self, student_user_id: int, full_name: str) -> None:
        self._student_user_id = int(student_user_id)
        self.set_full_name(full_name)
        self._progress: Dict[str, str] = {}
        self._outcomes: List[str] = []
        self._created_at = _utcnow()
        self._updated_at = self._created_at

    @property
    def student_user_id(self) -> int:
        return self._student_user_id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def set_full_name(self, full_name: str) -> None:
        if not isinstance(full_name, str) or not full_name.strip():
            raise ValidationError("Full name is required.")
        self._full_name = full_name.strip()
        self._updated_at = _utcnow()

    def set_progress(self, key: str, value: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValidationError("Progress key is required.")
        if not isinstance(value, str):
            raise ValidationError("Progress value must be a string.")
        self._progress[key.strip()] = value
        self._updated_at = _utcnow()

    def get_progress(self) -> Dict[str, str]:
        return dict(self._progress)

    def add_outcome(self, outcome: str) -> None:
        if not isinstance(outcome, str) or not outcome.strip():
            raise ValidationError("Outcome is required.")
        self._outcomes.append(outcome.strip())
        self._updated_at = _utcnow()

    def get_outcomes(self) -> List[str]:
        return list(self._outcomes)


class Volunteer:
    __slots__ = ("_id", "_name", "_created_at", "_active")

    def __init__(self, volunteer_id: int, name: str) -> None:
        self._id = int(volunteer_id)
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Volunteer name is required.")
        self._name = name.strip()
        self._created_at = _utcnow()
        self._active = True

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def is_active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def activate(self) -> None:
        self._active = True


class Waitlist:
    def __init__(self) -> None:
        self._queue: List[int] = []
        self._set: Set[int] = set()

    def add(self, student_user_id: int) -> None:
        sid = int(student_user_id)
        if sid in self._set:
            return
        self._queue.append(sid)
        self._set.add(sid)

    def remove(self, student_user_id: int) -> None:
        sid = int(student_user_id)
        if sid not in self._set:
            return
        self._set.remove(sid)
        self._queue = [x for x in self._queue if x != sid]

    def pop_next(self) -> Optional[int]:
        while self._queue:
            sid = self._queue.pop(0)
            if sid in self._set:
                self._set.remove(sid)
                return sid
        return None

    def list_all(self) -> List[int]:
        return [sid for sid in self._queue if sid in self._set]

    def contains(self, student_user_id: int) -> bool:
        return int(student_user_id) in self._set


class AuthService:
    def __init__(self, session_ttl: timedelta = timedelta(hours=8)) -> None:
        self._session_ttl = session_ttl
        self._sessions: Dict[str, Session] = {}

    def create_session(self, user: User) -> Session:
        token = secrets.token_urlsafe(32)
        now = _utcnow()
        session = Session(token=token, user_id=user.id, created_at=now, expires_at=now + self._session_ttl)
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

    def revoke_user_sessions(self, user_id: int) -> None:
        uid = int(user_id)
        to_delete = [t for t, s in self._sessions.items() if s.user_id == uid]
        for t in to_delete:
            self._sessions.pop(t, None)


class StudentManagementSystem:
    def __init__(self) -> None:
        self._auth = AuthService()
        self._users_by_id: Dict[int, User] = {}
        self._users_by_email: Dict[str, int] = {}
        self._profiles_by_student_id: Dict[int, StudentProfile] = {}
        self._volunteers_by_id: Dict[int, Volunteer] = {}
        self._waitlist = Waitlist()
        self._next_user_id = 1
        self._next_volunteer_id = 1

    @property
    def waitlist(self) -> Waitlist:
        return self._waitlist

    def _require_user(self, token: str) -> User:
        session = self._auth.get_session(token)
        if session is None:
            raise AuthError("Invalid or expired session.")
        user = self._users_by_id.get(session.user_id)
        if user is None or not user.is_active:
            raise AuthError("User not found or inactive.")
        return user

    def _require_role(self, user: User, allowed: Set[Role]) -> None:
        if user.role not in allowed:
            raise PermissionError("Insufficient permissions.")

    def register_student(self, email: str, password: str, full_name: str) -> int:
        email_n = _normalize_email(email)
        if email_n in self._users_by_email:
            raise ValidationError("Email already registered.")
        user_id = self._next_user_id
        self._next_user_id += 1
        user = User(user_id=user_id, email=email_n, password=password, role=Role.STUDENT)
        self._users_by_id[user_id] = user
        self._users_by_email[email_n] = user_id
        self._profiles_by_student_id[user_id] = StudentProfile(student_user_id=user_id, full_name=full_name)
        return user_id

    def register_organizer(self, email: str, password: str) -> int:
        email_n = _normalize_email(email)
        if email_n in self._users_by_email:
            raise ValidationError("Email already registered.")
        user_id = self._next_user_id
        self._next_user_id += 1
        user = User(user_id=user_id, email=email_n, password=password, role=Role.ORGANIZER)
        self._users_by_id[user_id] = user
        self._users_by_email[email_n] = user_id
        return user_id

    def register_admin(self, email: str, password: str) -> int:
        email_n = _normalize_email(email)
        if email_n in self._users_by_email:
            raise ValidationError("Email already registered.")
        user_id = self._next_user_id
        self._next_user_id += 1
        user = User(user_id=user_id, email=email_n, password=password, role=Role.ADMIN)
        self._users_by_id[user_id] = user
        self._users_by_email[email_n] = user_id
        return user_id

    def login(self, email: str, password: str) -> str:
        email_n = _normalize_email(email)
        user_id = self._users_by_email.get(email_n)
        if user_id is None:
            raise AuthError("Invalid credentials.")
        user = self._users_by_id.get(user_id)
        if user is None or not user.is_active:
            raise AuthError("Invalid credentials.")
        if not user.check_password(password):
            raise AuthError("Invalid credentials.")
        user._mark_login()
        session = self._auth.create_session(user)
        return session.token

    def logout(self, token: str) -> None:
        self._auth.revoke_session(token)

    def get_my_profile(self, token: str) -> StudentProfile:
        user = self._require_user(token)
        self._require_role(user, {Role.STUDENT})
        profile = self._profiles_by_student_id.get(user.id)
        if profile is None:
            raise ValidationError("Profile not found.")
        return profile

    def update_my_full_name(self, token: str, full_name: str) -> None:
        profile = self.get_my_profile(token)
        profile.set_full_name(full_name)

    def update_my_progress(self, token: str, key: str, value: str) -> None:
        profile = self.get_my_profile(token)
        profile.set_progress(key, value)

    def add_my_outcome(self, token: str, outcome: str) -> None:
        profile = self.get_my_profile(token)
        profile.add_outcome(outcome)

    def get_student_profile(self, token: str, student_user_id: int) -> StudentProfile:
        user = self._require_user(token)
        sid = int(student_user_id)
        if user.role == Role.STUDENT and user.id != sid:
            raise PermissionError("Students can only view their own profile.")
        if user.role in {Role.ORGANIZER, Role.ADMIN} or (user.role == Role.STUDENT and user.id == sid):
            profile = self._profiles_by_student_id.get(sid)
            if profile is None:
                raise ValidationError("Profile not found.")
            return profile
        raise PermissionError("Insufficient permissions.")

    def list_students(self, token: str) -> List[Tuple[int, str]]:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        result: List[Tuple[int, str]] = []
        for uid, u in self._users_by_id.items():
            if u.role == Role.STUDENT:
                profile = self._profiles_by_student_id.get(uid)
                name = profile.full_name if profile else ""
                result.append((uid, name))
        result.sort(key=lambda x: x[0])
        return result

    def admin_dashboard_summary(self, token: str) -> Dict[str, int]:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        students = sum(1 for u in self._users_by_id.values() if u.role == Role.STUDENT)
        organizers = sum(1 for u in self._users_by_id.values() if u.role == Role.ORGANIZER)
        admins = sum(1 for u in self._users_by_id.values() if u.role == Role.ADMIN)
        volunteers = len(self._volunteers_by_id)
        waitlisted = len(self._waitlist.list_all())
        return {
            "students": students,
            "organizers": organizers,
            "admins": admins,
            "volunteers": volunteers,
            "waitlist": waitlisted,
        }

    def add_volunteer(self, token: str, name: str) -> int:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        vid = self._next_volunteer_id
        self._next_volunteer_id += 1
        volunteer = Volunteer(volunteer_id=vid, name=name)
        self._volunteers_by_id[vid] = volunteer
        return vid

    def list_volunteers(self, token: str) -> List[Tuple[int, str, bool]]:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        items = [(v.id, v.name, v.is_active) for v in self._volunteers_by_id.values()]
        items.sort(key=lambda x: x[0])
        return items

    def deactivate_volunteer(self, token: str, volunteer_id: int) -> None:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        vid = int(volunteer_id)
        v = self._volunteers_by_id.get(vid)
        if v is None:
            raise ValidationError("Volunteer not found.")
        v.deactivate()

    def activate_volunteer(self, token: str, volunteer_id: int) -> None:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        vid = int(volunteer_id)
        v = self._volunteers_by_id.get(vid)
        if v is None:
            raise ValidationError("Volunteer not found.")
        v.activate()

    def add_student_to_waitlist(self, token: str, student_user_id: int) -> None:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        sid = int(student_user_id)
        u = self._users_by_id.get(sid)
        if u is None or u.role != Role.STUDENT:
            raise ValidationError("Student not found.")
        self._waitlist.add(sid)

    def remove_student_from_waitlist(self, token: str, student_user_id: int) -> None:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        self._waitlist.remove(int(student_user_id))

    def view_waitlist(self, token: str) -> List[int]:
        user = self._require_user(token)
        self._require_role(user, {Role.ORGANIZER, Role.ADMIN})
        return self._waitlist.list_all()

    def deactivate_user(self, token: str, user_id: int) -> None:
        user = self._require_user(token)
        self._require_role(user, {Role.ADMIN})
        uid = int(user_id)
        target = self._users_by_id.get(uid)
        if target is None:
            raise ValidationError("User not found.")
        target.deactivate()
        self._auth.revoke_user_sessions(uid)

    def activate_user(self, token: str, user_id: int) -> None:
        user = self._require_user(token)
        self._require_role(user, {Role.ADMIN})
        uid = int(user_id)
        target = self._users_by_id.get(uid)
        if target is None:
            raise ValidationError("User not found.")
        target.activate()

    def change_my_password(self, token: str, old_password: str, new_password: str) -> None:
        user = self._require_user(token)
        if not user.check_password(old_password):
            raise AuthError("Invalid credentials.")
        user.set_password(new_password)
        self._auth.revoke_user_sessions(user.id)

    def get_user_role(self, token: str) -> Role:
        user = self._require_user(token)
        return user.role

    def get_user_email(self, token: str) -> str:
        user = self._require_user(token)
        return user.email


__all__ = [
    "Role",
    "AuthError",
    "PermissionError",
    "ValidationError",
    "Session",
    "User",
    "StudentProfile",
    "Volunteer",
    "Waitlist",
    "AuthService",
    "StudentManagementSystem",
]