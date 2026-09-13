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
        valid_statuses = ["active", "graduated", "withdrawn", "waitlisted", "inactive"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
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
    start_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    notes: str = ""

    def update_progress(self, percentage: float):
        if not 0 <= percentage <= 100:
            raise ValueError("Completion percentage must be between 0 and 100")
        self.completion_percentage = percentage
        if percentage == 100:
            self.completed = True
            self.completion_date = datetime.now()

    def assign_grade(self, grade: str):
        valid_grades = ["A", "B", "C", "D", "F", "Pass", "Fail", "Incomplete"]
        if grade not in valid_grades:
            raise ValueError(f"Invalid grade. Must be one of: {valid_grades}")
        self.grade = grade

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "student_id": self.student_id,
            "module_name": self.module_name,
            "completion_percentage": self.completion_percentage,
            "grade": self.grade,
            "completed": self.completed,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "notes": self.notes,
        }


@dataclass
class Outcome:
    outcome_id: str
    student_id: str
    outcome_type: str
    description: str
    date_achieved: datetime
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
            "date_achieved": self.date_achieved.isoformat(),
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
    hours_contributed: float = 0.0
    joined_date: Optional[datetime] = None
    notes: str = ""

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def add_hours(self, hours: float):
        if hours < 0:
            raise ValueError("Hours cannot be negative")
        self.hours_contributed += hours

    def add_skill(self, skill: str):
        if skill not in self.skills:
            self.skills.append(skill)

    def update_status(self, status: str):
        valid_statuses = ["active", "inactive", "pending"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
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
            "hours_contributed": self.hours_contributed,
            "joined_date": self.joined_date.isoformat() if self.joined_date else None,
            "notes": self.notes,
        }


@dataclass
class WaitlistEntry:
    entry_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    applied_date: Optional[datetime] = None
    cohort_interest: Optional[str] = None
    status: str = "pending"
    priority: int = 0
    notes: str = ""
    background: Optional[str] = None
    motivation: Optional[str] = None

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
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "cohort_interest": self.cohort_interest,
            "status": self.status,
            "priority": self.priority,
            "notes": self.notes,
            "background": self.background,
            "motivation": self.motivation,
        }


