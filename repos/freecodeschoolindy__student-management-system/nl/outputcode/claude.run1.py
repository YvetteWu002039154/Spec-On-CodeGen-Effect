from datetime import datetime, date
from typing import Optional, List, Dict, Any
import hashlib
import secrets
import json


class PasswordHasher:
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed, salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        check_hash, _ = PasswordHasher.hash_password(password, salt)
        return check_hash == hashed


class Permission:
    VIEW_OWN_PROFILE = "view_own_profile"
    VIEW_ALL_PROFILES = "view_all_profiles"
    EDIT_OWN_PROFILE = "edit_own_profile"
    EDIT_ALL_PROFILES = "edit_all_profiles"
    MANAGE_STUDENTS = "manage_students"
    MANAGE_VOLUNTEERS = "manage_volunteers"
    MANAGE_WAITLIST = "manage_waitlist"
    VIEW_DASHBOARD = "view_dashboard"
    ADMIN_ACCESS = "admin_access"


class Role:
    STUDENT = "student"
    ORGANIZER = "organizer"
    ADMIN = "admin"
    VOLUNTEER = "volunteer"

    PERMISSIONS = {
        STUDENT: [
            Permission.VIEW_OWN_PROFILE,
            Permission.EDIT_OWN_PROFILE,
        ],
        ORGANIZER: [
            Permission.VIEW_OWN_PROFILE,
            Permission.EDIT_OWN_PROFILE,
            Permission.VIEW_ALL_PROFILES,
            Permission.MANAGE_STUDENTS,
            Permission.MANAGE_VOLUNTEERS,
            Permission.MANAGE_WAITLIST,
            Permission.VIEW_DASHBOARD,
        ],
        ADMIN: [
            Permission.VIEW_OWN_PROFILE,
            Permission.EDIT_OWN_PROFILE,
            Permission.VIEW_ALL_PROFILES,
            Permission.EDIT_ALL_PROFILES,
            Permission.MANAGE_STUDENTS,
            Permission.MANAGE_VOLUNTEERS,
            Permission.MANAGE_WAITLIST,
            Permission.VIEW_DASHBOARD,
            Permission.ADMIN_ACCESS,
        ],
        VOLUNTEER: [
            Permission.VIEW_OWN_PROFILE,
            Permission.EDIT_OWN_PROFILE,
            Permission.VIEW_ALL_PROFILES,
        ],
    }


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        password: str,
        role: str = Role.STUDENT,
        first_name: str = "",
        last_name: str = "",
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.is_active = True
        self.created_at = datetime.now()
        self.last_login: Optional[datetime] = None
        self._password_hash, self._salt = PasswordHasher.hash_password(password)
        self._session_token: Optional[str] = None

    def check_password(self, password: str) -> bool:
        return PasswordHasher.verify_password(password, self._password_hash, self._salt)

    def set_password(self, new_password: str):
        self._password_hash, self._salt = PasswordHasher.hash_password(new_password)

    def has_permission(self, permission: str) -> bool:
        return permission in Role.PERMISSIONS.get(self.role, [])

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def generate_session_token(self) -> str:
        self._session_token = secrets.token_hex(32)
        self.last_login = datetime.now()
        return self._session_token

    def invalidate_session(self):
        self._session_token = None

    def is_authenticated(self, token: str) -> bool:
        return self._session_token is not None and self._session_token == token

    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        data = {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
        if include_private:
            data["last_login"] = self.last_login.isoformat() if self.last_login else None
        return data

    def __repr__(self):
        return f"<User id={self.user_id} username={self.username} role={self.role}>"


class StudentProgress:
    def __init__(self):
        self.completed_modules: List[str] = []
        self.current_module: Optional[str] = None
        self.assignments: Dict[str, str] = {}
        self.grades: Dict[str, float] = {}
        self.attendance_records: List[Dict[str, Any]] = []
        self.notes: List[Dict[str, Any]] = []

    def add_completed_module(self, module_name: str):
        if module_name not in self.completed_modules:
            self.completed_modules.append(module_name)

    def set_current_module(self, module_name: str):
        self.current_module = module_name

    def submit_assignment(self, assignment_name: str, status: str = "submitted"):
        self.assignments[assignment_name] = status

    def add_grade(self, assignment_name: str, grade: float):
        if 0.0 <= grade <= 100.0:
            self.grades[assignment_name] = grade
        else:
            raise ValueError("Grade must be between 0 and 100")

    def get_average_grade(self) -> Optional[float]:
        if not self.grades:
            return None
        return sum(self.grades.values()) / len(self.grades)

    def record_attendance(self, session_date: date, present: bool, notes: str = ""):
        self.attendance_records.append({
            "date": session_date.isoformat(),
            "present": present,
            "notes": notes,
        })

    def get_attendance_rate(self) -> Optional[float]:
        if not self.attendance_records:
            return None
        present_count = sum(1 for r in self.attendance_records if r["present"])
        return (present_count / len(self.attendance_records)) * 100

    def add_note(self, note: str, author: str):
        self.notes.append({
            "note": note,
            "author": author,
            "timestamp": datetime.now().isoformat(),
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completed_modules": self.completed_modules,
            "current_module": self.current_module,
            "assignments": self.assignments,
            "grades": self.grades,
            "average_grade": self.get_average_grade(),
            "attendance_records": self.attendance_records,
            "attendance_rate": self.get_attendance_rate(),
            "notes": self.notes,
        }


class StudentOutcome:
    ENROLLED = "enrolled"
    GRADUATED = "graduated"
    DROPPED = "dropped"
    ON_HOLD = "on_hold"
    WAITLISTED = "waitlisted"

    def __init__(self):
        self.status: str = self.ENROLLED
        self.graduation_date: Optional[date] = None
        self.employment_status: Optional[str] = None
        self.employer: Optional[str] = None
        self.job_title: Optional[str] = None
        self.outcome_notes: str = ""
        self.history: List[Dict[str, Any]] = []

    def update_status(self, new_status: str, notes: str = ""):
        old_status = self.status
        self.status = new_status
        self.history.append({
            "from_status": old_status,
            "to_status": new_status,
            "timestamp": datetime.now().isoformat(),
            "notes": notes,
        })
        if new_status == self.GRADUATED:
            self.graduation_date = date.today()

    def set_employment(self, employer: str, job_title: str, employment_status: str = "employed"):
        self.employer = employer
        self.job_title = job_title
        self.employment_status = employment_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "graduation_date": self.graduation_date.isoformat() if self.graduation_date else None,
            "employment_status": self.employment_status,
            "employer": self.employer,
            "job_title": self.job_title,
            "outcome_notes": self.outcome_notes,
            "history": self.history,
        }


class StudentProfile:
    def __init__(
        self,
        user: User,
        phone: str = "",
        address: str = "",
        date_of_birth: Optional[date] = None,
        emergency_contact: str = "",
        bio: str = "",
        cohort: str = "",
        enrollment_date: Optional[date] = None,
    ):
        self.user = user
        self.phone = phone
        self.address = address
        self.date_of_birth = date_of_birth
        self.emergency_contact = emergency_contact
        self.bio = bio
        self.cohort = cohort
        self.enrollment_date = enrollment_date or date.today()
        self.progress = StudentProgress()
        self.outcome = StudentOutcome()
        self.skills: List[str] = []
        self.github_username: str = ""
        self.linkedin_url: str = ""
        self.portfolio_url: str = ""

    def add_skill(self, skill: str):
        if skill not in self.skills:
            self.skills.append(skill)

    def remove_skill(self, skill: str):
        if skill in self.skills:
            self.skills.remove(skill)

    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        data = {
            "user": self.user.to_dict(include_private=include_private),
            "cohort": self.cohort,
            "enrollment_date": self.enrollment_date.isoformat(),
            "bio": self.bio,
            "skills": self.skills,
            "github_username": self.github_username,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
            "outcome": self.outcome.to_dict(),
        }
        if include_private:
            data.update({
                "phone": self.phone,
                "address": self.address,
                "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
                "emergency_contact": self.emergency_contact,
                "progress": self.progress.to_dict(),
            })
        return data

    def __repr__(self):
        return f"<StudentProfile user={self.user.username} cohort={self.cohort}>"


class Volunteer:
    def __init__(
        self,
        user: User,
        skills: Optional[List[str]] = None,
        availability: str = "",
        area_of_expertise: str = "",
    ):
        self.user = user
        self.skills = skills or []
        self.availability = availability
        self.area_of_expertise = area_of_expertise
        self.is_active = True
        self.hours_contributed: float = 0.0
        self.sessions: List[Dict[str, Any]] = []
        self.joined_date = date.today()

    def log_session(self, session_date: date, hours: float, description: str = ""):
        if hours <= 0:
            raise ValueError("Hours must be positive")
        self.sessions.append({
            "date": session_date.isoformat(),
            "hours": hours,
            "description": description,
        })
        self.hours_contributed += hours

    def add_skill(self, skill: str):
        if skill not in self.skills:
            self.skills.append(skill)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user": self.user.to_dict(),
            "skills": self.skills,
            "availability": self.availability,
            "area_of_expertise": self.area_of_expertise,
            "is_active": self.is_active,
            "hours_contributed": self.hours_contributed,
            "sessions": self.sessions,
            "joined_date": self.joined_date.isoformat(),
        }

    def __repr__(self):
        return f"<Volunteer user={self.user.username} hours={self.hours_contributed}>"


