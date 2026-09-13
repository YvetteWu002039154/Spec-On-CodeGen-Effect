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
    ADMIN = "admin"
    ORGANIZER = "organizer"


class AuthError(Exception):
    pass


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


def _now_ts() -> int:
    return int(time.time())


def _normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValidationError("Email must be a string.")
    email = email.strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise ValidationError("Invalid email.")
    return email


def _hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    if not isinstance(password, str):
        raise ValidationError("Password must be a string.")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt, dk


def _verify_password(password: str, salt: bytes, digest: bytes) -> bool:
    _, dk = _hash_password(password, salt=salt)
    return hmac.compare_digest(dk, digest)


@dataclass(frozen=True)
class Session:
    token: str
    user_id: int
    created_at: int
    expires_at: int


@dataclass
class StudentProfile:
    student_id: int
    full_name: str
    cohort: Optional[str] = None
    progress: Optional[str] = None
    outcomes: Optional[str] = None

    def update(
        self,
        *,
        full_name: Optional[str] = None,
        cohort: Optional[str] = None,
        progress: Optional[str] = None,
        outcomes: Optional[str] = None,
    ) -> None:
        if full_name is not None:
            full_name = full_name.strip()
            if not full_name:
                raise ValidationError("Full name cannot be empty.")
            self.full_name = full_name
        if cohort is not None:
            cohort = cohort.strip()
            self.cohort = cohort if cohort else None
        if progress is not None:
            progress = progress.strip()
            self.progress = progress if progress else None
        if outcomes is not None:
            outcomes = outcomes.strip()
            self.outcomes = outcomes if outcomes else None


@dataclass
class Volunteer:
    volunteer_id: int
    full_name: str
    email: str
    active: bool = True

    def set_active(self, active: bool) -> None:
        self.active = bool(active)


@dataclass
class WaitlistEntry:
    entry_id: int
    full_name: str
    email: str
    created_at: int


class User:
    __slots__ = ("_id", "_email", "_role", "_salt", "_password_digest", "_created_at", "_active")

    def __init__(self, user_id: int, email: str, role: Role, password: str) -> None:
        self._id = int(user_id)
        self._email = _normalize_email(email)
        if not isinstance(role, Role):
            raise ValidationError("Invalid role.")
        self._role = role
        self._salt, self._password_digest = _hash_password(password)
        self._created_at = _now_ts()
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
    def created_at(self) -> int:
        return self._created_at

    @property
    def active(self) -> bool:
        return self._active

    def deactivate(self) -> None:
        self._active = False

    def activate(self) -> None:
        self._active = True

    def verify_password(self, password: str) -> bool:
        return _verify_password(password, self._salt, self._password_digest)

    def set_password(self, new_password: str) -> None:
        self._salt, self._password_digest = _hash_password(new_password)


class Student(User):
    def __init__(self, user_id: int, email: str, password: str) -> None:
        super().__init__(user_id=user_id, email=email, role=Role.STUDENT, password=password)


class Admin(User):
    def __init__(self, user_id: int, email: str, password: str) -> None:
        super().__init__(user_id=user_id, email=email, role=Role.ADMIN, password=password)


class Organizer(User):
    def __init__(self, user_id: int, email: str, password: str) -> None:
        super().__init__(user_id=user_id, email=email, role=Role.ORGANIZER, password=password)


class AuthService:
    def __init__(self, session_ttl_seconds: int = 60 * 60 * 8) -> None:
        if session_ttl_seconds <= 0:
            raise ValidationError("Session TTL must be positive.")
        self._session_ttl_seconds = session_ttl_seconds
        self._sessions_by_token: Dict[str, Session] = {}
        self._tokens_by_user_id: Dict[int, Set[str]] = {}

    def create_session(self, user: User) -> Session:
        if not user.active:
            raise AuthError("User is inactive.")
        token = secrets.token_urlsafe(32)
        created = _now_ts()
        session = Session(
            token=token,
            user_id=user.id,
            created_at=created,
            expires_at=created + self._session_ttl_seconds,
        )
        self._sessions_by_token[token] = session
        self._tokens_by_user_id.setdefault(user.id, set()).add(token)
        return session

    def revoke_session(self, token: str) -> None:
        session = self._sessions_by_token.pop(token, None)
        if session is None:
            return
        tokens = self._tokens_by_user_id.get(session.user_id)
        if tokens is not None:
            tokens.discard(token)
            if not tokens:
                self._tokens_by_user_id.pop(session.user_id, None)

    def revoke_all_sessions_for_user(self, user_id: int) -> None:
        tokens = list(self._tokens_by_user_id.get(user_id, set()))
        for t in tokens:
            self.revoke_session(t)

    def get_session(self, token: str) -> Session:
        session = self._sessions_by_token.get(token)
        if session is None:
            raise AuthError("Invalid session.")
        if _now_ts() >= session.expires_at:
            self.revoke_session(token)
            raise AuthError("Session expired.")
        return session


