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


class User:
    def __init__(self, user_id: int, username: str, email: str, password: str, role: str = "student"):
        if not username or not username.strip():
            raise ValidationError("Username cannot be empty")
        if not self._validate_email(email):
            raise ValidationError(f"Invalid email address: {email}")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")
        if role not in ("student", "organizer", "admin"):
            raise ValidationError(f"Invalid role: {role}")

        self._user_id = user_id
        self._username = username.strip()
        self._email = email.strip().lower()
        self._password_hash = self._hash_password(password)
        self._role = role
        self._is_active = True
        self._created_at = datetime.now()
        self._last_login: Optional[datetime] = None
        self._session_token: Optional[str] = None

    @staticmethod
    def _validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return bool(re.match(pattern, email))

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = "freeCodeSchool_salt"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self._password_hash == self._hash_password(password)

    def login(self, password: str) -> str:
        if not self._is_active:
            raise AuthenticationError("Account is deactivated")
        if not self.verify_password(password):
            raise AuthenticationError("Invalid credentials")
        self._last_login = datetime.now()
        self._session_token = secrets.token_hex(32)
        return self._session_token

    def logout(self):
        self._session_token = None

    def is_authenticated(self, token: str) -> bool:
        return self._session_token is not None and self._session_token == token

    def change_password(self, old_password: str, new_password: str):
        if not self.verify_password(old_password):
            raise AuthenticationError("Current password is incorrect")
        if len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters")
        self._password_hash = self._hash_password(new_password)

    def is_admin(self) -> bool:
        return self._role in ("admin", "organizer")

    def is_organizer(self) -> bool:
        return self._role in ("organizer", "admin")

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
        self._session_token = None

    def activate(self):
        self._is_active = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "email": self._email,
            "role": self._role,
            "is_active": self._is_active,
            "created_at": self._created_at.isoformat(),
            "last_login": self._last_login.isoformat() if self._last_login else None,
        }

    def __repr__(self) -> str:
        return f"User(id={self._user_id}, username={self._username}, role={self._role})"


class ProgressRecord:
    def __init__(self, record_id: int, student_id: int, course: str, module: str,
                 status: str, score: Optional[float] = None, notes: str = ""):
        valid_statuses = ("not_started", "in_progress", "completed", "failed")
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        if score is not None and not (0.0 <= score <= 100.0):
            raise ValidationError("Score must be between 0 and 100")

        self._record_id = record_id
        self._student_id = student_id
        self._course = course
        self._module = module
        self._status = status
        self._score = score
        self._notes = notes
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    def update(self, status: Optional[str] = None, score: Optional[float] = None, notes: Optional[str] = None):
        valid_statuses = ("not_started", "in_progress", "completed", "failed")
        if status is not None:
            if status not in valid_statuses:
                raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
            self._status = status
        if score is not None:
            if not (0.0 <= score <= 100.0):
                raise ValidationError("Score must be between 0 and 100")
            self._score = score
        if notes is not None:
            self._notes = notes
        self._updated_at = datetime.now()

    @property
    def record_id(self) -> int:
        return self._record_id

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def course(self) -> str:
        return self._course

    @property
    def module(self) -> str:
        return self._module

    @property
    def status(self) -> str:
        return self._status

    @property
    def score(self) -> Optional[float]:
        return self._score

    @property
    def notes(self) -> str:
        return self._notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self._record_id,
            "student_id": self._student_id,
            "course": self._course,
            "module": self._module,
            "status": self._status,
            "score": self._score,
            "notes": self._notes,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"ProgressRecord(id={self._record_id}, course={self._course}, module={self._module}, status={self._status})"


