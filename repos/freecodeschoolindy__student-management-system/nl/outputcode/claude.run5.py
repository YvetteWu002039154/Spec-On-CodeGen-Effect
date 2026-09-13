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

    def update_last_login(self):
        self.last_login = datetime.now()

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
    skills: List[str] = field(default_factory=list)
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def add_skill(self, skill: str):
        if skill not in self.skills:
            self.skills.append(skill)
            self.updated_at = datetime.now()

    def remove_skill(self, skill: str):
        if skill in self.skills:
            self.skills.remove(skill)
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "bio": self.bio,
            "cohort": self.cohort,
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None,
            "graduation_date": self.graduation_date.isoformat() if self.graduation_date else None,
            "status": self.status,
            "skills": self.skills,
            "github_url": self.github_url,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Progress:
    progress_id: str
    student_id: str
    course: str
    module: str
    completion_percentage: float = 0.0
    grade: Optional[str] = None
    score: Optional[float] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_progress(self, percentage: float, grade: Optional[str] = None, score: Optional[float] = None):
        if not (0.0 <= percentage <= 100.0):
            raise ValueError("Completion percentage must be between 0 and 100")
        self.completion_percentage = percentage
        if grade:
            self.grade = grade
        if score is not None:
            self.score = score
        if percentage >= 100.0:
            self.completed = True
            self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "student_id": self.student_id,
            "course": self.course,
            "module": self.module,
            "completion_percentage": self.completion_percentage,
            "grade": self.grade,
            "score": self.score,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
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
    start_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "student_id": self.student_id,
            "outcome_type": self.outcome_type,
            "description": self.description,
            "employer": self.employer,
            "job_title": self.job_title,
            "salary": self.salary,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
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
    availability: str = "flexible"
    status: str = "active"
    role_description: Optional[str] = None
    hours_contributed: float = 0.0
    joined_date: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def log_hours(self, hours: float):
        if hours < 0:
            raise ValueError("Hours cannot be negative")
        self.hours_contributed += hours
        self.updated_at = datetime.now()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volunteer_id": self.volunteer_id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "availability": self.availability,
            "status": self.status,
            "role_description": self.role_description,
            "hours_contributed": self.hours_contributed,
            "joined_date": self.joined_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class WaitlistEntry:
    entry_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    cohort_interest: Optional[str] = None
    background: Optional[str] = None
    motivation: Optional[str] = None
    status: str = "pending"
    position: int = 0
    applied_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""

    def approve(self):
        self.status = "approved"
        self.updated_at = datetime.now()

    def reject(self):
        self.status = "rejected"
        self.updated_at = datetime.now()

    def update_notes(self, notes: str):
        self.notes = notes
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "cohort_interest": self.cohort_interest,
            "background": self.background,
            "motivation": self.motivation,
            "status": self.status,
            "position": self.position,
            "applied_at": self.applied_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
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

    def invalidate(self):
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

    def save(self, user: User) -> User:
        self._users[user.user_id] = user
        self._email_index[user.email] = user.user_id
        self._username_index[user.username] = user.user_id
        return user

    def find_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def find_by_email(self, email: str) -> Optional[User]:
        user_id = self._email_index.get(email)
        if user_id:
            return self._users.get(user_id)
        return None

    def find_by_username(self, username: str) -> Optional[User]:
        user_id = self._username_index.get(username)
        if user_id:
            return self._users.get(user_id)
        return None

    def find_all(self) -> List[User]:
        return list(self._users.values())

    def find_by_role(self, role: str) -> List[User]:
        return [u for u in self._users.values() if u.role == role]

    def delete(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user:
            del self._email_index[user.email]
            del self._username_index[user.username]
            del self._users[user_id]
            return True
        return False

    def exists_email(self, email: str) -> bool:
        return email in self._email_index

    def exists_username(self, username: str) -> bool:
        return username in self._username_index


class StudentProfileRepository:
    def __init__(self):
        self._profiles: Dict[str, StudentProfile] = {}
        self._user_index: Dict[str, str] = {}

    def save(self, profile: StudentProfile) -> StudentProfile:
        self._profiles[profile.profile_id] = profile
        self._user_index[profile.user_id] = profile.profile_id
        return profile

    def find_by_id(self, profile_id: str) -> Optional[StudentProfile]:
        return self._profiles.get(profile_id)

    def find_by_user_id(self, user_id: str) -> Optional[StudentProfile]:
        profile_id = self._user_index.get(user_id)
        if profile_id:
            return self._profiles.get(profile_id)
        return None

    def find_all(self) -> List[StudentProfile]:
        return list(self._profiles.values())

    def find_by_cohort(self, cohort: str) -> List[StudentProfile]:
        return [p for p in self._profiles.values() if p.cohort == cohort]

    def find_by_status(self, status: str) -> List[StudentProfile]:
        return [p for p in self._profiles.values() if p.status == status]

    def delete(self, profile_id: str) -> bool:
        profile = self._profiles.get(profile_id)
        if profile:
            del self._user_index[profile.user_id]
            del self._profiles[profile_id]
            return True
        return False


class ProgressRepository:
    def __init__(self):
        self._progress: Dict[str, Progress] = {}

    def save(self, progress: Progress) -> Progress:
        self._progress[progress.progress_id] = progress
        return progress

    def find_by_id(self, progress_id: str) -> Optional[Progress]:
        return self._progress.get(progress_id)

    def find_by_student_id(self, student_id: str) -> List[Progress]:
        return [p for p in self._progress.values() if p.student_id == student_id]

    def find_by_student_and_course(self, student_id: str, course: str) -> List[Progress]:
        return [p for p in self._progress.values() if p.student_id == student_id and p.course == course]

    def find_all(self) -> List[Progress]:
        return list(self._progress.values())

    def delete(self, progress_id: str) -> bool:
        if progress_id in self._progress:
            del self._progress[progress_id]
            return True
        return False


class OutcomeRepository:
    def __init__(self):
        self._outcomes: Dict[str, Outcome] = {}

    def save(self, outcome: Outcome) -> Outcome:
        self._outcomes[outcome.outcome_id] = outcome
        return outcome

    def find_by_id(self, outcome_id: str) -> Optional[Outcome]:
        return self._outcomes.get(outcome_id)

    def find_by_student_id(self, student_id: str) -> List[Outcome]:
        return [o for o in self._outcomes.values() if o.student_id == student_id]

    def find_all(self) -> List[Outcome]:
        return list(self._outcomes.values())

    def delete(self, outcome_id: str) -> bool:
        if outcome_id in self._outcomes:
            del self._outcomes[outcome_id]
            return True
        return False


class VolunteerRepository:
    def __init__(self):
        self._volunteers: Dict[str, Volunteer] = {}
        self._user_index: Dict[str, str] = {}

    def save(self, volunteer: Volunteer) -> Volunteer:
        self._volunteers[volunteer.volunteer_id] = volunteer
        self._user_index[volunteer.user_id] = volunteer.volunteer_id
        return volunteer

    def find_by_id(self, volunteer_id: str) -> Optional[Volunteer]:
        return self._volunteers.get(volunteer_id)

    def find_by_user_id(self, user_id: str) -> Optional[Volunteer]:
        volunteer_id = self._user_index.get(user_id)
        if volunteer_id:
            return self._volunteers.get(volunteer_id)
        return None

    def find_all(self) -> List[Volunteer]:
        return list(self._volunteers.values())

    def find_by_status(self, status: str) -> List[Volunteer]:
        return [v for v in self._volunteers.values() if v.status == status]

    def delete(self, volunteer_id: str) -> bool:
        volunteer = self._volunteers.get(volunteer_id)
        if volunteer:
            del self._user_index[volunteer.user_id]
            del self._volunteers[volunteer_id]
            return True
        return False


class WaitlistRepository:
    def __init__(self):
        self._entries: Dict[str, WaitlistEntry] = {}
        self._email_index: Dict[str, str] = {}
        self._position_counter: int = 0

    def save(self, entry: WaitlistEntry) -> WaitlistEntry:
        if entry.entry_id not in self._entries:
            self._position_counter += 1
            entry.position = self._position_counter
        self._entries[entry.entry_id] = entry
        self._email_index[entry.email] = entry.entry_id
        return entry

    def find_by_id(self, entry_id: str) -> Optional[WaitlistEntry]:
        return self._entries.get(entry_id)

    def find_by_email(self, email: str) -> Optional[WaitlistEntry]:
        entry_id = self._email_index.get(email)
        if entry_id:
            return self._entries.get(entry_id)
        return None

    def find_all(self) -> List[WaitlistEntry]:
        return sorted(self._entries.values(), key=lambda e: e.position)

    def find_by_status(self, status: str) -> List[WaitlistEntry]:
        return [e for e in self._entries.values() if e.status == status]

    def delete(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry:
            del self._email_index[entry.email]
            del self._entries[entry_id]
            return True
        return False

    def exists_email(self, email: str) -> bool:
        return email in self._email_index


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
        self._sessions: Dict[str, Session] = {}

    def register(self, username: str, email: str, password: str, role: str = Role.STUDENT) -> User:
        if not username or not email or not password:
            raise ValidationError("Username, email, and password are required")
        if self._user_repo.exists_email(email):
            raise ValidationError(f"Email {email} is already registered")
        if self._user_repo.exists_username(username):
            raise ValidationError(f"Username {username} is already taken")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")
        if role not in [Role.STUDENT, Role.ORGANIZER, Role.ADMIN, Role.VOLUNTEER]:
            raise ValidationError(f"Invalid role: {role}")

        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        return self._user_repo.save(user)

    def login(self, username: str, password: str) -> Session:
        user = self._user_repo.find_by_username(username)
        if not user:
            user = self._user_repo.find_by_email(username)
        if not user:
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")
        if not user.check_password(password):
            raise AuthenticationError("Invalid credentials")

        user.update_last_login()
        session = Session(user)
        self._sessions[session.session_id] = session
        return session

    def logout(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.invalidate()
            del self._sessions[session_id]
            return True
        return False

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_valid:
            return session
        return None

    def validate_session(self, session_id: str) -> User:
        session = self.get_session(session_id)
        if not session:
            raise AuthenticationError("Invalid or expired session")
        return session.user

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        if not user.check_password(old_password):
            raise AuthenticationError("Current password is incorrect")
        if len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters long")
        user.password_hash = hash_password(new_password)
        self._user_repo.save(user)
        return True

    def deactivate_user(self, admin_user: User, target_user_id: str) -> bool:
        if admin_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can deactivate users")
        user = self._user_repo.find_by_id(target_user_id)
        if not user:
            raise NotFoundError(f"User {target_user_id} not found")
        user.is_active = False
        self._user_repo.save(user)
        return True

    def activate_user(self, admin_user: User, target_user_id: str) -> bool:
        if admin_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can activate users")
        user = self._user_repo.find_by_id(target_user_id)
        if not user:
            raise NotFoundError(f"User {target_user_id} not found")
        user.is_active = True
        self._user_repo.save(user)
        return True


class StudentService:
    def __init__(self, student_repo: StudentProfileRepository, user_repo: UserRepository):
        self._student_repo = student_repo
        self._user_repo = user_repo

    def create_profile(self, requesting_user: User, user_id: str, first_name: str,
                       last_name: str, **kwargs) -> StudentProfile:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER] and requesting_user.user_id != user_id:
            raise AuthorizationError("You can only create your own profile")

        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        existing = self._student_repo.find_by_user_id(user_id)
        if existing:
            raise ValidationError(f"Profile already exists for user {user_id}")

        profile = StudentProfile(
            profile_id=str(uuid.uuid4()),
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            **kwargs,
        )
        return self._student_repo.save(profile)

    def get_profile(self, requesting_user: User, profile_id: str) -> StudentProfile:
        profile = self._student_repo.find_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Profile {profile_id} not found")

        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            if requesting_user.user_id != profile.user_id:
                raise AuthorizationError("You can only view your own profile")

        return profile

    def get_my_profile(self, requesting_user: User) -> StudentProfile:
        profile = self._student_repo.find_by_user_id(requesting_user.user_id)
        if not profile:
            raise NotFoundError("Profile not found for current user")
        return profile

    def update_profile(self, requesting_user: User, profile_id: str, **kwargs) -> StudentProfile:
        profile = self._student_repo.find_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Profile {profile_id} not found")

        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            if requesting_user.user_id != profile.user_id:
                raise AuthorizationError("You can only update your own profile")

        profile.update(**kwargs)
        return self._student_repo.save(profile)

    def get_all_profiles(self, requesting_user: User) -> List[StudentProfile]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can view all profiles")
        return self._student_repo.find_all()

    def get_profiles_by_cohort(self, requesting_user: User, cohort: str) -> List[StudentProfile]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can filter profiles by cohort")
        return self._student_repo.find_by_cohort(cohort)

    def delete_profile(self, requesting_user: User, profile_id: str) -> bool:
        if requesting_user.role not in [Role.ADMIN]:
            raise AuthorizationError("Only admins can delete profiles")
        profile = self._student_repo.find_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Profile {profile_id} not found")
        return self._student_repo.delete(profile_id)

    def add_skill(self, requesting_user: User, profile_id: str, skill: str) -> StudentProfile:
        profile = self._student_repo.find_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Profile {profile_id} not found")

        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            if requesting_user.user_id != profile.user_id:
                raise AuthorizationError("You can only update your own profile")

        profile.add_skill(skill)
        return self._student_repo.save(profile)

    def remove_skill(self, requesting_user: User, profile_id: str, skill: str) -> StudentProfile:
        profile = self._student_repo.find_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Profile {profile_id} not found")

        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            if requesting_user.user_id != profile.user_id:
                raise AuthorizationError("You can only update your own profile")

        profile.remove_skill(skill)
        return self._student_repo.save(profile)


class ProgressService:
    def __init__(self, progress_repo: ProgressRepository, student_repo: StudentProfileRepository):
        self._progress_repo = progress_repo
        self._student_repo = student_repo

    def add_progress(self, requesting_user: User, student_id: str, course: str,
                     module: str, **kwargs) -> Progress:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            profile = self._student_repo.find_by_user_id(requesting_user.user_id)
            if not profile or profile.profile_id != student_id:
                raise AuthorizationError("You can only add progress for yourself")

        progress = Progress(
            progress_id=str(uuid.uuid4()),
            student_id=student_id,
            course=course,
            module=module,
            **kwargs,
        )
        return self._progress_repo.save(progress)

    def get_student_progress(self, requesting_user: User, student_id: str) -> List[Progress]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            profile = self._student_repo.find_by_user_id(requesting_user.user_id)
            if not profile or profile.profile_id != student_id:
                raise AuthorizationError("You can only view your own progress")
        return self._progress_repo.find_by_student_id(student_id)

    def update_progress(self, requesting_user: User, progress_id: str,
                        percentage: float, grade: Optional[str] = None,
                        score: Optional[float] = None) -> Progress:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can update progress")

        progress = self._progress_repo.find_by_id(progress_id)
        if not progress:
            raise NotFoundError(f"Progress {progress_id} not found")

        progress.update_progress(percentage, grade, score)
        return self._progress_repo.save(progress)

    def get_all_progress(self, requesting_user: User) -> List[Progress]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can view all progress")
        return self._progress_repo.find_all()

    def delete_progress(self, requesting_user: User, progress_id: str) -> bool:
        if requesting_user.role not in [Role.ADMIN]:
            raise AuthorizationError("Only admins can delete progress records")
        progress = self._progress_repo.find_by_id(progress_id)
        if not progress:
            raise NotFoundError(f"Progress {progress_id} not found")
        return self._progress_repo.delete(progress_id)

    def get_completion_summary(self, requesting_user: User, student_id: str) -> Dict[str, Any]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            profile = self._student_repo.find_by_user_id(requesting_user.user_id)
            if not profile or profile.profile_id != student_id:
                raise AuthorizationError("You can only view your own progress summary")

        progress_list = self._progress_repo.find_by_student_id(student_id)
        total = len(progress_list)
        completed = sum(1 for p in progress_list if p.completed)
        avg_completion = sum(p.completion_percentage for p in progress_list) / total if total > 0 else 0.0

        return {
            "student_id": student_id,
            "total_modules": total,
            "completed_modules": completed,
            "average_completion": avg_completion,
            "courses": list(set(p.course for p in progress_list)),
        }


class OutcomeService:
    def __init__(self, outcome_repo: OutcomeRepository, student_repo: StudentProfileRepository):
        self._outcome_repo = outcome_repo
        self._student_repo = student_repo

    def add_outcome(self, requesting_user: User, student_id: str, outcome_type: str,
                    description: str, **kwargs) -> Outcome:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            profile = self._student_repo.find_by_user_id(requesting_user.user_id)
            if not profile or profile.profile_id != student_id:
                raise AuthorizationError("You can only add outcomes for yourself")

        outcome = Outcome(
            outcome_id=str(uuid.uuid4()),
            student_id=student_id,
            outcome_type=outcome_type,
            description=description,
            **kwargs,
        )
        return self._outcome_repo.save(outcome)

    def get_student_outcomes(self, requesting_user: User, student_id: str) -> List[Outcome]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            profile = self._student_repo.find_by_user_id(requesting_user.user_id)
            if not profile or profile.profile_id != student_id:
                raise AuthorizationError("You can only view your own outcomes")
        return self._outcome_repo.find_by_student_id(student_id)

    def update_outcome(self, requesting_user: User, outcome_id: str, **kwargs) -> Outcome:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can update outcomes")

        outcome = self._outcome_repo.find_by_id(outcome_id)
        if not outcome:
            raise NotFoundError(f"Outcome {outcome_id} not found")

        outcome.update(**kwargs)
        return self._outcome_repo.save(outcome)

    def get_all_outcomes(self, requesting_user: User) -> List[Outcome]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can view all outcomes")
        return self._outcome_repo.find_all()

    def delete_outcome(self, requesting_user: User, outcome_id: str) -> bool:
        if requesting_user.role not in [Role.ADMIN]:
            raise AuthorizationError("Only admins can delete outcomes")
        outcome = self._outcome_repo.find_by_id(outcome_id)
        if not outcome:
            raise NotFoundError(f"Outcome {outcome_id} not found")
        return self._outcome_repo.delete(outcome_id)


class VolunteerService:
    def __init__(self, volunteer_repo: VolunteerRepository, user_repo: UserRepository):
        self._volunteer_repo = volunteer_repo
        self._user_repo = user_repo

    def register_volunteer(self, requesting_user: User, user_id: str, first_name: str,
                           last_name: str, email: str, **kwargs) -> Volunteer:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER] and requesting_user.user_id != user_id:
            raise AuthorizationError("You can only register yourself as a volunteer")

        existing = self._volunteer_repo.find_by_user_id(user_id)
        if existing:
            raise ValidationError(f"Volunteer profile already exists for user {user_id}")

        volunteer = Volunteer(
            volunteer_id=str(uuid.uuid4()),
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            **kwargs,
        )
        return self._volunteer_repo.save(volunteer)

    def get_volunteer(self, requesting_user: User, volunteer_id: str) -> Volunteer:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            volunteer = self._volunteer_repo.find_by_user_id(requesting_user.user_id)
            if not volunteer or volunteer.volunteer_id != volunteer_id:
                raise AuthorizationError("You can only view your own volunteer profile")

        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")
        return volunteer

    def get_all_volunteers(self, requesting_user: User) -> List[Volunteer]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can view all volunteers")
        return self._volunteer_repo.find_all()

    def update_volunteer(self, requesting_user: User, volunteer_id: str, **kwargs) -> Volunteer:
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")

        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            if requesting_user.user_id != volunteer.user_id:
                raise AuthorizationError("You can only update your own volunteer profile")

        volunteer.update(**kwargs)
        return self._volunteer_repo.save(volunteer)

    def log_volunteer_hours(self, requesting_user: User, volunteer_id: str, hours: float) -> Volunteer:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can log volunteer hours")

        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")

        volunteer.log_hours(hours)
        return self._volunteer_repo.save(volunteer)

    def deactivate_volunteer(self, requesting_user: User, volunteer_id: str) -> Volunteer:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can deactivate volunteers")

        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")

        volunteer.update(status="inactive")
        return self._volunteer_repo.save(volunteer)

    def delete_volunteer(self, requesting_user: User, volunteer_id: str) -> bool:
        if requesting_user.role not in [Role.ADMIN]:
            raise AuthorizationError("Only admins can delete volunteer records")
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found")
        return self._volunteer_repo.delete(volunteer_id)


class WaitlistService:
    def __init__(self, waitlist_repo: WaitlistRepository):
        self._waitlist_repo = waitlist_repo

    def add_to_waitlist(self, first_name: str, last_name: str, email: str, **kwargs) -> WaitlistEntry:
        if not first_name or not last_name or not email:
            raise ValidationError("First name, last name, and email are required")

        if self._waitlist_repo.exists_email(email):
            raise ValidationError(f"Email {email} is already on the waitlist")

        entry = WaitlistEntry(
            entry_id=str(uuid.uuid4()),
            first_name=first_name,
            last_name=last_name,
            email=email,
            **kwargs,
        )
        return self._waitlist_repo.save(entry)

    def get_waitlist(self, requesting_user: User) -> List[WaitlistEntry]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can view the waitlist")
        return self._waitlist_repo.find_all()

    def get_entry(self, requesting_user: User, entry_id: str) -> WaitlistEntry:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can view waitlist entries")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")
        return entry

    def approve_entry(self, requesting_user: User, entry_id: str) -> WaitlistEntry:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can approve waitlist entries")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")

        entry.approve()
        return self._waitlist_repo.save(entry)

    def reject_entry(self, requesting_user: User, entry_id: str) -> WaitlistEntry:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can reject waitlist entries")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")

        entry.reject()
        return self._waitlist_repo.save(entry)

    def update_notes(self, requesting_user: User, entry_id: str, notes: str) -> WaitlistEntry:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can update waitlist notes")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")

        entry.update_notes(notes)
        return self._waitlist_repo.save(entry)

    def delete_entry(self, requesting_user: User, entry_id: str) -> bool:
        if requesting_user.role not in [Role.ADMIN]:
            raise AuthorizationError("Only admins can delete waitlist entries")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {entry_id} not found")

        return self._waitlist_repo.delete(entry_id)

    def get_pending_entries(self, requesting_user: User) -> List[WaitlistEntry]:
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins and organizers can view pending waitlist entries")
        return self._waitlist_repo.find_by_status("pending")


