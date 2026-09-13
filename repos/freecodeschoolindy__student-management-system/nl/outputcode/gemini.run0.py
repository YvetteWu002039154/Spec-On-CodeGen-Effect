from enum import Enum
from typing import List, Dict, Optional

class Role(Enum):
    STUDENT = "Student"
    ADMIN = "Admin"
    VOLUNTEER = "Volunteer"

class User:
    def __init__(self, username: str, password: str, role: Role):
        self.username = username
        self._password = password
        self.role = role

    def verify_password(self, password: str) -> bool:
        return self._password == password

class Progress:
    def __init__(self):
        self.courses_completed: List[str] = []
        self.current_course: Optional[str] = None
        self.grades: Dict[str, str] = {}

    def update_progress(self, course: str, grade: str):
        self.courses_completed.append(course)
        self.grades[course] = grade

    def set_current_course(self, course: str):
        self.current_course = course

class Outcome:
    def __init__(self):
        self.job_secured: bool = False
        self.company: Optional[str] = None
        self.role_title: Optional[str] = None

    def set_outcome(self, job_secured: bool, company: Optional[str] = None, role_title: Optional[str] = None):
        self.job_secured = job_secured
        self.company = company
        self.role_title = role_title

class StudentProfile:
    def __init__(self, student_username: str):
        self.student_username = student_username
        self.progress = Progress()
        self.outcome = Outcome()
        self.bio: str = ""
        self.contact_email: str = ""

class Student(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password, Role.STUDENT)
        self._profile = StudentProfile(username)

    def get_profile(self, requester: User) -> StudentProfile:
        if requester == self or requester.role == Role.ADMIN:
            return self._profile
        raise PermissionError("Access denied: You do not have permission to view this profile.")

class Volunteer(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password, Role.VOLUNTEER)
        self.assigned_tasks: List[str] = []

    def assign_task(self, task: str):
        self.assigned_tasks.append(task)

class Admin(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password, Role.ADMIN)

class Waitlist:
    def __init__(self):
        self._entries: List[str] = []

    def add_student(self, email: str):
        if email not in self._entries:
            self._entries.append(email)

    def remove_student(self, email: str):
        if email in self._entries:
            self._entries.remove(email)

    def get_all(self) -> List[str]:
        return self._entries.copy()

class AdminDashboard:
    def __init__(self, system: 'StudentManagementSystem'):
        self.system = system

    def _verify_admin(self, user: User):
        if user.role != Role.ADMIN:
            raise PermissionError("Access denied: Admin privileges required.")

    def view_all_students(self, admin: User) -> List[Student]:
        self._verify_admin(admin)
        return self.system.students

    def view_student_progress(self, admin: User, student: Student) -> Progress:
        self._verify_admin(admin)
        return student.get_profile(admin).progress

    def view_student_outcome(self, admin: User, student: Student) -> Outcome:
        self._verify_admin(admin)
        return student.get_profile(admin).outcome

    def view_all_volunteers(self, admin: User) -> List[Volunteer]:
        self._verify_admin(admin)
        return self.system.volunteers

    def assign_volunteer_task(self, admin: User, volunteer: Volunteer, task: str):
        self._verify_admin(admin)
        if volunteer in self.system.volunteers:
            volunteer.assign_task(task)
        else:
            raise ValueError("Volunteer not found in the system.")

    def remove_volunteer(self, admin: User, volunteer: Volunteer):
        self._verify_admin(admin)
        if volunteer in self.system.volunteers:
            self.system.volunteers.remove(volunteer)
            del self.system.users[volunteer.username]

    def view_waitlist(self, admin: User) -> List[str]:
        self._verify_admin(admin)
        return self.system.waitlist.get_all()

    def add_to_waitlist(self, admin: User, email: str):
        self._verify_admin(admin)
        self.system.waitlist.add_student(email)

    def remove_from_waitlist(self, admin: User, email: str):
        self._verify_admin(admin)
        self.system.waitlist.remove_student(email)

class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.students: List[Student] = []
        self.volunteers: List[Volunteer] = []
        self.waitlist = Waitlist()
        self.admin_dashboard = AdminDashboard(self)

    def register_student(self, username: str, password: str) -> Student:
        if username in self.users:
            raise ValueError("Username already exists.")
        student = Student(username, password)
        self.users[username] = student
        self.students.append(student)
        return student

    def register_admin(self, username: str, password: str) -> Admin:
        if username in self.users:
            raise ValueError("Username already exists.")
        admin = Admin(username, password)
        self.users[username] = admin
        return admin

    def register_volunteer(self, username: str, password: str) -> Volunteer:
        if username in self.users:
            raise ValueError("Username already exists.")
        volunteer = Volunteer(username, password)
        self.users[username] = volunteer
        self.volunteers.append(volunteer)
        return volunteer

    def login(self, username: str, password: str) -> User:
        user = self.users.get(username)
        if user and user.verify_password(password):
            return user
        raise ValueError("Invalid username or password.")