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

    def verify_password(self, password: str) -> bool:
        return PasswordHasher.verify_password(password, self._password_hash)

    def update_password(self, old_password: str, new_password: str) -> None:
        if not self.verify_password(old_password):
            raise AuthenticationError("Current password is incorrect.")
        if len(new_password) < 8:
            raise ValidationError("New password must be at least 8 characters long.")
        self._password_hash = PasswordHasher.hash_password(new_password)

    def update_last_login(self) -> None:
        self._last_login = datetime.now()

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
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
        return f"User(id={self._user_id}, username={self._username}, role={self._role})"


class CourseProgress:
    def __init__(self, course_name: str):
        self._course_name = course_name
        self._completed_lessons: List[str] = []
        self._total_lessons = 0
        self._started_at = datetime.now()
        self._completed_at: Optional[datetime] = None
        self._grade: Optional[float] = None

    @property
    def course_name(self) -> str:
        return self._course_name

    @property
    def completed_lessons(self) -> List[str]:
        return list(self._completed_lessons)

    @property
    def total_lessons(self) -> int:
        return self._total_lessons

    @total_lessons.setter
    def total_lessons(self, value: int) -> None:
        if value < 0:
            raise ValidationError("Total lessons cannot be negative.")
        self._total_lessons = value

    @property
    def progress_percentage(self) -> float:
        if self._total_lessons == 0:
            return 0.0
        return (len(self._completed_lessons) / self._total_lessons) * 100

    @property
    def is_completed(self) -> bool:
        return self._completed_at is not None

    @property
    def grade(self) -> Optional[float]:
        return self._grade

    def complete_lesson(self, lesson_name: str) -> None:
        if lesson_name not in self._completed_lessons:
            self._completed_lessons.append(lesson_name)
        if self._total_lessons > 0 and len(self._completed_lessons) >= self._total_lessons:
            self._completed_at = datetime.now()

    def set_grade(self, grade: float) -> None:
        if not (0.0 <= grade <= 100.0):
            raise ValidationError("Grade must be between 0 and 100.")
        self._grade = grade

    def to_dict(self) -> Dict[str, Any]:
        return {
            "course_name": self._course_name,
            "completed_lessons": self._completed_lessons,
            "total_lessons": self._total_lessons,
            "progress_percentage": self.progress_percentage,
            "is_completed": self.is_completed,
            "grade": self._grade,
            "started_at": self._started_at.isoformat(),
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
        self._notes: List[Dict[str, Any]] = []
        self._updated_at = datetime.now()

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def bio(self) -> str:
        return self._bio

    @bio.setter
    def bio(self, value: str) -> None:
        self._bio = value
        self._updated_at = datetime.now()

    @property
    def phone(self) -> str:
        return self._phone

    @phone.setter
    def phone(self, value: str) -> None:
        self._phone = value
        self._updated_at = datetime.now()

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        self._address = value
        self._updated_at = datetime.now()

    @property
    def date_of_birth(self) -> Optional[date]:
        return self._date_of_birth

    @date_of_birth.setter
    def date_of_birth(self, value: Optional[date]) -> None:
        self._date_of_birth = value
        self._updated_at = datetime.now()

    @property
    def github_username(self) -> str:
        return self._github_username

    @github_username.setter
    def github_username(self, value: str) -> None:
        self._github_username = value
        self._updated_at = datetime.now()

    @property
    def linkedin_url(self) -> str:
        return self._linkedin_url

    @linkedin_url.setter
    def linkedin_url(self, value: str) -> None:
        self._linkedin_url = value
        self._updated_at = datetime.now()

    @property
    def portfolio_url(self) -> str:
        return self._portfolio_url

    @portfolio_url.setter
    def portfolio_url(self, value: str) -> None:
        self._portfolio_url = value
        self._updated_at = datetime.now()

    @property
    def skills(self) -> List[str]:
        return list(self._skills)

    @property
    def notes(self) -> List[Dict[str, Any]]:
        return list(self._notes)

    def add_skill(self, skill: str) -> None:
        if skill not in self._skills:
            self._skills.append(skill)
            self._updated_at = datetime.now()

    def remove_skill(self, skill: str) -> None:
        if skill in self._skills:
            self._skills.remove(skill)
            self._updated_at = datetime.now()

    def add_note(self, note_text: str, author: str) -> None:
        note = {
            "text": note_text,
            "author": author,
            "created_at": datetime.now().isoformat(),
        }
        self._notes.append(note)
        self._updated_at = datetime.now()

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
            "notes": self._notes,
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
        cohort: str = "",
        enrollment_status: str = "enrolled",
    ):
        super().__init__(user_id, username, email, password, first_name, last_name, role="student")
        self._cohort = cohort
        self._enrollment_status = enrollment_status
        self._profile = StudentProfile(user_id)
        self._course_progress: Dict[str, CourseProgress] = {}
        self._attendance_records: List[Dict[str, Any]] = []
        self._outcomes: Dict[str, Any] = {
            "employed": False,
            "employer": "",
            "job_title": "",
            "salary": None,
            "employment_date": None,
        }
        self._enrolled_at = datetime.now()

    @property
    def cohort(self) -> str:
        return self._cohort

    @cohort.setter
    def cohort(self, value: str) -> None:
        self._cohort = value

    @property
    def enrollment_status(self) -> str:
        return self._enrollment_status

    @enrollment_status.setter
    def enrollment_status(self, value: str) -> None:
        valid_statuses = ["enrolled", "graduated", "dropped", "waitlisted", "deferred"]
        if value not in valid_statuses:
            raise ValidationError(f"Invalid enrollment status. Must be one of: {valid_statuses}")
        self._enrollment_status = value

    @property
    def profile(self) -> StudentProfile:
        return self._profile

    @property
    def course_progress(self) -> Dict[str, CourseProgress]:
        return dict(self._course_progress)

    @property
    def attendance_records(self) -> List[Dict[str, Any]]:
        return list(self._attendance_records)

    @property
    def outcomes(self) -> Dict[str, Any]:
        return dict(self._outcomes)

    @property
    def enrolled_at(self) -> datetime:
        return self._enrolled_at

    def enroll_in_course(self, course_name: str) -> CourseProgress:
        if course_name not in self._course_progress:
            self._course_progress[course_name] = CourseProgress(course_name)
        return self._course_progress[course_name]

    def get_course_progress(self, course_name: str) -> Optional[CourseProgress]:
        return self._course_progress.get(course_name)

    def record_attendance(self, session_date: date, status: str, notes: str = "") -> None:
        valid_statuses = ["present", "absent", "late", "excused"]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid attendance status. Must be one of: {valid_statuses}")
        record = {
            "date": session_date.isoformat(),
            "status": status,
            "notes": notes,
            "recorded_at": datetime.now().isoformat(),
        }
        self._attendance_records.append(record)

    def get_attendance_rate(self) -> float:
        if not self._attendance_records:
            return 0.0
        present_count = sum(
            1 for r in self._attendance_records if r["status"] in ["present", "late"]
        )
        return (present_count / len(self._attendance_records)) * 100

    def update_outcomes(
        self,
        employed: bool,
        employer: str = "",
        job_title: str = "",
        salary: Optional[float] = None,
        employment_date: Optional[date] = None,
    ) -> None:
        self._outcomes["employed"] = employed
        self._outcomes["employer"] = employer
        self._outcomes["job_title"] = job_title
        self._outcomes["salary"] = salary
        self._outcomes["employment_date"] = employment_date.isoformat() if employment_date else None

    def get_overall_progress(self) -> float:
        if not self._course_progress:
            return 0.0
        total_progress = sum(cp.progress_percentage for cp in self._course_progress.values())
        return total_progress / len(self._course_progress)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "cohort": self._cohort,
                "enrollment_status": self._enrollment_status,
                "enrolled_at": self._enrolled_at.isoformat(),
                "overall_progress": self.get_overall_progress(),
                "attendance_rate": self.get_attendance_rate(),
                "outcomes": self._outcomes,
                "profile": self._profile.to_dict(),
                "courses": {name: cp.to_dict() for name, cp in self._course_progress.items()},
            }
        )
        return base

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "cohort": self._cohort,
            "enrollment_status": self._enrollment_status,
        }

    def __repr__(self) -> str:
        return f"Student(id={self.user_id}, username={self.username}, cohort={self._cohort})"