class AdminDashboard:
    def __init__(self, student_service: StudentService, progress_service: ProgressService,
                 outcome_service: OutcomeService, volunteer_service: VolunteerService,
                 waitlist_service: WaitlistService, user_repo: UserRepository):
        self._student_service = student_service
        self._progress_service = progress_service
        self._outcome_service = outcome_service
        self._volunteer_service = volunteer_service
        self._waitlist_service = waitlist_service
        self._user_repo = user_repo

    def _require_admin_or_organizer(self, user: User):
        if user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Access denied: Admin or Organizer role required")

    def get_overview(self, requesting_user: User) -> Dict[str, Any]:
        self._require_admin_or_organizer(requesting_user)

        all_students = self._student_service.get_all_profiles(requesting_user)
        all_volunteers = self._volunteer_service.get_all_volunteers(requesting_user)
        all_waitlist = self._waitlist_service.get_waitlist(requesting_user)
        all_progress = self._progress_service.get_all_progress(requesting_user)
        all_outcomes = self._outcome_service.get_all_outcomes(requesting_user)

        active_students = [s for s in all_students if s.status == "active"]
        graduated_students = [s for s in all_students if s.status == "graduated"]
        active_volunteers = [v for v in all_volunteers if v.status == "active"]
        pending_waitlist = [w for w in all_waitlist if w.status == "pending"]

        cohorts = list(set(s.cohort for s in all_students if s.cohort))

        return {
            "total_students": len(all_students),
            "active_students": len(active_students),
            "graduated_students": len(graduated_students),
            "total_volunteers": len(all_volunteers),
            "active_volunteers": len(active_volunteers),
            "waitlist_total": len(all_waitlist),
            "waitlist_pending": len(pending_waitlist),
            "total_progress_records": len(all_progress),
            "total_outcomes": len(all_outcomes),
            "cohorts": cohorts,
        }

    def get_student_dashboard(self, requesting_user: User, student_id: str) -> Dict[str, Any]:
        self._require_admin_or_organizer(requesting_user)

        profile = self._student_service.get_profile(requesting_user, student_id)
        progress_list = self._progress_service.get_student_progress(requesting_user, student_id)
        outcomes = self._outcome_service.get_student_outcomes(requesting_user, student_id)
        summary = self._progress_service.get_completion_summary(requesting_user, student_id)

        return {
            "profile": profile.to_dict(),
            "progress": [p.to_dict() for p in progress_list],
            "outcomes": [o.to_dict() for o in outcomes],
            "summary": summary,
        }

    def get_volunteer_dashboard(self, requesting_user: User) -> Dict[str, Any]:
        self._require_admin_or_organizer(requesting_user)

        volunteers = self._volunteer_service.get_all_volunteers(requesting_user)
        active = [v for v in volunteers if v.status == "active"]
        inactive = [v for v in volunteers if v.status == "inactive"]
        total_hours = sum(v.hours_contributed for v in volunteers)

        return {
            "total_volunteers": len(volunteers),
            "active_volunteers": len(active),
            "inactive_volunteers": len(inactive),
            "total_hours_contributed": total_hours,
            "volunteers": [v.to_dict() for v in volunteers],
        }

    def get_waitlist_dashboard(self, requesting_user: User) -> Dict[str, Any]:
        self._require_admin_or_organizer(requesting_user)

        all_entries = self._waitlist_service.get_waitlist(requesting_user)
        pending = [e for e in all_entries if e.status == "pending"]
        approved = [e for e in all_entries if e.status == "approved"]
        rejected = [e for e in all_entries if e.status == "rejected"]

        cohort_breakdown: Dict[str, int] = {}
        for entry in all_entries:
            if entry.cohort_interest:
                cohort_breakdown[entry.cohort_interest] = cohort_breakdown.get(entry.cohort_interest, 0) + 1

        return {
            "total_entries": len(all_entries),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "cohort_breakdown": cohort_breakdown,
            "entries": [e.to_dict() for e in all_entries],
        }

    def get_progress_report(self, requesting_user: User) -> Dict[str, Any]:
        self._require_admin_or_organizer(requesting_user)

        all_progress = self._progress_service.get_all_progress(requesting_user)
        all_students = self._student_service.get_all_profiles(requesting_user)

        completed = [p for p in all_progress if p.completed]
        in_progress = [p for p in all_progress if not p.completed and p.completion_percentage > 0]
        not_started = [p for p in all_progress if p.completion_percentage == 0]

        course_stats: Dict[str, Dict[str, Any]] = {}
        for p in all_progress:
            if p.course not in course_stats:
                course_stats[p.course] = {"total": 0, "completed": 0, "avg_score": []}
            course_stats[p.course]["total"] += 1
            if p.completed:
                course_stats[p.course]["completed"] += 1
            if p.score is not None:
                course_stats[p.course]["avg_score"].append(p.score)

        for course in course_stats:
            scores = course_stats[course]["avg_score"]
            course_stats[course]["avg_score"] = sum(scores) / len(scores) if scores else None

        return {
            "total_progress_records": len(all_progress),
            "completed": len(completed),
            "in_progress": len(in_progress),
            "not_started": len(not_started),
            "course_statistics": course_stats,
            "total_students": len(all_students),
        }

    def get_outcomes_report(self, requesting_user: User) -> Dict[str, Any]:
        self._require_admin_or_organizer(requesting_user)

        all_outcomes = self._outcome_service.get_all_outcomes(requesting_user)

        outcome_type_breakdown: Dict[str, int] = {}
        for outcome in all_outcomes:
            outcome_type_breakdown[outcome.outcome_type] = outcome_type_breakdown.get(outcome.outcome_type, 0) + 1

        employed = [o for o in all_outcomes if o.outcome_type == "employment"]
        avg_salary = None
        if employed:
            salaries = [o.salary for o in employed if o.salary is not None]
            avg_salary = sum(salaries) / len(salaries) if salaries else None

        return {
            "total_outcomes": len(all_outcomes),
            "outcome_type_breakdown": outcome_type_breakdown,
            "employment_count": len(employed),
            "average_salary": avg_salary,
            "outcomes": [o.to_dict() for o in all_outcomes],
        }