@dataclass
class Cohort:
    cohort_id: str
    name: str
    start_date: datetime
    end_date: Optional[datetime] = None
    description: str = ""
    max_students: int = 30
    is_active: bool = True
    curriculum: List[str] = field(default_factory=list)

    def add_curriculum_item(self, item: str):
        if item not in self.curriculum:
            self.curriculum.append(item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cohort_id": self.cohort_id,
            "name": self.name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "description": self.description,
            "max_students": self.max_students,
            "is_active": self.is_active,
            "curriculum": self.curriculum,
        }


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


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

    def exists_by_email(self, email: str) -> bool:
        return email in self._email_index

    def exists_by_username(self, username: str) -> bool:
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

    def find_by_module(self, module_name: str) -> List[Progress]:
        return [p for p in self._progress.values() if p.module_name == module_name]

    def delete(self, progress_id: str) -> bool:
        if progress_id in self._progress:
            del self._progress[progress_id]
            return True
        return False

    def find_all(self) -> List[Progress]:
        return list(self._progress.values())


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

    def save(self, entry: WaitlistEntry) -> WaitlistEntry:
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
        return list(self._entries.values())

    def find_by_status(self, status: str) -> List[WaitlistEntry]:
        return [e for e in self._entries.values() if e.status == status]

    def find_pending_sorted_by_priority(self) -> List[WaitlistEntry]:
        pending = [e for e in self._entries.values() if e.status == "pending"]
        return sorted(pending, key=lambda x: x.priority, reverse=True)

    def delete(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry:
            del self._email_index[entry.email]
            del self._entries[entry_id]
            return True
        return False

    def exists_by_email(self, email: str) -> bool:
        return email in self._email_index


class CohortRepository:
    def __init__(self):
        self._cohorts: Dict[str, Cohort] = {}

    def save(self, cohort: Cohort) -> Cohort:
        self._cohorts[cohort.cohort_id] = cohort
        return cohort

    def find_by_id(self, cohort_id: str) -> Optional[Cohort]:
        return self._cohorts.get(cohort_id)

    def find_all(self) -> List[Cohort]:
        return list(self._cohorts.values())

    def find_active(self) -> List[Cohort]:
        return [c for c in self._cohorts.values() if c.is_active]

    def delete(self, cohort_id: str) -> bool:
        if cohort_id in self._cohorts:
            del self._cohorts[cohort_id]
            return True
        return False


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
        self._sessions: Dict[str, str] = {}

    def register(
        self,
        username: str,
        email: str,
        password: str,
        role: str = Role.STUDENT,
    ) -> User:
        if self._user_repo.exists_by_email(email):
            raise ValidationError(f"Email '{email}' is already registered")
        if self._user_repo.exists_by_username(username):
            raise ValidationError(f"Username '{username}' is already taken")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")
        valid_roles = [Role.STUDENT, Role.ORGANIZER, Role.ADMIN, Role.VOLUNTEER]
        if role not in valid_roles:
            raise ValidationError(f"Invalid role. Must be one of: {valid_roles}")

        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
            created_at=datetime.now(),
        )
        return self._user_repo.save(user)

    def login(self, username: str, password: str) -> Dict[str, Any]:
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
        session_token = str(uuid.uuid4())
        self._sessions[session_token] = user.user_id

        return {
            "token": session_token,
            "user": user.to_dict(),
        }

    def logout(self, token: str) -> bool:
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def get_user_from_token(self, token: str) -> Optional[User]:
        user_id = self._sessions.get(token)
        if user_id:
            return self._user_repo.find_by_id(user_id)
        return None

    def is_authenticated(self, token: str) -> bool:
        return token in self._sessions

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id '{user_id}' not found")
        if not user.check_password(old_password):
            raise AuthenticationError("Old password is incorrect")
        if len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters long")
        user.password_hash = hash_password(new_password)
        self._user_repo.save(user)
        return True


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
        bio: Optional[str] = None,
    ) -> Dict[str, Any]:
        user = self._auth_service.register(username, email, password, Role.STUDENT)
        profile = StudentProfile(
            profile_id=str(uuid.uuid4()),
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            cohort=cohort,
            bio=bio,
            enrollment_date=datetime.now(),
        )
        self._profile_repo.save(profile)
        return {"user": user.to_dict(), "profile": profile.to_dict()}

    def get_student_profile(self, user_id: str, requester_id: str, requester_role: str) -> Dict[str, Any]:
        if requester_id != user_id and requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to view this profile")

        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id '{user_id}' not found")

        profile = self._profile_repo.find_by_user_id(user_id)
        if not profile:
            raise NotFoundError(f"Profile for user '{user_id}' not found")

        progress = self._progress_repo.find_by_student_id(profile.profile_id)
        outcomes = self._outcome_repo.find_by_student_id(profile.profile_id)

        return {
            "user": user.to_dict(),
            "profile": profile.to_dict(),
            "progress": [p.to_dict() for p in progress],
            "outcomes": [o.to_dict() for o in outcomes],
        }

    def update_student_profile(
        self,
        user_id: str,
        requester_id: str,
        requester_role: str,
        **kwargs,
    ) -> StudentProfile:
        if requester_id != user_id and requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to update this profile")

        profile = self._profile_repo.find_by_user_id(user_id)
        if not profile:
            raise NotFoundError(f"Profile for user '{user_id}' not found")

        updatable_fields = [
            "first_name", "last_name", "phone", "bio", "cohort",
            "github_username", "linkedin_url", "portfolio_url", "notes",
        ]
        for key, value in kwargs.items():
            if key in updatable_fields:
                setattr(profile, key, value)

        if "status" in kwargs and requester_role in [Role.ADMIN, Role.ORGANIZER]:
            profile.update_status(kwargs["status"])

        return self._profile_repo.save(profile)

    def add_progress(
        self,
        student_id: str,
        module_name: str,
        completion_percentage: float,
        grade: Optional[str] = None,
        notes: str = "",
    ) -> Progress:
        profile = self._profile_repo.find_by_id(student_id)
        if not profile:
            raise NotFoundError(f"Student profile '{student_id}' not found")

        progress = Progress(
            progress_id=str(uuid.uuid4()),
            student_id=student_id,
            module_name=module_name,
            completion_percentage=completion_percentage,
            grade=grade,
            notes=notes,
            start_date=datetime.now(),
        )
        if completion_percentage == 100:
            progress.completed = True
            progress.completion_date = datetime.now()

        return self._progress_repo.save(progress)

    def update_progress(
        self,
        progress_id: str,
        completion_percentage: Optional[float] = None,
        grade: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Progress:
        progress = self._progress_repo.find_by_id(progress_id)
        if not progress:
            raise NotFoundError(f"Progress record '{progress_id}' not found")

        if completion_percentage is not None:
            progress.update_progress(completion_percentage)
        if grade is not None:
            progress.assign_grade(grade)
        if notes is not None:
            progress.notes = notes

        return self._progress_repo.save(progress)

    def add_outcome(
        self,
        student_id: str,
        outcome_type: str,
        description: str,
        employer: Optional[str] = None,
        job_title: Optional[str] = None,
        salary_range: Optional[str] = None,
        notes: str = "",
    ) -> Outcome:
        profile = self._profile_repo.find_by_id(student_id)
        if not profile:
            raise NotFoundError(f"Student profile '{student_id}' not found")

        outcome = Outcome(
            outcome_id=str(uuid.uuid4()),
            student_id=student_id,
            outcome_type=outcome_type,
            description=description,
            date_achieved=datetime.now(),
            employer=employer,
            job_title=job_title,
            salary_range=salary_range,
            notes=notes,
        )
        return self._outcome_repo.save(outcome)

    def get_all_students(self, requester_role: str) -> List[Dict[str, Any]]:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to view all students")

        users = self._user_repo.find_by_role(Role.STUDENT)
        result = []
        for user in users:
            profile = self._profile_repo.find_by_user_id(user.user_id)
            result.append({
                "user": user.to_dict(),
                "profile": profile.to_dict() if profile else None,
            })
        return result

    def delete_student(self, user_id: str, requester_role: str) -> bool:
        if requester_role != Role.ADMIN:
            raise AuthorizationError("Only admins can delete students")

        profile = self._profile_repo.find_by_user_id(user_id)
        if profile:
            for progress in self._progress_repo.find_by_student_id(profile.profile_id):
                self._progress_repo.delete(progress.progress_id)
            for outcome in self._outcome_repo.find_by_student_id(profile.profile_id):
                self._outcome_repo.delete(outcome.outcome_id)
            self._profile_repo.delete(profile.profile_id)

        return self._user_repo.delete(user_id)


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

    def create_volunteer(
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
        user = self._auth_service.register(username, email, password, Role.VOLUNTEER)
        volunteer = Volunteer(
            volunteer_id=str(uuid.uuid4()),
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            skills=skills or [],
            availability=availability,
            joined_date=datetime.now(),
        )
        self._volunteer_repo.save(volunteer)
        return {"user": user.to_dict(), "volunteer": volunteer.to_dict()}

    def get_volunteer(self, volunteer_id: str, requester_role: str) -> Dict[str, Any]:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to view volunteer details")

        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer '{volunteer_id}' not found")

        user = self._user_repo.find_by_id(volunteer.user_id)
        return {
            "user": user.to_dict() if user else None,
            "volunteer": volunteer.to_dict(),
        }

    def get_all_volunteers(self, requester_role: str) -> List[Dict[str, Any]]:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to view all volunteers")

        volunteers = self._volunteer_repo.find_all()
        result = []
        for volunteer in volunteers:
            user = self._user_repo.find_by_id(volunteer.user_id)
            result.append({
                "user": user.to_dict() if user else None,
                "volunteer": volunteer.to_dict(),
            })
        return result

    def update_volunteer(
        self,
        volunteer_id: str,
        requester_role: str,
        **kwargs,
    ) -> Volunteer:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to update volunteer details")

        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer '{volunteer_id}' not found")

        updatable_fields = ["first_name", "last_name", "phone", "availability", "notes"]
        for key, value in kwargs.items():
            if key in updatable_fields:
                setattr(volunteer, key, value)

        if "status" in kwargs:
            volunteer.update_status(kwargs["status"])
        if "hours" in kwargs:
            volunteer.add_hours(kwargs["hours"])

        return self._volunteer_repo.save(volunteer)

    def delete_volunteer(self, volunteer_id: str, requester_role: str) -> bool:
        if requester_role != Role.ADMIN:
            raise AuthorizationError("Only admins can delete volunteers")

        return self._volunteer_repo.delete(volunteer_id)


class WaitlistService:
    def __init__(self, waitlist_repo: WaitlistRepository):
        self._waitlist_repo = waitlist_repo

    def add_to_waitlist(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str] = None,
        cohort_interest: Optional[str] = None,
        background: Optional[str] = None,
        motivation: Optional[str] = None,
    ) -> WaitlistEntry:
        if self._waitlist_repo.exists_by_email(email):
            raise ValidationError(f"Email '{email}' is already on the waitlist")

        entry = WaitlistEntry(
            entry_id=str(uuid.uuid4()),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            applied_date=datetime.now(),
            cohort_interest=cohort_interest,
            background=background,
            motivation=motivation,
        )
        return self._waitlist_repo.save(entry)

    def get_waitlist(self, requester_role: str) -> List[Dict[str, Any]]:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to view the waitlist")

        entries = self._waitlist_repo.find_pending_sorted_by_priority()
        return [e.to_dict() for e in entries]

    def get_all_waitlist_entries(self, requester_role: str) -> List[Dict[str, Any]]:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to view the waitlist")

        entries = self._waitlist_repo.find_all()
        return [e.to_dict() for e in entries]

    def approve_entry(self, entry_id: str, requester_role: str) -> WaitlistEntry:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to approve waitlist entries")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry '{entry_id}' not found")

        entry.approve()
        return self._waitlist_repo.save(entry)

    def reject_entry(self, entry_id: str, requester_role: str) -> WaitlistEntry:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to reject waitlist entries")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry '{entry_id}' not found")

        entry.reject()
        return self._waitlist_repo.save(entry)

    def set_priority(self, entry_id: str, priority: int, requester_role: str) -> WaitlistEntry:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to set priority")

        entry = self._waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry '{entry_id}' not found")

        entry.set_priority(priority)
        return self._waitlist_repo.save(entry)

    def delete_entry(self, entry_id: str, requester_role: str) -> bool:
        if requester_role != Role.ADMIN:
            raise AuthorizationError("Only admins can delete waitlist entries")

        return self._waitlist_repo.delete(entry_id)


