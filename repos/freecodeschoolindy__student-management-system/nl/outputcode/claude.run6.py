from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import hashlib
import uuid
import json


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@dataclass
class Permission:
    name: str
    description: str


class Role:
    STUDENT = "student"
    ORGANIZER = "organizer"
    ADMIN = "admin"
    VOLUNTEER = "volunteer"


@dataclass
class User:
    user_id: str
    username: str
    email: str
    password_hash: str
    role: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    def check_password(self, password: str) -> bool:
        return self.password_hash == hash_password(password)

    def set_password(self, password: str) -> None:
        self.password_hash = hash_password(password)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


@dataclass
class StudentProfile:
    profile_id: str
    user_id: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    bio: Optional[str] = None
    cohort: Optional[str] = None
    enrollment_date: Optional[datetime] = None
    graduation_date: Optional[datetime] = None
    status: str = "active"
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        data = {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "cohort": self.cohort,
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None,
            "graduation_date": self.graduation_date.isoformat() if self.graduation_date else None,
            "status": self.status,
            "github_username": self.github_username,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
        }
        if include_private:
            data.update({
                "phone": self.phone,
                "bio": self.bio,
                "notes": self.notes,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
            })
        return data

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ("profile_id", "user_id", "created_at"):
                setattr(self, key, value)
        self.updated_at = datetime.now()


@dataclass
class CourseProgress:
    progress_id: str
    student_id: str
    course_name: str
    module: str
    completion_percentage: float = 0.0
    grade: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    notes: str = ""

    def update_progress(self, percentage: float, grade: Optional[str] = None) -> None:
        if not 0.0 <= percentage <= 100.0:
            raise ValueError("Completion percentage must be between 0 and 100")
        self.completion_percentage = percentage
        if grade:
            self.grade = grade
        if percentage == 100.0 and not self.completed_at:
            self.completed_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "student_id": self.student_id,
            "course_name": self.course_name,
            "module": self.module,
            "completion_percentage": self.completion_percentage,
            "grade": self.grade,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
        }


@dataclass
class Outcome:
    outcome_id: str
    student_id: str
    outcome_type: str
    description: str
    employer: Optional[str] = None
    job_title: Optional[str] = None
    salary: Optional[float] = None
    outcome_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "student_id": self.student_id,
            "outcome_type": self.outcome_type,
            "description": self.description,
            "employer": self.employer,
            "job_title": self.job_title,
            "salary": self.salary,
            "outcome_date": self.outcome_date.isoformat() if self.outcome_date else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Volunteer:
    volunteer_id: str
    user_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    availability: str = ""
    status: str = "active"
    hours_contributed: float = 0.0
    joined_at: datetime = field(default_factory=datetime.now)
    notes: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def log_hours(self, hours: float) -> None:
        if hours < 0:
            raise ValueError("Hours cannot be negative")
        self.hours_contributed += hours

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volunteer_id": self.volunteer_id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "availability": self.availability,
            "status": self.status,
            "hours_contributed": self.hours_contributed,
            "joined_at": self.joined_at.isoformat(),
            "notes": self.notes,
        }


@dataclass
class WaitlistEntry:
    entry_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    cohort_interest: Optional[str] = None
    background: str = ""
    motivation: str = ""
    status: str = "pending"
    applied_at: datetime = field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    notes: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def approve(self, reviewer_id: str) -> None:
        self.status = "approved"
        self.reviewed_at = datetime.now()
        self.reviewed_by = reviewer_id

    def reject(self, reviewer_id: str, notes: str = "") -> None:
        self.status = "rejected"
        self.reviewed_at = datetime.now()
        self.reviewed_by = reviewer_id
        if notes:
            self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "cohort_interest": self.cohort_interest,
            "background": self.background,
            "motivation": self.motivation,
            "status": self.status,
            "applied_at": self.applied_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "notes": self.notes,
        }


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class Session:
    def __init__(self, user: User):
        self.session_id = str(uuid.uuid4())
        self.user = user
        self.created_at = datetime.now()
        self.is_valid = True

    def invalidate(self) -> None:
        self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user": self.user.to_dict(),
            "created_at": self.created_at.isoformat(),
            "is_valid": self.is_valid,
        }


