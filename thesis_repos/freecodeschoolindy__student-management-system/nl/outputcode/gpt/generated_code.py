from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set


class ValidationError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class AccountStatusError(Exception):
    pass


@dataclass(frozen=True)
class ProgressRecord:
    title: str
    status: str
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValidationError("Progress title is required.")
        if not self.status or not self.status.strip():
            raise ValidationError("Progress status is required.")


@dataclass(frozen=True)
class OutcomeRecord:
    title: str
    details: str
    recorded_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValidationError("Outcome title is required.")
        if not self.details or not self.details.strip():
            raise ValidationError("Outcome details are required.")


@dataclass(frozen=True)
class VolunteerRecord:
    name: str
    role: str
    added_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("Volunteer name is required.")
        if not self.role or not self.role.strip():
            raise ValidationError("Volunteer role is required.")


class UserAccount:
    ROLE_STUDENT = "student"
    ROLE_ADMIN = "admin"
    VALID_ROLES = {ROLE_STUDENT, ROLE_ADMIN}

    def __init__(self, username: str, password: str, role: str) -> None:
        self._validate_username(username)
        self._validate_password(password)
        self._validate_role(role)
        self._username = username
        self._password = password
        self._role = role
        self._active = True
        self._created_at = datetime.utcnow()
        self._last_login_at: Optional[datetime] = None

    @staticmethod
    def _validate_username(username: str) -> None:
        if not username or not username.strip():
            raise ValidationError("Username is required.")

    @staticmethod
    def _validate_password(password: str) -> None:
        if not password:
            raise ValidationError("Password is required.")

    @classmethod
    def _validate_role(cls, role: str) -> None:
        if role not in cls.VALID_ROLES:
            raise ValidationError("Invalid role.")

    @property
    def username(self) -> str:
        return self._username

    @property
    def role(self) -> str:
        return self._role

    @property
    def active(self) -> bool:
        return self._active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def last_login_at(self) -> Optional[datetime]:
        return self._last_login_at

    def check_password(self, password: str) -> bool:
        return self._password == password

    def login(self, password: str) -> None:
        if not self._active:
            raise AccountStatusError("Account is inactive.")
        if not self.check_password(password):
            raise AuthenticationError("Invalid credentials.")
        self._last_login_at = datetime.utcnow()

    def deactivate(self) -> None:
        self._active = False

    def activate(self) -> None:
        self._active = True


class StudentProfile:
    def __init__(self, student_account: UserAccount, full_name: str, email: str) -> None:
        if student_account.role != UserAccount.ROLE_STUDENT:
            raise ValidationError("Profile can only be created for student accounts.")
        self._validate_full_name(full_name)
        self._validate_email(email)
        self._student_account = student_account
        self._full_name = full_name
        self._email = email
        self._progress_records: List[ProgressRecord] = []
        self._outcome_records: List[OutcomeRecord] = []
        self._created_at = datetime.utcnow()
        self._updated_at = self._created_at

    @staticmethod
    def _validate_full_name(full_name: str) -> None:
        if not full_name or not full_name.strip():
            raise ValidationError("Full name is required.")

    @staticmethod
    def _validate_email(email: str) -> None:
        if not email or not email.strip() or "@" not in email:
            raise ValidationError("Valid email is required.")

    @property
    def username(self) -> str:
        return self._student_account.username

    @property
    def full_name(self) -> str:
        return self._full_name

    @property
    def email(self) -> str:
        return self._email

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_profile(self, full_name: Optional[str] = None, email: Optional[str] = None) -> None:
        if full_name is not None:
            self._validate_full_name(full_name)
            self._full_name = full_name
        if email is not None:
            self._validate_email(email)
            self._email = email
        self._updated_at = datetime.utcnow()

    def add_progress(self, title: str, status: str) -> ProgressRecord:
        record = ProgressRecord(title=title, status=status)
        self._progress_records.append(record)
        self._updated_at = datetime.utcnow()
        return record

    def add_outcome(self, title: str, details: str) -> OutcomeRecord:
        record = OutcomeRecord(title=title, details=details)
        self._outcome_records.append(record)
        self._updated_at = datetime.utcnow()
        return record

    def get_progress_records(self) -> List[ProgressRecord]:
        return list(self._progress_records)

    def get_outcome_records(self) -> List[OutcomeRecord]:
        return list(self._outcome_records)

    def to_dict(self) -> Dict[str, object]:
        return {
            "username": self.username,
            "full_name": self._full_name,
            "email": self._email,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "progress": list(self._progress_records),
            "outcomes": list(self._outcome_records),
        }


class Waitlist:
    def __init__(self) -> None:
        self._usernames: List[str] = []
        self._username_set: Set[str] = set()

    def add_student(self, username: str) -> None:
        if not username or not username.strip():
            raise ValidationError("Username is required.")
        if username in self._username_set:
            raise ValidationError("Student is already on the waitlist.")
        self._usernames.append(username)
        self._username_set.add(username)

    def remove_student(self, username: str) -> None:
        if username not in self._username_set:
            raise NotFoundError("Student is not on the waitlist.")
        self._username_set.remove(username)
        self._usernames.remove(username)

    def list_students(self) -> List[str]:
        return list(self._usernames)