class AdminDashboardService:
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

    def _require_admin_or_organizer(self, requester_role: str):
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to access the admin dashboard")

    def get_dashboard_summary(self, requester_role: str) -> Dict[str, Any]:
        self._require_admin_or_organizer(requester_role)

        all_students = self._user_repo.find_by_role(Role.STUDENT)
        all_profiles = self._profile_repo.find_all()
        all_volunteers = self._volunteer_repo.find_all()
        all_waitlist = self._waitlist_repo.find_all()
        all_progress = self._progress_repo.find_all()
        all_outcomes = self._outcome_repo.find_all()
        active_cohorts = self._cohort_repo.find_active()

        active_students = [p for p in all_profiles if p.status == "active"]
        graduated_students = [p for p in all_profiles if p.status == "graduated"]
        waitlisted_students = [p for p in all_profiles if p.status == "waitlisted"]
        pending_waitlist = [e for e in all_waitlist if e.status == "pending"]
        active_volunteers = [v for v in all_volunteers if v.status == "active"]

        completed_modules = [p for p in all_progress if p.completed]
        avg_completion = (
            sum(p.completion_percentage for p in all_progress) / len(all_progress)
            if all_progress else 0
        )

        return {
            "total_students": len(all_students),
            "active_students": len(active_students),
            "graduated_students": len(graduated_students),
            "waitlisted_students": len(waitlisted_students),
            "total_volunteers": len(all_volunteers),
            "active_volunteers": len(active_volunteers),
            "pending_waitlist_entries": len(pending_waitlist),
            "total_waitlist_entries": len(all_waitlist),
            "active_cohorts": len(active_cohorts),
            "total_progress_records": len(all_progress),
            "completed_modules": len(completed_modules),
            "average_completion_percentage": round(avg_completion, 2),
            "total_outcomes": len(all_outcomes),
        }

    def get_student_progress_report(self, requester_role: str) -> List[Dict[str, Any]]:
        self._require_admin_or_organizer(requester_role)

        profiles = self._profile_repo.find_all()
        report = []
        for profile in profiles:
            user = self._user_repo.find_by_id(profile.user_id)
            progress_records = self._progress_repo.find_by_student_id(profile.profile_id)
            outcomes = self._outcome_repo.find_by_student_id(profile.profile_id)

            total_modules = len(progress_records)
            completed_modules = sum(1 for p in progress_records if p.completed)
            avg_completion = (
                sum(p.completion_percentage for p in progress_records) / total_modules
                if total_modules > 0 else 0
            )

            report.append({
                "student_name": profile.get_full_name(),
                "user_id": profile.user_id,
                "profile_id": profile.profile_id,
                "cohort": profile.cohort,
                "status": profile.status,
                "total_modules": total_modules,
                "completed_modules": completed_modules,
                "average_completion": round(avg_completion, 2),
                "total_outcomes": len(outcomes),
                "progress": [p.to_dict() for p in progress_records],
                "outcomes": [o.to_dict() for o in outcomes],
            })
        return report

    def get_outcomes_report(self, requester_role: str) -> Dict[str, Any]:
        self._require_admin_or_organizer(requester_role)

        all_outcomes = self._outcome_repo.find_all()
        outcomes_by_type: Dict[str, List[Dict]] = {}
        for outcome in all_outcomes:
            if outcome.outcome_type not in outcomes_by_type:
                outcomes_by_type[outcome.outcome_type] = []
            outcomes_by_type[outcome.outcome_type].append(outcome.to_dict())

        return {
            "total_outcomes": len(all_outcomes),
            "outcomes_by_type": outcomes_by_type,
            "all_outcomes": [o.to_dict() for o in all_outcomes],
        }

    def get_volunteer_report(self, requester_role: str) -> Dict[str, Any]:
        self._require_admin_or_organizer(requester_role)

        volunteers = self._volunteer_repo.find_all()
        total_hours = sum(v.hours_contributed for v in volunteers)
        active_volunteers = [v for v in volunteers if v.status == "active"]

        return {
            "total_volunteers": len(volunteers),
            "active_volunteers": len(active_volunteers),
            "total_hours_contributed": total_hours,
            "volunteers": [v.to_dict() for v in volunteers],
        }

    def get_waitlist_report(self, requester_role: str) -> Dict[str, Any]:
        self._require_admin_or_organizer(requester_role)

        all_entries = self._waitlist_repo.find_all()
        pending = [e for e in all_entries if e.status == "pending"]
        approved = [e for e in all_entries if e.status == "approved"]
        rejected = [e for e in all_entries if e.status == "rejected"]

        return {
            "total_entries": len(all_entries),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "pending_entries": [e.to_dict() for e in sorted(pending, key=lambda x: x.priority, reverse=True)],
            "approved_entries": [e.to_dict() for e in approved],
            "rejected_entries": [e.to_dict() for e in rejected],
        }

    def manage_user(
        self,
        target_user_id: str,
        requester_role: str,
        action: str,
    ) -> Dict[str, Any]:
        if requester_role != Role.ADMIN:
            raise AuthorizationError("Only admins can manage users")

        user = self._user_repo.find_by_id(target_user_id)
        if not user:
            raise NotFoundError(f"User '{target_user_id}' not found")

        if action == "activate":
            user.activate()
        elif action == "deactivate":
            user.deactivate()
        else:
            raise ValidationError(f"Unknown action '{action}'")

        self._user_repo.save(user)
        return {"message": f"User '{user.username}' has been {action}d", "user": user.to_dict()}

    def create_cohort(
        self,
        name: str,
        start_date: datetime,
        requester_role: str,
        end_date: Optional[datetime] = None,
        description: str = "",
        max_students: int = 30,
    ) -> Cohort:
        if requester_role not in [Role.ADMIN, Role.ORGANIZER]:
            raise AuthorizationError("You do not have permission to create cohorts")

        cohort = Cohort(
            cohort_id=str(uuid.uuid4()),
            name=name,
            start_date=start_date,
            end_date=end_date,
            description=description,
            max_students=max_students,
        )
        return self._cohort_repo.save(cohort)

    def get_cohorts(self, requester_role: str) -> List[Dict[str, Any]]:
        self._require_admin_or_organizer(requester_role)
        cohorts = self._cohort_repo.find_all()
        return [c.to_dict() for c in cohorts]