class StudentProfile:
    def __init__(self, profile_id: int, user_id: int, first_name: str, last_name: str,
                 date_of_birth: Optional[date] = None, phone: str = "",
                 bio: str = "", cohort: str = "", enrollment_date: Optional[date] = None,
                 graduation_date: Optional[date] = None, outcome: str = "enrolled"):
        valid_outcomes = ("enrolled", "graduated", "dropped", "waitlisted", "pending")
        if outcome not in valid_outcomes:
            raise ValidationError(f"Invalid outcome. Must be one of: {valid_outcomes}")

        self._profile_id = profile_id
        self._user_id = user_id
        self._first_name = first_name.strip()
        self._last_name = last_name.strip()
        self._date_of_birth = date_of_birth
        self._phone = phone.strip()
        self._bio = bio.strip()
        self._cohort = cohort.strip()
        self._enrollment_date = enrollment_date or date.today()
        self._graduation_date = graduation_date
        self._outcome = outcome
        self._progress_records: List[ProgressRecord] = []
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    def update(self, first_name: Optional[str] = None, last_name: Optional[str] = None,
               date_of_birth: Optional[date] = None, phone: Optional[str] = None,
               bio: Optional[str] = None, cohort: Optional[str] = None,
               graduation_date: Optional[date] = None, outcome: Optional[str] = None):
        valid_outcomes = ("enrolled", "graduated", "dropped", "waitlisted", "pending")
        if first_name is not None:
            self._first_name = first_name.strip()
        if last_name is not None:
            self._last_name = last_name.strip()
        if date_of_birth is not None:
            self._date_of_birth = date_of_birth
        if phone is not None:
            self._phone = phone.strip()
        if bio is not None:
            self._bio = bio.strip()
        if cohort is not None:
            self._cohort = cohort.strip()
        if graduation_date is not None:
            self._graduation_date = graduation_date
        if outcome is not None:
            if outcome not in valid_outcomes:
                raise ValidationError(f"Invalid outcome. Must be one of: {valid_outcomes}")
            self._outcome = outcome
        self._updated_at = datetime.now()

    def add_progress_record(self, record: ProgressRecord):
        if record.student_id != self._user_id:
            raise ValidationError("Progress record does not belong to this student")
        self._progress_records.append(record)
        self._updated_at = datetime.now()

    def get_progress_records(self) -> List[ProgressRecord]:
        return list(self._progress_records)

    def get_progress_by_course(self, course: str) -> List[ProgressRecord]:
        return [r for r in self._progress_records if r.course == course]

    def get_completion_rate(self) -> float:
        if not self._progress_records:
            return 0.0
        completed = sum(1 for r in self._progress_records if r.status == "completed")
        return (completed / len(self._progress_records)) * 100.0

    def get_average_score(self) -> Optional[float]:
        scores = [r.score for r in self._progress_records if r.score is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)

    @property
    def profile_id(self) -> int:
        return self._profile_id

    @property
    def user_id(self) -> int:
        return self._user_id

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
    def date_of_birth(self) -> Optional[date]:
        return self._date_of_birth

    @property
    def phone(self) -> str:
        return self._phone

    @property
    def bio(self) -> str:
        return self._bio

    @property
    def cohort(self) -> str:
        return self._cohort

    @property
    def enrollment_date(self) -> date:
        return self._enrollment_date

    @property
    def graduation_date(self) -> Optional[date]:
        return self._graduation_date

    @property
    def outcome(self) -> str:
        return self._outcome

    def to_dict(self, include_progress: bool = False) -> Dict[str, Any]:
        data = {
            "profile_id": self._profile_id,
            "user_id": self._user_id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "full_name": self.full_name,
            "date_of_birth": self._date_of_birth.isoformat() if self._date_of_birth else None,
            "phone": self._phone,
            "bio": self._bio,
            "cohort": self._cohort,
            "enrollment_date": self._enrollment_date.isoformat(),
            "graduation_date": self._graduation_date.isoformat() if self._graduation_date else None,
            "outcome": self._outcome,
            "completion_rate": self.get_completion_rate(),
            "average_score": self.get_average_score(),
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }
        if include_progress:
            data["progress_records"] = [r.to_dict() for r in self._progress_records]
        return data

    def __repr__(self) -> str:
        return f"StudentProfile(id={self._profile_id}, name={self.full_name}, cohort={self._cohort})"


class WaitlistEntry:
    def __init__(self, entry_id: int, first_name: str, last_name: str, email: str,
                 phone: str = "", reason: str = "", cohort_interest: str = ""):
        if not User._validate_email(email):
            raise ValidationError(f"Invalid email address: {email}")

        self._entry_id = entry_id
        self._first_name = first_name.strip()
        self._last_name = last_name.strip()
        self._email = email.strip().lower()
        self._phone = phone.strip()
        self._reason = reason.strip()
        self._cohort_interest = cohort_interest.strip()
        self._status = "pending"
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._notes = ""

    def approve(self, notes: str = ""):
        self._status = "approved"
        self._notes = notes
        self._updated_at = datetime.now()

    def reject(self, notes: str = ""):
        self._status = "rejected"
        self._notes = notes
        self._updated_at = datetime.now()

    def update_notes(self, notes: str):
        self._notes = notes
        self._updated_at = datetime.now()

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
    def status(self) -> str:
        return self._status

    @property
    def notes(self) -> str:
        return self._notes

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self._entry_id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "full_name": self.full_name,
            "email": self._email,
            "phone": self._phone,
            "reason": self._reason,
            "cohort_interest": self._cohort_interest,
            "status": self._status,
            "notes": self._notes,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"WaitlistEntry(id={self._entry_id}, name={self.full_name}, status={self._status})"


