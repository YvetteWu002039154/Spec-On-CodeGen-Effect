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


class ValidationError(Exception):
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


def _hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 200_000) -> str:
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("Password must be a string of at least 8 characters.")
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
        if now is None:
            now = _utcnow()
        return now >= self.expires_at


class User:
    def __init__(self, user_id: int, email: str, password: str, role: Role) -> None:
        self._id = int(user_id)
        self._email = _normalize_email(email)
        self._password_hash = _hash_password(password)
        self._role = role
        self._created_at = _utcnow()
        self._last_login_at: Optional[datetime] = None
        self._is_active = True

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
        return self._is_active

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True

    def set_password(self, new_password: str) -> None:
        self._password_hash = _hash_password(new_password)

    def check_password(self, password: str) -> bool:
        return _verify_password(password, self._password_hash)

    def _mark_login(self) -> None:
        self._last_login_at = _utcnow()


class StudentProfile:
    def __init__(self, user_id: int, full_name: str) -> None:
        self._user_id = int(user_id)
        self._full_name = self._validate_name(full_name)
        self._created_at = _utcnow()
        self._updated_at = self._created_at
        self._progress: Dict[str, str] = {}
        self._outcomes: List[str] = []
        self._waitlisted = False
        self._volunteer_tags: Set[str] = set()

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str):
            raise ValidationError("Full name must be a string.")
        name = name.strip()
        if not name:
            raise ValidationError("Full name is required.")
        return name

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def waitlisted(self) -> bool:
        return self._waitlisted

    def set_waitlisted(self, value: bool) -> None:
        self._waitlisted = bool(value)
        self._updated_at = _utcnow()

    def set_full_name(self, full_name: str) -> None:
        self._full_name = self._validate_name(full_name)
        self._updated_at = _utcnow()

    def set_progress(self, key: str, value: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValidationError("Progress key must be a non-empty string.")
        if not isinstance(value, str):
            raise ValidationError("Progress value must be a string.")
        self._progress[key.strip()] = value
        self._updated_at = _utcnow()

    def get_progress(self) -> Dict[str, str]:
        return dict(self._progress)

    def add_outcome(self, outcome: str) -> None:
        if not isinstance(outcome, str) or not outcome.strip():
            raise ValidationError("Outcome must be a non-empty string.")
        self._outcomes.append(outcome.strip())
        self._updated_at = _utcnow()

    def get_outcomes(self) -> List[str]:
        return list(self._outcomes)

    def add_volunteer_tag(self, tag: str) -> None:
        if not isinstance(tag, str) or not tag.strip():
            raise ValidationError("Volunteer tag must be a non-empty string.")
        self._volunteer_tags.add(tag.strip().lower())
        self._updated_at = _utcnow()

    def remove_volunteer_tag(self, tag: str) -> None:
        if not isinstance(tag, str) or not tag.strip():
            raise ValidationError("Volunteer tag must be a non-empty string.")
        self._volunteer_tags.discard(tag.strip().lower())
        self._updated_at = _utcnow()

    def get_volunteer_tags(self) -> Set[str]:
        return set(self._volunteer_tags)

    def to_private_dict(self) -> Dict[str, object]:
        return {
            "user_id": self._user_id,
            "full_name": self._full_name,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "progress": dict(self._progress),
            "outcomes": list(self._outcomes),
            "waitlisted": self._waitlisted,
            "volunteer_tags": sorted(self._volunteer_tags),
        }


class AuthService:
    def __init__(self, session_ttl: timedelta = timedelta(hours=8)) -> None:
        self._session_ttl = session_ttl
        self._sessions: Dict[str, Session] = {}

    def create_session(self, user: User) -> Session:
        if not user.is_active:
            raise AuthError("User is inactive.")
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
        to_remove = [t for t, s in self._sessions.items() if s.user_id == user_id]
        for t in to_remove:
            self._sessions.pop(t, None)


class StudentManagementSystem:
    def __init__(self) -> None:
        self._users_by_id: Dict[int, User] = {}
        self._user_ids_by_email: Dict[str, int] = {}
        self._profiles_by_user_id: Dict[int, StudentProfile] = {}
        self._next_user_id = 1
        self._auth = AuthService()

    @property
    def auth(self) -> AuthService:
        return self._auth

    def _require_user(self, user_id: int) -> User:
        user = self._users_by_id.get(int(user_id))
        if user is None:
            raise ValidationError("User not found.")
        return user

    def _require_profile(self, user_id: int) -> StudentProfile:
        profile = self._profiles_by_user_id.get(int(user_id))
        if profile is None:
            raise ValidationError("Student profile not found.")
        return profile

    def _require_session_user(self, token: str) -> User:
        session = self._auth.get_session(token)
        if session is None:
            raise AuthError("Invalid or expired session.")
        user = self._require_user(session.user_id)
        if not user.is_active:
            raise AuthError("User is inactive.")
        return user

    def _ensure_role(self, user: User, allowed: Set[Role]) -> None:
        if user.role not in allowed:
            raise PermissionError("Permission denied.")

    def create_student_account(self, email: str, password: str, full_name: str) -> int:
        return self._create_user(email=email, password=password, role=Role.STUDENT, full_name=full_name)

    def create_organizer_account(self, email: str, password: str) -> int:
        return self._create_user(email=email, password=password, role=Role.ORGANIZER, full_name=None)

    def create_admin_account(self, email: str, password: str) -> int:
        return self._create_user(email=email, password=password, role=Role.ADMIN, full_name=None)

    def _create_user(self, email: str, password: str, role: Role, full_name: Optional[str]) -> int:
        email_n = _normalize_email(email)
        if email_n in self._user_ids_by_email:
            raise ValidationError("Email already exists.")
        user_id = self._next_user_id
        self._next_user_id += 1
        user = User(user_id=user_id, email=email_n, password=password, role=role)
        self._users_by_id[user_id] = user
        self._user_ids_by_email[email_n] = user_id
        if role == Role.STUDENT:
            if full_name is None:
                raise ValidationError("Student full name is required.")
            self._profiles_by_user_id[user_id] = StudentProfile(user_id=user_id, full_name=full_name)
        return user_id

    def login(self, email: str, password: str) -> str:
        email_n = _normalize_email(email)
        user_id = self._user_ids_by_email.get(email_n)
        if user_id is None:
            raise AuthError("Invalid credentials.")
        user = self._require_user(user_id)
        if not user.is_active:
            raise AuthError("User is inactive.")
        if not user.check_password(password):
            raise AuthError("Invalid credentials.")
        user._mark_login()
        session = self._auth.create_session(user)
        return session.token

    def logout(self, token: str) -> None:
        self._auth.revoke_session(token)

    def get_my_profile(self, token: str) -> Dict[str, object]:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.STUDENT})
        profile = self._require_profile(user.id)
        return profile.to_private_dict()

    def update_my_full_name(self, token: str, full_name: str) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.STUDENT})
        profile = self._require_profile(user.id)
        profile.set_full_name(full_name)

    def update_my_progress(self, token: str, key: str, value: str) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.STUDENT})
        profile = self._require_profile(user.id)
        profile.set_progress(key, value)

    def add_my_outcome(self, token: str, outcome: str) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.STUDENT})
        profile = self._require_profile(user.id)
        profile.add_outcome(outcome)

    def admin_list_students(self, token: str) -> List[Dict[str, object]]:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ORGANIZER, Role.ADMIN})
        students: List[Dict[str, object]] = []
        for uid, profile in self._profiles_by_user_id.items():
            u = self._users_by_id.get(uid)
            if u is None or u.role != Role.STUDENT:
                continue
            students.append(
                {
                    "user_id": uid,
                    "email": u.email,
                    "is_active": u.is_active,
                    "last_login_at": u.last_login_at,
                    **profile.to_private_dict(),
                }
            )
        students.sort(key=lambda d: (d.get("full_name") or "", d["user_id"]))
        return students

    def admin_get_student_profile(self, token: str, student_user_id: int) -> Dict[str, object]:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ORGANIZER, Role.ADMIN})
        student = self._require_user(student_user_id)
        if student.role != Role.STUDENT:
            raise ValidationError("Target user is not a student.")
        profile = self._require_profile(student_user_id)
        data = profile.to_private_dict()
        data.update(
            {
                "email": student.email,
                "is_active": student.is_active,
                "last_login_at": student.last_login_at,
            }
        )
        return data

    def admin_set_waitlist_status(self, token: str, student_user_id: int, waitlisted: bool) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ORGANIZER, Role.ADMIN})
        student = self._require_user(student_user_id)
        if student.role != Role.STUDENT:
            raise ValidationError("Target user is not a student.")
        profile = self._require_profile(student_user_id)
        profile.set_waitlisted(waitlisted)

    def admin_add_volunteer_tag(self, token: str, student_user_id: int, tag: str) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ORGANIZER, Role.ADMIN})
        student = self._require_user(student_user_id)
        if student.role != Role.STUDENT:
            raise ValidationError("Target user is not a student.")
        profile = self._require_profile(student_user_id)
        profile.add_volunteer_tag(tag)

    def admin_remove_volunteer_tag(self, token: str, student_user_id: int, tag: str) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ORGANIZER, Role.ADMIN})
        student = self._require_user(student_user_id)
        if student.role != Role.STUDENT:
            raise ValidationError("Target user is not a student.")
        profile = self._require_profile(student_user_id)
        profile.remove_volunteer_tag(tag)

    def admin_deactivate_user(self, token: str, user_id: int) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ADMIN})
        target = self._require_user(user_id)
        target.deactivate()
        self._auth.revoke_user_sessions(target.id)

    def admin_activate_user(self, token: str, user_id: int) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ADMIN})
        target = self._require_user(user_id)
        target.activate()

    def admin_reset_password(self, token: str, user_id: int, new_password: str) -> None:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ADMIN})
        target = self._require_user(user_id)
        target.set_password(new_password)
        self._auth.revoke_user_sessions(target.id)

    def admin_dashboard_summary(self, token: str) -> Dict[str, int]:
        user = self._require_session_user(token)
        self._ensure_role(user, {Role.ORGANIZER, Role.ADMIN})
        total_students = 0
        waitlisted = 0
        active_students = 0
        for uid, profile in self._profiles_by_user_id.items():
            u = self._users_by_id.get(uid)
            if u is None or u.role != Role.STUDENT:
                continue
            total_students += 1
            if profile.waitlisted:
                waitlisted += 1
            if u.is_active:
                active_students += 1
        return {
            "total_students": total_students,
            "active_students": active_students,
            "waitlisted_students": waitlisted,
        }