class StudentManagementSystem:
    def __init__(self):
        self._user_repo = UserRepository()
        self._profile_repo = StudentProfileRepository()
        self._progress_repo = ProgressRepository()
        self._outcome_repo = OutcomeRepository()
        self._volunteer_repo = VolunteerRepository()
        self._waitlist_repo = WaitlistRepository()
        self._cohort_repo = CohortRepository()

        self._auth_service = AuthService(self._user_repo)
        self._student_service = StudentService(
            self._user_repo,
            self._profile_repo,
            self._progress_repo,
            self._outcome_repo,
            self._auth_service,
        )
        self._volunteer_service = VolunteerService(
            self._user_repo,
            self._volunteer_repo,
            self._auth_service,
        )
        self._waitlist_service = WaitlistService(self._waitlist_repo)
        self._admin_dashboard = AdminDashboardService(
            self._user_repo,
            self._profile_repo,
            self._progress_repo,
            self._outcome_repo,
            self._volunteer_repo,
            self._waitlist_repo,
            self._cohort_repo,
        )

    @property
    def auth(self) -> AuthService:
        return self._auth_service

    @property
    def students(self) -> StudentService:
        return self._student_service

    @property
    def volunteers(self) -> VolunteerService:
        return self._volunteer_service

    @property
    def waitlist(self) -> WaitlistService:
        return self._waitlist_service

    @property
    def admin(self) -> AdminDashboardService:
        return self._admin_dashboard

    def create_admin(self, username: str, email: str, password: str) -> User:
        return self._auth_service.register(username, email, password, Role.ADMIN)

    def create_organizer(self, username: str, email: str, password: str) -> User:
        return self._auth_service.register(username, email, password, Role.ORGANIZER)


