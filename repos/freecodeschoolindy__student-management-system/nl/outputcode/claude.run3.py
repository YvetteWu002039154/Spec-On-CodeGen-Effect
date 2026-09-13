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
    status: str = "active"  # active, graduated, dropped, waitlisted
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        data = {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "cohort": self.cohort,
            "status": self.status,
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None,
            "graduation_date": self.graduation_date.isoformat() if self.graduation_date else None,
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


@dataclass
class Course:
    course_id: str
    name: str
    description: str
    cohort: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "course_id": self.course_id,
            "name": self.name,
            "description": self.description,
            "cohort": self.cohort,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
        }


@dataclass
class Assignment:
    assignment_id: str
    course_id: str
    title: str
    description: str
    due_date: Optional[datetime] = None
    max_score: float = 100.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "course_id": self.course_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "max_score": self.max_score,
        }


@dataclass
class StudentProgress:
    progress_id: str
    student_profile_id: str
    assignment_id: str
    score: Optional[float] = None
    submitted_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None
    feedback: str = ""
    status: str = "pending"  # pending, submitted, graded, late

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "student_profile_id": self.student_profile_id,
            "assignment_id": self.assignment_id,
            "score": self.score,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "feedback": self.feedback,
            "status": self.status,
        }


@dataclass
class Outcome:
    outcome_id: str
    student_profile_id: str
    outcome_type: str  # employed, freelance, further_education, other
    company: Optional[str] = None
    job_title: Optional[str] = None
    salary_range: Optional[str] = None
    outcome_date: Optional[datetime] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "student_profile_id": self.student_profile_id,
            "outcome_type": self.outcome_type,
            "company": self.company,
            "job_title": self.job_title,
            "salary_range": self.salary_range,
            "outcome_date": self.outcome_date.isoformat() if self.outcome_date else None,
            "notes": self.notes,
        }


@dataclass
class VolunteerProfile:
    volunteer_id: str
    user_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    availability: str = ""
    is_active: bool = True
    role_description: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

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
            "is_active": self.is_active,
            "role_description": self.role_description,
        }