class UserRepository:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}
        self._username_index: Dict[str, str] = {}

    def add(self, user: User) -> None:
        if user.email in self._email_index:
            raise ValidationError(f"Email {user.email} already exists")
        if user.username in self._username_index:
            raise ValidationError(f"Username {user.username} already exists")
        self._users[user.user_id] = user
        self._email_index[user.email] = user.user_id
        self._username_index[user.username] = user.user_id

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        user_id = self._email_index.get(email)
        if user_id:
            return self._users.get(user_id)
        return None

    def get_by_username(self, username: str) -> Optional[User]:
        user_id = self._username_index.get(username)
        if user_id:
            return self._users.get(user_id)
        return None

    def update(self, user: User) -> None:
        if user.user_id not in self._users:
            raise NotFoundError(f"User {user.user_id} not found")
        self._users[user.user_id] = user

    def delete(self, user_id: str) -> None:
        user = self._users.pop(user_id, None)
        if user:
            self._email_index.pop(user.email, None)
            self._username_index.pop(user.username, None)

    def list_all(self) -> List[User]:
        return list(self._users.values())

    def list_by_role(self, role: str) -> List[User]:
        return [u for u in self._users.values() if u.role == role]


class StudentProfileRepository:
    def __init__(self):
        self._profiles: Dict[str, StudentProfile] = {}
        self._user_index: Dict[str, str] = {}

    def add(self, profile: StudentProfile) -> None:
        self._profiles[profile.profile_id] = profile
        self._user_index[profile.user_id] = profile.profile_id

    def get_by_id(self, profile_id: str) -> Optional[StudentProfile]:
        return self._profiles.get(profile_id)

    def get_by_user_id(self, user_id: str) -> Optional[StudentProfile]:
        profile_id = self._user_index.get(user_id)
        if profile_id:
            return self._profiles.get(profile_id)
        return None

    def update(self, profile: StudentProfile) -> None:
        if profile.profile_id not in self._profiles:
            raise NotFoundError(f"Profile {profile.profile_id} not found")
        self._profiles[profile.profile_id] = profile

    def delete(self, profile_id: str) -> None:
        profile = self._profiles.pop(profile_id, None)
        if profile:
            self._user_index.pop(profile.user_id, None)

    def list_all(self) -> List[StudentProfile]:
        return list(self._profiles.values())

    def list_by_cohort(self, cohort: str) -> List[StudentProfile]:
        return [p for p in self._profiles.values() if p.cohort == cohort]

    def list_by_status(self, status: str) -> List[StudentProfile]:
        return [p for p in self._profiles.values() if p.status == status]


class CourseProgressRepository:
    def __init__(self):
        self._progress: Dict[str, CourseProgress] = {}
        self._student_index: Dict[str, List[str]] = {}

    def add(self, progress: CourseProgress) -> None:
        self._progress[progress.progress_id] = progress
        if progress.student_id not in self._student_index:
            self._student_index[progress.student_id] = []
        self._student_index[progress.student_id].append(progress.progress_id)

    def get_by_id(self, progress_id: str) -> Optional[CourseProgress]:
        return self._progress.get(progress_id)

    def get_by_student(self, student_id: str) -> List[CourseProgress]:
        ids = self._student_index.get(student_id, [])
        return [self._progress[pid] for pid in ids if pid in self._progress]

    def update(self, progress: CourseProgress) -> None:
        if progress.progress_id not in self._progress:
            raise NotFoundError(f"Progress {progress.progress_id} not found")
        self._progress[progress.progress_id] = progress

    def delete(self, progress_id: str) -> None:
        progress = self._progress.pop(progress_id, None)
        if progress:
            student_list = self._student_index.get(progress.student_id, [])
            if progress_id in student_list:
                student_list.remove(progress_id)

    def list_all(self) -> List[CourseProgress]:
        return list(self._progress.values())