class Volunteer:
    def __init__(self, volunteer_id: int, first_name: str, last_name: str, email: str,
                 phone: str = "", skills: Optional[List[str]] = None,
                 availability: str = "", role: str = "general"):
        if not User._validate_email(email):
            raise ValidationError(f"Invalid email address: {email}")

        self._volunteer_id = volunteer_id
        self._first_name = first_name.strip()
        self._last_name = last_name.strip()
        self._email = email.strip().lower()
        self._phone = phone.strip()
        self._skills = skills or []
        self._availability = availability.strip()
        self._role = role.strip()
        self._is_active = True
        self._hours_logged = 0.0
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._activity_log: List[Dict[str, Any]] = []

    def log_hours(self, hours: float, activity: str, log_date: Optional[date] = None):
        if hours <= 0:
            raise ValidationError("Hours must be positive")
        self._hours_logged += hours
        self._activity_log.append({
            "hours": hours,
            "activity": activity,
            "date": (log_date or date.today()).isoformat(),
            "logged_at": datetime.now().isoformat(),
        })
        self._updated_at = datetime.now()

    def update(self, first_name: Optional[str] = None, last_name: Optional[str] = None,
               phone: Optional[str] = None, skills: Optional[List[str]] = None,
               availability: Optional[str] = None, role: Optional[str] = None):
        if first_name is not None:
            self._first_name = first_name.strip()
        if last_name is not None:
            self._last_name = last_name.strip()
        if phone is not None:
            self._phone = phone.strip()
        if skills is not None:
            self._skills = skills
        if availability is not None:
            self._availability = availability.strip()
        if role is not None:
            self._role = role.strip()
        self._updated_at = datetime.now()

    def deactivate(self):
        self._is_active = False
        self._updated_at = datetime.now()

    def activate(self):
        self._is_active = True
        self._updated_at = datetime.now()

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
    def phone(self) -> str:
        return self._phone

    @property
    def skills(self) -> List[str]:
        return list(self._skills)

    @property
    def availability(self) -> str:
        return self._availability

    @property
    def role(self) -> str:
        return self._role

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def hours_logged(self) -> float:
        return self._hours_logged

    @property
    def activity_log(self) -> List[Dict[str, Any]]:
        return list(self._activity_log)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volunteer_id": self._volunteer_id,
            "first_name": self._first_name,
            "last_name": self._last_name,
            "full_name": self.full_name,
            "email": self._email,
            "phone": self._phone,
            "skills": self._skills,
            "availability": self._availability,
            "role": self._role,
            "is_active": self._is_active,
            "hours_logged": self._hours_logged,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"Volunteer(id={self._volunteer_id}, name={self.full_name}, role={self._role})"


