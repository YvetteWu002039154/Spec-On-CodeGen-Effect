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
    created_at: datetime
    is_active: bool = True
    last_login: Optional[datetime] = None

    def check_password(self, password: str) -> bool:
        return self.password_hash == hash_password(password)

    def update_last_login(self):
        self.last_login = datetime.now()

    def deactivate(self):
        self.is_active = False

    def activate(self):
        self.is_active = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
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
    notes: str = ""
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def add_skill(self, skill: str):
        if skill not in self.skills:
            self.skills.append(skill)

    def remove_skill(self, skill: str):
        if skill in self.skills:
            self.skills.remove(skill)

    def update_status(self, status: str):
        valid_statuses = ["active", "graduated", "dropped", "waitlisted", "on_hold"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of {valid_statuses}")
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "phone": self.phone,
            "bio": self.bio,
            "cohort": self.cohort,
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None,
            "graduation_date": self.graduation_date.isoformat() if self.graduation_date else None,
            "status": self.status,
            "skills": self.skills,
            "notes": self.notes,
            "github_username": self.github_username,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
        }


@dataclass
class Progress:
    progress_id: str
    student_id: str
    module_name: str
    completion_percentage: float
    grade: Optional[str] = None
    completed: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: str = ""

    def update_completion(self, percentage: float):
        if not 0 <= percentage <= 100:
            raise ValueError("Completion percentage must be between 0 and 100")
        self.completion_percentage = percentage
        if percentage == 100:
            self.completed = True
            self.completed_at = datetime.now()

    def assign_grade(self, grade: str):
        valid_grades = ["A", "B", "C", "D", "F", "Pass", "Fail", "Incomplete"]
        if grade not in valid_grades:
            raise ValueError(f"Invalid grade. Must be one of {valid_grades}")
        self.grade = grade

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "student_id": self.student_id,
            "module_name": self.module_name,
            "completion_percentage": self.completion_percentage,
            "grade": self.grade,
            "completed": self.completed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
        }


@dataclass
class Outcome:
    outcome_id: str
    student_id: str
    outcome_type: str
    description: str
    achieved_at: datetime
    employer: Optional[str] = None
    job_title: Optional[str] = None
    salary_range: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "student_id": self.student_id,
            "outcome_type": self.outcome_type,
            "description": self.description,
            "achieved_at": self.achieved_at.isoformat(),
            "employer": self.employer,
            "job_title": self.job_title,
            "salary_range": self.salary_range,
            "notes": self.notes,
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
    joined_at: Optional[datetime] = None
    hours_contributed: float = 0.0
    notes: str = ""

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def add_skill(self, skill: str):
        if skill not in self.skills:
            self.skills.append(skill)

    def log_hours(self, hours: float):
        if hours < 0:
            raise ValueError("Hours cannot be negative")
        self.hours_contributed += hours

    def update_status(self, status: str):
        valid_statuses = ["active", "inactive", "pending"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of {valid_statuses}")
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volunteer_id": self.volunteer_id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "availability": self.availability,
            "status": self.status,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "hours_contributed": self.hours_contributed,
            "notes": self.notes,
        }


@dataclass
class WaitlistEntry:
    entry_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    applied_at: Optional[datetime] = None
    status: str = "pending"
    cohort_interest: Optional[str] = None
    background: Optional[str] = None
    motivation: Optional[str] = None
    notes: str = ""
    priority: int = 0

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def approve(self):
        self.status = "approved"

    def reject(self):
        self.status = "rejected"

    def set_priority(self, priority: int):
        if priority < 0:
            raise ValueError("Priority cannot be negative")
        self.priority = priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "email": self.email,
            "phone": self.phone,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "status": self.status,
            "cohort_interest": self.cohort_interest,
            "background": self.background,
            "motivation": self.motivation,
            "notes": self.notes,
            "priority": self.priority,
        }