class VolunteerManagement:
    def __init__(self) -> None:
        self._volunteers: List[VolunteerRecord] = []

    def add_volunteer(self, name: str, role: str) -> VolunteerRecord:
        volunteer = VolunteerRecord(name=name, role=role)
        self._volunteers.append(volunteer)
        return volunteer

    def list_volunteers(self) -> List[VolunteerRecord]:
        return list(self._volunteers)


class AdminDashboard:
    def __init__(self, system: StudentManagementSystem) -> None:
        self._system = system
        self._volunteer_management = VolunteerManagement()
        self._waitlist = Waitlist()

    @property
    def volunteer_management(self) -> VolunteerManagement:
        return self._volunteer_management

    @property
    def waitlist(self) -> Waitlist:
        return self._waitlist

    def get_student_progress_outcomes(self) -> Dict[str, Dict[str, object]]:
        data: Dict[str, Dict[str, object]] = {}
        for username, profile in self._system._profiles.items():
            data[username] = {
                "profile": profile.to_dict(),
                "progress": profile.get_progress_records(),
                "outcomes": profile.get_outcome_records(),
            }
        return data

    def list_all_students(self) -> List[Dict[str, object]]:
        return [profile.to_dict() for profile in self._system._profiles.values()]


class StudentManagementSystem:
    def __init__(self) -> None:
        self._accounts: Dict[str, UserAccount] = {}
        self._profiles: Dict[str, StudentProfile] = {}
        self._admin_dashboard = AdminDashboard(self)

    @property
    def admin_dashboard(self) -> AdminDashboard:
        return self._admin_dashboard

    def register_student(self, username: str, password: str, full_name: str, email: str) -> StudentProfile:
        if username in self._accounts:
            raise ValidationError("Username already exists.")
        account = UserAccount(username=username, password=password, role=UserAccount.ROLE_STUDENT)
        profile = StudentProfile(student_account=account, full_name=full_name, email=email)
        self._accounts[username] = account
        self._profiles[username] = profile
        return profile

    def register_admin(self, username: str, password: str) -> UserAccount:
        if username in self._accounts:
            raise ValidationError("Username already exists.")
        account = UserAccount(username=username, password=password, role=UserAccount.ROLE_ADMIN)
        self._accounts[username] = account
        return account

    def login(self, username: str, password: str) -> UserAccount:
        account = self._accounts.get(username)
        if account is None:
            raise AuthenticationError("Invalid credentials.")
        account.login(password)
        return account

    def get_private_student_profile(self, requester_username: str, student_username: str) -> Dict[str, object]:
        requester = self._get_account(requester_username)
        profile = self._get_profile(student_username)
        if requester.role == UserAccount.ROLE_ADMIN or requester.username == student_username:
            return profile.to_dict()
        raise AuthorizationError("Access denied to private student profile.")

    def add_student_progress(self, admin_username: str, student_username: str, title: str, status: str) -> ProgressRecord:
        self._require_admin(admin_username)
        profile = self._get_profile(student_username)
        return profile.add_progress(title=title, status=status)

    def add_student_outcome(self, admin_username: str, student_username: str, title: str, details: str) -> OutcomeRecord:
        self._require_admin(admin_username)
        profile = self._get_profile(student_username)
        return profile.add_outcome(title=title, details=details)

    def update_own_profile(
        self,
        student_username: str,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> None:
        account = self._get_account(student_username)
        if account.role != UserAccount.ROLE_STUDENT:
            raise AuthorizationError("Only students can update student profiles.")
        profile = self._get_profile(student_username)
        profile.update_profile(full_name=full_name, email=email)

    def add_volunteer(self, admin_username: str, name: str, role: str) -> VolunteerRecord:
        self._require_admin(admin_username)
        return self._admin_dashboard.volunteer_management.add_volunteer(name=name, role=role)

    def list_volunteers(self, admin_username: str) -> List[VolunteerRecord]:
        self._require_admin(admin_username)
        return self._admin_dashboard.volunteer_management.list_volunteers()

    def add_student_to_waitlist(self, admin_username: str, student_username: str) -> None:
        self._require_admin(admin_username)
        self._get_profile(student_username)
        self._admin_dashboard.waitlist.add_student(student_username)

    def remove_student_from_waitlist(self, admin_username: str, student_username: str) -> None:
        self._require_admin(admin_username)
        self._admin_dashboard.waitlist.remove_student(student_username)

    def get_waitlist(self, admin_username: str) -> List[str]:
        self._require_admin(admin_username)
        return self._admin_dashboard.waitlist.list_students()

    def get_admin_dashboard_data(self, admin_username: str) -> Dict[str, object]:
        self._require_admin(admin_username)
        return {
            "students": self._admin_dashboard.list_all_students(),
            "student_progress_outcomes": self._admin_dashboard.get_student_progress_outcomes(),
            "volunteers": self._admin_dashboard.volunteer_management.list_volunteers(),
            "waitlist": self._admin_dashboard.waitlist.list_students(),
        }

    def _get_account(self, username: str) -> UserAccount:
        account = self._accounts.get(username)
        if account is None:
            raise NotFoundError("Account not found.")
        return account

    def _get_profile(self, username: str) -> StudentProfile:
        profile = self._profiles.get(username)
        if profile is None:
            raise NotFoundError("Student profile not found.")
        return profile

    def _require_admin(self, username: str) -> UserAccount:
        account = self._get_account(username)
        if account.role != UserAccount.ROLE_ADMIN:
            raise AuthorizationError("Admin access required.")
        return account