class OutcomeRepository:
    def __init__(self):
        self._outcomes: Dict[str, Outcome] = {}
        self._student_index: Dict[str, List[str]] = {}

    def add(self, outcome: Outcome) -> None:
        self._outcomes[outcome.outcome_id] = outcome
        if outcome.student_id not in self._student_index:
            self._student_index[outcome.student_id] = []
        self._student_index[outcome.student_id].append(outcome.outcome_id)

    def get_by_id(self, outcome_id: str) -> Optional[Outcome]:
        return self._outcomes.get(outcome_id)

    def get_by_student(self, student_id: str) -> List[Outcome]:
        ids = self._student_index.get(student_id, [])
        return [self._outcomes[oid] for oid in ids if oid in self._outcomes]

    def update(self, outcome: Outcome) -> None:
        if outcome.outcome_id not in self._outcomes:
            raise NotFoundError(f"Outcome {outcome.outcome_id} not found")
        self._outcomes[outcome.outcome_id] = outcome

    def delete(self, outcome_id: str) -> None:
        outcome = self._outcomes.pop(outcome_id, None)
        if outcome:
            student_list = self._student_index.get(outcome.student_id, [])
            if outcome_id in student_list:
                student_list.remove(outcome_id)

    def list_all(self) -> List[Outcome]:
        return list(self._outcomes.values())


class VolunteerRepository:
    def __init__(self):
        self._volunteers: Dict[str, Volunteer] = {}
        self._user_index: Dict[str, str] = {}

    def add(self, volunteer: Volunteer) -> None:
        self._volunteers[volunteer.volunteer_id] = volunteer
        self._user_index[volunteer.user_id] = volunteer.volunteer_id

    def get_by_id(self, volunteer_id: str) -> Optional[Volunteer]:
        return self._volunteers.get(volunteer_id)

    def get_by_user_id(self, user_id: str) -> Optional[Volunteer]:
        vid = self._user_index.get(user_id)
        if vid:
            return self._volunteers.get(vid)
        return None

    def update(self, volunteer: Volunteer) -> None:
        if volunteer.volunteer_id not in self._volunteers:
            raise NotFoundError(f"Volunteer {volunteer.volunteer_id} not found")
        self._volunteers[volunteer.volunteer_id] = volunteer

    def delete(self, volunteer_id: str) -> None:
        volunteer = self._volunteers.pop(volunteer_id, None)
        if volunteer:
            self._user_index.pop(volunteer.user_id, None)

    def list_all(self) -> List[Volunteer]:
        return list(self._volunteers.values())

    def list_by_status(self, status: str) -> List[Volunteer]:
        return [v for v in self._volunteers.values() if v.status == status]