@dataclass
class Cohort:
    cohort_id: str
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    capacity: int = 30
    description: str = ""
    status: str = "upcoming"
    student_ids: List[str] = field(default_factory=list)

    def add_student(self, student_id: str) -> bool:
        if len(self.student_ids) >= self.capacity:
            return False
        if student_id not in self.student_ids:
            self.student_ids.append(student_id)
        return True

    def remove_student(self, student_id: str):
        if student_id in self.student_ids:
            self.student_ids.remove(student_id)

    def get_enrollment_count(self) -> int:
        return len(self.student_ids)

    def is_full(self) -> bool:
        return len(self.student_ids) >= self.capacity

    def update_status(self, status: str):
        valid_statuses = ["upcoming", "active", "completed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of {valid_statuses}")
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cohort_id": self.cohort_id,
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "capacity": self.capacity,
            "description": self.description,
            "status": self.status,
            "enrollment_count": self.get_enrollment_count(),
            "is_full": self.is_full(),
        }


class UserRepository:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}
        self._username_index: Dict[str, str] = {}

    def save(self, user: User):
        self._users[user.user_id] = user
        self._email_index[user.email] = user.user_id
        self._username_index[user.username] = user.user_id

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

    def save(self, profile: StudentProfile):
        self._profiles[profile.profile_id] = profile
        self._user_index[profile.user_id] = profile.profile_id

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

    def save(self, progress: Progress):
        self._progress[progress.progress_id] = progress

    def find_by_id(self, progress_id: str) -> Optional[Progress]:
        return self._progress.get(progress_id)

    def find_by_student_id(self, student_id: str) -> List[Progress]:
        return [p for p in self._progress.values() if p.student_id == student_id]

    def find_by_module(self, module_name: str) -> List[Progress]:
        return [p for p in self._progress.values() if p.module_name == module_name]

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

    def save(self, outcome: Outcome):
        self._outcomes[outcome.outcome_id] = outcome

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

    def save(self, volunteer: Volunteer):
        self._volunteers[volunteer.volunteer_id] = volunteer
        self._user_index[volunteer.user_id] = volunteer.volunteer_id

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

    def save(self, entry: WaitlistEntry):
        self._entries[entry.entry_id] = entry
        self._email_index[entry.email] = entry.entry_id

    def find_by_id(self, entry_id: str) -> Optional[WaitlistEntry]:
        return self._entries.get(entry_id)

    def find_by_email(self, email: str) -> Optional[WaitlistEntry]:
        entry_id = self._email_index.get(email)
        if entry_id:
            return self._entries.get(entry_id)
        return None

    def find_all(self) -> List[WaitlistEntry]:
        return list(self._entries.values())

    def find_by_status(self, status: str) -> List[WaitlistEntry]:
        return [e for e in self._entries.values() if e.status == status]

    def find_pending_sorted(self) -> List[WaitlistEntry]:
        pending = [e for e in self._entries.values() if e.status == "pending"]
        return sorted(pending, key=lambda x: (-x.priority, x.applied_at or datetime.min))

    def delete(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry:
            del self._email_index[entry.email]
            del self._entries[entry_id]
            return True
        return False

    def exists_email(self, email: str) -> bool:
        return email in self._email_index


class CohortRepository:
    def __init__(self):
        self._cohorts: Dict[str, Cohort] = {}

    def save(self, cohort: Cohort):
        self._cohorts[cohort.cohort_id] = cohort

    def find_by_id(self, cohort_id: str) -> Optional[Cohort]:
        return self._cohorts.get(cohort_id)

    def find_by_name(self, name: str) -> Optional[Cohort]:
        for cohort in self._cohorts.values():
            if cohort.name == name:
                return cohort
        return None

    def find_all(self) -> List[Cohort]:
        return list(self._cohorts.values())

    def find_by_status(self, status: str) -> List[Cohort]:
        return [c for c in self._cohorts.values() if c.status == status]

    def delete(self, cohort_id: str) -> bool:
        if cohort_id in self._cohorts:
            del self._cohorts[cohort_id]
            return True
        return False


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class DuplicateError(Exception):
    pass


class Session:
    def __init__(self, session_id: str, user: User):
        self.session_id = session_id
        self.user = user
        self.created_at = datetime.now()
        self.is_active = True

    def invalidate(self):
        self.is_active = False


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
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        if not username or not email or not password:
            raise ValidationError("Username, email, and password are required")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")
        if self._user_repo.exists_email(email):
            raise DuplicateError(f"Email {email} is already registered")
        if self._user_repo.exists_username(username):
            raise DuplicateError(f"Username {username} is already taken")
        valid_roles = [Role.STUDENT, Role.ORGANIZER, Role.ADMIN, Role.VOLUNTEER]
        if role not in valid_roles:
            raise ValidationError(f"Invalid role. Must be one of {valid_roles}")
        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
            created_at=datetime.now(),
        )
        self._user_repo.save(user)
        return user

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
        session = Session(session_id=str(uuid.uuid4()), user=user)
        self._sessions[session.session_id] = session
        return session

    def logout(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session.invalidate()

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_active:
            return session
        return None

    def change_password(self, user_id: str, old_password: str, new_password: str):
        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        if not user.check_password(old_password):
            raise AuthenticationError("Current password is incorrect")
        if len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters")
        user.password_hash = hash_password(new_password)


class StudentService:
    def __init__(
        self,
        user_repo: UserRepository,
        profile_repo: StudentProfileRepository,
        progress_repo: ProgressRepository,
        outcome_repo: OutcomeRepository,
        auth_service: AuthService,
    ):
        self._user_repo = user_repo
        self._profile_repo = profile_repo
        self._progress_repo = progress_repo
        self._outcome_repo = outcome_repo
        self._auth_service = auth_service

    def create_student(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        cohort: Optional[str] = None,
    ) -> Dict[str, Any]:
        user = self._auth_service.register(
            username=username,
            email=email,
            password=password,
            role=Role.STUDENT,
            first_name=first_name,
            last_name=last_name,
        )
        profile = StudentProfile(
            profile_id=str(uuid.uuid4()),
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            cohort=cohort,
            enrollment_date=datetime.now(),
        )
        self._profile_repo.save(profile)
        return {"user": user.to_dict(), "profile": profile.to_dict()}

    def get_student_profile(
        self, requesting_user_id: str, target_user_id: str
    ) -> Dict[str, Any]:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user_id != target_user_id and requesting_user.role not in [
            Role.ADMIN,
            Role.ORGANIZER,
        ]:
            raise AuthorizationError("Access denied: insufficient permissions")
        profile = self._profile_repo.find_by_user_id(target_user_id)
        if not profile:
            raise NotFoundError("Student profile not found")
        user = self._user_repo.find_by_id(target_user_id)
        progress = self._progress_repo.find_by_student_id(profile.profile_id)
        outcomes = self._outcome_repo.find_by_student_id(profile.profile_id)
        return {
            "user": user.to_dict() if user else None,
            "profile": profile.to_dict(),
            "progress": [p.to_dict() for p in progress],
            "outcomes": [o.to_dict() for o in outcomes],
        }

    def update_student_profile(
        self,
        requesting_user_id: str,
        target_user_id: str,
        updates: Dict[str, Any],
    ) -> StudentProfile:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user_id != target_user_id and requesting_user.role not in [
            Role.ADMIN,
            Role.ORGANIZER,
        ]:
            raise AuthorizationError("Access denied: insufficient permissions")
        profile = self._profile_repo.find_by_user_id(target_user_id)
        if not profile:
            raise NotFoundError("Student profile not found")
        allowed_fields = [
            "first_name",
            "last_name",
            "phone",
            "bio",
            "github_username",
            "linkedin_url",
            "portfolio_url",
        ]
        admin_only_fields = ["cohort", "status", "notes", "graduation_date"]
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(profile, key, value)
            elif key in admin_only_fields:
                if requesting_user.role in [Role.ADMIN, Role.ORGANIZER]:
                    if key == "status":
                        profile.update_status(value)
                    elif key == "graduation_date" and isinstance(value, str):
                        profile.graduation_date = datetime.fromisoformat(value)
                    else:
                        setattr(profile, key, value)
                else:
                    raise AuthorizationError(
                        f"Field '{key}' can only be updated by admins/organizers"
                    )
        self._profile_repo.save(profile)
        return profile

    def add_progress(
        self,
        requesting_user_id: str,
        student_profile_id: str,
        module_name: str,
        completion_percentage: float = 0.0,
        notes: str = "",
    ) -> Progress:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can add progress records")
        progress = Progress(
            progress_id=str(uuid.uuid4()),
            student_id=student_profile_id,
            module_name=module_name,
            completion_percentage=completion_percentage,
            started_at=datetime.now(),
            notes=notes,
        )
        self._progress_repo.save(progress)
        return progress

    def update_progress(
        self,
        requesting_user_id: str,
        progress_id: str,
        completion_percentage: Optional[float] = None,
        grade: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Progress:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError(
                "Only admins/organizers can update progress records"
            )
        progress = self._progress_repo.find_by_id(progress_id)
        if not progress:
            raise NotFoundError("Progress record not found")
        if completion_percentage is not None:
            progress.update_completion(completion_percentage)
        if grade is not None:
            progress.assign_grade(grade)
        if notes is not None:
            progress.notes = notes
        self._progress_repo.save(progress)
        return progress

    def add_outcome(
        self,
        requesting_user_id: str,
        student_profile_id: str,
        outcome_type: str,
        description: str,
        employer: Optional[str] = None,
        job_title: Optional[str] = None,
        salary_range: Optional[str] = None,
        notes: str = "",
    ) -> Outcome:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can add outcome records")
        outcome = Outcome(
            outcome_id=str(uuid.uuid4()),
            student_id=student_profile_id,
            outcome_type=outcome_type,
            description=description,
            achieved_at=datetime.now(),
            employer=employer,
            job_title=job_title,
            salary_range=salary_range,
            notes=notes,
        )
        self._outcome_repo.save(outcome)
        return outcome

    def list_all_students(self, requesting_user_id: str) -> List[Dict[str, Any]]:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can list all students")
        profiles = self._profile_repo.find_all()
        result = []
        for profile in profiles:
            user = self._user_repo.find_by_id(profile.user_id)
            result.append(
                {
                    "user": user.to_dict() if user else None,
                    "profile": profile.to_dict(),
                }
            )
        return result


class VolunteerService:
    def __init__(
        self,
        user_repo: UserRepository,
        volunteer_repo: VolunteerRepository,
        auth_service: AuthService,
    ):
        self._user_repo = user_repo
        self._volunteer_repo = volunteer_repo
        self._auth_service = auth_service

    def register_volunteer(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        skills: Optional[List[str]] = None,
        availability: str = "flexible",
    ) -> Dict[str, Any]:
        user = self._auth_service.register(
            username=username,
            email=email,
            password=password,
            role=Role.VOLUNTEER,
            first_name=first_name,
            last_name=last_name,
        )
        volunteer = Volunteer(
            volunteer_id=str(uuid.uuid4()),
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            skills=skills or [],
            availability=availability,
            joined_at=datetime.now(),
        )
        self._volunteer_repo.save(volunteer)
        return {"user": user.to_dict(), "volunteer": volunteer.to_dict()}

    def get_volunteer(
        self, requesting_user_id: str, volunteer_id: str
    ) -> Dict[str, Any]:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError(
                "Only admins/organizers can view volunteer details"
            )
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError("Volunteer not found")
        user = self._user_repo.find_by_id(volunteer.user_id)
        return {
            "user": user.to_dict() if user else None,
            "volunteer": volunteer.to_dict(),
        }

    def list_volunteers(self, requesting_user_id: str) -> List[Dict[str, Any]]:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can list volunteers")
        volunteers = self._volunteer_repo.find_all()
        result = []
        for volunteer in volunteers:
            user = self._user_repo.find_by_id(volunteer.user_id)
            result.append(
                {
                    "user": user.to_dict() if user else None,
                    "volunteer": volunteer.to_dict(),
                }
            )
        return result

    def update_volunteer(
        self,
        requesting_user_id: str,
        volunteer_id: str,
        updates: Dict[str, Any],
    ) -> Volunteer:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can update volunteers")
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError("Volunteer not found")
        allowed_fields = ["first_name", "last_name", "phone", "availability", "notes"]
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(volunteer, key, value)
            elif key == "status":
                volunteer.update_status(value)
            elif key == "skills":
                volunteer.skills = value
            elif key == "hours_contributed":
                volunteer.log_hours(value)
        self._volunteer_repo.save(volunteer)
        return volunteer

    def log_volunteer_hours(
        self, requesting_user_id: str, volunteer_id: str, hours: float
    ) -> Volunteer:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can log volunteer hours")
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError("Volunteer not found")
        volunteer.log_hours(hours)
        self._volunteer_repo.save(volunteer)
        return volunteer


class WaitlistService:
    def __init__(
        self,
        user_repo: UserRepository,
        waitlist_repo: WaitlistRepository,
    ):
        self._user_repo = user_repo
        self._waitlist_repo = waitlist_repo

    def apply(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str] = None,
        cohort_interest: Optional[str] = None,
        background: Optional[str] = None,
        motivation: Optional[str] = None,
    ) -> WaitlistEntry:
        if not first_name or not last_name or not email:
            raise ValidationError("First name, last name, and email are required")
        if self._waitlist_repo.exists_email(email):
            raise DuplicateError("An application with this email already exists")
        entry = WaitlistEntry(
            entry_id=str(uuid.uuid4()),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            applied_at=datetime.now(),
            cohort_interest=cohort_interest,
            background=background,
            motivation=motivation,
        )
        self._waitlist_repo.save(entry)
        return entry

    def get_waitlist(self, requesting_user_id: str) -> List[WaitlistEntry]:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can view the waitlist")
        return self._waitlist_repo.find_pending_sorted()

    def get_all_applications(
        self, requesting_user_id: str
    ) -> List[WaitlistEntry]:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError(
                "Only admins/organizers can view all applications"
            )
        return self._waitlist_repo.find_all()

    def approve_application(
        self, requesting_user_id: str, entry_id: str
    ) -> WaitlistEntry:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError(
                "Only admins/organizers can approve applications"
            )
        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError("Waitlist entry not found")
        entry.approve()
        self._waitlist_repo.save(entry)
        return entry

    def reject_application(
        self, requesting_user_id: str, entry_id: str
    ) -> WaitlistEntry:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError(
                "Only admins/organizers can reject applications"
            )
        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError("Waitlist entry not found")
        entry.reject()
        self._waitlist_repo.save(entry)
        return entry

    def set_priority(
        self, requesting_user_id: str, entry_id: str, priority: int
    ) -> WaitlistEntry:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError(
                "Only admins/organizers can set application priority"
            )
        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError("Waitlist entry not found")
        entry.set_priority(priority)
        self._waitlist_repo.save(entry)
        return entry


class CohortService:
    def __init__(
        self,
        user_repo: UserRepository,
        cohort_repo: CohortRepository,
        profile_repo: StudentProfileRepository,
    ):
        self._user_repo = user_repo
        self._cohort_repo = cohort_repo
        self._profile_repo = profile_repo

    def create_cohort(
        self,
        requesting_user_id: str,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        capacity: int = 30,
        description: str = "",
    ) -> Cohort:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can create cohorts")
        if not name:
            raise ValidationError("Cohort name is required")
        cohort = Cohort(
            cohort_id=str(uuid.uuid4()),
            name=name,
            start_date=start_date,
            end_date=end_date,
            capacity=capacity,
            description=description,
        )
        self._cohort_repo.save(cohort)
        return cohort

    def get_cohort(self, cohort_id: str) -> Cohort:
        cohort = self._cohort_repo.find_by_id(cohort_id)
        if not cohort:
            raise NotFoundError("Cohort not found")
        return cohort

    def list_cohorts(self) -> List[Cohort]:
        return self._cohort_repo.find_all()

    def update_cohort(
        self,
        requesting_user_id: str,
        cohort_id: str,
        updates: Dict[str, Any],
    ) -> Cohort:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can update cohorts")
        cohort = self._cohort_repo.find_by_id(cohort_id)
        if not cohort:
            raise NotFoundError("Cohort not found")
        allowed_fields = ["name", "description", "capacity"]
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(cohort, key, value)
            elif key == "status":
                cohort.update_status(value)
            elif key == "start_date":
                cohort.start_date = (
                    datetime.fromisoformat(value) if isinstance(value, str) else value
                )
            elif key == "end_date":
                cohort.end_date = (
                    datetime.fromisoformat(value) if isinstance(value, str) else value
                )
        self._cohort_repo.save(cohort)
        return cohort

    def enroll_student(
        self,
        requesting_user_id: str,
        cohort_id: str,
        student_profile_id: str,
    ) -> Cohort:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Only admins/organizers can enroll students")
        cohort = self._cohort_repo.find_by_id(cohort_id)
        if not cohort:
            raise NotFoundError("Cohort not found")
        profile = self._profile_repo.find_by_id(student_profile_id)
        if not profile:
            raise NotFoundError("Student profile not found")
        if cohort.is_full():
            raise ValidationError("Cohort is at full capacity")
        cohort.add_student(student_profile_id)
        profile.cohort = cohort.name
        self._cohort_repo.save(cohort)
        self._profile_repo.save(profile)
        return cohort

    def remove_student_from_cohort(
        self,
        requesting_user_id: str,
        cohort_id: str,
        student_profile_id: str,
    ) -> Cohort:
        requesting_user = self._user_repo.find_by_id(requesting_user_id)
        if not requesting_user:
            raise NotFoundError("Requesting user not found")
        if requesting_user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError(
                "Only admins/organizers can remove students from cohorts"
            )
        cohort = self._cohort_repo.find_by_id(cohort_id)
        if not cohort:
            raise NotFoundError("Cohort not found")
        cohort.remove_student(student_profile_id)
        self._cohort_repo.save(cohort)
        return cohort


class AdminDashboard:
    def __init__(
        self,
        user_repo: UserRepository,
        profile_repo: StudentProfileRepository,
        progress_repo: ProgressRepository,
        outcome_repo: OutcomeRepository,
        volunteer_repo: VolunteerRepository,
        waitlist_repo: WaitlistRepository,
        cohort_repo: CohortRepository,
    ):
        self._user_repo = user_repo
        self._profile_repo = profile_repo
        self._progress_repo = progress_repo
        self._outcome_repo = outcome_repo
        self._volunteer_repo = volunteer_repo
        self._waitlist_repo = waitlist_repo
        self._cohort_repo = cohort_repo

    def _check_admin_access(self, requesting_user_id: str):
        user = self._user_repo.find_by_id(requesting_user_id)
        if not user:
            raise NotFoundError("User not found")
        if user.role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("Access denied: admin/organizer role required")

    def get_overview(self, requesting_user_id: str) -> Dict[str, Any]:
        self._check_admin_access(requesting_user_id)
        all_profiles = self._profile_repo.find_all()
        active_students = [p for p in all_profiles if p.status == "active"]
        graduated_students = [p for p in all_profiles if p.status == "graduated"]
        all_volunteers = self._volunteer_repo.find_all()
        active_volunteers = [v for v in all_volunteers if v.status == "active"]
        pending_waitlist = self._waitlist_repo.find_by_status("pending")
        all_cohorts = self._cohort_repo.find_all()
        active_cohorts = [c for c in all_cohorts if c.status == "active"]
        return {
            "students": {
                "total": len(all_profiles),
                "active": len(active_students),
                "graduated": len(graduated_students),
            },
            "volunteers": {
                "total": len(all_volunteers),
                "active": len(active_volunteers),
            },
            "waitlist": {
                "pending": len(pending_waitlist),
            },
            "cohorts": {
                "total": len(all_cohorts),
                "active": len(active_cohorts),
            },
        }

    def get_student_progress_report(
        self, requesting_user_id: str
    ) -> List[Dict[str, Any]]:
        self._check_admin_access(requesting_user_id)
        profiles = self._profile_repo.find_all()
        report = []
        for profile in profiles:
            user = self._user_repo.find_by_id(profile.user_id)
            progress_records = self._progress_repo.find_by_student_id(profile.profile_id)
            outcomes = self._outcome_repo.find_by_student_id(profile.profile_id)
            avg_completion = 0.0
            if progress_records:
                avg_completion = sum(
                    p.completion_percentage for p in progress_records
                ) / len(progress_records)
            report.append(
                {
                    "student": profile.to_dict(),
                    "user": user.to_dict() if user else None,
                    "progress_summary": {
                        "total_modules": len(progress_records),
                        "completed_modules": sum(
                            1 for p in progress_records if p.completed
                        ),
                        "average_completion": round(avg_completion, 2),
                        "modules": [p.to_dict() for p in progress_records],
                    },
                    "outcomes": [o.to_dict() for o in outcomes],
                }
            )
        return report

    def get_volunteer_report(self, requesting_user_id: str) -> List[Dict[str, Any]]:
        self._check_admin_access(requesting_user_id)
        volunteers = self._volunteer_repo.find_all()
        report = []
        for volunteer in volunteers:
            user = self._user_repo.find_by_id(volunteer.user_id)
            report.append(
                {
                    "volunteer": volunteer.to_dict(),
                    "user": user.to_dict() if user else None,
                }
            )
        return report

    def get_waitlist_report(self, requesting_user_id: str) -> Dict[str, Any]:
        self._check_admin_access(requesting_user_id)
        all_entries = self._waitlist_repo.find_all()
        pending = [e for e in all_entries if e.status == "pending"]
        approved = [e for e in all_entries if e.status == "approved"]
        rejected = [e for e in all_entries if e.status == "rejected"]
        return {
            "total": len(all_entries),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "pending_entries": [e.to_dict() for e in sorted(
                pending, key=lambda x: (-x.priority, x.applied_at or datetime.min)
            )],
            "approved_entries": [e.to_dict() for e in approved],
            "rejected_entries": [e.to_dict() for e in rejected],
        }

    def get_cohort_report(self, requesting_user_id: str) -> List[Dict[str, Any]]:
        self._check_admin_access(requesting_user_id)
        cohorts = self._cohort_repo.find_all()
        report = []
        for cohort in cohorts:
            student_profiles = []
            for student_id in cohort.student_ids:
                profile = self._profile_repo.find_by_id(student_id)
                if profile:
                    student_profiles.append(profile.to_dict())
            report.append(
                {
                    "cohort": cohort.to_dict(),
                    "students": student_profiles,
                }
            )
        return report

    def manage_user(
        self,
        requesting_user_id: str,
        target_user_id: str,
        action: str,
    ) -> User:
        self._check_admin_access(requesting_user_id)
        target_user = self._user_repo.find_by_id(target_user_id)
        if not target_user:
            raise NotFoundError("Target user not found")
        if action == "activate":
            target_user.activate()
        elif action == "deactivate":
            target_user.deactivate()
        else:
            raise ValidationError(f"Unknown action: {action}")
        self._user_repo.save(target_user)
        return target_user

    def list_all_users(self, requesting_user_id: str) -> List[Dict[str, Any]]:
        self._check_admin_access(requesting_user_id)
        users = self._user_repo.find_all()
        return [u.to_dict() for u in users]


class StudentManagementSystem:
    def __init__(self):
        self._user_repo = UserRepository()
        self._profile_repo = StudentProfileRepository()
        self._progress_repo = ProgressRepository()
        self._outcome_repo = OutcomeRepository()
        self._volunteer_repo = VolunteerRepository()
        self._waitlist_repo = WaitlistRepository()
        self._cohort_repo = CohortRepository()

        self.auth_service = AuthService(self._user_repo)
        self.student_service = StudentService(
            self._user_repo,
            self._profile_repo,
            self._progress_repo,
            self._outcome_repo,
            self.auth_service,
        )
        self.volunteer_service = VolunteerService(
            self._user_repo,
            self._volunteer_repo,
            self.auth_service,
        )
        self.waitlist_service = WaitlistService(
            self._user_repo,
            self._waitlist_repo,
        )
        self.cohort_service = CohortService(
            self._user_repo,
            self._cohort_repo,
            self._profile_repo,
        )
        self.admin_dashboard = AdminDashboard(
            self._user_repo,
            self._profile_repo,
            self._progress_repo,
            self._outcome_repo,
            self._volunteer_repo,
            self._waitlist_repo,
            self._cohort_repo,
        )

        self._initialize_default_admin()

    def _initialize_default_admin(self):
        try:
            admin = self.auth_service.register(
                username="admin",
                email="admin@freecodecamp.org",
                password="admin123",
                role=Role.ADMIN,
            )
        except DuplicateError:
            pass


def main():
    system = StudentManagementSystem()

    print("=== Student Management System Demo ===\n")

    admin_session = system.auth_service.login("admin", "admin123")
    admin_id = admin_session.user.user_id
    print(f"Admin logged in: {admin_session.user.username}")

    student_data = system.student_service.create_student(
        username="john_doe",
        email="john@example.com",
        password="password123",
        first_name="John",
        last_name="Doe",
        phone="555-1234",
        cohort="Spring 2024",
    )
    print(f"\nCreated student: {student_data['profile']['full_name']}")

    student_session = system.auth_service.login("john_doe", "password123")
    student_user_id = student_session.user.user_id
    print(f"Student logged in: {student_session.user.username}")

    profile = system.student_service.get_student_profile(student_user_id, student_user_id)
    print(f"\nStudent profile: {profile['profile']['full_name']}, Status: {profile['profile']['status']}")

    student_profile_id = profile['profile']['profile_id']
    progress = system.student_service.add_progress(
        requesting_user_id=admin_id,
        student_profile_id=student_profile_id,
        module_name="Python Basics",
        completion_percentage=75.0,
    )
    print(f"\nAdded progress: {progress.module_name} - {progress.completion_percentage}%")

    outcome = system.student_service.add_outcome(
        requesting_user_id=admin_id,
        student_profile_id=student_profile_id,
        outcome_type="employment",
        description="Hired as Junior Developer",
        employer="Tech Corp",
        job_title="Junior Developer",
    )
    print(f"Added outcome: {outcome.description}")

    volunteer_data = system.volunteer_service.register_volunteer(
        username="jane_volunteer",
        email="jane@example.com",
        password="password123",
        first_name="Jane",
        last_name="Smith",
        skills=["Python", "JavaScript"],
        availability="weekends",
    )
    print(f"\nRegistered volunteer: {volunteer_data['volunteer']['full_name']}")

    waitlist_entry = system.waitlist_service.apply(
        first_name="Bob",
        last_name="Johnson",
        email="bob@example.com",
        cohort_interest="Fall 2024",
        motivation="Want to learn programming",
    )
    print(f"\nWaitlist application: {waitlist_entry.get_full_name()}")

    cohort = system.cohort_service.create_cohort(
        requesting_user_id=admin_id,
        name="Fall 2024",
        capacity=25,
        description="Fall 2024 cohort",
    )
    print(f"\nCreated cohort: {cohort.name}")

    overview = system.admin_dashboard.get_overview(admin_id)
    print(f"\n=== Admin Dashboard Overview ===")
    print(f"Total Students: {overview['students']['total']}")
    print(f"Active Students: {overview['students']['active']}")
    print(f"Total Volunteers: {overview['volunteers']['total']}")
    print(f"Pending Waitlist: {overview['waitlist']['pending']}")
    print(f"Total Cohorts: {overview['cohorts']['total']}")

    progress_report = system.admin_dashboard.get_student_progress_report(admin_id)
    print(f"\n=== Student Progress Report ===")
    for entry in progress_report:
        print(f"Student: {entry['student']['full_name']}")
        print(f"  Modules: {entry['progress_summary']['total_modules']}")
        print(f"  Avg Completion: {entry['progress_summary']['average_completion']}%")
        print(f"  Outcomes: {len(entry['outcomes'])}")

    waitlist_report = system.admin_dashboard.get_waitlist_report(admin_id)
    print(f"\n=== Waitlist Report ===")
    print(f"Total Applications: {waitlist_report['total']}")
    print(f"Pending: {waitlist_report['pending']}")

    system.auth_service.logout(admin_session.session_id)
    system.auth_service.logout(student_session.session_id)
    print("\n=== Sessions closed ===")


if __name__ == "__main__":
    main()