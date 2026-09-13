from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
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


def _require_non_empty_str(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string.")
    value = value.strip()
    if not value:
        raise ValidationError(f"{field} is required.")
    return value


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


def _constant_time_equals(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)


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
    __slots__ = (
        "_id",
        "_email",
        "_name",
        "_role",
        "_password_salt",
        "_password_hash",
        "_created_at",
        "_last_login_at",
        "_is_active",
    )

    def __init__(self, user_id: int, email: str, name: str, role: Role, password: str) -> None:
        self._id = int(user_id)
        self._email = _normalize_email(email)
        self._name = _require_non_empty_str(name, "Name")
        if not isinstance(role, Role):
            raise ValidationError("Invalid role.")
        self._role = role
        password = _require_non_empty_str(password, "Password")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        self._password_salt = os.urandom(16)
        self._password_hash = _hash_password(password, self._password_salt)
        self._created_at = _utcnow()
        self._last_login_at = None  # type: Optional[datetime]
        self._is_active = True

    @property
    def id(self) -> int:
        return self._id

    @property
    def email(self) -> str:
        return self._email

    @property
    def name(self) -> str:
        return self._name

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
        return self._is_active

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True

    def set_name(self, name: str) -> None:
        self._name = _require_non_empty_str(name, "Name")

    def set_password(self, new_password: str) -> None:
        new_password = _require_non_empty_str(new_password, "Password")
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        self._password_salt = os.urandom(16)
        self._password_hash = _hash_password(new_password, self._password_salt)

    def verify_password(self, password: str) -> bool:
        if not isinstance(password, str):
            return False
        candidate = _hash_password(password, self._password_salt)
        return _constant_time_equals(candidate, self._password_hash)

    def _mark_login(self) -> None:
        self._last_login_at = _utcnow()


class StudentProfile:
    __slots__ = (
        "_student_user_id",
        "_bio",
        "_progress",
        "_outcomes",
        "_created_at",
        "_updated_at",
    )

    def __init__(self, student_user_id: int, bio: str = "") -> None:
        self._student_user_id = int(student_user_id)
        self._bio = bio if isinstance(bio, str) else ""
        self._progress = {}  # type: Dict[str, str]
        self._outcomes = []  # type: List[str]
        self._created_at = _utcnow()
        self._updated_at = self._created_at

    @property
    def student_user_id(self) -> int:
        return self._student_user_id

    @property
    def bio(self) -> str:
        return self._bio

    @property
    def progress(self) -> Dict[str, str]:
        return dict(self._progress)

    @property
    def outcomes(self) -> List[str]:
        return list(self._outcomes)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def set_bio(self, bio: str) -> None:
        if not isinstance(bio, str):
            raise ValidationError("Bio must be a string.")
        self._bio = bio
        self._updated_at = _utcnow()

    def set_progress(self, key: str, value: str) -> None:
        key = _require_non_empty_str(key, "Progress key")
        value = _require_non_empty_str(value, "Progress value")
        self._progress[key] = value
        self._updated_at = _utcnow()

    def remove_progress(self, key: str) -> None:
        key = _require_non_empty_str(key, "Progress key")
        if key in self._progress:
            del self._progress[key]
            self._updated_at = _utcnow()

    def add_outcome(self, outcome: str) -> None:
        outcome = _require_non_empty_str(outcome, "Outcome")
        self._outcomes.append(outcome)
        self._updated_at = _utcnow()

    def clear_outcomes(self) -> None:
        self._outcomes.clear()
        self._updated_at = _utcnow()


class Volunteer:
    __slots__ = ("_id", "_name", "_email", "_created_at", "_is_active")

    def __init__(self, volunteer_id: int, name: str, email: str) -> None:
        self._id = int(volunteer_id)
        self._name = _require_non_empty_str(name, "Volunteer name")
        self._email = _normalize_email(email)
        self._created_at = _utcnow()
        self._is_active = True

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
    def is_active(self) -> bool:
        return self._is_active

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True

    def set_name(self, name: str) -> None:
        self._name = _require_non_empty_str(name, "Volunteer name")


class Waitlist:
    def __init__(self) -> None:
        self._student_user_ids: List[int] = []
        self._set: Set[int] = set()

    def add(self, student_user_id: int) -> None:
        student_user_id = int(student_user_id)
        if student_user_id in self._set:
            return
        self._student_user_ids.append(student_user_id)
        self._set.add(student_user_id)

    def remove(self, student_user_id: int) -> None:
        student_user_id = int(student_user_id)
        if student_user_id not in self._set:
            return
        self._set.remove(student_user_id)
        self._student_user_ids = [sid for sid in self._student_user_ids if sid != student_user_id]

    def list(self) -> List[int]:
        return list(self._student_user_ids)

    def contains(self, student_user_id: int) -> bool:
        return int(student_user_id) in self._set

    def __len__(self) -> int:
        return len(self._student_user_ids)


class AuthService:
    def __init__(self, session_ttl: timedelta = timedelta(hours=8)) -> None:
        if not isinstance(session_ttl, timedelta) or session_ttl.total_seconds() <= 0:
            raise ValidationError("Invalid session TTL.")
        self._session_ttl = session_ttl
        self._sessions_by_token: Dict[str, Session] = {}
        self._tokens_by_user: Dict[int, Set[str]] = {}
        self._lock = threading.RLock()

    def create_session(self, user: User) -> Session:
        if not user.is_active:
            raise AuthError("User is inactive.")
        now = _utcnow()
        token = secrets.token_urlsafe(32)
        session = Session(
            token=token,
            user_id=user.id,
            created_at=now,
            expires_at=now + self._session_ttl,
        )
        with self._lock:
            self._sessions_by_token[token] = session
            self._tokens_by_user.setdefault(user.id, set()).add(token)
        return session

    def get_session(self, token: str) -> Session:
        if not isinstance(token, str) or not token:
            raise AuthError("Invalid token.")
        with self._lock:
            session = self._sessions_by_token.get(token)
        if session is None:
            raise AuthError("Invalid session.")
        if session.is_expired():
            self.revoke_session(token)
            raise AuthError("Session expired.")
        return session

    def revoke_session(self, token: str) -> None:
        if not isinstance(token, str) or not token:
            return
        with self._lock:
            session = self._sessions_by_token.pop(token, None)
            if session is None:
                return
            tokens = self._tokens_by_user.get(session.user_id)
            if tokens is not None:
                tokens.discard(token)
                if not tokens:
                    self._tokens_by_user.pop(session.user_id, None)

    def revoke_all_for_user(self, user_id: int) -> None:
        user_id = int(user_id)
        with self._lock:
            tokens = list(self._tokens_by_user.get(user_id, set()))
        for t in tokens:
            self.revoke_session(t)


class StudentManagementSystem:
    def __init__(self) -> None:
        self._users_by_id: Dict[int, User] = {}
        self._users_by_email: Dict[str, int] = {}
        self._profiles_by_student_id: Dict[int, StudentProfile] = {}
        self._volunteers_by_id: Dict[int, Volunteer] = {}
        self._volunteers_by_email: Dict[str, int] = {}
        self._waitlist = Waitlist()
        self._auth = AuthService()
        self._lock = threading.RLock()
        self._next_user_id = 1
        self._next_volunteer_id = 1

    @property
    def auth(self) -> AuthService:
        return self._auth

    def _create_user(self, email: str, name: str, role: Role, password: str) -> User:
        email_n = _normalize_email(email)
        with self._lock:
            if email_n in self._users_by_email:
                raise ValidationError("Email already in use.")
            user_id = self._next_user_id
            self._next_user_id += 1
            user = User(user_id=user_id, email=email_n, name=name, role=role, password=password)
            self._users_by_id[user_id] = user
            self._users_by_email[email_n] = user_id
            return user

    def register_student(self, email: str, name: str, password: str, bio: str = "") -> User:
        user = self._create_user(email=email, name=name, role=Role.STUDENT, password=password)
        with self._lock:
            self._profiles_by_student_id[user.id] = StudentProfile(student_user_id=user.id, bio=bio)
        return user

    def register_admin(self, email: str, name: str, password: str) -> User:
        return self._create_user(email=email, name=name, role=Role.ADMIN, password=password)

    def register_organizer(self, email: str, name: str, password: str) -> User:
        return self._create_user(email=email, name=name, role=Role.ORGANIZER, password=password)

    def login(self, email: str, password: str) -> Session:
        email_n = _normalize_email(email)
        with self._lock:
            user_id = self._users_by_email.get(email_n)
            user = self._users_by_id.get(user_id) if user_id is not None else None
        if user is None or not user.is_active:
            raise AuthError("Invalid credentials.")
        if not user.verify_password(password):
            raise AuthError("Invalid credentials.")
        user._mark_login()
        return self._auth.create_session(user)

    def logout(self, token: str) -> None:
        self._auth.revoke_session(token)

    def _get_user_by_id(self, user_id: int) -> User:
        user_id = int(user_id)
        with self._lock:
            user = self._users_by_id.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def _get_user_from_token(self, token: str) -> User:
        session = self._auth.get_session(token)
        return self._get_user_by_id(session.user_id)

    def _is_admin_or_organizer(self, user: User) -> bool:
        return user.role in (Role.ADMIN, Role.ORGANIZER)

    def get_my_profile(self, token: str) -> StudentProfile:
        user = self._get_user_from_token(token)
        if user.role != Role.STUDENT:
            raise PermissionError("Only students have student profiles.")
        with self._lock:
            profile = self._profiles_by_student_id.get(user.id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        return profile

    def get_student_profile(self, token: str, student_user_id: int) -> StudentProfile:
        requester = self._get_user_from_token(token)
        student_user_id = int(student_user_id)
        if requester.role == Role.STUDENT and requester.id != student_user_id:
            raise PermissionError("Student profiles are private.")
        if requester.role != Role.STUDENT and not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        with self._lock:
            profile = self._profiles_by_student_id.get(student_user_id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        return profile

    def update_my_bio(self, token: str, bio: str) -> None:
        profile = self.get_my_profile(token)
        profile.set_bio(bio)

    def update_my_progress(self, token: str, key: str, value: str) -> None:
        profile = self.get_my_profile(token)
        profile.set_progress(key, value)

    def add_my_outcome(self, token: str, outcome: str) -> None:
        profile = self.get_my_profile(token)
        profile.add_outcome(outcome)

    def admin_set_student_progress(self, token: str, student_user_id: int, key: str, value: str) -> None:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        profile = self.get_student_profile(token, student_user_id)
        profile.set_progress(key, value)

    def admin_add_student_outcome(self, token: str, student_user_id: int, outcome: str) -> None:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        profile = self.get_student_profile(token, student_user_id)
        profile.add_outcome(outcome)

    def list_students(self, token: str) -> List[Tuple[User, StudentProfile]]:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        with self._lock:
            students = [u for u in self._users_by_id.values() if u.role == Role.STUDENT]
            result: List[Tuple[User, StudentProfile]] = []
            for s in students:
                p = self._profiles_by_student_id.get(s.id)
                if p is not None:
                    result.append((s, p))
            result.sort(key=lambda t: t[0].id)
            return result

    def create_volunteer(self, token: str, name: str, email: str) -> Volunteer:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        email_n = _normalize_email(email)
        with self._lock:
            if email_n in self._volunteers_by_email:
                raise ValidationError("Volunteer email already in use.")
            vid = self._next_volunteer_id
            self._next_volunteer_id += 1
            v = Volunteer(volunteer_id=vid, name=name, email=email_n)
            self._volunteers_by_id[vid] = v
            self._volunteers_by_email[email_n] = vid
            return v

    def list_volunteers(self, token: str) -> List[Volunteer]:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        with self._lock:
            volunteers = list(self._volunteers_by_id.values())
        volunteers.sort(key=lambda v: v.id)
        return volunteers

    def deactivate_volunteer(self, token: str, volunteer_id: int) -> None:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        volunteer_id = int(volunteer_id)
        with self._lock:
            v = self._volunteers_by_id.get(volunteer_id)
        if v is None:
            raise NotFoundError("Volunteer not found.")
        v.deactivate()

    def add_student_to_waitlist(self, token: str, student_user_id: int) -> None:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        student_user_id = int(student_user_id)
        student = self._get_user_by_id(student_user_id)
        if student.role != Role.STUDENT:
            raise ValidationError("Only students can be waitlisted.")
        with self._lock:
            self._waitlist.add(student_user_id)

    def remove_student_from_waitlist(self, token: str, student_user_id: int) -> None:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        with self._lock:
            self._waitlist.remove(int(student_user_id))

    def list_waitlist(self, token: str) -> List[int]:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        with self._lock:
            return self._waitlist.list()

    def admin_dashboard(self, token: str) -> Dict[str, object]:
        requester = self._get_user_from_token(token)
        if not self._is_admin_or_organizer(requester):
            raise PermissionError("Not authorized.")
        with self._lock:
            students = [u for u in self._users_by_id.values() if u.role == Role.STUDENT]
            admins = [u for u in self._users_by_id.values() if u.role == Role.ADMIN]
            organizers = [u for u in self._users_by_id.values() if u.role == Role.ORGANIZER]
            volunteers = list(self._volunteers_by_id.values())
            waitlist_ids = self._waitlist.list()

        return {
            "generated_at": _utcnow(),
            "counts": {
                "students": len(students),
                "admins": len(admins),
                "organizers": len(organizers),
                "volunteers": len(volunteers),
                "waitlist": len(waitlist_ids),
            },
            "waitlist_student_ids": waitlist_ids,
        }