class StudentManagementSystem:
    def __init__(self) -> None:
        self._next_user_id = 1
        self._next_waitlist_id = 1
        self._next_volunteer_id = 1

        self._users_by_id: Dict[int, User] = {}
        self._users_by_email: Dict[str, int] = {}

        self._profiles_by_student_id: Dict[int, StudentProfile] = {}

        self._waitlist: Dict[int, WaitlistEntry] = {}
        self._volunteers: Dict[int, Volunteer] = {}

        self._auth = AuthService()

    @property
    def auth(self) -> AuthService:
        return self._auth

    def _allocate_user_id(self) -> int:
        uid = self._next_user_id
        self._next_user_id += 1
        return uid

    def _require_user(self, user_id: int) -> User:
        user = self._users_by_id.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def _require_student(self, student_id: int) -> Student:
        user = self._require_user(student_id)
        if user.role != Role.STUDENT:
            raise ValidationError("User is not a student.")
        return user  # type: ignore[return-value]

    def _require_admin_or_organizer(self, actor: User) -> None:
        if actor.role not in (Role.ADMIN, Role.ORGANIZER):
            raise AuthError("Insufficient permissions.")

    def _require_admin(self, actor: User) -> None:
        if actor.role != Role.ADMIN:
            raise AuthError("Admin permissions required.")

    def register_student(self, email: str, password: str, full_name: str) -> Student:
        email_n = _normalize_email(email)
        if email_n in self._users_by_email:
            raise ValidationError("Email already registered.")
        full_name = full_name.strip()
        if not full_name:
            raise ValidationError("Full name cannot be empty.")

        user_id = self._allocate_user_id()
        student = Student(user_id=user_id, email=email_n, password=password)
        self._users_by_id[user_id] = student
        self._users_by_email[email_n] = user_id
        self._profiles_by_student_id[user_id] = StudentProfile(student_id=user_id, full_name=full_name)
        return student

    def register_admin(self, email: str, password: str) -> Admin:
        email_n = _normalize_email(email)
        if email_n in self._users_by_email:
            raise ValidationError("Email already registered.")
        user_id = self._allocate_user_id()
        admin = Admin(user_id=user_id, email=email_n, password=password)
        self._users_by_id[user_id] = admin
        self._users_by_email[email_n] = user_id
        return admin

    def register_organizer(self, email: str, password: str) -> Organizer:
        email_n = _normalize_email(email)
        if email_n in self._users_by_email:
            raise ValidationError("Email already registered.")
        user_id = self._allocate_user_id()
        organizer = Organizer(user_id=user_id, email=email_n, password=password)
        self._users_by_id[user_id] = organizer
        self._users_by_email[email_n] = user_id
        return organizer

    def login(self, email: str, password: str) -> Session:
        email_n = _normalize_email(email)
        user_id = self._users_by_email.get(email_n)
        if user_id is None:
            raise AuthError("Invalid credentials.")
        user = self._users_by_id[user_id]
        if not user.active:
            raise AuthError("User is inactive.")
        if not user.verify_password(password):
            raise AuthError("Invalid credentials.")
        return self._auth.create_session(user)

    def logout(self, token: str) -> None:
        self._auth.revoke_session(token)

    def get_user_by_session(self, token: str) -> User:
        session = self._auth.get_session(token)
        return self._require_user(session.user_id)

    def get_own_student_profile(self, token: str) -> StudentProfile:
        user = self.get_user_by_session(token)
        if user.role != Role.STUDENT:
            raise AuthError("Only students have student profiles.")
        profile = self._profiles_by_student_id.get(user.id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        return profile

    def update_own_student_profile(
        self,
        token: str,
        *,
        full_name: Optional[str] = None,
        cohort: Optional[str] = None,
        progress: Optional[str] = None,
        outcomes: Optional[str] = None,
    ) -> StudentProfile:
        profile = self.get_own_student_profile(token)
        profile.update(full_name=full_name, cohort=cohort, progress=progress, outcomes=outcomes)
        return profile

    def get_student_profile(self, token: str, student_id: int) -> StudentProfile:
        actor = self.get_user_by_session(token)
        if actor.role == Role.STUDENT and actor.id != student_id:
            raise AuthError("Insufficient permissions.")
        if actor.role in (Role.ADMIN, Role.ORGANIZER):
            pass
        elif actor.role == Role.STUDENT:
            pass
        else:
            raise AuthError("Insufficient permissions.")

        self._require_student(student_id)
        profile = self._profiles_by_student_id.get(student_id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        return profile

    def admin_list_students(self, token: str) -> List[StudentProfile]:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        return [self._profiles_by_student_id[sid] for sid, u in self._users_by_id.items() if u.role == Role.STUDENT]

    def admin_update_student_progress(
        self,
        token: str,
        student_id: int,
        *,
        progress: Optional[str] = None,
        outcomes: Optional[str] = None,
        cohort: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> StudentProfile:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        profile = self.get_student_profile(token, student_id)
        profile.update(full_name=full_name, cohort=cohort, progress=progress, outcomes=outcomes)
        return profile

    def admin_deactivate_user(self, token: str, user_id: int) -> None:
        actor = self.get_user_by_session(token)
        self._require_admin(actor)
        user = self._require_user(user_id)
        user.deactivate()
        self._auth.revoke_all_sessions_for_user(user_id)

    def admin_activate_user(self, token: str, user_id: int) -> None:
        actor = self.get_user_by_session(token)
        self._require_admin(actor)
        user = self._require_user(user_id)
        user.activate()

    def add_waitlist_entry(self, full_name: str, email: str) -> WaitlistEntry:
        full_name = full_name.strip()
        if not full_name:
            raise ValidationError("Full name cannot be empty.")
        email_n = _normalize_email(email)
        entry_id = self._next_waitlist_id
        self._next_waitlist_id += 1
        entry = WaitlistEntry(entry_id=entry_id, full_name=full_name, email=email_n, created_at=_now_ts())
        self._waitlist[entry_id] = entry
        return entry

    def admin_list_waitlist(self, token: str) -> List[WaitlistEntry]:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        return sorted(self._waitlist.values(), key=lambda e: e.created_at)

    def admin_remove_waitlist_entry(self, token: str, entry_id: int) -> None:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        if entry_id not in self._waitlist:
            raise NotFoundError("Waitlist entry not found.")
        del self._waitlist[entry_id]

    def admin_add_volunteer(self, token: str, full_name: str, email: str) -> Volunteer:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        full_name = full_name.strip()
        if not full_name:
            raise ValidationError("Full name cannot be empty.")
        email_n = _normalize_email(email)
        volunteer_id = self._next_volunteer_id
        self._next_volunteer_id += 1
        volunteer = Volunteer(volunteer_id=volunteer_id, full_name=full_name, email=email_n, active=True)
        self._volunteers[volunteer_id] = volunteer
        return volunteer

    def admin_list_volunteers(self, token: str) -> List[Volunteer]:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        return list(self._volunteers.values())

    def admin_set_volunteer_active(self, token: str, volunteer_id: int, active: bool) -> Volunteer:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise NotFoundError("Volunteer not found.")
        volunteer.set_active(active)
        return volunteer

    def admin_dashboard_summary(self, token: str) -> Dict[str, int]:
        actor = self.get_user_by_session(token)
        self._require_admin_or_organizer(actor)
        students = sum(1 for u in self._users_by_id.values() if u.role == Role.STUDENT)
        admins = sum(1 for u in self._users_by_id.values() if u.role == Role.ADMIN)
        organizers = sum(1 for u in self._users_by_id.values() if u.role == Role.ORGANIZER)
        waitlist = len(self._waitlist)
        volunteers = len(self._volunteers)
        return {
            "students": students,
            "admins": admins,
            "organizers": organizers,
            "waitlist_entries": waitlist,
            "volunteers": volunteers,
        }