class StudentManagementSystem:
    def __init__(self):
        self._user_repo = UserRepository()
        self._student_repo = StudentProfileRepository()
        self._progress_repo = ProgressRepository()
        self._outcome_repo = OutcomeRepository()
        self._volunteer_repo = VolunteerRepository()
        self._waitlist_repo = WaitlistRepository()

        self.auth_service = AuthService(self._user_repo)
        self.student_service = StudentService(self._student_repo, self._user_repo)
        self.progress_service = ProgressService(self._progress_repo, self._student_repo)
        self.outcome_service = OutcomeService(self._outcome_repo, self._student_repo)
        self.volunteer_service = VolunteerService(self._volunteer_repo, self._user_repo)
        self.waitlist_service = WaitlistService(self._waitlist_repo)
        self.admin_dashboard = AdminDashboard(
            self.student_service,
            self.progress_service,
            self.outcome_service,
            self.volunteer_service,
            self.waitlist_service,
            self._user_repo,
        )

        self._initialize_default_admin()

    def _initialize_default_admin(self):
        try:
            self.auth_service.register(
                username="admin",
                email="admin@freecodecamp.org",
                password="admin123",
                role=Role.ADMIN,
            )
        except ValidationError:
            pass

    def get_user_repo(self) -> UserRepository:
        return self._user_repo

    def get_student_repo(self) -> StudentProfileRepository:
        return self._student_repo