class WaitlistEntry:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ENROLLED = "enrolled"

    def __init__(
        self,
        entry_id: int,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        reason: str = "",
        cohort_preference: str = "",
    ):
        self.entry_id = entry_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.reason = reason
        self.cohort_preference = cohort_preference
        self.status = self.PENDING
        self.applied_date = date.today()
        self.reviewed_by: Optional[str] = None
        self.review_notes: str = ""
        self.review_date: Optional[date] = None

    def approve(self, reviewer: str, notes: str = ""):
        self.status = self.APPROVED
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.review_date = date.today()

    def reject(self, reviewer: str, notes: str = ""):
        self.status = self.REJECTED
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.review_date = date.today()

    def mark_enrolled(self):
        self.status = self.ENROLLED

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "reason": self.reason,
            "cohort_preference": self.cohort_preference,
            "status": self.status,
            "applied_date": self.applied_date.isoformat(),
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "review_date": self.review_date.isoformat() if self.review_date else None,
        }

    def __repr__(self):
        return f"<WaitlistEntry id={self.entry_id} name={self.get_full_name()} status={self.status}>"


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


class AuthService:
    def __init__(self):
        self._active_sessions: Dict[str, int] = {}

    def login(self, user: User, password: str) -> str:
        if not user.is_active:
            raise AuthenticationError("Account is inactive")
        if not user.check_password(password):
            raise AuthenticationError("Invalid credentials")
        token = user.generate_session_token()
        self._active_sessions[token] = user.user_id
        return token

    def logout(self, user: User, token: str):
        if token in self._active_sessions:
            del self._active_sessions[token]
        user.invalidate_session()

    def validate_session(self, token: str) -> Optional[int]:
        return self._active_sessions.get(token)

    def require_permission(self, user: User, token: str, permission: str):
        if not user.is_authenticated(token):
            raise AuthenticationError("Not authenticated")
        if not user.has_permission(permission):
            raise AuthorizationError(f"Permission denied: {permission}")


