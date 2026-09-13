from typing import List, Dict, Optional, Set
from datetime import datetime

class Role:
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"

class User:
    def __init__(self, user_id: int, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role

class StudentProfile:
    def __init__(self, user: User):
        self.user = user
        self.bio: str = ""
        self.progress: str = "Not Started"
        self.outcomes: str = "No outcomes yet"

    def update_progress(self, progress: str, outcomes: str) -> None:
        self.progress = progress
        self.outcomes = outcomes

class Volunteer:
    def __init__(self, volunteer_id: int, name: str, email: str, skills: str = ""):
        self.volunteer_id = volunteer_id
        self.name = name
        self.email = email
        self.skills = skills

class WaitlistEntry:
    def __init__(self, entry_id: int, student_name: str, email: str):
        self.entry_id = entry_id
        self.student_name = student_name
        self.email = email
        self.date_added: datetime = datetime.now()

class DjangoAdminInterface:
    def __init__(self, system: 'StudentManagementSystem'):
        self.system = system

    def get_dashboard(self, requesting_user: User) -> Dict:
        if requesting_user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied. Admins and Organizers only.")
        
        return {
            "student_progress_outcomes": [
                {
                    "student_id": profile.user.user_id,
                    "username": profile.user.username,
                    "progress": profile.progress,
                    "outcomes": profile.outcomes
                }
                for profile in self.system.profiles.values()
            ],
            "volunteers": self.system.volunteers,
            "waitlist": self.system.waitlist
        }

    def view_all_users(self, requesting_user: User) -> List[User]:
        if requesting_user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Access denied. Admins and Organizers only.")
        return list(self.system.users.values())

class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.profiles: Dict[int, StudentProfile] = {}
        self.volunteers: List[Volunteer] = []
        self.waitlist: List[WaitlistEntry] = []
        self.logged_in_users: Set[int] = set()
        self.admin_interface = DjangoAdminInterface(self)

    def register_user(self, user: User) -> None:
        self.users[user.user_id] = user
        if user.role == Role.STUDENT:
            self.profiles[user.user_id] = StudentProfile(user)

    def login(self, user_id: int) -> bool:
        if user_id in self.users:
            self.logged_in_users.add(user_id)
            return True
        return False

    def logout(self, user_id: int) -> None:
        if user_id in self.logged_in_users:
            self.logged_in_users.remove(user_id)

    def get_student_profile(self, requesting_user_id: int, target_student_id: int) -> StudentProfile:
        if requesting_user_id not in self.logged_in_users:
            raise PermissionError("User must be logged in.")
        
        requesting_user = self.users[requesting_user_id]
        
        if target_student_id not in self.profiles:
            raise ValueError("Student profile not found.")
            
        if requesting_user.role in (Role.ADMIN, Role.ORGANIZER) or requesting_user.user_id == target_student_id:
            return self.profiles[target_student_id]
        
        raise PermissionError("Private Profile: Visible only to the user and organizers/admins.")

    def update_student_profile(self, requesting_user_id: int, target_student_id: int, bio: str = None, progress: str = None, outcomes: str = None) -> None:
        profile = self.get_student_profile(requesting_user_id, target_student_id)
        requesting_user = self.users[requesting_user_id]
        
        if bio is not None:
            if requesting_user.user_id == target_student_id or requesting_user.role in (Role.ADMIN, Role.ORGANIZER):
                profile.bio = bio
            else:
                raise PermissionError("Cannot update this profile's bio.")
                
        if progress is not None or outcomes is not None:
            if requesting_user.role in (Role.ADMIN, Role.ORGANIZER):
                profile.update_progress(
                    progress if progress is not None else profile.progress,
                    outcomes if outcomes is not None else profile.outcomes
                )
            else:
                raise PermissionError("Only admins and organizers can update progress and outcomes.")

    def add_volunteer(self, requesting_user_id: int, volunteer: Volunteer) -> None:
        if requesting_user_id not in self.logged_in_users:
            raise PermissionError("User must be logged in.")
        user = self.users[requesting_user_id]
        if user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Only admins and organizers can manage volunteers.")
        self.volunteers.append(volunteer)

    def add_to_waitlist(self, requesting_user_id: int, entry: WaitlistEntry) -> None:
        if requesting_user_id not in self.logged_in_users:
            raise PermissionError("User must be logged in.")
        user = self.users[requesting_user_id]
        if user.role not in (Role.ADMIN, Role.ORGANIZER):
            raise PermissionError("Only admins and organizers can manage the waitlist.")
        self.waitlist.append(entry)

def main():
    system = StudentManagementSystem()
    
    admin = User(1, "admin_alice", Role.ADMIN)
    organizer = User(2, "org_bob", Role.ORGANIZER)
    student1 = User(3, "student_charlie", Role.STUDENT)
    student2 = User(4, "student_dave", Role.STUDENT)
    
    system.register_user(admin)
    system.register_user(organizer)
    system.register_user(student1)
    system.register_user(student2)
    
    system.login(admin.user_id)
    system.login(student1.user_id)
    
    system.update_student_profile(
        requesting_user_id=admin.user_id, 
        target_student_id=student1.user_id, 
        progress="Completed Python Basics", 
        outcomes="Ready for Django"
    )
    
    system.add_volunteer(admin.user_id, Volunteer(1, "Eve", "eve@example.com", "Python, Mentoring"))
    system.add_to_waitlist(admin.user_id, WaitlistEntry(1, "Frank", "frank@example.com"))
    
    my_profile = system.get_student_profile(student1.user_id, student1.user_id)
    
    try:
        system.get_student_profile(student1.user_id, student2.user_id)
    except PermissionError:
        pass 
        
    dashboard = system.admin_interface.get_dashboard(admin)

if __name__ == "__main__":
    main()