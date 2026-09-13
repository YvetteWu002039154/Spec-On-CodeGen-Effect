from enum import Enum
from typing import List, Dict, Optional

class Role(Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"

class User:
    def __init__(self, user_id: int, username: str, password: str, role: Role):
        self._user_id = user_id
        self._username = username
        self._password = password
        self._role = role

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def role(self) -> Role:
        return self._role

    def check_password(self, password: str) -> bool:
        return self._password == password

class StudentProfile:
    def __init__(self, student: User, progress: str, outcomes: str):
        if student.role != Role.STUDENT:
            raise ValueError("Profile can only be created for a student.")
        self._student = student
        self._progress = progress
        self._outcomes = outcomes

    @property
    def student(self) -> User:
        return self._student

    def get_details(self, requester: User) -> Dict[str, str]:
        if requester.user_id == self._student.user_id or requester.role in (Role.ADMIN, Role.ORGANIZER):
            return {
                "username": self._student.username,
                "progress": self._progress,
                "outcomes": self._outcomes
            }
        raise PermissionError("Access denied: You can only view your own profile.")

    def update_progress(self, requester: User, new_progress: str) -> None:
        if requester.role in (Role.ADMIN, Role.ORGANIZER) or requester.user_id == self._student.user_id:
            self._progress = new_progress
        else:
            raise PermissionError("Access denied.")

    def update_outcomes(self, requester: User, new_outcomes: str) -> None:
        if requester.role in (Role.ADMIN, Role.ORGANIZER) or requester.user_id == self._student.user_id:
            self._outcomes = new_outcomes
        else:
            raise PermissionError("Access denied.")

class Volunteer:
    def __init__(self, volunteer_id: int, name: str, email: str):
        self._volunteer_id = volunteer_id
        self._name = name
        self._email = email

    @property
    def volunteer_id(self) -> int:
        return self._volunteer_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

class WaitlistEntry:
    def __init__(self, entry_id: int, student_name: str, contact_info: str):
        self._entry_id = entry_id
        self._student_name = student_name
        self._contact_info = contact_info

    @property
    def entry_id(self) -> int:
        return self._entry_id

    @property
    def student_name(self) -> str:
        return self._student_name

    @property
    def contact_info(self) -> str:
        return self._contact_info

class DjangoAdminInterface:
    def __init__(self):
        self._users: Dict[int, User] = {}
        self._profiles: Dict[int, StudentProfile] = {}
        self._volunteers: Dict[int, Volunteer] = {}
        self._waitlist: Dict[int, WaitlistEntry] = {}

    def add_user(self, user: User) -> None:
        self._users[user.user_id] = user

    def add_profile(self, profile: StudentProfile) -> None:
        self._profiles[profile.student.user_id] = profile

    def get_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def view_all_users(self, requester: User) -> List[User]:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Only admins and organizers can view all users via the admin interface.")
        return list(self._users.values())

    @property
    def profiles(self) -> Dict[int, StudentProfile]:
        return self._profiles

    @property
    def volunteers(self) -> Dict[int, Volunteer]:
        return self._volunteers

    @property
    def waitlist(self) -> Dict[int, WaitlistEntry]:
        return self._waitlist

class AdminDashboard:
    def __init__(self, admin_interface: DjangoAdminInterface):
        self._admin_interface = admin_interface

    def view_all_student_progress_and_outcomes(self, requester: User) -> List[Dict[str, str]]:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Admin/Organizer role required.")
        
        return [
            profile.get_details(requester) 
            for profile in self._admin_interface.profiles.values()
        ]

    def add_volunteer(self, requester: User, volunteer: Volunteer) -> None:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Admin/Organizer role required.")
        self._admin_interface.volunteers[volunteer.volunteer_id] = volunteer

    def remove_volunteer(self, requester: User, volunteer_id: int) -> None:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Admin/Organizer role required.")
        if volunteer_id in self._admin_interface.volunteers:
            del self._admin_interface.volunteers[volunteer_id]

    def list_volunteers(self, requester: User) -> List[Volunteer]:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Admin/Organizer role required.")
        return list(self._admin_interface.volunteers.values())

    def add_to_waitlist(self, requester: User, entry: WaitlistEntry) -> None:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Admin/Organizer role required.")
        self._admin_interface.waitlist[entry.entry_id] = entry

    def remove_from_waitlist(self, requester: User, entry_id: int) -> None:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Admin/Organizer role required.")
        if entry_id in self._admin_interface.waitlist:
            del self._admin_interface.waitlist[entry_id]

    def view_waitlist(self, requester: User) -> List[WaitlistEntry]:
        if requester.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied: Admin/Organizer role required.")
        return list(self._admin_interface.waitlist.values())

class StudentManagementSystem:
    def __init__(self):
        self.admin_interface = DjangoAdminInterface()
        self.dashboard = AdminDashboard(self.admin_interface)
        self._next_user_id = 1
        self._next_volunteer_id = 1
        self._next_waitlist_id = 1

    def register_user(self, username: str, password: str, role: Role) -> User:
        user = User(self._next_user_id, username, password, role)
        self._next_user_id += 1
        self.admin_interface.add_user(user)
        return user

    def create_student_profile(self, student: User, progress: str, outcomes: str) -> StudentProfile:
        profile = StudentProfile(student, progress, outcomes)
        self.admin_interface.add_profile(profile)
        return profile

    def login(self, username: str, password: str) -> Optional[User]:
        user = self.admin_interface.get_user_by_username(username)
        if user and user.check_password(password):
            return user
        return None
        
    def create_volunteer(self, name: str, email: str) -> Volunteer:
        volunteer = Volunteer(self._next_volunteer_id, name, email)
        self._next_volunteer_id += 1
        return volunteer
        
    def create_waitlist_entry(self, student_name: str, contact_info: str) -> WaitlistEntry:
        entry = WaitlistEntry(self._next_waitlist_id, student_name, contact_info)
        self._next_waitlist_id += 1
        return entry