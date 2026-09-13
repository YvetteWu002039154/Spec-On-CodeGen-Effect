from typing import List, Dict, Any, Optional

class User:
    def __init__(self, username: str, password: str):
        self.username: str = username
        self._password: str = password
        self.is_logged_in: bool = False

    def login(self, password: str) -> bool:
        if self._password == password:
            self.is_logged_in = True
            return True
        return False

    def logout(self) -> None:
        self.is_logged_in = False


class StudentProfile:
    def __init__(self, student: 'Student'):
        self.student: 'Student' = student
        self.progress: str = "Not started"
        self.outcomes: str = "No outcomes yet"
        self.personal_info: Dict[str, Any] = {}

    def update_progress(self, progress: str) -> None:
        self.progress = progress

    def update_outcomes(self, outcomes: str) -> None:
        self.outcomes = outcomes

    def view_profile(self, user: User) -> Dict[str, Any]:
        if not user.is_logged_in:
            raise PermissionError("User must be logged in to view profiles.")
        
        if isinstance(user, Admin) or (isinstance(user, Student) and user == self.student):
            return {
                "username": self.student.username,
                "progress": self.progress,
                "outcomes": self.outcomes,
                "personal_info": self.personal_info
            }
        raise PermissionError("Access denied. Profile is private.")


class Student(User):
    def __init__(self, username: str, password: str):
        super().__init__(username, password)
        self.profile: StudentProfile = StudentProfile(self)

    def view_own_page(self) -> Dict[str, Any]:
        return self.profile.view_profile(self)


class Volunteer(User):
    def __init__(self, username: str, password: str, role_description: str = ""):
        super().__init__(username, password)
        self.role_description: str = role_description


class Waitlist:
    def __init__(self):
        self._students: List[str] = []

    def add_student(self, student_name: str) -> None:
        if student_name not in self._students:
            self._students.append(student_name)

    def remove_student(self, student_name: str) -> None:
        if student_name in self._students:
            self._students.remove(student_name)

    def get_waitlist(self) -> List[str]:
        return self._students.copy()


class AdminDashboard:
    def __init__(self):
        self.volunteers: List[Volunteer] = []
        self.waitlist: Waitlist = Waitlist()
        self.students: List[Student] = []

    def _verify_admin(self, admin: 'Admin') -> None:
        if not isinstance(admin, Admin) or not admin.is_logged_in:
            raise PermissionError("Admin access required and must be logged in.")

    def register_student(self, student: Student) -> None:
        self.students.append(student)

    def view_student_progress(self, admin: 'Admin', student: Student) -> str:
        self._verify_admin(admin)
        return student.profile.progress

    def view_student_outcomes(self, admin: 'Admin', student: Student) -> str:
        self._verify_admin(admin)
        return student.profile.outcomes

    def add_volunteer(self, admin: 'Admin', volunteer: Volunteer) -> None:
        self._verify_admin(admin)
        if volunteer not in self.volunteers:
            self.volunteers.append(volunteer)

    def remove_volunteer(self, admin: 'Admin', volunteer: Volunteer) -> None:
        self._verify_admin(admin)
        if volunteer in self.volunteers:
            self.volunteers.remove(volunteer)

    def list_volunteers(self, admin: 'Admin') -> List[Volunteer]:
        self._verify_admin(admin)
        return self.volunteers.copy()

    def add_to_waitlist(self, admin: 'Admin', student_name: str) -> None:
        self._verify_admin(admin)
        self.waitlist.add_student(student_name)

    def remove_from_waitlist(self, admin: 'Admin', student_name: str) -> None:
        self._verify_admin(admin)
        self.waitlist.remove_student(student_name)

    def view_waitlist(self, admin: 'Admin') -> List[str]:
        self._verify_admin(admin)
        return self.waitlist.get_waitlist()


class Admin(User):
    def __init__(self, username: str, password: str, dashboard: AdminDashboard):
        super().__init__(username, password)
        self.dashboard: AdminDashboard = dashboard

    def view_student_profile(self, student: Student) -> Dict[str, Any]:
        return student.profile.view_profile(self)


class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.dashboard: AdminDashboard = AdminDashboard()

    def create_student_account(self, username: str, password: str) -> Student:
        if username in self.users:
            raise ValueError("Username already exists.")
        student = Student(username, password)
        self.users[username] = student
        self.dashboard.register_student(student)
        return student

    def create_admin_account(self, username: str, password: str) -> Admin:
        if username in self.users:
            raise ValueError("Username already exists.")
        admin = Admin(username, password, self.dashboard)
        self.users[username] = admin
        return admin

    def create_volunteer_account(self, username: str, password: str, role_description: str = "") -> Volunteer:
        if username in self.users:
            raise ValueError("Username already exists.")
        volunteer = Volunteer(username, password, role_description)
        self.users[username] = volunteer
        return volunteer

    def login(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username)
        if user and user.login(password):
            return user
        raise ValueError("Invalid username or password.")