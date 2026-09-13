import enum
from typing import List, Optional, Dict, Any

class Role(enum.Enum):
    STUDENT = "student"
    ADMIN = "admin"
    ORGANIZER = "organizer"


class User:
    def __init__(self, user_id: int, username: str, password: str, role: Role):
        self._user_id = user_id
        self._username = username
        self._password = password
        self._role = role
        self._is_logged_in = False

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def role(self) -> Role:
        return self._role

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    def login(self, password: str) -> bool:
        if self._password == password:
            self._is_logged_in = True
            return True
        return False

    def logout(self) -> None:
        self._is_logged_in = False


class StudentProfile:
    def __init__(self, student: User):
        if student.role != Role.STUDENT:
            raise ValueError("Profile must belong to a student.")
        self._student = student
        self._progress = "Not started"
        self._outcomes = "No outcomes yet"

    @property
    def student(self) -> User:
        return self._student

    def get_profile_data(self, viewer: User) -> Dict[str, Any]:
        if not viewer.is_logged_in:
            raise PermissionError("Viewer must be logged in.")
        
        if viewer.role in (Role.ADMIN, Role.ORGANIZER) or viewer.user_id == self._student.user_id:
            return {
                "username": self._student.username,
                "progress": self._progress,
                "outcomes": self._outcomes
            }
        raise PermissionError("You do not have permission to view this profile.")

    def update_progress(self, updater: User, progress: str, outcomes: str) -> None:
        if not updater.is_logged_in:
            raise PermissionError("Updater must be logged in.")
            
        if updater.role in (Role.ADMIN, Role.ORGANIZER) or updater.user_id == self._student.user_id:
            self._progress = progress
            self._outcomes = outcomes
        else:
            raise PermissionError("You do not have permission to update this profile.")


class Volunteer:
    def __init__(self, volunteer_id: int, name: str, email: str, task: str):
        self.volunteer_id = volunteer_id
        self.name = name
        self.email = email
        self.task = task


class WaitlistEntry:
    def __init__(self, entry_id: int, name: str, email: str, interest_area: str):
        self.entry_id = entry_id
        self.name = name
        self.email = email
        self.interest_area = interest_area


class AdminDashboard:
    def __init__(self):
        self._volunteers: List[Volunteer] = []
        self._waitlist: List[WaitlistEntry] = []
        self._volunteer_id_counter = 1
        self._waitlist_id_counter = 1

    def _verify_access(self, user: User) -> None:
        if not user.is_logged_in:
            raise PermissionError("User must be logged in.")
        if user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied. Admins or Organizers only.")

    def view_all_student_progress(self, user: User, profiles: List[StudentProfile]) -> List[Dict[str, Any]]:
        self._verify_access(user)
        return [profile.get_profile_data(user) for profile in profiles]

    def update_student_progress(self, user: User, profile: StudentProfile, progress: str, outcomes: str) -> None:
        self._verify_access(user)
        profile.update_progress(user, progress, outcomes)

    def add_volunteer(self, user: User, name: str, email: str, task: str) -> Volunteer:
        self._verify_access(user)
        volunteer = Volunteer(self._volunteer_id_counter, name, email, task)
        self._volunteers.append(volunteer)
        self._volunteer_id_counter += 1
        return volunteer

    def remove_volunteer(self, user: User, volunteer_id: int) -> None:
        self._verify_access(user)
        self._volunteers = [v for v in self._volunteers if v.volunteer_id != volunteer_id]

    def get_volunteers(self, user: User) -> List[Volunteer]:
        self._verify_access(user)
        return self._volunteers

    def add_to_waitlist(self, user: User, name: str, email: str, interest_area: str) -> WaitlistEntry:
        self._verify_access(user)
        entry = WaitlistEntry(self._waitlist_id_counter, name, email, interest_area)
        self._waitlist.append(entry)
        self._waitlist_id_counter += 1
        return entry

    def remove_from_waitlist(self, user: User, entry_id: int) -> None:
        self._verify_access(user)
        self._waitlist = [w for w in self._waitlist if w.entry_id != entry_id]

    def get_waitlist(self, user: User) -> List[WaitlistEntry]:
        self._verify_access(user)
        return self._waitlist


class StudentManagementSystem:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._profiles: Dict[str, StudentProfile] = {}
        self._dashboard = AdminDashboard()
        self._next_user_id = 1

    @property
    def dashboard(self) -> AdminDashboard:
        return self._dashboard

    def register_user(self, username: str, password: str, role: Role) -> User:
        if username in self._users:
            raise ValueError("Username already exists.")
        
        user = User(self._next_user_id, username, password, role)
        self._users[username] = user
        self._next_user_id += 1
        
        if role == Role.STUDENT:
            self._profiles[username] = StudentProfile(user)
            
        return user

    def login(self, username: str, password: str) -> Optional[User]:
        user = self._users.get(username)
        if user and user.login(password):
            return user
        return None

    def get_student_profile(self, viewer: User, student_username: str) -> Dict[str, Any]:
        profile = self._profiles.get(student_username)
        if not profile:
            raise ValueError("Student profile not found.")
        return profile.get_profile_data(viewer)

    def get_all_profiles(self) -> List[StudentProfile]:
        return list(self._profiles.values())