from enum import Enum
from typing import List, Dict, Any

class Role(Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"
    VOLUNTEER = "VOLUNTEER"

class User:
    def __init__(self, username: str, password: str, role: Role):
        self.username = username
        self.password = password
        self.role = role
        self.is_logged_in = False

    def login(self, password: str) -> bool:
        if self.password == password:
            self.is_logged_in = True
            return True
        return False

    def logout(self) -> None:
        self.is_logged_in = False

class WaitlistEntry:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

class Waitlist:
    def __init__(self):
        self.entries: List[WaitlistEntry] = []

    def add(self, name: str, email: str) -> None:
        self.entries.append(WaitlistEntry(name, email))

    def remove(self, email: str) -> None:
        self.entries = [e for e in self.entries if e.email != email]

    def view_all(self) -> List[WaitlistEntry]:
        return self.entries

class StudentProfile:
    def __init__(self, student: User, details: str = ""):
        self.student = student
        self.details = details
        self.progress: List[str] = []
        self.outcomes: List[str] = []

    def view_profile(self, viewer: User) -> Dict[str, Any]:
        if not viewer.is_logged_in:
            raise PermissionError("Viewer must be logged in.")
        
        if viewer == self.student or viewer.role in (Role.ADMIN, Role.ORGANIZER):
            return {
                "username": self.student.username,
                "details": self.details,
                "progress": self.progress,
                "outcomes": self.outcomes
            }
        raise PermissionError("Access denied. Private profile.")

    def update_progress(self, user: User, progress_note: str) -> None:
        if not user.is_logged_in:
            raise PermissionError("User must be logged in.")
        if user == self.student or user.role in (Role.ADMIN, Role.ORGANIZER):
            self.progress.append(progress_note)
        else:
            raise PermissionError("Access denied.")

    def update_outcome(self, user: User, outcome_note: str) -> None:
        if not user.is_logged_in:
            raise PermissionError("User must be logged in.")
        if user == self.student or user.role in (Role.ADMIN, Role.ORGANIZER):
            self.outcomes.append(outcome_note)
        else:
            raise PermissionError("Access denied.")

class AdminDashboard:
    def __init__(self, system: 'StudentManagementSystem'):
        self.system = system

    def _check_admin_access(self, user: User) -> None:
        if not user.is_logged_in:
            raise PermissionError("User must be logged in.")
        if user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Admin or Organizer access required.")

    def view_all_students(self, admin_user: User) -> List[User]:
        self._check_admin_access(admin_user)
        return self.system.students

    def view_student_progress_outcomes(self, admin_user: User) -> Dict[str, Dict[str, List[str]]]:
        self._check_admin_access(admin_user)
        report = {}
        for student in self.system.students:
            profile = self.system.profiles.get(student.username)
            if profile:
                report[student.username] = {
                    "progress": profile.progress,
                    "outcomes": profile.outcomes
                }
        return report

    def manage_volunteers_add(self, admin_user: User, username: str, password: str) -> User:
        self._check_admin_access(admin_user)
        return self.system.register_user(username, password, Role.VOLUNTEER)

    def manage_volunteers_remove(self, admin_user: User, username: str) -> None:
        self._check_admin_access(admin_user)
        volunteer = self.system.users.get(username)
        if volunteer and volunteer.role == Role.VOLUNTEER:
            self.system.volunteers.remove(volunteer)
            del self.system.users[username]
        else:
            raise ValueError("Volunteer not found.")

    def view_volunteers(self, admin_user: User) -> List[User]:
        self._check_admin_access(admin_user)
        return self.system.volunteers

    def view_waitlist(self, admin_user: User) -> List[WaitlistEntry]:
        self._check_admin_access(admin_user)
        return self.system.waitlist.view_all()

    def add_to_waitlist(self, admin_user: User, name: str, email: str) -> None:
        self._check_admin_access(admin_user)
        self.system.waitlist.add(name, email)

    def remove_from_waitlist(self, admin_user: User, email: str) -> None:
        self._check_admin_access(admin_user)
        self.system.waitlist.remove(email)

class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.students: List[User] = []
        self.volunteers: List[User] = []
        self.profiles: Dict[str, StudentProfile] = {}
        self.waitlist = Waitlist()
        self.admin_dashboard = AdminDashboard(self)

    def register_user(self, username: str, password: str, role: Role) -> User:
        if username in self.users:
            raise ValueError(f"Username {username} already exists.")
        
        user = User(username, password, role)
        self.users[username] = user
        
        if role == Role.STUDENT:
            self.students.append(user)
            self.profiles[username] = StudentProfile(user)
        elif role == Role.VOLUNTEER:
            self.volunteers.append(user)
            
        return user

    def login(self, username: str, password: str) -> User:
        user = self.users.get(username)
        if not user:
            raise ValueError("User not found.")
        if user.login(password):
            return user
        raise ValueError("Invalid password.")

    def get_student_profile(self, username: str) -> StudentProfile:
        profile = self.profiles.get(username)
        if not profile:
            raise ValueError("Student profile not found.")
        return profile

if __name__ == "__main__":
    system = StudentManagementSystem()
    
    admin = system.register_user("admin1", "adminpass", Role.ADMIN)
    student1 = system.register_user("student1", "studpass", Role.STUDENT)
    
    system.login("admin1", "adminpass")
    system.login("student1", "studpass")
    
    profile = system.get_student_profile("student1")
    profile.update_progress(student1, "Completed Python Basics")
    profile.update_outcome(admin, "Passed final exam")
    
    system.admin_dashboard.add_to_waitlist(admin, "Jane Doe", "jane@example.com")
    system.admin_dashboard.manage_volunteers_add(admin, "vol1", "volpass")
    
    assert len(system.admin_dashboard.view_waitlist(admin)) == 1
    assert len(system.admin_dashboard.view_volunteers(admin)) == 1
    assert "Completed Python Basics" in profile.view_profile(student1)["progress"]