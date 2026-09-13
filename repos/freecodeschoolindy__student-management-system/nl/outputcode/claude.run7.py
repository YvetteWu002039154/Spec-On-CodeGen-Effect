from datetime import datetime, date
from typing import Optional, List, Dict, Any
import hashlib
import secrets
import re


class ValidationError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class PermissionError(Exception):
    pass


class NotFoundError(Exception):
    pass


class PasswordHasher:
    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{hashed}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt, hashed = stored_hash.split(":")
            return hashlib.sha256((password + salt).encode()).hexdigest() == hashed
        except ValueError:
            return False


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str = "student",
    ):
        self._user_id = user_id
        self._username = self._validate_username(username)
        self._email = self._validate_email(email)
        self._password_hash = PasswordHasher.hash_password(password)
        self._first_name = first_name
        self._last_name = last_name
        self._role = role
        self._created_at = datetime.now()
        self._last_login: Optional[datetime] = None
        self._is_active = True

    def _validate_username(self, username: str) -> str:
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        return username

    def _validate_email(self, email: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, email):
            raise ValidationError(f"Invalid email address: {email}")
        return email

    def verify_password(self, password: str) -> bool:
        return PasswordHasher.verify_password(password, self._password_hash)

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not self.verify_password(old_password):
            raise AuthenticationError("Current password is incorrect.")
        if len(new_password) < 8:
            raise ValidationError("New password must be at least 8 characters long.")
        self._password_hash = PasswordHasher.hash_password(new_password)
        return True

    def record_login(self):
        self._last_login = datetime.now()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def email(self) -> str:
        return self._email

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def full_name(self) -> str:
        return f"{self._first_name} {self._last_name}"

    @property
    def role(self) -> str:
        return self._role

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def last_login(self) -> Optional[datetime]:
        return self._last_login

    def deactivate(self):
        self._is_active = False

    def activate(self):
        self._is_active = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "email": self._email,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "role": self._role,
            "is_active": self._is_active,
            "created_at": self._created_at.isoformat(),
            "last_login": self._last_login.isoformat() if self._last_login else None,
        }

    def __repr__(self) -> str:
        return f"<User(id={self._user_id}, username={self._username}, role={self._role})>"


class CourseProgress:
    def __init__(self, course_name: str):
        self._course_name = course_name
        self._completed_modules: List[str] = []
        self._total_modules: int = 0
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._grade: Optional[float] = None
        self._notes: str = ""

    def start_course(self, total_modules: int):
        self._total_modules = total_modules
        self._started_at = datetime.now()

    def complete_module(self, module_name: str):
        if module_name not in self._completed_modules:
            self._completed_modules.append(module_name)
        if len(self._completed_modules) == self._total_modules:
            self._completed_at = datetime.now()

    def set_grade(self, grade: float):
        if not 0.0 <= grade <= 100.0:
            raise ValidationError("Grade must be between 0 and 100.")
        self._grade = grade

    def add_note(self, note: str):
        self._notes = note

    @property
    def course_name(self) -> str:
        return self._course_name

    @property
    def progress_percentage(self) -> float:
        if self._total_modules == 0:
            return 0.0
        return (len(self._completed_modules) / self._total_modules) * 100

    @property
    def is_completed(self) -> bool:
        return self._completed_at is not None

    @property
    def grade(self) -> Optional[float]:
        return self._grade

    @property
    def completed_modules(self) -> List[str]:
        return list(self._completed_modules)

    @property
    def total_modules(self) -> int:
        return self._total_modules

    @property
    def started_at(self) -> Optional[datetime]:
        return self._started_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "course_name": self._course_name,
            "completed_modules": self._completed_modules,
            "total_modules": self._total_modules,
            "progress_percentage": self.progress_percentage,
            "is_completed": self.is_completed,
            "grade": self._grade,
            "notes": self._notes,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }


class StudentProfile:
    def __init__(
        self,
        student_id: int,
        bio: str = "",
        phone: str = "",
        address: str = "",
        date_of_birth: Optional[date] = None,
        github_username: str = "",
        linkedin_url: str = "",
        portfolio_url: str = "",
    ):
        self._student_id = student_id
        self._bio = bio
        self._phone = phone
        self._address = address
        self._date_of_birth = date_of_birth
        self._github_username = github_username
        self._linkedin_url = linkedin_url
        self._portfolio_url = portfolio_url
        self._skills: List[str] = []
        self._course_progress: Dict[str, CourseProgress] = {}
        self._outcomes: List[Dict[str, Any]] = []
        self._attendance_records: List[Dict[str, Any]] = []
        self._updated_at = datetime.now()

    def update_profile(self, **kwargs):
        allowed_fields = {
            "bio", "phone", "address", "date_of_birth",
            "github_username", "linkedin_url", "portfolio_url"
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(self, f"_{key}", value)
        self._updated_at = datetime.now()

    def add_skill(self, skill: str):
        if skill not in self._skills:
            self._skills.append(skill)
            self._updated_at = datetime.now()

    def remove_skill(self, skill: str):
        if skill in self._skills:
            self._skills.remove(skill)
            self._updated_at = datetime.now()

    def enroll_in_course(self, course_name: str, total_modules: int = 0):
        if course_name not in self._course_progress:
            progress = CourseProgress(course_name)
            if total_modules > 0:
                progress.start_course(total_modules)
            self._course_progress[course_name] = progress
            self._updated_at = datetime.now()

    def get_course_progress(self, course_name: str) -> Optional[CourseProgress]:
        return self._course_progress.get(course_name)

    def complete_module(self, course_name: str, module_name: str):
        if course_name not in self._course_progress:
            raise NotFoundError(f"Course '{course_name}' not found in student's enrollments.")
        self._course_progress[course_name].complete_module(module_name)
        self._updated_at = datetime.now()

    def set_course_grade(self, course_name: str, grade: float):
        if course_name not in self._course_progress:
            raise NotFoundError(f"Course '{course_name}' not found.")
        self._course_progress[course_name].set_grade(grade)
        self._updated_at = datetime.now()

    def add_outcome(self, outcome_type: str, description: str, date_achieved: Optional[date] = None):
        outcome = {
            "type": outcome_type,
            "description": description,
            "date_achieved": (date_achieved or date.today()).isoformat(),
            "recorded_at": datetime.now().isoformat(),
        }
        self._outcomes.append(outcome)
        self._updated_at = datetime.now()

    def record_attendance(self, session_date: date, attended: bool, notes: str = ""):
        record = {
            "date": session_date.isoformat(),
            "attended": attended,
            "notes": notes,
        }
        self._attendance_records.append(record)
        self._updated_at = datetime.now()

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def bio(self) -> str:
        return self._bio

    @property
    def phone(self) -> str:
        return self._phone

    @property
    def address(self) -> str:
        return self._address

    @property
    def date_of_birth(self) -> Optional[date]:
        return self._date_of_birth

    @property
    def github_username(self) -> str:
        return self._github_username

    @property
    def linkedin_url(self) -> str:
        return self._linkedin_url

    @property
    def portfolio_url(self) -> str:
        return self._portfolio_url

    @property
    def skills(self) -> List[str]:
        return list(self._skills)

    @property
    def course_progress(self) -> Dict[str, CourseProgress]:
        return dict(self._course_progress)

    @property
    def outcomes(self) -> List[Dict[str, Any]]:
        return list(self._outcomes)

    @property
    def attendance_records(self) -> List[Dict[str, Any]]:
        return list(self._attendance_records)

    @property
    def attendance_rate(self) -> float:
        if not self._attendance_records:
            return 0.0
        attended = sum(1 for r in self._attendance_records if r["attended"])
        return (attended / len(self._attendance_records)) * 100

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self._student_id,
            "bio": self._bio,
            "phone": self._phone,
            "address": self._address,
            "date_of_birth": self._date_of_birth.isoformat() if self._date_of_birth else None,
            "github_username": self._github_username,
            "linkedin_url": self._linkedin_url,
            "portfolio_url": self._portfolio_url,
            "skills": self._skills,
            "course_progress": {k: v.to_dict() for k, v in self._course_progress.items()},
            "outcomes": self._outcomes,
            "attendance_records": self._attendance_records,
            "attendance_rate": self.attendance_rate,
            "updated_at": self._updated_at.isoformat(),
        }