class WaitlistRepository:
    def __init__(self):
        self._entries: Dict[str, WaitlistEntry] = {}
        self._email_index: Dict[str, str] = {}

    def add(self, entry: WaitlistEntry) -> None:
        if entry.email in self._email_index:
            raise ValidationError(f"Email {entry.email} already on waitlist")
        self._entries[entry.entry_id] = entry
        self._email_index[entry.email] = entry.entry_id

    def get_by_id(self, entry_id: str) -> Optional[WaitlistEntry]:
        return self._entries.get(entry_id)

    def get_by_email(self, email: str) -> Optional[WaitlistEntry]:
        entry_id = self._email_index.get(email)
        if entry_id:
            return self._entries.get(entry_id)
        return None

    def update(self, entry: WaitlistEntry) -> None:
        if entry.entry_id not in self._entries:
            raise NotFoundError(f"Waitlist entry {entry.entry_id} not found")
        self._entries[entry.entry_id] = entry

    def delete(self, entry_id: str) -> None:
        entry = self._entries.pop(entry_id, None)
        if entry:
            self._email_index.pop(entry.email, None)

    def list_all(self) -> List[WaitlistEntry]:
        return list(self._entries.values())

    def list_by_status(self, status: str) -> List[WaitlistEntry]:
        return [e for e in self._entries.values() if e.status == status]


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
        self._sessions: Dict[str, Session] = {}

    def register(
        self,
        username: str,
        email: str,
        password: str,
        role: str = Role.STUDENT,
    ) -> User:
        if not username or not email or not password:
            raise ValidationError("Username, email, and password are required")
        if role not in (Role.STUDENT, Role.ORGANIZER, Role.ADMIN, Role.VOLUNTEER):
            raise ValidationError(f"Invalid role: {role}")
        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        self._user_repo.add(user)
        return user

    def login(self, username: str, password: str) -> Session:
        user = self._user_repo.get_by_username(username)
        if not user:
            user = self._user_repo.get_by_email(username)
        if not user:
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account is inactive")
        if not user.check_password(password):
            raise AuthenticationError("Invalid credentials")
        user.last_login = datetime.now()
        self._user_repo.update(user)
        session = Session(user)
        self._sessions[session.session_id] = session
        return session

    def logout(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.invalidate()
            del self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_valid:
            return session
        return None

    def change_password(self, user_id: str, old_password: str, new_password: str) -> None:
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        if not user.check_password(old_password):
            raise AuthenticationError("Invalid current password")
        user.set_password(new_password)
        self._user_repo.update(user)

    def deactivate_user(self, admin_user_id: str, target_user_id: str) -> None:
        admin = self._user_repo.get_by_id(admin_user_id)
        if not admin or admin.role not in (Role.ADMIN, Role.ORGANIZER):
            raise AuthorizationError("Only admins or organizers can deactivate users")
        user = self._user_repo.get_by_id(target_user_id)
        if not user:
            raise NotFoundError(f"User {target_user_id} not found")
        user.is_active = False
        self._user_repo.update(user)


class StudentService:
    def __init__(
        self,
        user_repo: UserRepository,
        profile_repo: StudentProfileRepository,
        progress_repo: CourseProgressRepository,
        outcome_repo: OutcomeRepository,
    ):
        self._user_repo = user_repo
        self._profile_repo = profile_repo
        self._progress_repo = progress_repo
        self._outcome_repo = outcome_repo

    def create_student_profile(
        self,
        user_id: str,
        first_name: str,
        last_name: str,
        **kwargs,
    ) -> StudentProfile:
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        if user.role != Role.STUDENT:
            raise ValidationError("User is not a student")
        existing = self._profile_repo.get_by_user_id(user_id)
        if existing:
            raise ValidationError(f"Profile already exists for user {user_id}")
        profile = StudentProfile(
            profile_id=str(uuid.uuid4()),
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            **kwargs,
        )
        self._profile_repo.add(profile)
        return profile

    def get_student_profile(
        self, requester_id: str, target_user_id: str
    ) -> Dict[str, Any]:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        profile = self._profile_repo.get_by_user_id(target_user_id)
        if not profile:
            raise NotFoundError(f"Profile for user {target_user_id} not found")
        is_owner = requester_id == target_user_id
        is_privileged = requester.role in (Role.ADMIN, Role.ORGANIZER)
        if not is_owner and not is_privileged:
            raise AuthorizationError("Access denied to this profile")
        include_private = is_owner or is_privileged
        return profile.to_dict(include_private=include_private)

    def update_student_profile(
        self, requester_id: str, target_user_id: str, **kwargs
    ) -> StudentProfile:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        profile = self._profile_repo.get_by_user_id(target_user_id)
        if not profile:
            raise NotFoundError(f"Profile for user {target_user_id} not found")
        is_owner = requester_id == target_user_id
        is_privileged = requester.role in (Role.ADMIN, Role.ORGANIZER)
        if not is_owner and not is_privileged:
            raise AuthorizationError("Access denied")
        profile.update(**kwargs)
        self._profile_repo.update(profile)
        return profile

    def add_course_progress(
        self,
        requester_id: str,
        student_user_id: str,
        course_name: str,
        module: str,
        **kwargs,
    ) -> CourseProgress:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        profile = self._profile_repo.get_by_user_id(student_user_id)
        if not profile:
            raise NotFoundError(f"Profile for user {student_user_id} not found")
        is_owner = requester_id == student_user_id
        is_privileged = requester.role in (Role.ADMIN, Role.ORGANIZER)
        if not is_owner and not is_privileged:
            raise AuthorizationError("Access denied")
        progress = CourseProgress(
            progress_id=str(uuid.uuid4()),
            student_id=profile.profile_id,
            course_name=course_name,
            module=module,
            **kwargs,
        )
        self._progress_repo.add(progress)
        return progress

    def update_course_progress(
        self,
        requester_id: str,
        progress_id: str,
        percentage: float,
        grade: Optional[str] = None,
    ) -> CourseProgress:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        progress = self._progress_repo.get_by_id(progress_id)
        if not progress:
            raise NotFoundError(f"Progress {progress_id} not found")
        profile = self._profile_repo.get_by_id(progress.student_id)
        is_owner = profile and profile.user_id == requester_id
        is_privileged = requester.role in (Role.ADMIN, Role.ORGANIZER)
        if not is_owner and not is_privileged:
            raise AuthorizationError("Access denied")
        progress.update_progress(percentage, grade)
        self._progress_repo.update(progress)
        return progress

    def get_student_progress(
        self, requester_id: str, student_user_id: str
    ) -> List[Dict[str, Any]]:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        profile = self._profile_repo.get_by_user_id(student_user_id)
        if not profile:
            raise NotFoundError(f"Profile for user {student_user_id} not found")
        is_owner = requester_id == student_user_id
        is_privileged = requester.role in (Role.ADMIN, Role.ORGANIZER)
        if not is_owner and not is_privileged:
            raise AuthorizationError("Access denied")
        progress_list = self._progress_repo.get_by_student(profile.profile_id)
        return [p.to_dict() for p in progress_list]

    def add_outcome(
        self,
        requester_id: str,
        student_user_id: str,
        outcome_type: str,
        description: str,
        **kwargs,
    ) -> Outcome:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise AuthorizationError("Only admins or organizers can add outcomes")
        profile = self._profile_repo.get_by_user_id(student_user_id)
        if not profile:
            raise NotFoundError(f"Profile for user {student_user_id} not found")
        outcome = Outcome(
            outcome_id=str(uuid.uuid4()),
            student_id=profile.profile_id,
            outcome_type=outcome_type,
            description=description,
            **kwargs,
        )
        self._outcome_repo.add(outcome)
        return outcome

    def get_student_outcomes(
        self, requester_id: str, student_user_id: str
    ) -> List[Dict[str, Any]]:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        profile = self._profile_repo.get_by_user_id(student_user_id)
        if not profile:
            raise NotFoundError(f"Profile for user {student_user_id} not found")
        is_owner = requester_id == student_user_id
        is_privileged = requester.role in (Role.ADMIN, Role.ORGANIZER)
        if not is_owner and not is_privileged:
            raise AuthorizationError("Access denied")
        outcomes = self._outcome_repo.get_by_student(profile.profile_id)
        return [o.to_dict() for o in outcomes]

    def list_all_students(self, requester_id: str) -> List[Dict[str, Any]]:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise AuthorizationError("Only admins or organizers can list all students")
        profiles = self._profile_repo.list_all()
        return [p.to_dict(include_private=True) for p in profiles]


class VolunteerService:
    def __init__(
        self,
        user_repo: UserRepository,
        volunteer_repo: VolunteerRepository,
    ):
        self._user_repo = user_repo
        self._volunteer_repo = volunteer_repo

    def _check_admin_or_organizer(self, requester_id: str) -> User:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise AuthorizationError("Only admins or organizers can manage volunteers")
        return requester

    def create_volunteer(
        self,
        requester_id: str,
        user_id: str,
        first_name: str,
        last_name: str,
        email: str,
        **kwargs,
    ) -> Volunteer:
        self._check_admin_or_organizer(requester_id)
        volunteer = Volunteer(
            volunteer_id=str(uuid.uuid4()),
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            **kwargs,
        )
        self._volunteer_repo.add(volunteer)
        return volunteer

    def get_volunteer(self, requester_id: str, volunteer_id: str) -> Dict[str, Any]:
        self._check_admin_or_organizer(requester_id)
        volunteer = self._volunteer_repo.get_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")
        return volunteer.to_dict()

    def list_volunteers(
        self, requester_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self._check_admin_or_organizer(requester_id)
        if status:
            volunteers = self._volunteer_repo.list_by_status(status)
        else:
            volunteers = self._volunteer_repo.list_all()
        return [v.to_dict() for v in volunteers]

    def update_volunteer(
        self, requester_id: str, volunteer_id: str, **kwargs
    ) -> Volunteer:
        self._check_admin_or_organizer(requester_id)
        volunteer = self._volunteer_repo.get_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")
        for key, value in kwargs.items():
            if hasattr(volunteer, key) and key not in ("volunteer_id", "user_id"):
                setattr(volunteer, key, value)
        self._volunteer_repo.update(volunteer)
        return volunteer

    def log_volunteer_hours(
        self, requester_id: str, volunteer_id: str, hours: float
    ) -> Volunteer:
        self._check_admin_or_organizer(requester_id)
        volunteer = self._volunteer_repo.get_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")
        volunteer.log_hours(hours)
        self._volunteer_repo.update(volunteer)
        return volunteer

    def deactivate_volunteer(self, requester_id: str, volunteer_id: str) -> Volunteer:
        self._check_admin_or_organizer(requester_id)
        volunteer = self._volunteer_repo.get_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")
        volunteer.status = "inactive"
        self._volunteer_repo.update(volunteer)
        return volunteer


class WaitlistService:
    def __init__(
        self,
        user_repo: UserRepository,
        waitlist_repo: WaitlistRepository,
    ):
        self._user_repo = user_repo
        self._waitlist_repo = waitlist_repo

    def _check_admin_or_organizer(self, requester_id: str) -> User:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise AuthorizationError("Only admins or organizers can manage the waitlist")
        return requester

    def apply_to_waitlist(
        self,
        first_name: str,
        last_name: str,
        email: str,
        **kwargs,
    ) -> WaitlistEntry:
        if not first_name or not last_name or not email:
            raise ValidationError("First name, last name, and email are required")
        entry = WaitlistEntry(
            entry_id=str(uuid.uuid4()),
            first_name=first_name,
            last_name=last_name,
            email=email,
            **kwargs,
        )
        self._waitlist_repo.add(entry)
        return entry

    def get_waitlist_entry(
        self, requester_id: str, entry_id: str
    ) -> Dict[str, Any]:
        self._check_admin_or_organizer(requester_id)
        entry = self._waitlist_repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")
        return entry.to_dict()

    def list_waitlist(
        self, requester_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self._check_admin_or_organizer(requester_id)
        if status:
            entries = self._waitlist_repo.list_by_status(status)
        else:
            entries = self._waitlist_repo.list_all()
        return [e.to_dict() for e in entries]

    def approve_applicant(
        self, requester_id: str, entry_id: str
    ) -> WaitlistEntry:
        self._check_admin_or_organizer(requester_id)
        entry = self._waitlist_repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")
        entry.approve(requester_id)
        self._waitlist_repo.update(entry)
        return entry

    def reject_applicant(
        self, requester_id: str, entry_id: str, notes: str = ""
    ) -> WaitlistEntry:
        self._check_admin_or_organizer(requester_id)
        entry = self._waitlist_repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")
        entry.reject(requester_id, notes)
        self._waitlist_repo.update(entry)
        return entry

    def delete_entry(self, requester_id: str, entry_id: str) -> None:
        self._check_admin_or_organizer(requester_id)
        entry = self._waitlist_repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")
        self._waitlist_repo.delete(entry_id)


class AdminDashboard:
    def __init__(
        self,
        user_repo: UserRepository,
        profile_repo: StudentProfileRepository,
        progress_repo: CourseProgressRepository,
        outcome_repo: OutcomeRepository,
        volunteer_repo: VolunteerRepository,
        waitlist_repo: WaitlistRepository,
    ):
        self._user_repo = user_repo
        self._profile_repo = profile_repo
        self._progress_repo = progress_repo
        self._outcome_repo = outcome_repo
        self._volunteer_repo = volunteer_repo
        self._waitlist_repo = waitlist_repo

    def _check_admin_or_organizer(self, requester_id: str) -> User:
        requester = self._user_repo.get_by_id(requester_id)
        if not requester:
            raise AuthenticationError("Requester not found")
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise AuthorizationError("Access denied to admin dashboard")
        return requester

    def get_overview(self, requester_id: str) -> Dict[str, Any]:
        self._check_admin_or_organizer(requester_id)
        all_profiles = self._profile_repo.list_all()
        active_students = [p for p in all_profiles if p.status == "active"]
        graduated_students = [p for p in all_profiles if p.status == "graduated"]
        all_volunteers = self._volunteer_repo.list_all()
        active_volunteers = [v for v in all_volunteers if v.status == "active"]
        all_waitlist = self._waitlist_repo.list_all()
        pending_waitlist = [e for e in all_waitlist if e.status == "pending"]
        all_outcomes = self._outcome_repo.list_all()
        return {
            "total_students": len(all_profiles),
            "active_students": len(active_students),
            "graduated_students": len(graduated_students),
            "total_volunteers": len(all_volunteers),
            "active_volunteers": len(active_volunteers),
            "total_waitlist_entries": len(all_waitlist),
            "pending_waitlist_entries": len(pending_waitlist),
            "total_outcomes": len(all_outcomes),
        }

    def get_student_progress_report(self, requester_id: str) -> List[Dict[str, Any]]:
        self._check_admin_or_organizer(requester_id)
        profiles = self._profile_repo.list_all()
        report = []
        for profile in profiles:
            progress_list = self._progress_repo.get_by_student(profile.profile_id)
            outcomes = self._outcome_repo.get_by_student(profile.profile_id)
            avg_completion = 0.0
            if progress_list:
                avg_completion = sum(p.completion_percentage for p in progress_list) / len(progress_list)
            report.append({
                "profile": profile.to_dict(include_private=True),
                "progress_summary": {
                    "total_modules": len(progress_list),
                    "average_completion": avg_completion,
                    "completed_modules": sum(1 for p in progress_list if p.completion_percentage == 100.0),
                },
                "outcomes": [o.to_dict() for o in outcomes],
            })
        return report

    def get_volunteer_report(self, requester_id: str) -> List[Dict[str, Any]]:
        self._check_admin_or_organizer(requester_id)
        volunteers = self._volunteer_repo.list_all()
        return [v.to_dict() for v in volunteers]

    def get_waitlist_report(self, requester_id: str) -> Dict[str, Any]:
        self._check_admin_or_organizer(requester_id)
        all_entries = self._waitlist_repo.list_all()
        pending = [e for e in all_entries if e.status == "pending"]
        approved = [e for e in all_entries if e.status == "approved"]
        rejected = [e for e in all_entries if e.status == "rejected"]
        return {
            "total": len(all_entries),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "entries": [e.to_dict() for e in all_entries],
        }

    def get_cohort_report(self, requester_id: str) -> Dict[str, Any]:
        self._check_admin_or_organizer(requester_id)
        profiles = self._profile_repo.list_all()
        cohorts: Dict[str, List[StudentProfile]] = {}
        for profile in profiles:
            cohort_key = profile.cohort or "unassigned"
            if cohort_key not in cohorts:
                cohorts[cohort_key] = []
            cohorts[cohort_key].append(profile)
        report = {}
        for cohort_name, cohort_profiles in cohorts.items():
            report[cohort_name] = {
                "total_students": len(cohort_profiles),
                "active": sum(1 for p in cohort_profiles if p.status == "active"),
                "graduated": sum(1 for p in cohort_profiles if p.status == "graduated"),
                "students": [p.to_dict(include_private=True) for p in cohort_profiles],
            }
        return report

    def list_all_users(self, requester_id: str) -> List[Dict[str, Any]]:
        self._check_admin_or_organizer(requester_id)
        users = self._user_repo.list_all()
        return [u.to_dict() for u in users]


class StudentManagementSystem:
    def __init__(self):
        self._user_repo = UserRepository()
        self._profile_repo = StudentProfileRepository()
        self._progress_repo = CourseProgressRepository()
        self._outcome_repo = OutcomeRepository()
        self._volunteer_repo = VolunteerRepository()
        self._waitlist_repo = WaitlistRepository()

        self.auth_service = AuthService(self._user_repo)
        self.student_service = StudentService(
            self._user_repo,
            self._profile_repo,
            self._progress_repo,
            self._outcome_repo,
        )
        self.volunteer_service = VolunteerService(
            self._user_repo,
            self._volunteer_repo,
        )
        self.waitlist_service = WaitlistService(
            self._user_repo,
            self._waitlist_repo,
        )
        self.admin_dashboard = AdminDashboard(
            self._user_repo,
            self._profile_repo,
            self._progress_repo,
            self._outcome_repo,
            self._volunteer_repo,
            self._waitlist_repo,
        )

    def seed_admin(
        self,
        username: str = "admin",
        email: str = "admin@freecodecamp.org",
        password: str = "admin123",
    ) -> User:
        return self.auth_service.register(username, email, password, Role.ADMIN)


if __name__ == "__main__":
    sms = StudentManagementSystem()

    admin = sms.seed_admin()
    print(f"Admin created: {admin.username} ({admin.role})")

    admin_session = sms.auth_service.login("admin", "admin123")
    print(f"Admin logged in, session: {admin_session.session_id}")

    student_user = sms.auth_service.register(
        "john_doe", "john@example.com", "password123", Role.STUDENT
    )
    print(f"Student user created: {student_user.username}")

    student_profile = sms.student_service.create_student_profile(
        user_id=student_user.user_id,
        first_name="John",
        last_name="Doe",
        cohort="2024-Spring",
        enrollment_date=datetime(2024, 1, 15),
        phone="555-1234",
        bio="Aspiring developer",
    )
    print(f"Student profile created: {student_profile.full_name}")

    student_session = sms.auth_service.login("john_doe", "password123")
    print(f"Student logged in, session: {student_session.session_id}")

    profile_data = sms.student_service.get_student_profile(
        student_user.user_id, student_user.user_id
    )
    print(f"Student profile (self view): {json.dumps(profile_data, indent=2)}")

    progress = sms.student_service.add_course_progress(
        requester_id=admin.user_id,
        student_user_id=student_user.user_id,
        course_name="Python Fundamentals",
        module="Variables and Data Types",
    )
    print(f"Progress added: {progress.course_name} - {progress.module}")

    sms.student_service.update_course_progress(
        requester_id=admin.user_id,
        progress_id=progress.progress_id,
        percentage=75.0,
        grade="B+",
    )
    print(f"Progress updated: {progress.completion_percentage}%")

    outcome = sms.student_service.add_outcome(
        requester_id=admin.user_id,
        student_user_id=student_user.user_id,
        outcome_type="employment",
        description="Hired as Junior Developer",
        employer="Tech Corp",
        job_title="Junior Developer",
        salary=65000.0,
    )
    print(f"Outcome added: {outcome.outcome_type} at {outcome.employer}")

    waitlist_entry = sms.waitlist_service.apply_to_waitlist(
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        cohort_interest="2024-Fall",
        motivation="Want to learn programming",
    )
    print(f"Waitlist entry created: {waitlist_entry.full_name}")

    sms.waitlist_service.approve_applicant(admin.user_id, waitlist_entry.entry_id)
    print(f"Waitlist entry approved: {waitlist_entry.status}")

    volunteer_user = sms.auth_service.register(
        "vol_alice", "alice@example.com", "vol123", Role.VOLUNTEER
    )
    volunteer = sms.volunteer_service.create_volunteer(
        requester_id=admin.user_id,
        user_id=volunteer_user.user_id,
        first_name="Alice",
        last_name="Johnson",
        email="alice@example.com",
        skills=["Python", "JavaScript"],
        availability="Weekends",
    )
    print(f"Volunteer created: {volunteer.full_name}")

    sms.volunteer_service.log_volunteer_hours(admin.user_id, volunteer.volunteer_id, 5.0)
    print(f"Volunteer hours logged: {volunteer.hours_contributed}")

    overview = sms.admin_dashboard.get_overview(admin.user_id)
    print(f"\nAdmin Dashboard Overview:")
    print(json.dumps(overview, indent=2))

    progress_report = sms.admin_dashboard.get_student_progress_report(admin.user_id)
    print(f"\nStudent Progress Report (count): {len(progress_report)}")

    waitlist_report = sms.admin_dashboard.get_waitlist_report(admin.user_id)
    print(f"\nWaitlist Report:")
    print(json.dumps({k: v for k, v in waitlist_report.items() if k != "entries"}, indent=2))

    cohort_report = sms.admin_dashboard.get_cohort_report(admin.user_id)
    print(f"\nCohort Report:")
    for cohort_name, cohort_data in cohort_report.items():
        print(f"  {cohort_name}: {cohort_data['total_students']} students")

    try:
        other_user = sms.auth_service.register(
            "other_user", "other@example.com", "pass123", Role.STUDENT
        )
        sms.student_service.get_student_profile(other_user.user_id, student_user.user_id)
    except AuthorizationError as e:
        print(f"\nAccess control working: {e}")

    sms.auth_service.logout(admin_session.session_id)
    sms.auth_service.logout(student_session.session_id)
    print("\nSessions invalidated successfully")