class StudentManagementSystem:
    def __init__(self):
        self._users: Dict[int, User] = {}
        self._profiles: Dict[int, StudentProfile] = {}
        self._waitlist: Dict[int, WaitlistEntry] = {}
        self._volunteers: Dict[int, Volunteer] = {}
        self._progress_records: Dict[int, ProgressRecord] = {}
        self._sessions: Dict[str, int] = {}

        self._user_id_counter = 1
        self._profile_id_counter = 1
        self._waitlist_id_counter = 1
        self._volunteer_id_counter = 1
        self._progress_id_counter = 1

        self._create_default_admin()

    def _create_default_admin(self):
        admin = User(
            user_id=self._user_id_counter,
            username="admin",
            email="admin@freecodeschool.org",
            password="admin123",
            role="admin"
        )
        self._users[self._user_id_counter] = admin
        self._user_id_counter += 1

    def _get_next_user_id(self) -> int:
        uid = self._user_id_counter
        self._user_id_counter += 1
        return uid

    def _get_next_profile_id(self) -> int:
        pid = self._profile_id_counter
        self._profile_id_counter += 1
        return pid

    def _get_next_waitlist_id(self) -> int:
        wid = self._waitlist_id_counter
        self._waitlist_id_counter += 1
        return wid

    def _get_next_volunteer_id(self) -> int:
        vid = self._volunteer_id_counter
        self._volunteer_id_counter += 1
        return vid

    def _get_next_progress_id(self) -> int:
        rid = self._progress_id_counter
        self._progress_id_counter += 1
        return rid

    def _validate_session(self, token: str) -> User:
        user_id = self._sessions.get(token)
        if user_id is None:
            raise AuthenticationError("Invalid or expired session token")
        user = self._users.get(user_id)
        if user is None or not user.is_authenticated(token):
            raise AuthenticationError("Invalid or expired session token")
        return user

    def _require_admin(self, token: str) -> User:
        user = self._validate_session(token)
        if not user.is_admin():
            raise PermissionError("Admin or organizer access required")
        return user

    def register_user(self, username: str, email: str, password: str,
                      role: str = "student") -> Dict[str, Any]:
        for user in self._users.values():
            if user.username == username.strip():
                raise ValidationError(f"Username '{username}' is already taken")
            if user.email == email.strip().lower():
                raise ValidationError(f"Email '{email}' is already registered")

        uid = self._get_next_user_id()
        user = User(user_id=uid, username=username, email=email, password=password, role=role)
        self._users[uid] = user
        return user.to_dict()

    def login(self, username: str, password: str) -> Dict[str, Any]:
        for user in self._users.values():
            if user.username == username.strip():
                token = user.login(password)
                self._sessions[token] = user.user_id
                return {
                    "token": token,
                    "user": user.to_dict(),
                    "message": "Login successful"
                }
        raise AuthenticationError("Invalid credentials")

    def logout(self, token: str):
        user = self._validate_session(token)
        if token in self._sessions:
            del self._sessions[token]
        user.logout()

    def get_current_user(self, token: str) -> Dict[str, Any]:
        user = self._validate_session(token)
        return user.to_dict()

    def change_password(self, token: str, old_password: str, new_password: str):
        user = self._validate_session(token)
        user.change_password(old_password, new_password)

    def create_student_profile(self, token: str, first_name: str, last_name: str,
                               date_of_birth: Optional[date] = None, phone: str = "",
                               bio: str = "", cohort: str = "",
                               enrollment_date: Optional[date] = None,
                               outcome: str = "enrolled") -> Dict[str, Any]:
        user = self._validate_session(token)

        if user.role != "student" and not user.is_admin():
            raise PermissionError("Only students or admins can create student profiles")

        for profile in self._profiles.values():
            if profile.user_id == user.user_id:
                raise ValidationError("Student profile already exists for this user")

        pid = self._get_next_profile_id()
        profile = StudentProfile(
            profile_id=pid,
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            phone=phone,
            bio=bio,
            cohort=cohort,
            enrollment_date=enrollment_date,
            outcome=outcome
        )
        self._profiles[pid] = profile
        return profile.to_dict()

    def create_student_profile_for_user(self, admin_token: str, user_id: int,
                                        first_name: str, last_name: str,
                                        date_of_birth: Optional[date] = None,
                                        phone: str = "", bio: str = "",
                                        cohort: str = "",
                                        enrollment_date: Optional[date] = None,
                                        outcome: str = "enrolled") -> Dict[str, Any]:
        self._require_admin(admin_token)

        if user_id not in self._users:
            raise ValidationError(f"User with ID {user_id} not found")

        for profile in self._profiles.values():
            if profile.user_id == user_id:
                raise ValidationError("Student profile already exists for this user")

        pid = self._get_next_profile_id()
        profile = StudentProfile(
            profile_id=pid,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            phone=phone,
            bio=bio,
            cohort=cohort,
            enrollment_date=enrollment_date,
            outcome=outcome
        )
        self._profiles[pid] = profile
        return profile.to_dict()

    def get_my_profile(self, token: str) -> Dict[str, Any]:
        user = self._validate_session(token)
        for profile in self._profiles.values():
            if profile.user_id == user.user_id:
                return profile.to_dict(include_progress=True)
        raise ValidationError("No profile found for current user")

    def get_student_profile(self, token: str, profile_id: int) -> Dict[str, Any]:
        user = self._validate_session(token)
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValidationError(f"Profile with ID {profile_id} not found")

        if profile.user_id != user.user_id and not user.is_admin():
            raise PermissionError("You do not have permission to view this profile")

        return profile.to_dict(include_progress=True)

    def update_my_profile(self, token: str, **kwargs) -> Dict[str, Any]:
        user = self._validate_session(token)
        for profile in self._profiles.values():
            if profile.user_id == user.user_id:
                allowed_fields = {"first_name", "last_name", "date_of_birth",
                                  "phone", "bio", "cohort", "graduation_date"}
                update_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}
                profile.update(**update_kwargs)
                return profile.to_dict(include_progress=True)
        raise ValidationError("No profile found for current user")

    def update_student_profile(self, admin_token: str, profile_id: int, **kwargs) -> Dict[str, Any]:
        self._require_admin(admin_token)
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValidationError(f"Profile with ID {profile_id} not found")
        profile.update(**kwargs)
        return profile.to_dict(include_progress=True)

    def get_all_students(self, admin_token: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [p.to_dict(include_progress=True) for p in self._profiles.values()]

    def get_students_by_cohort(self, admin_token: str, cohort: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [p.to_dict(include_progress=True) for p in self._profiles.values()
                if p.cohort == cohort]

    def get_students_by_outcome(self, admin_token: str, outcome: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [p.to_dict(include_progress=True) for p in self._profiles.values()
                if p.outcome == outcome]

    def add_progress_record(self, admin_token: str, student_id: int, course: str,
                            module: str, status: str, score: Optional[float] = None,
                            notes: str = "") -> Dict[str, Any]:
        self._require_admin(admin_token)

        profile = None
        for p in self._profiles.values():
            if p.user_id == student_id:
                profile = p
                break

        if profile is None:
            raise ValidationError(f"No student profile found for user ID {student_id}")

        rid = self._get_next_progress_id()
        record = ProgressRecord(
            record_id=rid,
            student_id=student_id,
            course=course,
            module=module,
            status=status,
            score=score,
            notes=notes
        )
        self._progress_records[rid] = record
        profile.add_progress_record(record)
        return record.to_dict()

    def update_progress_record(self, admin_token: str, record_id: int,
                               status: Optional[str] = None,
                               score: Optional[float] = None,
                               notes: Optional[str] = None) -> Dict[str, Any]:
        self._require_admin(admin_token)
        record = self._progress_records.get(record_id)
        if record is None:
            raise ValidationError(f"Progress record with ID {record_id} not found")
        record.update(status=status, score=score, notes=notes)
        return record.to_dict()

    def get_my_progress(self, token: str) -> List[Dict[str, Any]]:
        user = self._validate_session(token)
        for profile in self._profiles.values():
            if profile.user_id == user.user_id:
                return [r.to_dict() for r in profile.get_progress_records()]
        raise ValidationError("No profile found for current user")

    def add_to_waitlist(self, first_name: str, last_name: str, email: str,
                        phone: str = "", reason: str = "",
                        cohort_interest: str = "") -> Dict[str, Any]:
        for entry in self._waitlist.values():
            if entry.email == email.strip().lower():
                raise ValidationError(f"Email '{email}' is already on the waitlist")

        wid = self._get_next_waitlist_id()
        entry = WaitlistEntry(
            entry_id=wid,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            reason=reason,
            cohort_interest=cohort_interest
        )
        self._waitlist[wid] = entry
        return entry.to_dict()

    def get_waitlist(self, admin_token: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [e.to_dict() for e in self._waitlist.values()]

    def get_waitlist_entry(self, admin_token: str, entry_id: int) -> Dict[str, Any]:
        self._require_admin(admin_token)
        entry = self._waitlist.get(entry_id)
        if entry is None:
            raise ValidationError(f"Waitlist entry with ID {entry_id} not found")
        return entry.to_dict()

    def approve_waitlist_entry(self, admin_token: str, entry_id: int,
                               notes: str = "") -> Dict[str, Any]:
        self._require_admin(admin_token)
        entry = self._waitlist.get(entry_id)
        if entry is None:
            raise ValidationError(f"Waitlist entry with ID {entry_id} not found")
        entry.approve(notes=notes)
        return entry.to_dict()

    def reject_waitlist_entry(self, admin_token: str, entry_id: int,
                              notes: str = "") -> Dict[str, Any]:
        self._require_admin(admin_token)
        entry = self._waitlist.get(entry_id)
        if entry is None:
            raise ValidationError(f"Waitlist entry with ID {entry_id} not found")
        entry.reject(notes=notes)
        return entry.to_dict()

    def get_pending_waitlist(self, admin_token: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [e.to_dict() for e in self._waitlist.values() if e.status == "pending"]

    def add_volunteer(self, admin_token: str, first_name: str, last_name: str,
                      email: str, phone: str = "", skills: Optional[List[str]] = None,
                      availability: str = "", role: str = "general") -> Dict[str, Any]:
        self._require_admin(admin_token)

        for vol in self._volunteers.values():
            if vol.email == email.strip().lower():
                raise ValidationError(f"Volunteer with email '{email}' already exists")

        vid = self._get_next_volunteer_id()
        volunteer = Volunteer(
            volunteer_id=vid,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            skills=skills,
            availability=availability,
            role=role
        )
        self._volunteers[vid] = volunteer
        return volunteer.to_dict()

    def get_all_volunteers(self, admin_token: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [v.to_dict() for v in self._volunteers.values()]

    def get_active_volunteers(self, admin_token: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [v.to_dict() for v in self._volunteers.values() if v.is_active]

    def get_volunteer(self, admin_token: str, volunteer_id: int) -> Dict[str, Any]:
        self._require_admin(admin_token)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise ValidationError(f"Volunteer with ID {volunteer_id} not found")
        return volunteer.to_dict()

    def update_volunteer(self, admin_token: str, volunteer_id: int, **kwargs) -> Dict[str, Any]:
        self._require_admin(admin_token)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise ValidationError(f"Volunteer with ID {volunteer_id} not found")
        volunteer.update(**kwargs)
        return volunteer.to_dict()

    def log_volunteer_hours(self, admin_token: str, volunteer_id: int, hours: float,
                            activity: str, log_date: Optional[date] = None) -> Dict[str, Any]:
        self._require_admin(admin_token)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise ValidationError(f"Volunteer with ID {volunteer_id} not found")
        volunteer.log_hours(hours=hours, activity=activity, log_date=log_date)
        return volunteer.to_dict()

    def deactivate_volunteer(self, admin_token: str, volunteer_id: int) -> Dict[str, Any]:
        self._require_admin(admin_token)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise ValidationError(f"Volunteer with ID {volunteer_id} not found")
        volunteer.deactivate()
        return volunteer.to_dict()

    def activate_volunteer(self, admin_token: str, volunteer_id: int) -> Dict[str, Any]:
        self._require_admin(admin_token)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise ValidationError(f"Volunteer with ID {volunteer_id} not found")
        volunteer.activate()
        return volunteer.to_dict()

    def get_dashboard(self, admin_token: str) -> Dict[str, Any]:
        self._require_admin(admin_token)

        total_students = len(self._profiles)
        outcomes: Dict[str, int] = {}
        cohorts: Dict[str, int] = {}
        total_completion = 0.0
        total_scores = []

        for profile in self._profiles.values():
            outcome = profile.outcome
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

            cohort = profile.cohort or "Unknown"
            cohorts[cohort] = cohorts.get(cohort, 0) + 1

            total_completion += profile.get_completion_rate()
            avg_score = profile.get_average_score()
            if avg_score is not None:
                total_scores.append(avg_score)

        avg_completion = total_completion / total_students if total_students > 0 else 0.0
        overall_avg_score = sum(total_scores) / len(total_scores) if total_scores else None

        total_volunteers = len(self._volunteers)
        active_volunteers = sum(1 for v in self._volunteers.values() if v.is_active)
        total_volunteer_hours = sum(v.hours_logged for v in self._volunteers.values())

        pending_waitlist = sum(1 for e in self._waitlist.values() if e.status == "pending")
        approved_waitlist = sum(1 for e in self._waitlist.values() if e.status == "approved")
        rejected_waitlist = sum(1 for e in self._waitlist.values() if e.status == "rejected")

        total_users = len(self._users)

        return {
            "students": {
                "total": total_students,
                "by_outcome": outcomes,
                "by_cohort": cohorts,
                "average_completion_rate": round(avg_completion, 2),
                "overall_average_score": round(overall_avg_score, 2) if overall_avg_score is not None else None,
            },
            "volunteers": {
                "total": total_volunteers,
                "active": active_volunteers,
                "inactive": total_volunteers - active_volunteers,
                "total_hours_logged": total_volunteer_hours,
            },
            "waitlist": {
                "total": len(self._waitlist),
                "pending": pending_waitlist,
                "approved": approved_waitlist,
                "rejected": rejected_waitlist,
            },
            "users": {
                "total": total_users,
            },
            "generated_at": datetime.now().isoformat(),
        }

    def get_all_users(self, admin_token: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        return [u.to_dict() for u in self._users.values()]

    def deactivate_user(self, admin_token: str, user_id: int) -> Dict[str, Any]:
        self._require_admin(admin_token)
        user = self._users.get(user_id)
        if user is None:
            raise ValidationError(f"User with ID {user_id} not found")
        user.deactivate()
        return user.to_dict()

    def activate_user(self, admin_token: str, user_id: int) -> Dict[str, Any]:
        self._require_admin(admin_token)
        user = self._users.get(user_id)
        if user is None:
            raise ValidationError(f"User with ID {user_id} not found")
        user.activate()
        return user.to_dict()

    def search_students(self, admin_token: str, query: str) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        query_lower = query.lower().strip()
        results = []
        for profile in self._profiles.values():
            if (query_lower in profile.full_name.lower() or
                    query_lower in profile.cohort.lower() or
                    query_lower in profile.outcome.lower()):
                results.append(profile.to_dict(include_progress=True))
        return results

    def get_volunteer_activity_log(self, admin_token: str, volunteer_id: int) -> List[Dict[str, Any]]:
        self._require_admin(admin_token)
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer is None:
            raise ValidationError(f"Volunteer with ID {volunteer_id} not found")
        return volunteer.activity_log

    def __repr__(self) -> str:
        return (f"StudentManagementSystem("
                f"users={len(self._users)}, "
                f"profiles={len(self._profiles)}, "
                f"volunteers={len(self._volunteers)}, "
                f"waitlist={len(self._waitlist)})")


if __name__ == "__main__":
    sms = StudentManagementSystem()

    admin_result = sms.login("admin", "admin123")
    admin_token = admin_result["token"]
    print("Admin logged in:", admin_result["user"]["username"])

    student_data = sms.register_user("john_doe", "john@example.com", "password123", role="student")
    print("Registered student:", student_data["username"])

    student_login = sms.login("john_doe", "password123")
    student_token = student_login["token"]
    print("Student logged in:", student_login["user"]["username"])

    profile = sms.create_student_profile(
        token=student_token,
        first_name="John",
        last_name="Doe",
        phone="555-1234",
        bio="Aspiring developer",
        cohort="2024-Spring",
        outcome="enrolled"
    )
    print("Created profile:", profile["full_name"])

    my_profile = sms.get_my_profile(student_token)
    print("My profile:", my_profile["full_name"], "- Cohort:", my_profile["cohort"])

    progress = sms.add_progress_record(
        admin_token=admin_token,
        student_id=student_data["user_id"],
        course="Python Basics",
        module="Variables and Types",
        status="completed",
        score=95.0,
        notes="Excellent work"
    )
    print("Added progress record:", progress["module"], "- Score:", progress["score"])

    waitlist_entry = sms.add_to_waitlist(
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        reason="Interested in web development",
        cohort_interest="2024-Fall"
    )
    print("Added to waitlist:", waitlist_entry["full_name"])

    approved = sms.approve_waitlist_entry(admin_token, waitlist_entry["entry_id"], notes="Great candidate")
    print("Waitlist status:", approved["status"])

    volunteer = sms.add_volunteer(
        admin_token=admin_token,
        first_name="Bob",
        last_name="Volunteer",
        email="bob@example.com",
        skills=["Python", "JavaScript"],
        availability="Weekends",
        role="mentor"
    )
    print("Added volunteer:", volunteer["full_name"])

    sms.log_volunteer_hours(admin_token, volunteer["volunteer_id"], 3.5, "Mentoring session")
    vol_data = sms.get_volunteer(admin_token, volunteer["volunteer_id"])
    print("Volunteer hours logged:", vol_data["hours_logged"])

    dashboard = sms.get_dashboard(admin_token)
    print("\n=== Dashboard ===")
    print("Total students:", dashboard["students"]["total"])
    print("Total volunteers:", dashboard["volunteers"]["total"])
    print("Waitlist pending:", dashboard["waitlist"]["pending"])
    print("Average completion rate:", dashboard["students"]["average_completion_rate"])

    sms.logout(student_token)
    print("\nStudent logged out successfully")

    print("\nSystem:", sms)