class Organizer(User):
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization: str = "",
        is_admin: bool = False,
    ):
        role = "admin" if is_admin else "organizer"
        super().__init__(user_id, username, email, password, first_name, last_name, role=role)
        self._organization = organization
        self._is_admin = is_admin
        self._permissions: List[str] = self._default_permissions()

    def _default_permissions(self) -> List[str]:
        if self._is_admin:
            return [
                "view_all_students",
                "edit_students",
                "delete_students",
                "manage_volunteers",
                "manage_waitlist",
                "view_outcomes",
                "manage_organizers",
                "manage_cohorts",
            ]
        return [
            "view_all_students",
            "edit_students",
            "manage_volunteers",
            "manage_waitlist",
            "view_outcomes",
        ]

    @property
    def organization(self) -> str:
        return self._organization

    @property
    def is_admin(self) -> bool:
        return self._is_admin

    @property
    def permissions(self) -> List[str]:
        return list(self._permissions)

    def has_permission(self, permission: str) -> bool:
        return permission in self._permissions

    def grant_permission(self, permission: str) -> None:
        if permission not in self._permissions:
            self._permissions.append(permission)

    def revoke_permission(self, permission: str) -> None:
        if permission in self._permissions:
            self._permissions.remove(permission)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "organization": self._organization,
                "is_admin": self._is_admin,
                "permissions": self._permissions,
            }
        )
        return base

    def __repr__(self) -> str:
        return f"Organizer(id={self.user_id}, username={self.username}, is_admin={self._is_admin})"