if __name__ == "__main__":
    sms = StudentManagementSystem()

    admin = sms.create_admin("admin", "admin@freecode.school", "adminpass123")
    print(f"Created admin: {admin.username}")

    organizer = sms.create_organizer("organizer1", "organizer@freecode.school", "orgpass123")
    print(f"Created organizer: {organizer.username}")

    admin_login = sms.auth.login("admin", "adminpass123")
    admin_token = admin_login["token"]
    print(f"Admin logged in with token: {admin_token[:8]}...")

    student_data = sms.students.create_student(
        username="john_doe",
        email="john@example.com",
        password="student123",
        first_name="John",
        last_name="Doe",
        cohort="Cohort 2024",
        bio="Aspiring software developer",
    )
    print(f"Created student: {student_data['profile']['full_name']}")

    student_login = sms.auth.login("john_doe", "student123")
    student_token = student_login["token"]
    student_user_id = student_login["user"]["user_id"]
    print(f"Student logged in: {student_login['user']['username']}")

    student_profile = sms.students.get_student_profile(
        user_id=student_user_id,
        requester_id=student_user_id,
        requester_role=Role.STUDENT,
    )
    print(f"Student profile retrieved: {student_profile['profile']['full_name']}")

    profile_id = student_profile["profile"]["profile_id"]
    progress = sms.students.add_progress(
        student_id=profile_id,
        module_name="Python Basics",
        completion_percentage=75.0,
        notes="Making good progress",
    )
    print(f"Added progress: {progress.module_name} - {progress.completion_percentage}%")

    outcome = sms.students.add_outcome(
        student_id=profile_id,
        outcome_type="employment",
        description="Got a job as junior developer",
        employer="Tech Corp",
        job_title="Junior Developer",
    )
    print(f"Added outcome: {outcome.outcome_type} - {outcome.description}")

    volunteer_data = sms.volunteers.create_volunteer(
        username="volunteer1",
        email="volunteer@example.com",
        password="volpass123",
        first_name="Jane",
        last_name="Smith",
        skills=["Python", "JavaScript"],
        availability="weekends",
    )
    print(f"Created volunteer: {volunteer_data['volunteer']['full_name']}")

    waitlist_entry = sms.waitlist.add_to_waitlist(
        first_name="Alice",
        last_name="Johnson",
        email="alice@example.com",
        cohort_interest="Cohort 2025",
        motivation="Want to learn programming",
    )
    print(f"Added to waitlist: {waitlist_entry.get_full_name()}")

    dashboard = sms.admin.get_dashboard_summary(requester_role=Role.ADMIN)
    print("\n=== Admin Dashboard Summary ===")
    for key, value in dashboard.items():
        print(f"  {key}: {value}")

    progress_report = sms.admin.get_student_progress_report(requester_role=Role.ADMIN)
    print(f"\nProgress report for {len(progress_report)} students")

    waitlist_report = sms.admin.get_waitlist_report(requester_role=Role.ADMIN)
    print(f"Waitlist report: {waitlist_report['total_entries']} total entries")

    cohort = sms.admin.create_cohort(
        name="Cohort 2025",
        start_date=datetime(2025, 1, 15),
        requester_role=Role.ADMIN,
        description="Spring 2025 cohort",
        max_students=25,
    )
    print(f"\nCreated cohort: {cohort.name}")

    try:
        sms.students.get_student_profile(
            user_id=student_user_id,
            requester_id="other_user_id",
            requester_role=Role.STUDENT,
        )
    except AuthorizationError as e:
        print(f"\nAuthorization error (expected): {e}")

    sms.auth.logout(student_token)
    print("Student logged out successfully")

    print("\nStudent Management System demo completed successfully!")