class UserRepository:
    def __init__(self):
        self._users: Dict[int, User] = {}
        self._next_id = 1

    def create(
        self,
        username: str,
        email: str,
        password: str,
        role: str = Role.STUDENT,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        if self.find_by_username(username):
            raise ValidationError(f"Username '{username}' already exists")
        if self.find_by_email(email):
            raise ValidationError(f"Email '{email}' already exists")
        user = User(
            user_id=self._next_id,
            username=username,
            email=email,
            password=password,
            role=role,
            first_name=first_name,
            last_name=last_name,
        )
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def find_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def find_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def get_all(self) -> List[User]:
        return list(self._users.values())

    def get_by_role(self, role: str) -> List[User]:
        return [u for u in self._users.values() if u.role == role]

    def delete(self, user_id: int) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    def update(self, user_id: int, **kwargs) -> Optional[User]:
        user = self.find_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ("user_id", "_password_hash", "_salt"):
                setattr(user, key, value)
        return user


class StudentProfileRepository:
    def __init__(self):
        self._profiles: Dict[int, StudentProfile] = {}

    def create(self, user: User, **kwargs) -> StudentProfile:
        if user.user_id in self._profiles:
            raise ValidationError(f"Profile already exists for user {user.user_id}")
        profile = StudentProfile(user=user, **kwargs)
        self._profiles[user.user_id] = profile
        return profile

    def find_by_user_id(self, user_id: int) -> Optional[StudentProfile]:
        return self._profiles.get(user_id)

    def get_all(self) -> List[StudentProfile]:
        return list(self._profiles.values())

    def get_by_cohort(self, cohort: str) -> List[StudentProfile]:
        return [p for p in self._profiles.values() if p.cohort == cohort]

    def get_by_outcome_status(self, status: str) -> List[StudentProfile]:
        return [p for p in self._profiles.values() if p.outcome.status == status]

    def delete(self, user_id: int) -> bool:
        if user_id in self._profiles:
            del self._profiles[user_id]
            return True
        return False


class VolunteerRepository:
    def __init__(self):
        self._volunteers: Dict[int, Volunteer] = {}

    def create(self, user: User, **kwargs) -> Volunteer:
        if user.user_id in self._volunteers:
            raise ValidationError(f"Volunteer record already exists for user {user.user_id}")
        volunteer = Volunteer(user=user, **kwargs)
        self._volunteers[user.user_id] = volunteer
        return volunteer

    def find_by_user_id(self, user_id: int) -> Optional[Volunteer]:
        return self._volunteers.get(user_id)

    def get_all(self) -> List[Volunteer]:
        return list(self._volunteers.values())

    def get_active(self) -> List[Volunteer]:
        return [v for v in self._volunteers.values() if v.is_active]

    def delete(self, user_id: int) -> bool:
        if user_id in self._volunteers:
            del self._volunteers[user_id]
            return True
        return False


class WaitlistRepository:
    def __init__(self):
        self._entries: Dict[int, WaitlistEntry] = {}
        self._next_id = 1

    def create(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        reason: str = "",
        cohort_preference: str = "",
    ) -> WaitlistEntry:
        for entry in self._entries.values():
            if entry.email == email and entry.status == WaitlistEntry.PENDING:
                raise ValidationError(f"Email '{email}' already has a pending waitlist entry")
        entry = WaitlistEntry(
            entry_id=self._next_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            reason=reason,
            cohort_preference=cohort_preference,
        )
        self._entries[self._next_id] = entry
        self._next_id += 1
        return entry

    def find_by_id(self, entry_id: int) -> Optional[WaitlistEntry]:
        return self._entries.get(entry_id)

    def get_all(self) -> List[WaitlistEntry]:
        return list(self._entries.values())

    def get_by_status(self, status: str) -> List[WaitlistEntry]:
        return [e for e in self._entries.values() if e.status == status]

    def get_pending(self) -> List[WaitlistEntry]:
        return self.get_by_status(WaitlistEntry.PENDING)

    def delete(self, entry_id: int) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False


class AdminDashboard:
    def __init__(
        self,
        student_repo: StudentProfileRepository,
        volunteer_repo: VolunteerRepository,
        waitlist_repo: WaitlistRepository,
        user_repo: UserRepository,
    ):
        self.student_repo = student_repo
        self.volunteer_repo = volunteer_repo
        self.waitlist_repo = waitlist_repo
        self.user_repo = user_repo

    def get_student_summary(self) -> Dict[str, Any]:
        profiles = self.student_repo.get_all()
        total = len(profiles)
        by_status: Dict[str, int] = {}
        for profile in profiles:
            status = profile.outcome.status
            by_status[status] = by_status.get(status, 0) + 1

        cohorts: Dict[str, int] = {}
        for profile in profiles:
            cohort = profile.cohort or "Unassigned"
            cohorts[cohort] = cohorts.get(cohort, 0) + 1

        return {
            "total_students": total,
            "by_status": by_status,
            "by_cohort": cohorts,
        }

    def get_student_progress_report(self) -> List[Dict[str, Any]]:
        profiles = self.student_repo.get_all()
        report = []
        for profile in profiles:
            avg_grade = profile.progress.get_average_grade()
            attendance_rate = profile.progress.get_attendance_rate()
            report.append({
                "student": profile.user.get_full_name() or profile.user.username,
                "cohort": profile.cohort,
                "current_module": profile.progress.current_module,
                "completed_modules": len(profile.progress.completed_modules),
                "average_grade": avg_grade,
                "attendance_rate": attendance_rate,
                "outcome_status": profile.outcome.status,
            })
        return report

    def get_volunteer_summary(self) -> Dict[str, Any]:
        volunteers = self.volunteer_repo.get_all()
        active = self.volunteer_repo.get_active()
        total_hours = sum(v.hours_contributed for v in volunteers)
        return {
            "total_volunteers": len(volunteers),
            "active_volunteers": len(active),
            "total_hours_contributed": total_hours,
            "volunteers": [v.to_dict() for v in volunteers],
        }

    def get_waitlist_summary(self) -> Dict[str, Any]:
        all_entries = self.waitlist_repo.get_all()
        pending = self.waitlist_repo.get_pending()
        approved = self.waitlist_repo.get_by_status(WaitlistEntry.APPROVED)
        rejected = self.waitlist_repo.get_by_status(WaitlistEntry.REJECTED)
        enrolled = self.waitlist_repo.get_by_status(WaitlistEntry.ENROLLED)
        return {
            "total": len(all_entries),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "enrolled": len(enrolled),
            "pending_entries": [e.to_dict() for e in pending],
        }

    def get_full_dashboard(self) -> Dict[str, Any]:
        return {
            "students": self.get_student_summary(),
            "progress_report": self.get_student_progress_report(),
            "volunteers": self.get_volunteer_summary(),
            "waitlist": self.get_waitlist_summary(),
        }


class StudentManagementSystem:
    def __init__(self):
        self.user_repo = UserRepository()
        self.student_repo = StudentProfileRepository()
        self.volunteer_repo = VolunteerRepository()
        self.waitlist_repo = WaitlistRepository()
        self.auth_service = AuthService()
        self.dashboard = AdminDashboard(
            student_repo=self.student_repo,
            volunteer_repo=self.volunteer_repo,
            waitlist_repo=self.waitlist_repo,
            user_repo=self.user_repo,
        )
        self._current_user: Optional[User] = None
        self._current_token: Optional[str] = None

    def register_student(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        cohort: str = "",
        phone: str = "",
        bio: str = "",
    ) -> StudentProfile:
        user = self.user_repo.create(
            username=username,
            email=email,
            password=password,
            role=Role.STUDENT,
            first_name=first_name,
            last_name=last_name,
        )
        profile = self.student_repo.create(
            user=user,
            cohort=cohort,
            phone=phone,
            bio=bio,
        )
        return profile

    def register_admin(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        user = self.user_repo.create(
            username=username,
            email=email,
            password=password,
            role=Role.ADMIN,
            first_name=first_name,
            last_name=last_name,
        )
        return user

    def register_organizer(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        user = self.user_repo.create(
            username=username,
            email=email,
            password=password,
            role=Role.ORGANIZER,
            first_name=first_name,
            last_name=last_name,
        )
        return user

    def register_volunteer(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        skills: Optional[List[str]] = None,
        availability: str = "",
        area_of_expertise: str = "",
    ) -> Volunteer:
        user = self.user_repo.create(
            username=username,
            email=email,
            password=password,
            role=Role.VOLUNTEER,
            first_name=first_name,
            last_name=last_name,
        )
        volunteer = self.volunteer_repo.create(
            user=user,
            skills=skills or [],
            availability=availability,
            area_of_expertise=area_of_expertise,
        )
        return volunteer

    def login(self, username: str, password: str) -> str:
        user = self.user_repo.find_by_username(username)
        if not user:
            raise AuthenticationError("Invalid credentials")
        token = self.auth_service.login(user, password)
        self._current_user = user
        self._current_token = token
        return token

    def logout(self, username: str, token: str):
        user = self.user_repo.find_by_username(username)
        if user:
            self.auth_service.logout(user, token)
        if self._current_user and self._current_user.username == username:
            self._current_user = None
            self._current_token = None

    def get_student_profile(
        self, requesting_user: User, token: str, target_user_id: int
    ) -> Dict[str, Any]:
        self.auth_service.require_permission(requesting_user, token, Permission.VIEW_OWN_PROFILE)

        is_own_profile = requesting_user.user_id == target_user_id
        can_view_all = requesting_user.has_permission(Permission.VIEW_ALL_PROFILES)

        if not is_own_profile and not can_view_all:
            raise AuthorizationError("Cannot view other students' profiles")

        profile = self.student_repo.find_by_user_id(target_user_id)
        if not profile:
            raise NotFoundError(f"Student profile not found for user_id={target_user_id}")

        include_private = is_own_profile or can_view_all
        return profile.to_dict(include_private=include_private)

    def update_student_profile(
        self,
        requesting_user: User,
        token: str,
        target_user_id: int,
        **kwargs,
    ) -> StudentProfile:
        self.auth_service.require_permission(requesting_user, token, Permission.EDIT_OWN_PROFILE)

        is_own_profile = requesting_user.user_id == target_user_id
        can_edit_all = requesting_user.has_permission(Permission.EDIT_ALL_PROFILES)

        if not is_own_profile and not can_edit_all:
            raise AuthorizationError("Cannot edit other students' profiles")

        profile = self.student_repo.find_by_user_id(target_user_id)
        if not profile:
            raise NotFoundError(f"Student profile not found for user_id={target_user_id}")

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        return profile

    def update_student_progress(
        self,
        requesting_user: User,
        token: str,
        student_user_id: int,
        action: str,
        **kwargs,
    ):
        self.auth_service.require_permission(requesting_user, token, Permission.MANAGE_STUDENTS)

        profile = self.student_repo.find_by_user_id(student_user_id)
        if not profile:
            raise NotFoundError(f"Student profile not found for user_id={student_user_id}")

        if action == "add_completed_module":
            profile.progress.add_completed_module(kwargs["module_name"])
        elif action == "set_current_module":
            profile.progress.set_current_module(kwargs["module_name"])
        elif action == "add_grade":
            profile.progress.add_grade(kwargs["assignment_name"], kwargs["grade"])
        elif action == "record_attendance":
            profile.progress.record_attendance(
                kwargs["session_date"], kwargs["present"], kwargs.get("notes", "")
            )
        elif action == "add_note":
            profile.progress.add_note(kwargs["note"], requesting_user.username)
        else:
            raise ValidationError(f"Unknown action: {action}")

        return profile

    def update_student_outcome(
        self,
        requesting_user: User,
        token: str,
        student_user_id: int,
        new_status: str,
        notes: str = "",
    ):
        self.auth_service.require_permission(requesting_user, token, Permission.MANAGE_STUDENTS)

        profile = self.student_repo.find_by_user_id(student_user_id)
        if not profile:
            raise NotFoundError(f"Student profile not found for user_id={student_user_id}")

        profile.outcome.update_status(new_status, notes)
        return profile

    def add_waitlist_entry(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        reason: str = "",
        cohort_preference: str = "",
    ) -> WaitlistEntry:
        return self.waitlist_repo.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            reason=reason,
            cohort_preference=cohort_preference,
        )

    def review_waitlist_entry(
        self,
        requesting_user: User,
        token: str,
        entry_id: int,
        decision: str,
        notes: str = "",
    ) -> WaitlistEntry:
        self.auth_service.require_permission(requesting_user, token, Permission.MANAGE_WAITLIST)

        entry = self.waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry not found: {entry_id}")

        if decision == "approve":
            entry.approve(requesting_user.username, notes)
        elif decision == "reject":
            entry.reject(requesting_user.username, notes)
        else:
            raise ValidationError(f"Invalid decision: {decision}. Must be 'approve' or 'reject'")

        return entry

    def enroll_from_waitlist(
        self,
        requesting_user: User,
        token: str,
        entry_id: int,
        password: str,
        cohort: str = "",
    ) -> StudentProfile:
        self.auth_service.require_permission(requesting_user, token, Permission.MANAGE_WAITLIST)

        entry = self.waitlist_repo.find_by_id(entry_id)
        if not entry:
            raise NotFoundError(f"Waitlist entry not found: {entry_id}")

        if entry.status != WaitlistEntry.APPROVED:
            raise ValidationError("Waitlist entry must be approved before enrollment")

        username = f"{entry.first_name.lower()}.{entry.last_name.lower()}"
        base_username = username
        counter = 1
        while self.user_repo.find_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1

        profile = self.register_student(
            username=username,
            email=entry.email,
            password=password,
            first_name=entry.first_name,
            last_name=entry.last_name,
            cohort=cohort or entry.cohort_preference,
            phone=entry.phone,
        )
        entry.mark_enrolled()
        return profile

    def manage_volunteer(
        self,
        requesting_user: User,
        token: str,
        volunteer_user_id: int,
        action: str,
        **kwargs,
    ) -> Volunteer:
        self.auth_service.require_permission(requesting_user, token, Permission.MANAGE_VOLUNTEERS)

        volunteer = self.volunteer_repo.find_by_user_id(volunteer_user_id)
        if not volunteer:
            raise NotFoundError(f"Volunteer not found for user_id={volunteer_user_id}")

        if action == "deactivate":
            volunteer.is_active = False
        elif action == "activate":
            volunteer.is_active = True
        elif action == "log_session":
            volunteer.log_session(
                kwargs["session_date"], kwargs["hours"], kwargs.get("description", "")
            )
        elif action == "add_skill":
            volunteer.add_skill(kwargs["skill"])
        else:
            raise ValidationError(f"Unknown action: {action}")

        return volunteer

    def get_admin_dashboard(self, requesting_user: User, token: str) -> Dict[str, Any]:
        self.auth_service.require_permission(requesting_user, token, Permission.VIEW_DASHBOARD)
        return self.dashboard.get_full_dashboard()

    def get_all_students(
        self, requesting_user: User, token: str
    ) -> List[Dict[str, Any]]:
        self.auth_service.require_permission(requesting_user, token, Permission.VIEW_ALL_PROFILES)
        profiles = self.student_repo.get_all()
        return [p.to_dict(include_private=True) for p in profiles]

    def get_all_volunteers(
        self, requesting_user: User, token: str
    ) -> List[Dict[str, Any]]:
        self.auth_service.require_permission(requesting_user, token, Permission.MANAGE_VOLUNTEERS)
        volunteers = self.volunteer_repo.get_all()
        return [v.to_dict() for v in volunteers]

    def get_waitlist(
        self, requesting_user: User, token: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self.auth_service.require_permission(requesting_user, token, Permission.MANAGE_WAITLIST)
        if status:
            entries = self.waitlist_repo.get_by_status(status)
        else:
            entries = self.waitlist_repo.get_all()
        return [e.to_dict() for e in entries]

    def deactivate_user(
        self, requesting_user: User, token: str, target_user_id: int
    ) -> User:
        self.auth_service.require_permission(requesting_user, token, Permission.ADMIN_ACCESS)
        user = self.user_repo.find_by_id(target_user_id)
        if not user:
            raise NotFoundError(f"User not found: {target_user_id}")
        user.is_active = False
        return user

    def activate_user(
        self, requesting_user: User, token: str, target_user_id: int
    ) -> User:
        self.auth_service.require_permission(requesting_user, token, Permission.ADMIN_ACCESS)
        user = self.user_repo.find_by_id(target_user_id)
        if not user:
            raise NotFoundError(f"User not found: {target_user_id}")
        user.is_active = True
        return user

    def change_user_role(
        self, requesting_user: User, token: str, target_user_id: int, new_role: str
    ) -> User:
        self.auth_service.require_permission(requesting_user, token, Permission.ADMIN_ACCESS)
        valid_roles = [Role.STUDENT, Role.ORGANIZER, Role.ADMIN, Role.VOLUNTEER]
        if new_role not in valid_roles:
            raise ValidationError(f"Invalid role: {new_role}")
        user = self.user_repo.find_by_id(target_user_id)
        if not user:
            raise NotFoundError(f"User not found: {target_user_id}")
        user.role = new_role
        return user

    def search_students(
        self,
        requesting_user: User,
        token: str,
        query: str = "",
        cohort: str = "",
        outcome_status: str = "",
    ) -> List[Dict[str, Any]]:
        self.auth_service.require_permission(requesting_user, token, Permission.VIEW_ALL_PROFILES)
        profiles = self.student_repo.get_all()

        if cohort:
            profiles = [p for p in profiles if p.cohort == cohort]

        if outcome_status:
            profiles = [p for p in profiles if p.outcome.status == outcome_status]

        if query:
            query_lower = query.lower()
            filtered = []
            for p in profiles:
                full_name = p.user.get_full_name().lower()
                username = p.user.username.lower()
                email = p.user.email.lower()
                if (
                    query_lower in full_name
                    or query_lower in username
                    or query_lower in email
                ):
                    filtered.append(p)
            profiles = filtered

        return [p.to_dict(include_private=True) for p in profiles]


def main():
    system = StudentManagementSystem()

    admin = system.register_admin(
        username="admin",
        email="admin@freecodecamp.org",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
    )
    print(f"Created admin: {admin}")

    organizer = system.register_organizer(
        username="organizer1",
        email="organizer@freecodecamp.org",
        password="OrgPass123!",
        first_name="Jane",
        last_name="Organizer",
    )
    print(f"Created organizer: {organizer}")

    student1 = system.register_student(
        username="john.doe",
        email="john.doe@example.com",
        password="StudentPass123!",
        first_name="John",
        last_name="Doe",
        cohort="2024-Spring",
        bio="Aspiring web developer",
    )
    print(f"Created student: {student1}")

    student2 = system.register_student(
        username="jane.smith",
        email="jane.smith@example.com",
        password="StudentPass456!",
        first_name="Jane",
        last_name="Smith",
        cohort="2024-Spring",
        bio="Learning Python",
    )
    print(f"Created student: {student2}")

    volunteer1 = system.register_volunteer(
        username="vol.mentor",
        email="mentor@example.com",
        password="VolPass123!",
        first_name="Bob",
        last_name="Mentor",
        skills=["Python", "JavaScript", "React"],
        availability="Weekends",
        area_of_expertise="Web Development",
    )
    print(f"Created volunteer: {volunteer1}")

    waitlist_entry = system.add_waitlist_entry(
        first_name="Alice",
        last_name="Waitlisted",
        email="alice@example.com",
        phone="555-1234",
        reason="I want to learn programming",
        cohort_preference="2024-Fall",
    )
    print(f"Created waitlist entry: {waitlist_entry}")

    admin_token = system.login("admin", "AdminPass123!")
    print(f"\nAdmin logged in with token: {admin_token[:16]}...")

    student1_token = system.login("john.doe", "StudentPass123!")
    print(f"Student logged in with token: {student1_token[:16]}...")

    admin_user = system.user_repo.find_by_username("admin")
    student1_user = system.user_repo.find_by_username("john.doe")
    student2_user = system.user_repo.find_by_username("jane.smith")
    volunteer_user = system.user_repo.find_by_username("vol.mentor")

    system.update_student_progress(
        requesting_user=admin_user,
        token=admin_token,
        student_user_id=student1_user.user_id,
        action="set_current_module",
        module_name="HTML & CSS Basics",
    )

    system.update_student_progress(
        requesting_user=admin_user,
        token=admin_token,
        student_user_id=student1_user.user_id,
        action="add_grade",
        assignment_name="HTML Project",
        grade=85.5,
    )

    system.update_student_progress(
        requesting_user=admin_user,
        token=admin_token,
        student_user_id=student1_user.user_id,
        action="record_attendance",
        session_date=date.today(),
        present=True,
        notes="Great participation",
    )

    own_profile = system.get_student_profile(
        requesting_user=student1_user,
        token=student1_token,
        target_user_id=student1_user.user_id,
    )
    print(f"\nStudent's own profile (private view):")
    print(json.dumps(own_profile, indent=2, default=str))

    try:
        other_profile = system.get_student_profile(
            requesting_user=student1_user,
            token=student1_token,
            target_user_id=student2_user.user_id,
        )
    except AuthorizationError as e:
        print(f"\nExpected authorization error: {e}")

    all_students = system.get_all_students(
        requesting_user=admin_user,
        token=admin_token,
    )
    print(f"\nAdmin can see all {len(all_students)} students")

    system.review_waitlist_entry(
        requesting_user=admin_user,
        token=admin_token,
        entry_id=waitlist_entry.entry_id,
        decision="approve",
        notes="Looks like a great candidate",
    )
    print(f"\nWaitlist entry approved: {waitlist_entry.status}")

    new_student_profile = system.enroll_from_waitlist(
        requesting_user=admin_user,
        token=admin_token,
        entry_id=waitlist_entry.entry_id,
        password="NewStudentPass123!",
        cohort="2024-Fall",
    )
    print(f"Enrolled from waitlist: {new_student_profile}")

    system.manage_volunteer(
        requesting_user=admin_user,
        token=admin_token,
        volunteer_user_id=volunteer_user.user_id,
        action="log_session",
        session_date=date.today(),
        hours=3.5,
        description="Mentoring session with students",
    )

    dashboard = system.get_admin_dashboard(
        requesting_user=admin_user,
        token=admin_token,
    )
    print(f"\nAdmin Dashboard Summary:")
    print(f"Total Students: {dashboard['students']['total_students']}")
    print(f"Students by Status: {dashboard['students']['by_status']}")
    print(f"Total Volunteers: {dashboard['volunteers']['total_volunteers']}")
    print(f"Total Volunteer Hours: {dashboard['volunteers']['total_hours_contributed']}")
    print(f"Waitlist - Total: {dashboard['waitlist']['total']}, Pending: {dashboard['waitlist']['pending']}")

    search_results = system.search_students(
        requesting_user=admin_user,
        token=admin_token,
        cohort="2024-Spring",
    )
    print(f"\nStudents in 2024-Spring cohort: {len(search_results)}")

    system.logout("admin", admin_token)
    system.logout("john.doe", student1_token)
    print("\nUsers logged out successfully")

    print("\nStudent Management System demo completed successfully!")


if __name__ == "__main__":
    main()