class Volunteer:
    def __init__(
        self,
        volunteer_id: int,
        first_name: str,
        last_name: str,
        email: str,
        skills: Optional[List[str]] = None,
        availability: str = "",
        role: str = "mentor",
    ):
        self._volunteer_id = volunteer_id
        self._first_name = first_name
        self._last_name = last_name
        self._email = self._validate_email(email)
        self._skills = skills or []
        self._availability = availability
        self._role = role
        self._is_active = True
        self._sessions: List[Dict[str, Any]] = []
        self._created_at = datetime.now()

    def _validate_email(self, email: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, email):
            raise ValidationError(f"Invalid email address: {email}")
        return email

    @property
    def volunteer_id(self) -> int:
        return self._volunteer_id

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
    def skills(self) -> List[str]:
        return list(self._skills)

    @property
    def availability(self) -> str:
        return self._availability

    @availability.setter
    def availability(self, value: str) -> None:
        self._availability = value

    @property
    def role(self) -> str:
        return self._role

    @role.setter
    def role(self, value: str) -> None:
        valid_roles = ["mentor", "instructor", "ta", "guest_speaker", "coordinator"]
        if value not in valid_roles:
            raise ValidationError(f"Invalid volunteer role. Must be one of: {valid_roles}")
        self._role = value

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def sessions(self) -> List[Dict[str, Any]]:
        return list(self._sessions)

    def add_skill(self, skill: str) -> None:
        if skill not in self._skills:
            self._skills.append(skill)

    def remove_skill(self, skill: str) -> None:
        if skill in self._skills:
            self._skills.remove(skill)

    def log_session(self, session_date: date, duration_hours: float, description: str = "") -> None:
        session = {
            "date": session_date.isoformat(),
            "duration_hours": duration_hours,
            "description": description,
            "logged_at": datetime.now().isoformat(),
        }
        self._sessions.append(session)

    def get_total_hours(self) -> float:
        return sum(s["duration_hours"] for s in self._sessions)

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volunteer_id": self._volunteer_id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "email": self._email,
            "skills": self._skills,
            "availability": self._availability,
            "role": self._role,
            "is_active": self._is_active,
            "total_hours": self.get_total_hours(),
            "sessions_count": len(self._sessions),
            "created_at": self._created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"Volunteer(id={self._volunteer_id}, name={self.full_name}, role={self._role})"


class WaitlistEntry:
    def __init__(
        self,
        entry_id: int,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        cohort_preference: str = "",
        notes: str = "",
    ):
        self._entry_id = entry_id
        self._first_name = first_name
        self._last_name = last_name
        self._email = self._validate_email(email)
        self._phone = phone
        self._cohort_preference = cohort_preference
        self._notes = notes
        self._status = "waiting"
        self._applied_at = datetime.now()
        self._updated_at = datetime.now()
        self._position: Optional[int] = None

    def _validate_email(self, email: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, email):
            raise ValidationError(f"Invalid email address: {email}")
        return email

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
    def cohort_preference(self) -> str:
        return self._cohort_preference

    @property
    def notes(self) -> str:
        return self._notes

    @notes.setter
    def notes(self, value: str) -> None:
        self._notes = value
        self._updated_at = datetime.now()

    @property
    def status(self) -> str:
        return self._status

    @property
    def applied_at(self) -> datetime:
        return self._applied_at

    @property
    def position(self) -> Optional[int]:
        return self._position

    @position.setter
    def position(self, value: Optional[int]) -> None:
        self._position = value

    def accept(self) -> None:
        self._status = "accepted"
        self._updated_at = datetime.now()

    def reject(self) -> None:
        self._status = "rejected"
        self._updated_at = datetime.now()

    def defer(self) -> None:
        self._status = "deferred"
        self._updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self._entry_id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "email": self._email,
            "phone": self._phone,
            "cohort_preference": self._cohort_preference,
            "notes": self._notes,
            "status": self._status,
            "position": self._position,
            "applied_at": self._applied_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"WaitlistEntry(id={self._entry_id}, name={self.full_name}, status={self._status})"


