from enum import Enum
from typing import Dict, List, Optional, Any

class Role(Enum):
    STUDENT = "student"
    ADMIN = "admin"
    ORGANIZER = "organizer"
    VOLUNTEER = "volunteer"

class User:
    def __init__(self, username: str, password: str, role: Role):
        self._username = username
        self._password = password
        self._role = role

    @property
    def username(self) -> str:
        return self._username

    @property
    def role(self) -> Role:
        return self._role

    def check_password(self, password: str) -> bool:
        return self._password == password

class StudentProfile:
    def __init__(self, student: 'Student', details: Dict[str, Any]):
        self._student = student
        self._details = details

    def view_profile(self, viewer: User) -> Dict[str, Any]:
        if viewer.username == self._student.username or viewer.role in (Role.ADMIN, Role.ORGANIZER):
            return self._details
        raise PermissionError("Profile is private and only visible to the student, admins, or organizers.")

class Student(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password, Role.STUDENT)
        self._profile: Optional[StudentProfile] = None
        self._progress: str = "Not started"
        self._outcomes: str = "None"

    @property
    def profile(self) -> Optional[StudentProfile]:
        return self._profile

    def set_profile(self, details: Dict[str, Any]) -> None:
        self._profile = StudentProfile(self, details)

    @property
    def progress(self) -> str:
        return self._progress

    @progress.setter
    def progress(self, value: str) -> None:
        self._progress = value

    @property
    def outcomes(self) -> str:
        return self._outcomes

    @outcomes.setter
    def outcomes(self, value: str) -> None:
        self._outcomes = value

class Admin(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password, Role.ADMIN)

class Organizer(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password, Role.ORGANIZER)

class Volunteer(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password, Role.VOLUNTEER)

class Waitlist:
    def __init__(self):
        self._entries: List[str] = []

    def add_entry(self, name: str) -> None:
        if name not in self._entries:
            self._entries.append(name)

    def remove_entry(self, name: str) -> None:
        if name in self._entries:
            self._entries.remove(name)

    def get_entries(self) -> List[str]:
        return self._entries.copy()

class AdminDashboard:
    def __init__(self, system: 'StudentManagementSystem'):
        self._system = system

    def _check_admin_access(self, viewer: User) -> None:
        if viewer.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied. Admin or Organizer role required.")

    def view_student_progress_and_outcomes(self, viewer: User) -> Dict[str, Dict[str, str]]:
        self._check_admin_access(viewer)
        report = {}
        for user in self._system.get_all_users():
            if isinstance(user, Student):
                report[user.username] = {
                    "progress": user.progress,
                    "outcomes": user.outcomes
                }
        return report

    def add_volunteer(self, viewer: User, volunteer: Volunteer) -> None:
        self._check_admin_access(viewer)
        self._system.register_user(volunteer)

    def remove_volunteer(self, viewer: User, username: str) -> None:
        self._check_admin_access(viewer)
        self._system.remove_user(username, Role.VOLUNTEER)

    def get_volunteers(self, viewer: User) -> List[Volunteer]:
        self._check_admin_access(viewer)
        return [u for u in self._system.get_all_users() if isinstance(u, Volunteer)]

    def add_to_waitlist(self, viewer: User, name: str) -> None:
        self._check_admin_access(viewer)
        self._system.waitlist.add_entry(name)

    def remove_from_waitlist(self, viewer: User, name: str) -> None:
        self._check_admin_access(viewer)
        self._system.waitlist.remove_entry(name)

    def view_waitlist(self, viewer: User) -> List[str]:
        self._check_admin_access(viewer)
        return self._system.waitlist.get_entries()

class StudentManagementSystem:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._waitlist: Waitlist = Waitlist()
        self._dashboard: AdminDashboard = AdminDashboard(self)

    @property
    def waitlist(self) -> Waitlist:
        return self._waitlist

    @property
    def dashboard(self) -> AdminDashboard:
        return self._dashboard

    def register_user(self, user: User) -> None:
        if user.username in self._users:
            raise ValueError("Username already exists.")
        self._users[user.username] = user

    def remove_user(self, username: str, expected_role: Optional[Role] = None) -> None:
        if username in self._users:
            if expected_role and self._users[username].role != expected_role:
                raise ValueError(f"User is not a {expected_role.value}.")
            del self._users[username]

    def login(self, username: str, password: str) -> User:
        user = self._users.get(username)
        if user and user.check_password(password):
            return user
        raise ValueError("Invalid username or password.")

    def get_all_users(self) -> List[User]:
        return list(self._users.values())