@dataclass
class WaitlistEntry:
    waitlist_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    cohort_interest: Optional[str] = None
    application_date: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, accepted, rejected, withdrawn
    notes: str = ""
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "waitlist_id": self.waitlist_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "cohort_interest": self.cohort_interest,
            "application_date": self.application_date.isoformat(),
            "status": self.status,
            "notes": self.notes,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
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

    def is_admin(self) -> bool:
        return self.user.role in [Role.ADMIN, Role.ORGANIZER]

    def is_student(self) -> bool:
        return self.user.role == Role.STUDENT

    def is_volunteer(self) -> bool:
        return self.user.role == Role.VOLUNTEER


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

    def delete(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user:
            del self._email_index[user.email]
            del self._username_index[user.username]
            del self._users[user_id]
            return True
        return False


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


class CourseRepository:
    def __init__(self):
        self._courses: Dict[str, Course] = {}

    def save(self, course: Course) -> Course:
        self._courses[course.course_id] = course
        return course

    def find_by_id(self, course_id: str) -> Optional[Course]:
        return self._courses.get(course_id)

    def find_all(self) -> List[Course]:
        return list(self._courses.values())

    def find_by_cohort(self, cohort: str) -> List[Course]:
        return [c for c in self._courses.values() if c.cohort == cohort]

    def delete(self, course_id: str) -> bool:
        if course_id in self._courses:
            del self._courses[course_id]
            return True
        return False


class AssignmentRepository:
    def __init__(self):
        self._assignments: Dict[str, Assignment] = {}

    def save(self, assignment: Assignment) -> Assignment:
        self._assignments[assignment.assignment_id] = assignment
        return assignment

    def find_by_id(self, assignment_id: str) -> Optional[Assignment]:
        return self._assignments.get(assignment_id)

    def find_by_course(self, course_id: str) -> List[Assignment]:
        return [a for a in self._assignments.values() if a.course_id == course_id]

    def find_all(self) -> List[Assignment]:
        return list(self._assignments.values())

    def delete(self, assignment_id: str) -> bool:
        if assignment_id in self._assignments:
            del self._assignments[assignment_id]
            return True
        return False


class ProgressRepository:
    def __init__(self):
        self._progress: Dict[str, StudentProgress] = {}

    def save(self, progress: StudentProgress) -> StudentProgress:
        self._progress[progress.progress_id] = progress
        return progress

    def find_by_id(self, progress_id: str) -> Optional[StudentProgress]:
        return self._progress.get(progress_id)

    def find_by_student(self, student_profile_id: str) -> List[StudentProgress]:
        return [p for p in self._progress.values() if p.student_profile_id == student_profile_id]

    def find_by_assignment(self, assignment_id: str) -> List[StudentProgress]:
        return [p for p in self._progress.values() if p.assignment_id == assignment_id]

    def find_by_student_and_assignment(self, student_profile_id: str, assignment_id: str) -> Optional[StudentProgress]:
        for p in self._progress.values():
            if p.student_profile_id == student_profile_id and p.assignment_id == assignment_id:
                return p
        return None

    def find_all(self) -> List[StudentProgress]:
        return list(self._progress.values())


class OutcomeRepository:
    def __init__(self):
        self._outcomes: Dict[str, Outcome] = {}

    def save(self, outcome: Outcome) -> Outcome:
        self._outcomes[outcome.outcome_id] = outcome
        return outcome

    def find_by_id(self, outcome_id: str) -> Optional[Outcome]:
        return self._outcomes.get(outcome_id)

    def find_by_student(self, student_profile_id: str) -> List[Outcome]:
        return [o for o in self._outcomes.values() if o.student_profile_id == student_profile_id]

    def find_all(self) -> List[Outcome]:
        return list(self._outcomes.values())

    def delete(self, outcome_id: str) -> bool:
        if outcome_id in self._outcomes:
            del self._outcomes[outcome_id]
            return True
        return False


class VolunteerRepository:
    def __init__(self):
        self._volunteers: Dict[str, VolunteerProfile] = {}
        self._user_index: Dict[str, str] = {}

    def save(self, volunteer: VolunteerProfile) -> VolunteerProfile:
        self._volunteers[volunteer.volunteer_id] = volunteer
        self._user_index[volunteer.user_id] = volunteer.volunteer_id
        return volunteer

    def find_by_id(self, volunteer_id: str) -> Optional[VolunteerProfile]:
        return self._volunteers.get(volunteer_id)

    def find_by_user_id(self, user_id: str) -> Optional[VolunteerProfile]:
        volunteer_id = self._user_index.get(user_id)
        if volunteer_id:
            return self._volunteers.get(volunteer_id)
        return None

    def find_all(self) -> List[VolunteerProfile]:
        return list(self._volunteers.values())

    def find_active(self) -> List[VolunteerProfile]:
        return [v for v in self._volunteers.values() if v.is_active]

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
        self._entries[entry.waitlist_id] = entry
        self._email_index[entry.email] = entry.waitlist_id
        return entry

    def find_by_id(self, waitlist_id: str) -> Optional[WaitlistEntry]:
        return self._entries.get(waitlist_id)

    def find_by_email(self, email: str) -> Optional[WaitlistEntry]:
        waitlist_id = self._email_index.get(email)
        if waitlist_id:
            return self._entries.get(waitlist_id)
        return None

    def find_all(self) -> List[WaitlistEntry]:
        return list(self._entries.values())

    def find_by_status(self, status: str) -> List[WaitlistEntry]:
        return [e for e in self._entries.values() if e.status == status]

    def find_by_cohort(self, cohort: str) -> List[WaitlistEntry]:
        return [e for e in self._entries.values() if e.cohort_interest == cohort]

    def delete(self, waitlist_id: str) -> bool:
        entry = self._entries.get(waitlist_id)
        if entry:
            del self._email_index[entry.email]
            del self._entries[waitlist_id]
            return True
        return False


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo
        self._sessions: Dict[str, Session] = {}

    def register(self, username: str, email: str, password: str, role: str = Role.STUDENT) -> User:
        if not username or not email or not password:
            raise ValidationError("Username, email, and password are required.")
        if self._user_repo.find_by_email(email):
            raise ValidationError(f"Email '{email}' is already registered.")
        if self._user_repo.find_by_username(username):
            raise ValidationError(f"Username '{username}' is already taken.")
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
        if not user or not user.check_password(password):
            raise AuthenticationError("Invalid credentials.")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated.")
        user.last_login = datetime.now()
        session = Session(user)
        self._sessions[session.session_id] = session
        return session

    def logout(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        if not user.check_password(old_password):
            raise AuthenticationError("Old password is incorrect.")
        if not new_password:
            raise ValidationError("New password cannot be empty.")
        user.set_password(new_password)
        self._user_repo.save(user)
        return True

    def deactivate_user(self, admin_session: Session, user_id: str) -> bool:
        if not admin_session.is_admin():
            raise AuthorizationError("Only admins can deactivate users.")
        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        user.is_active = False
        self._user_repo.save(user)
        return True

    def activate_user(self, admin_session: Session, user_id: str) -> bool:
        if not admin_session.is_admin():
            raise AuthorizationError("Only admins can activate users.")
        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        user.is_active = True
        self._user_repo.save(user)
        return True


class StudentService:
    def __init__(
        self,
        student_repo: StudentProfileRepository,
        user_repo: UserRepository,
        auth_service: AuthService,
    ):
        self._student_repo = student_repo
        self._user_repo = user_repo
        self._auth_service = auth_service

    def create_student_profile(
        self,
        session: Session,
        user_id: str,
        first_name: str,
        last_name: str,
        **kwargs,
    ) -> StudentProfile:
        if not session.is_admin() and session.user.user_id != user_id:
            raise AuthorizationError("Cannot create profile for another user.")
        user = self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found.")
        if self._student_repo.find_by_user_id(user_id):
            raise ValidationError("Student profile already exists for this user.")
        profile = StudentProfile(
            profile_id=str(uuid.uuid4()),
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            **kwargs,
        )
        return self._student_repo.save(profile)

    def get_student_profile(self, session: Session, profile_id: str) -> Dict[str, Any]:
        profile = self._student_repo.find_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Student profile {profile_id} not found.")
        is_owner = session.user.user_id == profile.user_id
        include_private = is_owner or session.is_admin()
        return profile.to_dict(include_private=include_private)

    def get_my_profile(self, session: Session) -> Dict[str, Any]:
        profile = self._student_repo.find_by_user_id(session.user.user_id)
        if not profile:
            raise NotFoundError("No student profile found for current user.")
        return profile.to_dict(include_private=True)

    def update_student_profile(
        self, session: Session, profile_id: str, **updates
    ) -> StudentProfile:
        profile = self._student_repo.find_by_id(profile_id)
        if not profile:
            raise NotFoundError(f"Student profile {profile_id} not found.")
        is_owner = session.user.user_id == profile.user_id
        if not is_owner and not session.is_admin():
            raise AuthorizationError("Cannot update another student's profile.")
        restricted_fields = {"profile_id", "user_id", "created_at"}
        admin_only_fields = {"status", "cohort", "notes", "enrollment_date", "graduation_date"}
        for key, value in updates.items():
            if key in restricted_fields:
                continue
            if key in admin_only_fields and not session.is_admin():
                raise AuthorizationError(f"Only admins can update field: {key}")
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = datetime.now()
        return self._student_repo.save(profile)

    def list_students(self, session: Session, cohort: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can list all students.")
        if cohort:
            profiles = self._student_repo.find_by_cohort(cohort)
        elif status:
            profiles = self._student_repo.find_by_status(status)
        else:
            profiles = self._student_repo.find_all()
        return [p.to_dict(include_private=True) for p in profiles]

    def delete_student_profile(self, session: Session, profile_id: str) -> bool:
        if not session.is_admin():
            raise AuthorizationError("Only admins can delete student profiles.")
        if not self._student_repo.find_by_id(profile_id):
            raise NotFoundError(f"Student profile {profile_id} not found.")
        return self._student_repo.delete(profile_id)

    def register_student(
        self,
        admin_session: Session,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        cohort: Optional[str] = None,
        **profile_kwargs,
    ) -> Dict[str, Any]:
        if not admin_session.is_admin():
            raise AuthorizationError("Only admins can register students.")
        user = self._auth_service.register(username, email, password, Role.STUDENT)
        profile = StudentProfile(
            profile_id=str(uuid.uuid4()),
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name,
            cohort=cohort,
            enrollment_date=datetime.now(),
            **profile_kwargs,
        )
        self._student_repo.save(profile)
        return {"user": user.to_dict(), "profile": profile.to_dict(include_private=True)}


class CourseService:
    def __init__(self, course_repo: CourseRepository, assignment_repo: AssignmentRepository):
        self._course_repo = course_repo
        self._assignment_repo = assignment_repo

    def create_course(self, session: Session, name: str, description: str, cohort: str, **kwargs) -> Course:
        if not session.is_admin():
            raise AuthorizationError("Only admins can create courses.")
        course = Course(
            course_id=str(uuid.uuid4()),
            name=name,
            description=description,
            cohort=cohort,
            **kwargs,
        )
        return self._course_repo.save(course)

    def get_course(self, session: Session, course_id: str) -> Course:
        course = self._course_repo.find_by_id(course_id)
        if not course:
            raise NotFoundError(f"Course {course_id} not found.")
        return course

    def list_courses(self, session: Session, cohort: Optional[str] = None) -> List[Course]:
        if cohort:
            return self._course_repo.find_by_cohort(cohort)
        return self._course_repo.find_all()

    def update_course(self, session: Session, course_id: str, **updates) -> Course:
        if not session.is_admin():
            raise AuthorizationError("Only admins can update courses.")
        course = self._course_repo.find_by_id(course_id)
        if not course:
            raise NotFoundError(f"Course {course_id} not found.")
        restricted = {"course_id", "created_at"}
        for key, value in updates.items():
            if key not in restricted and hasattr(course, key):
                setattr(course, key, value)
        return self._course_repo.save(course)

    def delete_course(self, session: Session, course_id: str) -> bool:
        if not session.is_admin():
            raise AuthorizationError("Only admins can delete courses.")
        if not self._course_repo.find_by_id(course_id):
            raise NotFoundError(f"Course {course_id} not found.")
        return self._course_repo.delete(course_id)

    def create_assignment(
        self, session: Session, course_id: str, title: str, description: str, **kwargs
    ) -> Assignment:
        if not session.is_admin():
            raise AuthorizationError("Only admins can create assignments.")
        if not self._course_repo.find_by_id(course_id):
            raise NotFoundError(f"Course {course_id} not found.")
        assignment = Assignment(
            assignment_id=str(uuid.uuid4()),
            course_id=course_id,
            title=title,
            description=description,
            **kwargs,
        )
        return self._assignment_repo.save(assignment)

    def get_assignment(self, session: Session, assignment_id: str) -> Assignment:
        assignment = self._assignment_repo.find_by_id(assignment_id)
        if not assignment:
            raise NotFoundError(f"Assignment {assignment_id} not found.")
        return assignment

    def list_assignments(self, session: Session, course_id: str) -> List[Assignment]:
        if not self._course_repo.find_by_id(course_id):
            raise NotFoundError(f"Course {course_id} not found.")
        return self._assignment_repo.find_by_course(course_id)

    def delete_assignment(self, session: Session, assignment_id: str) -> bool:
        if not session.is_admin():
            raise AuthorizationError("Only admins can delete assignments.")
        if not self._assignment_repo.find_by_id(assignment_id):
            raise NotFoundError(f"Assignment {assignment_id} not found.")
        return self._assignment_repo.delete(assignment_id)


class ProgressService:
    def __init__(
        self,
        progress_repo: ProgressRepository,
        student_repo: StudentProfileRepository,
        assignment_repo: AssignmentRepository,
    ):
        self._progress_repo = progress_repo
        self._student_repo = student_repo
        self._assignment_repo = assignment_repo

    def submit_assignment(
        self, session: Session, student_profile_id: str, assignment_id: str
    ) -> StudentProgress:
        profile = self._student_repo.find_by_id(student_profile_id)
        if not profile:
            raise NotFoundError(f"Student profile {student_profile_id} not found.")
        is_owner = session.user.user_id == profile.user_id
        if not is_owner and not session.is_admin():
            raise AuthorizationError("Cannot submit assignment for another student.")
        if not self._assignment_repo.find_by_id(assignment_id):
            raise NotFoundError(f"Assignment {assignment_id} not found.")
        existing = self._progress_repo.find_by_student_and_assignment(student_profile_id, assignment_id)
        if existing:
            existing.submitted_at = datetime.now()
            existing.status = "submitted"
            return self._progress_repo.save(existing)
        progress = StudentProgress(
            progress_id=str(uuid.uuid4()),
            student_profile_id=student_profile_id,
            assignment_id=assignment_id,
            submitted_at=datetime.now(),
            status="submitted",
        )
        return self._progress_repo.save(progress)

    def grade_assignment(
        self,
        session: Session,
        progress_id: str,
        score: float,
        feedback: str = "",
    ) -> StudentProgress:
        if not session.is_admin():
            raise AuthorizationError("Only admins can grade assignments.")
        progress = self._progress_repo.find_by_id(progress_id)
        if not progress:
            raise NotFoundError(f"Progress record {progress_id} not found.")
        assignment = self._assignment_repo.find_by_id(progress.assignment_id)
        if assignment and score > assignment.max_score:
            raise ValidationError(f"Score {score} exceeds max score {assignment.max_score}.")
        if score < 0:
            raise ValidationError("Score cannot be negative.")
        progress.score = score
        progress.feedback = feedback
        progress.graded_at = datetime.now()
        progress.status = "graded"
        return self._progress_repo.save(progress)

    def get_student_progress(self, session: Session, student_profile_id: str) -> List[Dict[str, Any]]:
        profile = self._student_repo.find_by_id(student_profile_id)
        if not profile:
            raise NotFoundError(f"Student profile {student_profile_id} not found.")
        is_owner = session.user.user_id == profile.user_id
        if not is_owner and not session.is_admin():
            raise AuthorizationError("Cannot view another student's progress.")
        records = self._progress_repo.find_by_student(student_profile_id)
        return [r.to_dict() for r in records]

    def get_progress_summary(self, session: Session, student_profile_id: str) -> Dict[str, Any]:
        profile = self._student_repo.find_by_id(student_profile_id)
        if not profile:
            raise NotFoundError(f"Student profile {student_profile_id} not found.")
        is_owner = session.user.user_id == profile.user_id
        if not is_owner and not session.is_admin():
            raise AuthorizationError("Cannot view another student's progress.")
        records = self._progress_repo.find_by_student(student_profile_id)
        graded = [r for r in records if r.status == "graded" and r.score is not None]
        total_score = sum(r.score for r in graded)
        avg_score = total_score / len(graded) if graded else 0.0
        return {
            "student_profile_id": student_profile_id,
            "total_assignments": len(records),
            "submitted": len([r for r in records if r.status in ["submitted", "graded"]]),
            "graded": len(graded),
            "pending": len([r for r in records if r.status == "pending"]),
            "average_score": round(avg_score, 2),
            "total_score": round(total_score, 2),
        }

    def list_all_progress(self, session: Session) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view all progress records.")
        return [r.to_dict() for r in self._progress_repo.find_all()]


class OutcomeService:
    def __init__(self, outcome_repo: OutcomeRepository, student_repo: StudentProfileRepository):
        self._outcome_repo = outcome_repo
        self._student_repo = student_repo

    def add_outcome(
        self,
        session: Session,
        student_profile_id: str,
        outcome_type: str,
        **kwargs,
    ) -> Outcome:
        if not session.is_admin():
            raise AuthorizationError("Only admins can add outcomes.")
        if not self._student_repo.find_by_id(student_profile_id):
            raise NotFoundError(f"Student profile {student_profile_id} not found.")
        valid_types = ["employed", "freelance", "further_education", "other"]
        if outcome_type not in valid_types:
            raise ValidationError(f"Invalid outcome type. Must be one of: {valid_types}")
        outcome = Outcome(
            outcome_id=str(uuid.uuid4()),
            student_profile_id=student_profile_id,
            outcome_type=outcome_type,
            **kwargs,
        )
        return self._outcome_repo.save(outcome)

    def get_student_outcomes(self, session: Session, student_profile_id: str) -> List[Dict[str, Any]]:
        profile = self._student_repo.find_by_id(student_profile_id)
        if not profile:
            raise NotFoundError(f"Student profile {student_profile_id} not found.")
        is_owner = session.user.user_id == profile.user_id
        if not is_owner and not session.is_admin():
            raise AuthorizationError("Cannot view another student's outcomes.")
        outcomes = self._outcome_repo.find_by_student(student_profile_id)
        return [o.to_dict() for o in outcomes]

    def list_all_outcomes(self, session: Session) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can list all outcomes.")
        return [o.to_dict() for o in self._outcome_repo.find_all()]

    def update_outcome(self, session: Session, outcome_id: str, **updates) -> Outcome:
        if not session.is_admin():
            raise AuthorizationError("Only admins can update outcomes.")
        outcome = self._outcome_repo.find_by_id(outcome_id)
        if not outcome:
            raise NotFoundError(f"Outcome {outcome_id} not found.")
        restricted = {"outcome_id", "student_profile_id", "created_at"}
        for key, value in updates.items():
            if key not in restricted and hasattr(outcome, key):
                setattr(outcome, key, value)
        return self._outcome_repo.save(outcome)

    def delete_outcome(self, session: Session, outcome_id: str) -> bool:
        if not session.is_admin():
            raise AuthorizationError("Only admins can delete outcomes.")
        if not self._outcome_repo.find_by_id(outcome_id):
            raise NotFoundError(f"Outcome {outcome_id} not found.")
        return self._outcome_repo.delete(outcome_id)

    def get_outcomes_summary(self, session: Session) -> Dict[str, Any]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view outcomes summary.")
        outcomes = self._outcome_repo.find_all()
        summary: Dict[str, int] = {}
        for outcome in outcomes:
            summary[outcome.outcome_type] = summary.get(outcome.outcome_type, 0) + 1
        return {
            "total_outcomes": len(outcomes),
            "by_type": summary,
        }


class VolunteerService:
    def __init__(self, volunteer_repo: VolunteerRepository, user_repo: UserRepository, auth_service: AuthService):
        self._volunteer_repo = volunteer_repo
        self._user_repo = user_repo
        self._auth_service = auth_service

    def register_volunteer(
        self,
        admin_session: Session,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        **profile_kwargs,
    ) -> Dict[str, Any]:
        if not admin_session.is_admin():
            raise AuthorizationError("Only admins can register volunteers.")
        user = self._auth_service.register(username, email, password, Role.VOLUNTEER)
        volunteer = VolunteerProfile(
            volunteer_id=str(uuid.uuid4()),
            user_id=user.user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            **profile_kwargs,
        )
        self._volunteer_repo.save(volunteer)
        return {"user": user.to_dict(), "volunteer": volunteer.to_dict()}

    def get_volunteer(self, session: Session, volunteer_id: str) -> Dict[str, Any]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view volunteer details.")
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found.")
        return volunteer.to_dict()

    def list_volunteers(self, session: Session, active_only: bool = False) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can list volunteers.")
        if active_only:
            volunteers = self._volunteer_repo.find_active()
        else:
            volunteers = self._volunteer_repo.find_all()
        return [v.to_dict() for v in volunteers]

    def update_volunteer(self, session: Session, volunteer_id: str, **updates) -> VolunteerProfile:
        if not session.is_admin():
            raise AuthorizationError("Only admins can update volunteer profiles.")
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found.")
        restricted = {"volunteer_id", "user_id", "created_at"}
        for key, value in updates.items():
            if key not in restricted and hasattr(volunteer, key):
                setattr(volunteer, key, value)
        return self._volunteer_repo.save(volunteer)

    def deactivate_volunteer(self, session: Session, volunteer_id: str) -> bool:
        if not session.is_admin():
            raise AuthorizationError("Only admins can deactivate volunteers.")
        volunteer = self._volunteer_repo.find_by_id(volunteer_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer {volunteer_id} not found.")
        volunteer.is_active = False
        self._volunteer_repo.save(volunteer)
        return True

    def delete_volunteer(self, session: Session, volunteer_id: str) -> bool:
        if not session.is_admin():
            raise AuthorizationError("Only admins can delete volunteers.")
        if not self._volunteer_repo.find_by_id(volunteer_id):
            raise NotFoundError(f"Volunteer {volunteer_id} not found.")
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
        notes: str = "",
    ) -> WaitlistEntry:
        if not first_name or not last_name or not email:
            raise ValidationError("First name, last name, and email are required.")
        if self._waitlist_repo.find_by_email(email):
            raise ValidationError(f"Email '{email}' is already on the waitlist.")
        entry = WaitlistEntry(
            waitlist_id=str(uuid.uuid4()),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            cohort_interest=cohort_interest,
            notes=notes,
        )
        return self._waitlist_repo.save(entry)

    def get_waitlist_entry(self, session: Session, waitlist_id: str) -> Dict[str, Any]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view waitlist entries.")
        entry = self._waitlist_repo.find_by_id(waitlist_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {waitlist_id} not found.")
        return entry.to_dict()

    def list_waitlist(
        self,
        session: Session,
        status: Optional[str] = None,
        cohort: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view the waitlist.")
        if status:
            entries = self._waitlist_repo.find_by_status(status)
        elif cohort:
            entries = self._waitlist_repo.find_by_cohort(cohort)
        else:
            entries = self._waitlist_repo.find_all()
        return [e.to_dict() for e in entries]

    def review_waitlist_entry(
        self,
        session: Session,
        waitlist_id: str,
        status: str,
        notes: str = "",
    ) -> WaitlistEntry:
        if not session.is_admin():
            raise AuthorizationError("Only admins can review waitlist entries.")
        entry = self._waitlist_repo.find_by_id(waitlist_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry {waitlist_id} not found.")
        valid_statuses = ["pending", "accepted", "rejected", "withdrawn"]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        entry.status = status
        entry.reviewed_by = session.user.user_id
        entry.reviewed_at = datetime.now()
        if notes:
            entry.notes = notes
        return self._waitlist_repo.save(entry)

    def delete_waitlist_entry(self, session: Session, waitlist_id: str) -> bool:
        if not session.is_admin():
            raise AuthorizationError("Only admins can delete waitlist entries.")
        if not self._waitlist_repo.find_by_id(waitlist_id):
            raise NotFoundError(f"Waitlist entry {waitlist_id} not found.")
        return self._waitlist_repo.delete(waitlist_id)

    def get_waitlist_stats(self, session: Session) -> Dict[str, Any]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view waitlist statistics.")
        entries = self._waitlist_repo.find_all()
        stats: Dict[str, int] = {}
        for entry in entries:
            stats[entry.status] = stats.get(entry.status, 0) + 1
        return {
            "total": len(entries),
            "by_status": stats,
        }


class AdminDashboard:
    def __init__(
        self,
        student_service: StudentService,
        progress_service: ProgressService,
        outcome_service: OutcomeService,
        volunteer_service: VolunteerService,
        waitlist_service: WaitlistService,
        user_repo: UserRepository,
    ):
        self._student_service = student_service
        self._progress_service = progress_service
        self._outcome_service = outcome_service
        self._volunteer_service = volunteer_service
        self._waitlist_service = waitlist_service
        self._user_repo = user_repo

    def get_overview(self, session: Session) -> Dict[str, Any]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can access the dashboard.")
        all_students = self._student_service.list_students(session)
        active_students = [s for s in all_students if s["status"] == "active"]
        graduated_students = [s for s in all_students if s["status"] == "graduated"]
        waitlisted_students = [s for s in all_students if s["status"] == "waitlisted"]
        volunteers = self._volunteer_service.list_volunteers(session)
        active_volunteers = [v for v in volunteers if v["is_active"]]
        waitlist_stats = self._waitlist_service.get_waitlist_stats(session)
        outcomes_summary = self._outcome_service.get_outcomes_summary(session)
        all_users = self._user_repo.find_all()
        return {
            "students": {
                "total": len(all_students),
                "active": len(active_students),
                "graduated": len(graduated_students),
                "waitlisted": len(waitlisted_students),
            },
            "volunteers": {
                "total": len(volunteers),
                "active": len(active_volunteers),
            },
            "waitlist": waitlist_stats,
            "outcomes": outcomes_summary,
            "users": {
                "total": len(all_users),
            },
        }

    def get_student_detail(self, session: Session, profile_id: str) -> Dict[str, Any]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can access student details.")
        profile = self._student_service.get_student_profile(session, profile_id)
        progress_summary = self._progress_service.get_progress_summary(session, profile_id)
        outcomes = self._outcome_service.get_student_outcomes(session, profile_id)
        return {
            "profile": profile,
            "progress_summary": progress_summary,
            "outcomes": outcomes,
        }

    def list_all_students(self, session: Session, cohort: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can list all students.")
        return self._student_service.list_students(session, cohort=cohort, status=status)

    def list_all_volunteers(self, session: Session) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can list all volunteers.")
        return self._volunteer_service.list_volunteers(session)

    def get_waitlist(self, session: Session, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view the waitlist.")
        return self._waitlist_service.list_waitlist(session, status=status)

    def get_all_progress(self, session: Session) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view all progress.")
        return self._progress_service.list_all_progress(session)

    def get_all_outcomes(self, session: Session) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can view all outcomes.")
        return self._outcome_service.list_all_outcomes(session)

    def manage_users(self, session: Session) -> List[Dict[str, Any]]:
        if not session.is_admin():
            raise AuthorizationError("Only admins can manage users.")
        users = self._user_repo.find_all()
        return [u.to_dict() for u in users]


class StudentManagementSystem:
    def __init__(self):
        self._user_repo = UserRepository()
        self._student_repo = StudentProfileRepository()
        self._course_repo = CourseRepository()
        self._assignment_repo = AssignmentRepository()
        self._progress_repo = ProgressRepository()
        self._outcome_repo = OutcomeRepository()
        self._volunteer_repo = VolunteerRepository()
        self._waitlist_repo = WaitlistRepository()

        self.auth_service = AuthService(self._user_repo)
        self.student_service = StudentService(self._student_repo, self._user_repo, self.auth_service)
        self.course_service = CourseService(self._course_repo, self._assignment_repo)
        self.progress_service = ProgressService(self._progress_repo, self._student_repo, self._assignment_repo)
        self.outcome_service = OutcomeService(self._outcome_repo, self._student_repo)
        self.volunteer_service = VolunteerService(self._volunteer_repo, self._user_repo, self.auth_service)
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

    def _initialize_default_admin(self) -> None:
        try:
            self.auth_service.register(
                username="admin",
                email="admin@freecodecamp.org",
                password="admin123",
                role=Role.ADMIN,
            )
        except ValidationError:
            pass

    def login(self, username: str, password: str) -> Session:
        return self.auth_service.login(username, password)

    def logout(self, session_id: str) -> bool:
        return self.auth_service.logout(session_id)


if __name__ == "__main__":
    sms = StudentManagementSystem()

    admin_session = sms.login("admin", "admin123")
    print("Admin logged in:", admin_session.user.username)
    print("Is admin:", admin_session.is_admin())

    student_data = sms.student_service.register_student(
        admin_session=admin_session,
        username="john_doe",
        email="john@example.com",
        password="password123",
        first_name="John",
        last_name="Doe",
        cohort="2024-Spring",
    )
    print("\nStudent registered:", student_data["profile"]["first_name"], student_data["profile"]["last_name"])

    student_session = sms.login("john_doe", "password123")
    print("Student logged in:", student_session.user.username)
    print("Is student:", student_session.is_student())

    my_profile = sms.student_service.get_my_profile(student_session)
    print("\nMy profile:", my_profile["first_name"], my_profile["last_name"], "- Cohort:", my_profile["cohort"])

    course = sms.course_service.create_course(
        session=admin_session,
        name="Python Fundamentals",
        description="Learn Python from scratch",
        cohort="2024-Spring",
    )
    print("\nCourse created:", course.name)

    assignment = sms.course_service.create_assignment(
        session=admin_session,
        course_id=course.course_id,
        title="Hello World",
        description="Write your first Python program",
        max_score=100.0,
    )
    print("Assignment created:", assignment.title)

    student_profile_id = student_data["profile"]["profile_id"]
    progress = sms.progress_service.submit_assignment(
        session=student_session,
        student_profile_id=student_profile_id,
        assignment_id=assignment.assignment_id,
    )
    print("\nAssignment submitted, status:", progress.status)

    graded = sms.progress_service.grade_assignment(
        session=admin_session,
        progress_id=progress.progress_id,
        score=95.0,
        feedback="Excellent work!",
    )
    print("Assignment graded, score:", graded.score)

    summary = sms.progress_service.get_progress_summary(admin_session, student_profile_id)
    print("\nProgress summary:", summary)

    outcome = sms.outcome_service.add_outcome(
        session=admin_session,
        student_profile_id=student_profile_id,
        outcome_type="employed",
        company="Tech Corp",
        job_title="Junior Developer",
    )
    print("\nOutcome added:", outcome.outcome_type, "at", outcome.company)

    volunteer_data = sms.volunteer_service.register_volunteer(
        admin_session=admin_session,
        username="volunteer_jane",
        email="jane@example.com",
        password="vol123",
        first_name="Jane",
        last_name="Smith",
        skills=["Python", "JavaScript"],
        availability="Weekends",
    )
    print("\nVolunteer registered:", volunteer_data["volunteer"]["first_name"])

    waitlist_entry = sms.waitlist_service.add_to_waitlist(
        first_name="Bob",
        last_name="Johnson",
        email="bob@example.com",
        cohort_interest="2024-Fall",
    )
    print("\nWaitlist entry added:", waitlist_entry.full_name())

    reviewed = sms.waitlist_service.review_waitlist_entry(
        session=admin_session,
        waitlist_id=waitlist_entry.waitlist_id,
        status="accepted",
        notes="Great candidate",
    )
    print("Waitlist entry reviewed:", reviewed.status)

    overview = sms.admin_dashboard.get_overview(admin_session)
    print("\nAdmin Dashboard Overview:")
    print(json.dumps(overview, indent=2))

    sms.logout(admin_session.session_id)
    sms.logout(student_session.session_id)
    print("\nAll sessions logged out.")