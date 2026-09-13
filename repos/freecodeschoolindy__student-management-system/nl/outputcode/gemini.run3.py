from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime

class Role(Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"

class UnauthorizedError(Exception):
    pass

class AuthenticationError(Exception):
    pass

class User:
    def __init__(self, user_id: int, username: str, password: str, role: Role):
        self.user_id = user_id
        self.username = username
        self._password = password
        self.role = role

    def verify_password(self, password: str) -> bool:
        return self._password == password

class Student(User):
    def __init__(self, user_id: int, username: str, password: str):
        super().__init__(user_id, username, password, Role.STUDENT)

class Admin(User):
    def __init__(self, user_id: int, username: str, password: str):
        super().__init__(user_id, username, password, Role.ADMIN)

class Organizer(User):
    def __init__(self, user_id: int, username: str, password: str):
        super().__init__(user_id, username, password, Role.ORGANIZER)

class Progress:
    def __init__(self):
        self.courses_completed: List[str] = []
        self.current_module: str = "Not Started"
        self.attendance_score: float = 0.0

    def update_module(self, module: str) -> None:
        self.current_module = module

    def complete_course(self, course: str) -> None:
        if course not in self.courses_completed:
            self.courses_completed.append(course)

class Outcome:
    def __init__(self):
        self.graduated: bool = False
        self.job_placed: bool = False
        self.employer: Optional[str] = None
        self.notes: str = ""

    def record_graduation(self) -> None:
        self.graduated = True

    def record_job_placement(self, employer: str) -> None:
        self.job_placed = True
        self.employer = employer

class StudentProfile:
    def __init__(self, student: Student):
        self.student = student
        self.progress = Progress()
        self.outcome = Outcome()
        self.personal_info: str = ""

    def update_personal_info(self, info: str) -> None:
        self.personal_info = info

    def view_profile(self, requester: User) -> Dict[str, Any]:
        if requester.role in (Role.ADMIN, Role.ORGANIZER) or requester.user_id == self.student.user_id:
            return {
                "user_id": self.student.user_id,
                "username": self.student.username,
                "personal_info": self.personal_info,
                "progress": {
                    "current_module": self.progress.current_module,
                    "courses_completed": self.progress.courses_completed,
                    "attendance_score": self.progress.attendance_score
                },
                "outcome": {
                    "graduated": self.outcome.graduated,
                    "job_placed": self.outcome.job_placed,
                    "employer": self.outcome.employer,
                    "notes": self.outcome.notes
                }
            }
        raise UnauthorizedError("You do not have permission to view this profile.")

class Volunteer:
    def __init__(self, volunteer_id: int, name: str, skills: str):
        self.volunteer_id = volunteer_id
        self.name = name
        self.skills = skills
        self.is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False

class WaitlistEntry:
    def __init__(self, entry_id: int, name: str, email: str):
        self.entry_id = entry_id
        self.name = name
        self.email = email
        self.date_added: datetime = datetime.now()

class AdminDashboard:
    def __init__(self, user: User, system: 'StudentManagementSystem'):
        if user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise UnauthorizedError("Only admins and organizers can access the dashboard.")
        self.user = user
        self.system = system

    def view_all_students(self) -> List[Dict[str, Any]]:
        return [profile.view_profile(self.user) for profile in self.system.profiles.values()]

    def view_student_progress_and_outcomes(self, student_id: int) -> Dict[str, Any]:
        if student_id not in self.system.profiles:
            raise ValueError("Student not found.")
        profile = self.system.profiles[student_id]
        data = profile.view_profile(self.user)
        return {
            "student_username": data["username"],
            "progress": data["progress"],
            "outcome": data["outcome"]
        }

    def update_student_progress(self, student_id: int, module: str, completed_course: Optional[str] = None) -> None:
        if student_id not in self.system.profiles:
            raise ValueError("Student not found.")
        profile = self.system.profiles[student_id]
        profile.progress.update_module(module)
        if completed_course:
            profile.progress.complete_course(completed_course)

    def update_student_outcome(self, student_id: int, graduated: bool, employer: Optional[str] = None) -> None:
        if student_id not in self.system.profiles:
            raise ValueError("Student not found.")
        profile = self.system.profiles[student_id]
        if graduated:
            profile.outcome.record_graduation()
        if employer:
            profile.outcome.record_job_placement(employer)

    def add_volunteer(self, name: str, skills: str) -> Volunteer:
        return self.system.add_volunteer(name, skills)

    def remove_volunteer(self, volunteer_id: int) -> None:
        self.system.remove_volunteer(volunteer_id)

    def view_volunteers(self) -> List[Volunteer]:
        return list(self.system.volunteers.values())

    def add_to_waitlist(self, name: str, email: str) -> WaitlistEntry:
        return self.system.add_to_waitlist(name, email)

    def view_waitlist(self) -> List[WaitlistEntry]:
        return self.system.waitlist

    def admit_from_waitlist(self, entry_id: int, username: str, password: str) -> Student:
        return self.system.admit_from_waitlist(entry_id, username, password)

class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.profiles: Dict[int, StudentProfile] = {}
        self.volunteers: Dict[int, Volunteer] = {}
        self.waitlist: List[WaitlistEntry] = []
        self._next_user_id: int = 1
        self._next_volunteer_id: int = 1
        self._next_waitlist_id: int = 1

    def register_student(self, username: str, password: str) -> Student:
        if any(u.username == username for u in self.users.values()):
            raise ValueError("Username already exists.")
        student = Student(self._next_user_id, username, password)
        self.users[student.user_id] = student
        self.profiles[student.user_id] = StudentProfile(student)
        self._next_user_id += 1
        return student

    def register_admin(self, username: str, password: str) -> Admin:
        if any(u.username == username for u in self.users.values()):
            raise ValueError("Username already exists.")
        admin = Admin(self._next_user_id, username, password)
        self.users[admin.user_id] = admin
        self._next_user_id += 1
        return admin

    def register_organizer(self, username: str, password: str) -> Organizer:
        if any(u.username == username for u in self.users.values()):
            raise ValueError("Username already exists.")
        organizer = Organizer(self._next_user_id, username, password)
        self.users[organizer.user_id] = organizer
        self._next_user_id += 1
        return organizer

    def login(self, username: str, password: str) -> User:
        for user in self.users.values():
            if user.username == username:
                if user.verify_password(password):
                    return user
                raise AuthenticationError("Invalid password.")
        raise AuthenticationError("User not found.")

    def get_student_profile(self, requester: User, student_id: int) -> Dict[str, Any]:
        if student_id not in self.profiles:
            raise ValueError("Student profile not found.")
        return self.profiles[student_id].view_profile(requester)

    def get_admin_dashboard(self, user: User) -> AdminDashboard:
        return AdminDashboard(user, self)

    def add_volunteer(self, name: str, skills: str) -> Volunteer:
        vol = Volunteer(self._next_volunteer_id, name, skills)
        self.volunteers[vol.volunteer_id] = vol
        self._next_volunteer_id += 1
        return vol

    def remove_volunteer(self, volunteer_id: int) -> None:
        if volunteer_id in self.volunteers:
            del self.volunteers[volunteer_id]
        else:
            raise ValueError("Volunteer not found.")

    def add_to_waitlist(self, name: str, email: str) -> WaitlistEntry:
        entry = WaitlistEntry(self._next_waitlist_id, name, email)
        self.waitlist.append(entry)
        self._next_waitlist_id += 1
        return entry

    def admit_from_waitlist(self, entry_id: int, username: str, password: str) -> Student:
        for i, entry in enumerate(self.waitlist):
            if entry.entry_id == entry_id:
                self.waitlist.pop(i)
                return self.register_student(username, password)
        raise ValueError("Waitlist entry not found.")

if __name__ == "__main__":
    system = StudentManagementSystem()
    
    admin = system.register_admin("admin_user", "securepass123")
    student1 = system.register_student("student_one", "pass1")
    
    logged_in_admin = system.login("admin_user", "securepass123")
    dashboard = system.get_admin_dashboard(logged_in_admin)
    
    dashboard.add_to_waitlist("Jane Doe", "jane@example.com")
    dashboard.add_volunteer("John Smith", "Python, Django")
    
    dashboard.update_student_progress(student1.user_id, "Backend Development", "Python Basics")
    dashboard.update_student_outcome(student1.user_id, graduated=True, employer="Tech Corp")
    
    logged_in_student = system.login("student_one", "pass1")
    student_profile = system.get_student_profile(logged_in_student, logged_in_student.user_id)