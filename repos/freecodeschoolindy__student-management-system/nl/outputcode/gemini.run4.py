from enum import Enum
from typing import List, Dict, Optional, Any

class Role(Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"

class User:
    def __init__(self, user_id: int, username: str, password: str, role: Role):
        self.user_id = user_id
        self.username = username
        self._password = password
        self.role = role

    def check_password(self, password: str) -> bool:
        return self._password == password

class StudentProfile:
    def __init__(self, bio: str = "", contact_email: str = ""):
        self.bio = bio
        self.contact_email = contact_email

class Student(User):
    def __init__(self, user_id: int, username: str, password: str):
        super().__init__(user_id, username, password, Role.STUDENT)
        self.profile = StudentProfile()
        self.progress: str = "Not Started"
        self.outcomes: str = "None"

class Admin(User):
    def __init__(self, user_id: int, username: str, password: str):
        super().__init__(user_id, username, password, Role.ADMIN)

class Volunteer:
    def __init__(self, volunteer_id: int, name: str, role_description: str):
        self.volunteer_id = volunteer_id
        self.name = name
        self.role_description = role_description

class WaitlistEntry:
    def __init__(self, entry_id: int, applicant_name: str, email: str):
        self.entry_id = entry_id
        self.applicant_name = applicant_name
        self.email = email

class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.volunteers: Dict[int, Volunteer] = {}
        self.waitlist: Dict[int, WaitlistEntry] = {}
        self.logged_in_user: Optional[User] = None
        self._next_user_id = 1
        self._next_volunteer_id = 1
        self._next_waitlist_id = 1

    def register_student(self, username: str, password: str) -> Student:
        student = Student(self._next_user_id, username, password)
        self.users[self._next_user_id] = student
        self._next_user_id += 1
        return student

    def register_admin(self, username: str, password: str) -> Admin:
        admin = Admin(self._next_user_id, username, password)
        self.users[self._next_user_id] = admin
        self._next_user_id += 1
        return admin

    def login(self, username: str, password: str) -> bool:
        for user in self.users.values():
            if user.username == username and user.check_password(password):
                self.logged_in_user = user
                return True
        return False

    def logout(self) -> None:
        self.logged_in_user = None

    def get_student_profile(self, student_id: int) -> StudentProfile:
        if not self.logged_in_user:
            raise PermissionError("Must be logged in to view profiles.")
        
        user = self.users.get(student_id)
        if not user or user.role != Role.STUDENT:
            raise ValueError("Student not found.")
        
        if self.logged_in_user.role == Role.ADMIN or self.logged_in_user.user_id == student_id:
            return user.profile
        else:
            raise PermissionError("Private profile: Visible only to the user and admins.")

    def update_student_progress(self, student_id: int, progress: str, outcomes: str) -> None:
        if not self.logged_in_user or self.logged_in_user.role != Role.ADMIN:
            raise PermissionError("Only admins can update student progress and outcomes.")
        
        student = self.users.get(student_id)
        if not student or student.role != Role.STUDENT:
            raise ValueError("Student not found.")
        
        student.progress = progress
        student.outcomes = outcomes

    def add_volunteer(self, name: str, role_description: str) -> Volunteer:
        if not self.logged_in_user or self.logged_in_user.role != Role.ADMIN:
            raise PermissionError("Only admins can manage volunteers.")
        
        volunteer = Volunteer(self._next_volunteer_id, name, role_description)
        self.volunteers[self._next_volunteer_id] = volunteer
        self._next_volunteer_id += 1
        return volunteer

    def remove_volunteer(self, volunteer_id: int) -> None:
        if not self.logged_in_user or self.logged_in_user.role != Role.ADMIN:
            raise PermissionError("Only admins can manage volunteers.")
        if volunteer_id in self.volunteers:
            del self.volunteers[volunteer_id]

    def add_to_waitlist(self, applicant_name: str, email: str) -> WaitlistEntry:
        if not self.logged_in_user or self.logged_in_user.role != Role.ADMIN:
            raise PermissionError("Only admins can manage the waitlist.")
        
        entry = WaitlistEntry(self._next_waitlist_id, applicant_name, email)
        self.waitlist[self._next_waitlist_id] = entry
        self._next_waitlist_id += 1
        return entry

    def remove_from_waitlist(self, entry_id: int) -> None:
        if not self.logged_in_user or self.logged_in_user.role != Role.ADMIN:
            raise PermissionError("Only admins can manage the waitlist.")
        if entry_id in self.waitlist:
            del self.waitlist[entry_id]

    def get_admin_dashboard(self) -> Dict[str, Any]:
        if not self.logged_in_user or self.logged_in_user.role != Role.ADMIN:
            raise PermissionError("Only admins can view the admin dashboard.")
        
        students_data = []
        for user in self.users.values():
            if user.role == Role.STUDENT:
                students_data.append({
                    "student_id": user.user_id,
                    "username": user.username,
                    "progress": user.progress,
                    "outcomes": user.outcomes
                })
        
        return {
            "students_progress_outcomes": students_data,
            "volunteers": [vars(v) for v in self.volunteers.values()],
            "waitlist": [vars(w) for w in self.waitlist.values()]
        }