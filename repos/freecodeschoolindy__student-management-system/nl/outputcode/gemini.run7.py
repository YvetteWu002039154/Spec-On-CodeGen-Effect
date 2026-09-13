from enum import Enum
from typing import Dict, List, Optional

class Role(Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"
    VOLUNTEER = "VOLUNTEER"

class User:
    def __init__(self, username: str, password: str, role: Role):
        self.username = username
        self._password = password
        self.role = role

    def check_password(self, password: str) -> bool:
        return self._password == password

class StudentProfile:
    def __init__(self, student: User):
        self.student = student
        self.progress: str = "Not started"
        self.outcomes: str = "No outcomes recorded yet"

    def update_progress(self, progress: str) -> None:
        self.progress = progress

    def update_outcomes(self, outcomes: str) -> None:
        self.outcomes = outcomes

class AdminDashboard:
    def __init__(self, system: 'StudentManagementSystem'):
        self._system = system

    def _verify_admin_or_organizer(self, user: User) -> None:
        if user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Requires Admin or Organizer privileges.")

    def view_all_students(self, admin_user: User) -> List[StudentProfile]:
        self._verify_admin_or_organizer(admin_user)
        return list(self._system._profiles.values())

    def view_student_progress_and_outcomes(self, admin_user: User, student_username: str) -> Dict[str, str]:
        self._verify_admin_or_organizer(admin_user)
        profile = self._system._profiles.get(student_username)
        if not profile:
            raise ValueError("Student not found.")
        return {
            "progress": profile.progress,
            "outcomes": profile.outcomes
        }

    def add_volunteer(self, admin_user: User, volunteer_name: str) -> None:
        self._verify_admin_or_organizer(admin_user)
        if volunteer_name not in self._system._volunteers:
            self._system._volunteers.append(volunteer_name)

    def remove_volunteer(self, admin_user: User, volunteer_name: str) -> None:
        self._verify_admin_or_organizer(admin_user)
        if volunteer_name in self._system._volunteers:
            self._system._volunteers.remove(volunteer_name)

    def view_volunteers(self, admin_user: User) -> List[str]:
        self._verify_admin_or_organizer(admin_user)
        return self._system._volunteers

    def add_to_waitlist(self, admin_user: User, student_name: str) -> None:
        self._verify_admin_or_organizer(admin_user)
        if student_name not in self._system._waitlist:
            self._system._waitlist.append(student_name)

    def remove_from_waitlist(self, admin_user: User, student_name: str) -> None:
        self._verify_admin_or_organizer(admin_user)
        if student_name in self._system._waitlist:
            self._system._waitlist.remove(student_name)

    def view_waitlist(self, admin_user: User) -> List[str]:
        self._verify_admin_or_organizer(admin_user)
        return self._system._waitlist

class StudentManagementSystem:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._profiles: Dict[str, StudentProfile] = {}
        self._volunteers: List[str] = []
        self._waitlist: List[str] = []
        self.admin_dashboard = AdminDashboard(self)

    def register_user(self, username: str, password: str, role: Role) -> User:
        if username in self._users:
            raise ValueError("Username already exists.")
        
        new_user = User(username, password, role)
        self._users[username] = new_user
        
        if role == Role.STUDENT:
            self._profiles[username] = StudentProfile(new_user)
            
        return new_user

    def login(self, username: str, password: str) -> Optional[User]:
        user = self._users.get(username)
        if user and user.check_password(password):
            return user
        return None

    def view_student_profile(self, requester: User, target_username: str) -> StudentProfile:
        target_profile = self._profiles.get(target_username)
        if not target_profile:
            raise ValueError("Student profile not found.")
            
        if requester.username == target_username or requester.role in (Role.ADMIN, Role.ORGANIZER):
            return target_profile
            
        raise PermissionError("Access denied: You can only view your own profile unless you are an Admin/Organizer.")