def main():
    system = StudentManagementSystem()

    print("=== Student Management System Demo ===\n")

    admin_session = system.auth_service.login("admin", "admin123")
    admin_user = admin_session.user
    print(f"Admin logged in: {admin_user.username} (role: {admin_user.role})")

    student_user = system.auth_service.register(
        username="john_doe",
        email="john@example.com",
        password="password123",
        role=Role.STUDENT,
    )
    print(f"Student registered: {student_user.username}")

    student_session = system.auth_service.login("john_doe", "password123")
    logged_in_student = student_session.user
    print(f"Student logged in: {logged_in_student.username}")

    student_profile = system.student_service.create_profile(
        requesting_user=admin_user,
        user_id=student_user.user_id,
        first_name="John",
        last_name="Doe",
        cohort="2024-Spring",
        enrollment_date=datetime(2024, 1, 15),
        status="active",
    )
    print(f"\nStudent profile created: {student_profile.first_name} {student_profile.last_name}")

    system.student_service.add_skill(admin_user, student_profile.profile_id, "Python")
    system.student_service.add_skill(admin_user, student_profile.profile_id, "JavaScript")
    print(f"Skills added: {student_profile.skills}")

    progress = system.progress_service.add_progress(
        requesting_user=admin_user,
        student_id=student_profile.profile_id,
        course="Web Development",
        module="HTML & CSS",
    )
    system.progress_service.update_progress(admin_user, progress.progress_id, 100.0, "A", 95.0)
    print(f"\nProgress updated: {progress.course} - {progress.module} - {progress.completion_percentage}%")

    outcome = system.outcome_service.add_outcome(
        requesting_user=admin_user,
        student_id=student_profile.profile_id,
        outcome_type="employment",
        description="Full-time software developer position",
        employer="Tech Corp",
        job_title="Junior Developer",
        salary=65000.0,
    )
    print(f"Outcome added: {outcome.outcome_type} at {outcome.employer}")

    volunteer_user = system.auth_service.register(
        username="volunteer_jane",
        email="jane@example.com",
        password="password123",
        role=Role.VOLUNTEER,
    )
    volunteer = system.volunteer_service.register_volunteer(
        requesting_user=admin_user,
        user_id=volunteer_user.user_id,
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        skills=["Mentoring", "Python"],
    )
    system.volunteer_service.log_volunteer_hours(admin_user, volunteer.volunteer_id, 10.0)
    print(f"\nVolunteer registered: {volunteer.first_name} {volunteer.last_name}, Hours: {volunteer.hours_contributed}")

    waitlist_entry = system.waitlist_service.add_to_waitlist(
        first_name="Bob",
        last_name="Johnson",
        email="bob@example.com",
        cohort_interest="2024-Fall",
        motivation="Want to learn programming",
    )
    print(f"\nWaitlist entry added: {waitlist_entry.first_name} {waitlist_entry.last_name} (position: {waitlist_entry.position})")

    system.waitlist_service.approve_entry(admin_user, waitlist_entry.entry_id)
    print(f"Waitlist entry approved: {waitlist_entry.status}")

    print("\n=== Admin Dashboard Overview ===")
    overview = system.admin_dashboard.get_overview(admin_user)
    for key, value in overview.items():
        print(f"  {key}: {value}")

    print("\n=== Student Dashboard ===")
    student_dashboard = system.admin_dashboard.get_student_dashboard(admin_user, student_profile.profile_id)
    print(f"  Profile: {student_dashboard['profile']['first_name']} {student_dashboard['profile']['last_name']}")
    print(f"  Progress records: {len(student_dashboard['progress'])}")
    print(f"  Outcomes: {len(student_dashboard['outcomes'])}")
    print(f"  Summary: {student_dashboard['summary']}")

    print("\n=== Volunteer Dashboard ===")
    volunteer_dashboard = system.admin_dashboard.get_volunteer_dashboard(admin_user)
    print(f"  Total volunteers: {volunteer_dashboard['total_volunteers']}")
    print(f"  Total hours: {volunteer_dashboard['total_hours_contributed']}")

    print("\n=== Waitlist Dashboard ===")
    waitlist_dashboard = system.admin_dashboard.get_waitlist_dashboard(admin_user)
    print(f"  Total entries: {waitlist_dashboard['total_entries']}")
    print(f"  Pending: {waitlist_dashboard['pending']}")
    print(f"  Approved: {waitlist_dashboard['approved']}")

    print("\n=== Student Self-Service ===")
    my_profile = system.student_service.get_my_profile(logged_in_student)
    print(f"  Student viewing own profile: {my_profile.first_name} {my_profile.last_name}")

    my_progress = system.progress_service.get_student_progress(logged_in_student, student_profile.profile_id)
    print(f"  Student viewing own progress: {len(my_progress)} records")

    print("\n=== Authorization Test ===")
    try:
        system.student_service.get_all_profiles(logged_in_student)
    except AuthorizationError as e:
        print(f"  Authorization blocked (expected): {e}")

    system.auth_service.logout(admin_session.session_id)
    system.auth_service.logout(student_session.session_id)
    print("\nSessions logged out successfully")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()