class Student(User):
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ):
        super().__init__(user_id, username, email, password, first_name, last_name, role="student")
        self._profile = StudentProfile(user_id)
        self._enrollment_date = date.today()
        self._cohort: Optional[str] = None
        self._status: str = "active"

    @property
    def profile(self) -> StudentProfile:
        return self._profile

    @property
    def enrollment_date(self) -> date:
        return self._enrollment_date

    @property
    def cohort(self) -> Optional[str]:
        return self._cohort

    @property
    def status(self) -> str:
        return self._status

    def assign_cohort(self, cohort_name: str):
        self._cohort = cohort_name

    def update_status(self, status: str):
        valid_statuses = {"active", "graduated", "dropped", "on_hold"}
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        self._status = status

    def get_private_profile(self) -> Dict[str, Any]:
        data = self.to_dict()
        data["profile"] = self._profile.to_dict()
        data["enrollment_date"] = self._enrollment_date.isoformat()
        data["cohort"] = self._cohort
        data["status"] = self._status
        return data

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["enrollment_date"] = self._enrollment_date.isoformat()
        data["cohort"] = self._cohort
        data["status"] = self._status
        return data

    def __repr__(self) -> str:
        return f"<Student(id={self._user_id}, username={self._username}, cohort={self._cohort})>"


class Organizer(User):
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        is_admin: bool = False,
    ):
        role = "admin" if is_admin else "organizer"
        super().__init__(user_id, username, email, password, first_name, last_name, role=role)
        self._is_admin = is_admin
        self._managed_cohorts: List[str] = []
        self._permissions: List[str] = self._default_permissions()

    def _default_permissions(self) -> List[str]:
        base = ["view_students", "edit_student_progress", "manage_waitlist", "view_volunteers"]
        if self._is_admin:
            base.extend(["manage_users", "delete_records", "manage_volunteers", "full_access"])
        return base

    def has_permission(self, permission: str) -> bool:
        return permission in self._permissions or "full_access" in self._permissions

    def add_permission(self, permission: str):
        if permission not in self._permissions:
            self._permissions.append(permission)

    def remove_permission(self, permission: str):
        if permission in self._permissions:
            self._permissions.remove(permission)

    def assign_cohort(self, cohort_name: str):
        if cohort_name not in self._managed_cohorts:
            self._managed_cohorts.append(cohort_name)

    @property
    def is_admin(self) -> bool:
        return self._is_admin

    @property
    def managed_cohorts(self) -> List[str]:
        return list(self._managed_cohorts)

    @property
    def permissions(self) -> List[str]:
        return list(self._permissions)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["is_admin"] = self._is_admin
        data["managed_cohorts"] = self._managed_cohorts
        data["permissions"] = self._permissions
        return data

    def __repr__(self) -> str:
        return f"<Organizer(id={self._user_id}, username={self._username}, is_admin={self._is_admin})>"