class Session:
    def __init__(self, session_id: str, user: User):
        self._session_id = session_id
        self._user = user
        self._created_at = datetime.now()
        self._expires_at = datetime.now().replace(
            hour=datetime.now().hour + 24
            if datetime.now().hour < 0
            else datetime.now().hour
        )
        self._is_valid = True

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def user(self) -> User:
        return self._user

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    def invalidate(self) -> None:
        self._is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self._session_id,
            "user_id": self._user.user_id,
            "username": self._user.username,
            "role": self._user.role,
            "created_at": self._created_at.isoformat(),
        }


class AuthService:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def login(self, user: User, password: str) -> Session:
        if not user.is_active:
            raise AuthenticationError("Account is deactivated.")
        if not user.verify_password(password):
            raise AuthenticationError("Invalid password.")
        user.update_last_login()
        session_id = secrets.token_hex(32)
        session = Session(session_id, user)
        self._sessions[session_id] = session
        return session

    def logout(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].invalidate()
            del self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_valid:
            return session
        return None

    def is_authenticated(self, session_id: str) -> bool:
        return self.get_session(session_id) is not None

    def get_user_from_session(self, session_id: str) -> Optional[User]:
        session = self.get_session(session_id)
        return session.user if session else None


class StudentManagementSystem:
    def __init__(self):
        self._users: Dict[int, User] = {}
        self._students: Dict[int, Student] = {}
        self._organizers: Dict[int, Organizer] = {}
        self._volunteers: Dict[int, Volunteer] = {}
        self._waitlist: Dict[int, WaitlistEntry] = {}
        self._cohorts: List[str] = []
        self._auth_service = AuthService()
        self._next_user_id = 1
        self._next_volunteer_id = 1
        self._next_waitlist_id = 1
        self._username_index: Dict[str, int] = {}
        self._email_index: Dict[str, int] = {}

    def _get_next_user_id(self) -> int:
        uid = self._next_user_id
        self._next_user_id += 1
        return uid

    def _get_next_volunteer_id(self) -> int:
        vid = self._next_volunteer_id
        self._next_volunteer_id += 1
        return vid

    def _get_next_waitlist_id(self) -> int:
        wid = self._next_waitlist_id
        self._next_waitlist_id += 1
        return wid

    def _check_username_available(self, username: str) -> None:
        if username in self._username_index:
            raise ValidationError(f"Username '{username}' is already taken.")

    def _check_email_available(self, email: str) -> None:
        if email in self._email_index:
            raise ValidationError(f"Email '{email}' is already registered.")

    def register_student(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        cohort: str = "",
        enrollment_status: str = "enrolled",
    ) -> Student:
        self._check_username_available(username)
        self._check_email_available(email)
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        user_id = self._get_next_user_id()
        student = Student(
            user_id, username, email, password, first_name, last_name, cohort, enrollment_status
        )
        self._users[user_id] = student
        self._students[user_id] = student
        self._username_index[username] = user_id
        self._email_index[email] = user_id
        if cohort and cohort not in self._cohorts:
            self._cohorts.append(cohort)
        return student

    def register_organizer(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization: str = "",
        is_admin: bool = False,
    ) -> Organizer:
        self._check_username_available(username)
        self._check_email_available(email)
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        user_id = self._get_next_user_id()
        organizer = Organizer(
            user_id, username, email, password, first_name, last_name, organization, is_admin
        )
        self._users[user_id] = organizer
        self._organizers[user_id] = organizer
        self._username_index[username] = user_id
        self._email_index[email] = user_id
        return organizer

    def login(self, username: str, password: str) -> Session:
        user_id = self._username_index.get(username)
        if user_id is None:
            raise AuthenticationError("Invalid username or password.")
        user = self._users.get(user_id)
        if user is None:
            raise AuthenticationError("Invalid username or password.")
        return self._auth_service.login(user, password)

    def logout(self, session_id: str) -> None:
        self._auth_service.logout(session_id)

    def get_authenticated_user(self, session_id: str) -> Optional[User]:
        return self._auth_service.get_user_from_session(session_id)

    def _require_auth(self, session_id: str) -> User:
        user = self.get_authenticated_user(session_id)
        if user is None:
            raise AuthenticationError("Not authenticated. Please log in.")
        return user

    def _require_organizer(self, session_id: str) -> Organizer:
        user = self._require_auth(session_id)
        if user.role not in ("organizer", "admin"):
            raise PermissionError("Access denied. Organizer or admin role required.")
        return self._organizers[user.user_id]

    def _require_admin(self, session_id: str) -> Organizer:
        user = self._require_auth(session_id)
        if user.role != "admin":
            raise PermissionError("Access denied. Admin role required.")
        return self._organizers[user.user_id]

    def get_student_profile(self, session_id: str, student_id: int) -> Dict[str, Any]:
        user = self._require_auth(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        if user.role in ("organizer", "admin"):
            return student.to_dict()
        if user.user_id == student_id:
            return student.to_dict()
        raise PermissionError("Access denied. You can only view your own profile.")

    def update_student_profile(
        self, session_id: str, student_id: int, profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        user = self._require_auth(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        if user.role not in ("organizer", "admin") and user.user_id != student_id:
            raise PermissionError("Access denied.")
        profile = student.profile
        if "bio" in profile_data:
            profile.bio = profile_data["bio"]
        if "phone" in profile_data:
            profile.phone = profile_data["phone"]
        if "address" in profile_data:
            profile.address = profile_data["address"]
        if "github_username" in profile_data:
            profile.github_username = profile_data["github_username"]
        if "linkedin_url" in profile_data:
            profile.linkedin_url = profile_data["linkedin_url"]
        if "portfolio_url" in profile_data:
            profile.portfolio_url = profile_data["portfolio_url"]
        if "skills" in profile_data:
            for skill in profile_data["skills"]:
                profile.add_skill(skill)
        return student.to_dict()

    def list_all_students(self, session_id: str) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        return [s.to_dict() for s in self._students.values()]

    def get_student_by_cohort(self, session_id: str, cohort: str) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        return [s.to_dict() for s in self._students.values() if s.cohort == cohort]

    def update_student_enrollment_status(
        self, session_id: str, student_id: int, status: str
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.enrollment_status = status
        return student.to_dict()

    def enroll_student_in_course(
        self, session_id: str, student_id: int, course_name: str
    ) -> Dict[str, Any]:
        user = self._require_auth(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        if user.role not in ("organizer", "admin") and user.user_id != student_id:
            raise PermissionError("Access denied.")
        progress = student.enroll_in_course(course_name)
        return progress.to_dict()

    def update_course_progress(
        self,
        session_id: str,
        student_id: int,
        course_name: str,
        lesson_name: str,
    ) -> Dict[str, Any]:
        user = self._require_auth(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        if user.role not in ("organizer", "admin") and user.user_id != student_id:
            raise PermissionError("Access denied.")
        progress = student.get_course_progress(course_name)
        if progress is None:
            raise NotFoundError(f"Student is not enrolled in course '{course_name}'.")
        progress.complete_lesson(lesson_name)
        return progress.to_dict()

    def record_student_attendance(
        self,
        session_id: str,
        student_id: int,
        attendance_date: date,
        status: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.record_attendance(attendance_date, status, notes)
        return {"student_id": student_id, "attendance_rate": student.get_attendance_rate()}

    def update_student_outcomes(
        self,
        session_id: str,
        student_id: int,
        employed: bool,
        employer: str = "",
        job_title: str = "",
        salary: Optional[float] = None,
        employment_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.update_outcomes(employed, employer, job_title, salary, employment_date)
        return student.outcomes

    def add_note_to_student(
        self, session_id: str, student_id: int, note_text: str
    ) -> Dict[str, Any]:
        organizer = self._require_organizer(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        student.profile.add_note(note_text, organizer.username)
        return {"student_id": student_id, "notes": student.profile.notes}

    def add_volunteer(
        self,
        session_id: str,
        first_name: str,
        last_name: str,
        email: str,
        skills: Optional[List[str]] = None,
        availability: str = "",
        role: str = "mentor",
    ) -> Volunteer:
        self._require_organizer(session_id)
        volunteer_id = self._get_next_volunteer_id()
        volunteer = Volunteer(volunteer_id, first_name, last_name, email, skills, availability, role)
        self._volunteers[volunteer_id] = volunteer
        return volunteer

    def get_volunteer(self, session_id: str, volunteer_id: int) -> Dict[str, Any]:
        self._require_organizer(session_id)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise NotFoundError(f"Volunteer with ID {volunteer_id} not found.")
        return volunteer.to_dict()

    def list_volunteers(self, session_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        volunteers = self._volunteers.values()
        if active_only:
            volunteers = [v for v in volunteers if v.is_active]
        return [v.to_dict() for v in volunteers]

    def update_volunteer(
        self, session_id: str, volunteer_id: int, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise NotFoundError(f"Volunteer with ID {volunteer_id} not found.")
        if "availability" in update_data:
            volunteer.availability = update_data["availability"]
        if "role" in update_data:
            volunteer.role = update_data["role"]
        if "skills_to_add" in update_data:
            for skill in update_data["skills_to_add"]:
                volunteer.add_skill(skill)
        if "skills_to_remove" in update_data:
            for skill in update_data["skills_to_remove"]:
                volunteer.remove_skill(skill)
        return volunteer.to_dict()

    def log_volunteer_session(
        self,
        session_id: str,
        volunteer_id: int,
        session_date: date,
        duration_hours: float,
        description: str = "",
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise NotFoundError(f"Volunteer with ID {volunteer_id} not found.")
        volunteer.log_session(session_date, duration_hours, description)
        return volunteer.to_dict()

    def deactivate_volunteer(self, session_id: str, volunteer_id: int) -> Dict[str, Any]:
        self._require_organizer(session_id)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise NotFoundError(f"Volunteer with ID {volunteer_id} not found.")
        volunteer.deactivate()
        return volunteer.to_dict()

    def add_to_waitlist(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        cohort_preference: str = "",
        notes: str = "",
    ) -> WaitlistEntry:
        for entry in self._waitlist.values():
            if entry.email == email and entry.status == "waiting":
                raise ValidationError(f"Email '{email}' is already on the waitlist.")
        entry_id = self._get_next_waitlist_id()
        entry = WaitlistEntry(entry_id, first_name, last_name, email, phone, cohort_preference, notes)
        self._waitlist[entry_id] = entry
        self._update_waitlist_positions()
        return entry

    def _update_waitlist_positions(self) -> None:
        waiting_entries = [e for e in self._waitlist.values() if e.status == "waiting"]
        waiting_entries.sort(key=lambda e: e.applied_at)
        for i, entry in enumerate(waiting_entries, start=1):
            entry.position = i

    def get_waitlist(self, session_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        entries = self._waitlist.values()
        if status_filter:
            entries = [e for e in entries if e.status == status_filter]
        return [e.to_dict() for e in entries]

    def update_waitlist_entry_status(
        self, session_id: str, entry_id: int, new_status: str
    ) -> Dict[str, Any]:
        self._require_organizer(session_id)
        entry = self._waitlist.get(entry_id)
        if entry is None:
            raise NotFoundError(f"Waitlist entry with ID {entry_id} not found.")
        if new_status == "accepted":
            entry.accept()
        elif new_status == "rejected":
            entry.reject()
        elif new_status == "deferred":
            entry.defer()
        else:
            raise ValidationError(f"Invalid status '{new_status}'. Must be accepted, rejected, or deferred.")
        self._update_waitlist_positions()
        return entry.to_dict()

    def add_cohort(self, session_id: str, cohort_name: str) -> List[str]:
        self._require_organizer(session_id)
        if cohort_name not in self._cohorts:
            self._cohorts.append(cohort_name)
        return list(self._cohorts)

    def list_cohorts(self, session_id: str) -> List[str]:
        self._require_organizer(session_id)
        return list(self._cohorts)

    def get_admin_dashboard(self, session_id: str) -> Dict[str, Any]:
        self._require_organizer(session_id)
        total_students = len(self._students)
        enrolled_students = sum(1 for s in self._students.values() if s.enrollment_status == "enrolled")
        graduated_students = sum(1 for s in self._students.values() if s.enrollment_status == "graduated")
        employed_graduates = sum(
            1 for s in self._students.values()
            if s.enrollment_status == "graduated" and s.outcomes.get("employed", False)
        )
        employment_rate = (
            (employed_graduates / graduated_students * 100) if graduated_students > 0 else 0.0
        )
        active_volunteers = sum(1 for v in self._volunteers.values() if v.is_active)
        waitlist_count = sum(1 for e in self._waitlist.values() if e.status == "waiting")
        avg_progress = 0.0
        if total_students > 0:
            avg_progress = sum(s.get_overall_progress() for s in self._students.values()) / total_students
        avg_attendance = 0.0
        students_with_attendance = [s for s in self._students.values() if s.attendance_records]
        if students_with_attendance:
            avg_attendance = (
                sum(s.get_attendance_rate() for s in students_with_attendance)
                / len(students_with_attendance)
            )
        cohort_breakdown: Dict[str, int] = {}
        for student in self._students.values():
            cohort = student.cohort or "Unassigned"
            cohort_breakdown[cohort] = cohort_breakdown.get(cohort, 0) + 1
        return {
            "total_students": total_students,
            "enrolled_students": enrolled_students,
            "graduated_students": graduated_students,
            "employed_graduates": employed_graduates,
            "employment_rate": employment_rate,
            "active_volunteers": active_volunteers,
            "waitlist_count": waitlist_count,
            "average_progress": avg_progress,
            "average_attendance": avg_attendance,
            "cohort_breakdown": cohort_breakdown,
            "total_cohorts": len(self._cohorts),
        }

    def get_outcomes_report(self, session_id: str) -> Dict[str, Any]:
        self._require_organizer(session_id)
        graduates = [s for s in self._students.values() if s.enrollment_status == "graduated"]
        employed = [s for s in graduates if s.outcomes.get("employed", False)]
        salaries = [
            s.outcomes["salary"]
            for s in employed
            if s.outcomes.get("salary") is not None
        ]
        avg_salary = sum(salaries) / len(salaries) if salaries else None
        employer_distribution: Dict[str, int] = {}
        for s in employed:
            employer = s.outcomes.get("employer", "Unknown")
            employer_distribution[employer] = employer_distribution.get(employer, 0) + 1
        return {
            "total_graduates": len(graduates),
            "employed_count": len(employed),
            "employment_rate": (len(employed) / len(graduates) * 100) if graduates else 0.0,
            "average_salary": avg_salary,
            "employer_distribution": employer_distribution,
            "employed_students": [
                {
                    "student_id": s.user_id,
                    "name": s.full_name,
                    "employer": s.outcomes.get("employer"),
                    "job_title": s.outcomes.get("job_title"),
                    "salary": s.outcomes.get("salary"),
                }
                for s in employed
            ],
        }

    def search_students(
        self,
        session_id: str,
        query: str = "",
        cohort: Optional[str] = None,
        enrollment_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._require_organizer(session_id)
        results = list(self._students.values())
        if query:
            query_lower = query.lower()
            results = [
                s for s in results
                if query_lower in s.full_name.lower()
                or query_lower in s.username.lower()
                or query_lower in s.email.lower()
            ]
        if cohort:
            results = [s for s in results if s.cohort == cohort]
        if enrollment_status:
            results = [s for s in results if s.enrollment_status == enrollment_status]
        return [s.to_dict() for s in results]

    def delete_student(self, session_id: str, student_id: int) -> bool:
        self._require_admin(session_id)
        student = self._students.get(student_id)
        if student is None:
            raise NotFoundError(f"Student with ID {student_id} not found.")
        del self._students[student_id]
        del self._users[student_id]
        if student.username in self._username_index:
            del self._username_index[student.username]
        if student.email in self._email_index:
            del self._email_index[student.email]
        return True

    def deactivate_user(self, session_id: str, user_id: int) -> Dict[str, Any]:
        self._require_admin(session_id)
        user = self._users.get(user_id)
        if user is None:
            raise NotFoundError(f"User with ID {user_id} not found.")
        user.deactivate()
        return user.to_dict()

    def activate_user(self, session_id: str, user_id: int) -> Dict[str, Any]:
        self._require_admin(session_id)
        user = self._users.get(user_id)
        if user is None:
            raise NotFoundError(f"User with ID {user_id} not found.")
        user.activate()
        return user.to_dict()

    def list_organizers(self, session_id: str) -> List[Dict[str, Any]]:
        self._require_admin(session_id)
        return [o.to_dict() for o in self._organizers.values()]

    def get_system_stats(self, session_id: str) -> Dict[str, Any]:
        self._require_admin(session_id)
        return {
            "total_users": len(self._users),
            "total_students": len(self._students),
            "total_organizers": len(self._organizers),
            "total_volunteers": len(self._volunteers),
            "active_volunteers": sum(1 for v in self._volunteers.values() if v.is_active),
            "total_waitlist_entries": len(self._waitlist),
            "waiting_count": sum(1 for e in self._waitlist.values() if e.status == "waiting"),
            "total_cohorts": len(self._cohorts),
            "cohorts": self._cohorts,
        }


def main():
    sms = StudentManagementSystem()

    admin = sms.register_organizer(
        username="admin",
        email="admin@freecodecamp.org",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
        organization="freeCodeSchool",
        is_admin=True,
    )
    print(f"Created admin: {admin}")

    organizer = sms.register_organizer(
        username="organizer1",
        email="organizer1@freecodecamp.org",
        password="orgpass123",
        first_name="Jane",
        last_name="Doe",
        organization="freeCodeSchool",
        is_admin=False,
    )
    print(f"Created organizer: {organizer}")

    student1 = sms.register_student(
        username="student1",
        email="student1@example.com",
        password="studentpass123",
        first_name="John",
        last_name="Smith",
        cohort="2024-Spring",
        enrollment_status="enrolled",
    )
    print(f"Created student: {student1}")

    student2 = sms.register_student(
        username="student2",
        email="student2@example.com",
        password="studentpass456",
        first_name="Alice",
        last_name="Johnson",
        cohort="2024-Spring",
        enrollment_status="enrolled",
    )
    print(f"Created student: {student2}")

    admin_session = sms.login("admin", "adminpass123")
    print(f"\nAdmin logged in, session: {admin_session.session_id[:16]}...")

    org_session = sms.login("organizer1", "orgpass123")
    print(f"Organizer logged in, session: {org_session.session_id[:16]}...")

    student_session = sms.login("student1", "studentpass123")
    print(f"Student logged in, session: {student_session.session_id[:16]}...")

    sms.enroll_student_in_course(org_session.session_id, student1.user_id, "Python Basics")
    progress = student1.get_course_progress("Python Basics")
    progress.total_lessons = 10
    sms.update_course_progress(
        student_session.session_id, student1.user_id, "Python Basics", "Lesson 1: Variables"
    )
    sms.update_course_progress(
        student_session.session_id, student1.user_id, "Python Basics", "Lesson 2: Functions"
    )
    print(f"\nStudent1 Python Basics progress: {student1.get_course_progress('Python Basics').progress_percentage:.1f}%")

    sms.update_student_profile(
        student_session.session_id,
        student1.user_id,
        {
            "bio": "Aspiring software developer",
            "github_username": "johnsmith",
            "skills": ["Python", "JavaScript"],
        },
    )
    print(f"Updated student1 profile")

    sms.record_student_attendance(
        org_session.session_id, student1.user_id, date.today(), "present"
    )
    sms.record_student_attendance(
        org_session.session_id, student1.user_id, date.today(), "present"
    )
    print(f"Student1 attendance rate: {student1.get_attendance_rate():.1f}%")

    volunteer = sms.add_volunteer(
        org_session.session_id,
        first_name="Bob",
        last_name="Mentor",
        email="bob@mentor.com",
        skills=["Python", "Web Development"],
        availability="Weekends",
        role="mentor",
    )
    print(f"\nAdded volunteer: {volunteer}")

    sms.log_volunteer_session(
        org_session.session_id, volunteer.volunteer_id, date.today(), 2.5, "Python tutoring"
    )
    print(f"Volunteer total hours: {volunteer.get_total_hours()}")

    waitlist_entry = sms.add_to_waitlist(
        first_name="Charlie",
        last_name="Brown",
        email="charlie@example.com",
        phone="555-1234",
        cohort_preference="2024-Fall",
    )
    print(f"\nAdded to waitlist: {waitlist_entry}")

    waitlist_entry2 = sms.add_to_waitlist(
        first_name="Diana",
        last_name="Prince",
        email="diana@example.com",
        cohort_preference="2024-Fall",
    )
    print(f"Added to waitlist: {waitlist_entry2}")

    sms.update_waitlist_entry_status(org_session.session_id, waitlist_entry.entry_id, "accepted")
    print(f"Waitlist entry status: {waitlist_entry.status}")

    sms.update_student_enrollment_status(
        org_session.session_id, student2.user_id, "graduated"
    )
    sms.update_student_outcomes(
        org_session.session_id,
        student2.user_id,
        employed=True,
        employer="Tech Corp",
        job_title="Junior Developer",
        salary=65000.0,
        employment_date=date.today(),
    )
    print(f"\nStudent2 outcomes: {student2.outcomes}")

    dashboard = sms.get_admin_dashboard(admin_session.session_id)
    print(f"\nAdmin Dashboard:")
    for key, value in dashboard.items():
        print(f"  {key}: {value}")

    outcomes_report = sms.get_outcomes_report(org_session.session_id)
    print(f"\nOutcomes Report:")
    print(f"  Employment rate: {outcomes_report['employment_rate']:.1f}%")
    print(f"  Average salary: {outcomes_report['average_salary']}")

    profile_data = sms.get_student_profile(student_session.session_id, student1.user_id)
    print(f"\nStudent1 can view own profile: {profile_data['username']}")

    try:
        sms.get_student_profile(student_session.session_id, student2.user_id)
    except PermissionError as e:
        print(f"Permission denied (expected): {e}")

    system_stats = sms.get_system_stats(admin_session.session_id)
    print(f"\nSystem Stats:")
    for key, value in system_stats.items():
        print(f"  {key}: {value}")

    sms.logout(student_session.session_id)
    print(f"\nStudent logged out")

    try:
        sms.get_student_profile(student_session.session_id, student1.user_id)
    except AuthenticationError as e:
        print(f"Auth error after logout (expected): {e}")


if __name__ == "__main__":
    main()