class Volunteer(User):
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        expertise: str = "",
    ):
        super().__init__(user_id, username, email, password, first_name, last_name, role="volunteer")
        self._expertise = expertise
        self._availability: List[str] = []
        self._assigned_cohorts: List[str] = []
        self._volunteer_hours: float = 0.0
        self._status: str = "active"

    def add_availability(self, time_slot: str):
        if time_slot not in self._availability:
            self._availability.append(time_slot)

    def remove_availability(self, time_slot: str):
        if time_slot in self._availability:
            self._availability.remove(time_slot)

    def assign_to_cohort(self, cohort_name: str):
        if cohort_name not in self._assigned_cohorts:
            self._assigned_cohorts.append(cohort_name)

    def log_hours(self, hours: float):
        if hours < 0:
            raise ValidationError("Hours cannot be negative.")
        self._volunteer_hours += hours

    def update_status(self, status: str):
        valid_statuses = {"active", "inactive", "pending"}
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        self._status = status

    @property
    def expertise(self) -> str:
        return self._expertise

    @property
    def availability(self) -> List[str]:
        return list(self._availability)

    @property
    def assigned_cohorts(self) -> List[str]:
        return list(self._assigned_cohorts)

    @property
    def volunteer_hours(self) -> float:
        return self._volunteer_hours

    @property
    def status(self) -> str:
        return self._status

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["expertise"] = self._expertise
        data["availability"] = self._availability
        data["assigned_cohorts"] = self._assigned_cohorts
        data["volunteer_hours"] = self._volunteer_hours
        data["status"] = self._status
        return data

    def __repr__(self) -> str:
        return f"<Volunteer(id={self._user_id}, username={self._username}, expertise={self._expertise})>"


class WaitlistEntry:
    def __init__(
        self,
        entry_id: int,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        reason: str = "",
        cohort_interest: str = "",
    ):
        self._entry_id = entry_id
        self._first_name = first_name
        self._last_name = last_name
        self._email = self._validate_email(email)
        self._phone = phone
        self._reason = reason
        self._cohort_interest = cohort_interest
        self._applied_at = datetime.now()
        self._status: str = "waiting"
        self._notes: str = ""
        self._priority: int = 0

    def _validate_email(self, email: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, email):
            raise ValidationError(f"Invalid email address: {email}")
        return email

    def update_status(self, status: str):
        valid_statuses = {"waiting", "accepted", "rejected", "enrolled", "withdrawn"}
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        self._status = status

    def set_priority(self, priority: int):
        if priority < 0:
            raise ValidationError("Priority cannot be negative.")
        self._priority = priority

    def add_note(self, note: str):
        self._notes = note

    @property
    def entry_id(self) -> int:
        return self._entry_id

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def full_name(self) -> str:
        return f"{self._first_name} {self._last_name}"

    @property
    def email(self) -> str:
        return self._email

    @property
    def phone(self) -> str:
        return self._phone

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def cohort_interest(self) -> str:
        return self._cohort_interest

    @property
    def applied_at(self) -> datetime:
        return self._applied_at

    @property
    def status(self) -> str:
        return self._status

    @property
    def notes(self) -> str:
        return self._notes

    @property
    def priority(self) -> int:
        return self._priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self._entry_id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "email": self._email,
            "phone": self._phone,
            "reason": self._reason,
            "cohort_interest": self._cohort_interest,
            "applied_at": self._applied_at.isoformat(),
            "status": self._status,
            "notes": self._notes,
            "priority": self._priority,
        }

    def __repr__(self) -> str:
        return f"<WaitlistEntry(id={self._entry_id}, name={self.full_name}, status={self._status})>"


class Session:
    def __init__(self, session_id: str, user: User):
        self._session_id = session_id
        self._user = user
        self._created_at = datetime.now()
        self._expires_at = None
        self._is_active = True

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def user(self) -> User:
        return self._user

    @property
    def is_active(self) -> bool:
        return self._is_active

    def invalidate(self):
        self._is_active = False

    def __repr__(self) -> str:
        return f"<Session(id={self._session_id}, user={self._user.username})>"


class AuthenticationManager:
    def __init__(self):
        self._active_sessions: Dict[str, Session] = {}

    def login(self, user: User, password: str) -> Session:
        if not user.is_active:
            raise AuthenticationError("Account is deactivated.")
        if not user.verify_password(password):
            raise AuthenticationError("Invalid credentials.")
        user.record_login()
        session_id = secrets.token_hex(32)
        session = Session(session_id, user)
        self._active_sessions[session_id] = session
        return session

    def logout(self, session_id: str) -> bool:
        if session_id in self._active_sessions:
            self._active_sessions[session_id].invalidate()
            del self._active_sessions[session_id]
            return True
        return False

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._active_sessions.get(session_id)
        if session and session.is_active:
            return session
        return None

    def is_authenticated(self, session_id: str) -> bool:
        return self.get_session(session_id) is not None

    def get_user_from_session(self, session_id: str) -> Optional[User]:
        session = self.get_session(session_id)
        return session.user if session else None

    def invalidate_all_user_sessions(self, user_id: int):
        to_remove = [
            sid for sid, session in self._active_sessions.items()
            if session.user.user_id == user_id
        ]
        for sid in to_remove:
            self._active_sessions[sid].invalidate()
            del self._active_sessions[sid]


class StudentManagementSystem:
    def __init__(self):
        self._students: Dict[int, Student] = {}
        self._organizers: Dict[int, Organizer] = {}
        self._volunteers: Dict[int, Volunteer] = {}
        self._waitlist: Dict[int, WaitlistEntry] = {}
        self._users_by_username: Dict[str, User] = {}
        self._users_by_email: Dict[str, User] = {}
        self._auth_manager = AuthenticationManager()
        self._next_user_id = 1
        self._next_waitlist_id = 1
        self._cohorts: List[str] = []

    def _get_next_user_id(self) -> int:
        uid = self._next_user_id
        self._next_user_id += 1
        return uid

    def _get_next_waitlist_id(self) -> int:
        wid = self._next_waitlist_id
        self._next_waitlist_id += 1
        return wid

    def _check_username_available(self, username: str):
        if username in self._users_by_username:
            raise ValidationError(f"Username '{username}' is already taken.")

    def _check_email_available(self, email: str):
        if email in self._users_by_email:
            raise ValidationError(f"Email '{email}' is already registered.")

    def _register_user(self, user: User):
        self._users_by_username[user.username] = user
        self._users_by_email[user.email] = user

    def register_student(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        cohort: Optional[str] = None,
    ) -> Student:
        self._check_username_available(username)
        self._check_email_available(email)
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        uid = self._get_next_user_id()
        student = Student(uid, username, email, password, first_name, last_name)
        if cohort:
            student.assign_cohort(cohort)
            if cohort not in self._cohorts:
                self._cohorts.append(cohort)
        self._students[uid] = student
        self._register_user(student)
        return student

    def register_organizer(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        is_admin: bool = False,
        requesting_session_id: Optional[str] = None,
    ) -> Organizer:
        if requesting_session_id:
            self._require_admin(requesting_session_id)
        self._check_username_available(username)
        self._check_email_available(email)
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        uid = self._get_next_user_id()
        organizer = Organizer(uid, username, email, password, first_name, last_name, is_admin)
        self._organizers[uid] = organizer
        self._register_user(organizer)
        return organizer

    def register_volunteer(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        expertise: str = "",
        requesting_session_id: Optional[str] = None,
    ) -> Volunteer:
        if requesting_session_id:
            self._require_organizer(requesting_session_id)
        self._check_username_available(username)
        self._check_email_available(email)
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        uid = self._get_next_user_id()
        volunteer = Volunteer(uid, username, email, password, first_name, last_name, expertise)
        self._volunteers[uid] = volunteer
        self._register_user(volunteer)
        return volunteer

    def login(self, username: str, password: str) -> Session:
        user = self._users_by_username.get(username)
        if not user:
            raise AuthenticationError("Invalid credentials.")
        return self._auth_manager.login(user, password)

    def logout(self, session_id: str) -> bool:
        return self._auth_manager.logout(session_id)

    def _get_session_user(self, session_id: str) -> User:
        user = self._auth_manager.get_user_from_session(session_id)
        if not user:
            raise AuthenticationError("Invalid or expired session.")
        return user

    def _require_organizer(self, session_id: str) -> User:
        user = self._get_session_user(session_id)
        if user.role not in ("organizer", "admin"):
            raise PermissionError("Access denied. Organizer or admin role required.")
        return user

    def _require_admin(self, session_id: str) -> User:
        user = self._get_session_user(session_id)
        if user.role != "admin":
            raise PermissionError("Access denied. Admin role required.")
        return user

    def get_student_profile(self, session_id: str, student_id: int) -> Dict[str, Any]:
        requesting_user = self._get_session_user(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        if requesting_user.role in ("organizer", "admin"):
            return student.get_private_profile()
        if requesting_user.user_id == student_id:
            return student.get_private_profile()
        raise PermissionError("Access denied. You can only view your own profile.")

    def update_student_profile(
        self,
        session_id: str,
        student_id: int,
        **profile_data,
    ) -> Dict[str, Any]:
        requesting_user = self._get_session_user(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        if requesting_user.role not in ("organizer", "admin") and requesting_user.user_id != student_id:
            raise PermissionError("Access denied.")
        student.profile.update_profile(**profile_data)
        return student.get_private_profile()

    def enroll_student_in_course(
        self,
        session_id: str,
        student_id: int,
        course_name: str,
        total_modules: int = 0,
    ):
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.profile.enroll_in_course(course_name, total_modules)

    def update_student_progress(
        self,
        session_id: str,
        student_id: int,
        course_name: str,
        module_name: str,
    ):
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.profile.complete_module(course_name, module_name)

    def set_student_grade(
        self,
        session_id: str,
        student_id: int,
        course_name: str,
        grade: float,
    ):
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.profile.set_course_grade(course_name, grade)

    def add_student_outcome(
        self,
        session_id: str,
        student_id: int,
        outcome_type: str,
        description: str,
        date_achieved: Optional[date] = None,
    ):
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.profile.add_outcome(outcome_type, description, date_achieved)

    def record_student_attendance(
        self,
        session_id: str,
        student_id: int,
        session_date: date,
        attended: bool,
        notes: str = "",
    ):
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.profile.record_attendance(session_date, attended, notes)

    def update_student_status(
        self,
        session_id: str,
        student_id: int,
        status: str,
    ):
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if not student:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.update_status(status)

    def add_to_waitlist(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        reason: str = "",
        cohort_interest: str = "",
    ) -> WaitlistEntry:
        for entry in self._waitlist.values():
            if entry.email == email and entry.status == "waiting":
                raise ValidationError(f"Email '{email}' is already on the waitlist.")
        wid = self._get_next_waitlist_id()
        entry = WaitlistEntry(wid, first_name, last_name, email, phone, reason, cohort_interest)
        self._waitlist[wid] = entry
        return entry

    def get_waitlist(self, session_id: str) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        return [entry.to_dict() for entry in sorted(
            self._waitlist.values(),
            key=lambda e: (e.priority, e.applied_at),
            reverse=False,
        )]

    def update_waitlist_entry(
        self,
        session_id: str,
        entry_id: int,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        entry = self._waitlist.get(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry with ID {entry_id} not found.")
        if status:
            entry.update_status(status)
        if priority is not None:
            entry.set_priority(priority)
        if notes is not None:
            entry.add_note(notes)
        return entry.to_dict()

    def get_all_students(self, session_id: str) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        return [student.to_dict() for student in self._students.values()]

    def get_all_students_with_profiles(self, session_id: str) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        return [student.get_private_profile() for student in self._students.values()]

    def get_all_volunteers(self, session_id: str) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        return [volunteer.to_dict() for volunteer in self._volunteers.values()]

    def update_volunteer(
        self,
        session_id: str,
        volunteer_id: int,
        status: Optional[str] = None,
        cohort: Optional[str] = None,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        volunteer = self._volunteers.get(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer with ID {volunteer_id} not found.")
        if status:
            volunteer.update_status(status)
        if cohort:
            volunteer.assign_to_cohort(cohort)
        if hours is not None:
            volunteer.log_hours(hours)
        return volunteer.to_dict()

    def get_admin_dashboard(self, session_id: str) -> Dict[str, Any]:
        self._require_organizer(session_id)
        total_students = len(self._students)
        active_students = sum(1 for s in self._students.values() if s.status == "active")
        graduated_students = sum(1 for s in self._students.values() if s.status == "graduated")
        dropped_students = sum(1 for s in self._students.values() if s.status == "dropped")
        waiting_count = sum(1 for e in self._waitlist.values() if e.status == "waiting")
        active_volunteers = sum(1 for v in self._volunteers.values() if v.status == "active")
        total_volunteer_hours = sum(v.volunteer_hours for v in self._volunteers.values())

        cohort_stats: Dict[str, Dict[str, Any]] = {}
        for student in self._students.values():
            cohort = student.cohort or "Unassigned"
            if cohort not in cohort_stats:
                cohort_stats[cohort] = {"total": 0, "active": 0, "graduated": 0, "dropped": 0}
            cohort_stats[cohort]["total"] += 1
            if student.status in cohort_stats[cohort]:
                cohort_stats[cohort][student.status] += 1

        outcomes_summary: Dict[str, int] = {}
        for student in self._students.values():
            for outcome in student.profile.outcomes:
                otype = outcome["type"]
                outcomes_summary[otype] = outcomes_summary.get(otype, 0) + 1

        return {
            "student_stats": {
                "total": total_students,
                "active": active_students,
                "graduated": graduated_students,
                "dropped": dropped_students,
            },
            "cohort_stats": cohort_stats,
            "waitlist_stats": {
                "waiting": waiting_count,
                "total": len(self._waitlist),
            },
            "volunteer_stats": {
                "active": active_volunteers,
                "total": len(self._volunteers),
                "total_hours": total_volunteer_hours,
            },
            "outcomes_summary": outcomes_summary,
            "cohorts": self._cohorts,
        }

    def search_students(
        self,
        session_id: str,
        query: str = "",
        cohort: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        results = []
        for student in self._students.values():
            if cohort and student.cohort != cohort:
                continue
            if status and student.status != status:
                continue
            if query:
                q = query.lower()
                if not (
                    q in student.username.lower()
                    or q in student.email.lower()
                    or q in student.full_name.lower()
                ):
                    continue
            results.append(student.to_dict())
        return results

    def add_cohort(self, session_id: str, cohort_name: str):
        self._require_organizer(session_id)
        if cohort_name not in self._cohorts:
            self._cohorts.append(cohort_name)

    def get_cohorts(self, session_id: str) -> List[str]:
        self._require_organizer(session_id)
        return list(self._cohorts)

    def deactivate_user(self, session_id: str, user_id: int):
        self._require_admin(session_id)
        user = (
            self._students.get(user_id)
            or self._organizers.get(user_id)
            or self._volunteers.get(user_id)
        )
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found.")
        user.deactivate()
        self._auth_manager.invalidate_all_user_sessions(user_id)

    def activate_user(self, session_id: str, user_id: int):
        self._require_admin(session_id)
        user = (
            self._students.get(user_id)
            or self._organizers.get(user_id)
            or self._volunteers.get(user_id)
        )
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found.")
        user.activate()

    def get_student_by_id(self, student_id: int) -> Optional[Student]:
        return self._students.get(student_id)

    def get_organizer_by_id(self, organizer_id: int) -> Optional[Organizer]:
        return self._organizers.get(organizer_id)

    def get_volunteer_by_id(self, volunteer_id: int) -> Optional[Volunteer]:
        return self._volunteers.get(volunteer_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self._users_by_username.get(username)

    def is_authenticated(self, session_id: str) -> bool:
        return self._auth_manager.is_authenticated(session_id)

    def get_current_user(self, session_id: str) -> Optional[User]:
        return self._auth_manager.get_user_from_session(session_id)

    def __repr__(self) -> str:
        return (
            f"<StudentManagementSystem("
            f"students={len(self._students)}, "
            f"organizers={len(self._organizers)}, "
            f"volunteers={len(self._volunteers)}, "
            f"waitlist={len(self._waitlist)})>"
        )


if __name__ == "__main__":
    sms = StudentManagementSystem()

    admin = sms.register_organizer(
        username="admin",
        email="admin@freecodecamp.org",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
        is_admin=True,
    )

    organizer = sms.register_organizer(
        username="organizer1",
        email="organizer1@freecodecamp.org",
        password="orgpass123",
        first_name="Jane",
        last_name="Doe",
        is_admin=False,
    )

    admin_session = sms.login("admin", "adminpass123")
    print(f"Admin logged in: {admin_session}")

    org_session = sms.login("organizer1", "orgpass123")
    print(f"Organizer logged in: {org_session}")

    student1 = sms.register_student(
        username="student1",
        email="student1@example.com",
        password="studentpass123",
        first_name="John",
        last_name="Smith",
        cohort="2024-Spring",
    )
    print(f"Student registered: {student1}")

    student2 = sms.register_student(
        username="student2",
        email="student2@example.com",
        password="studentpass123",
        first_name="Alice",
        last_name="Johnson",
        cohort="2024-Spring",
    )

    volunteer1 = sms.register_volunteer(
        username="volunteer1",
        email="volunteer1@example.com",
        password="volpass123",
        first_name="Bob",
        last_name="Williams",
        expertise="Python",
        requesting_session_id=org_session.session_id,
    )
    print(f"Volunteer registered: {volunteer1}")

    sms.enroll_student_in_course(org_session.session_id, student1.user_id, "Python Basics", 5)
    sms.update_student_progress(org_session.session_id, student1.user_id, "Python Basics", "Module 1: Intro")
    sms.update_student_progress(org_session.session_id, student1.user_id, "Python Basics", "Module 2: Variables")
    sms.set_student_grade(org_session.session_id, student1.user_id, "Python Basics", 92.5)

    sms.add_student_outcome(
        org_session.session_id,
        student1.user_id,
        "employment",
        "Got a job at TechCorp as a Junior Developer",
    )

    sms.record_student_attendance(
        org_session.session_id,
        student1.user_id,
        date.today(),
        True,
        "On time",
    )

    student1_session = sms.login("student1", "studentpass123")
    profile = sms.get_student_profile(student1_session.session_id, student1.user_id)
    print(f"\nStudent Profile:")
    print(f"  Name: {profile['first_name']} {profile['last_name']}")
    print(f"  Cohort: {profile['cohort']}")
    print(f"  Status: {profile['status']}")
    print(f"  Courses: {list(profile['profile']['course_progress'].keys())}")

    waitlist_entry = sms.add_to_waitlist(
        first_name="Charlie",
        last_name="Brown",
        email="charlie@example.com",
        phone="555-1234",
        reason="Interested in learning programming",
        cohort_interest="2024-Fall",
    )
    print(f"\nWaitlist entry added: {waitlist_entry}")

    waitlist = sms.get_waitlist(org_session.session_id)
    print(f"Waitlist count: {len(waitlist)}")

    dashboard = sms.get_admin_dashboard(admin_session.session_id)
    print(f"\nAdmin Dashboard:")
    print(f"  Total Students: {dashboard['student_stats']['total']}")
    print(f"  Active Students: {dashboard['student_stats']['active']}")
    print(f"  Waitlist: {dashboard['waitlist_stats']['waiting']}")
    print(f"  Volunteers: {dashboard['volunteer_stats']['total']}")
    print(f"  Cohorts: {dashboard['cohorts']}")

    all_students = sms.get_all_students(org_session.session_id)
    print(f"\nAll Students: {len(all_students)}")

    search_results = sms.search_students(org_session.session_id, query="john", cohort="2024-Spring")
    print(f"Search results for 'john' in 2024-Spring: {len(search_results)}")

    sms.update_volunteer(
        org_session.session_id,
        volunteer1.user_id,
        cohort="2024-Spring",
        hours=5.0,
    )
    print(f"\nVolunteer hours: {volunteer1.volunteer_hours}")

    sms.logout(student1_session.session_id)
    sms.logout(org_session.session_id)
    sms.logout(admin_session.session_id)
    print("\nAll sessions logged out.")
    print(f"\nSystem: {sms}")