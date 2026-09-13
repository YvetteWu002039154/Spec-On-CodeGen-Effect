from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Union
import uuid

# -----------------------------------------------------------------------------
# Enums / constants
# -----------------------------------------------------------------------------
class LeaveStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class FeedbackStatus:
    UNREAD = "unread"
    READ = "read"
    REPLIED = "replied"

class ResultGrade:
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

AttendanceStatus = Union[str, bool]  # present/absent

# -----------------------------------------------------------------------------
# Entity classes
# -----------------------------------------------------------------------------
class Course:
    def __init__(self, course_id: str, name: str):
        self.course_id = course_id
        self.name = name

    def __repr__(self):
        return f"Course({self.course_id}, {self.name})"


class Subject:
    def __init__(self, subject_id: str, name: str, course_id: Optional[str] = None,
                 staff_id: Optional[str] = None):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id  # assigned teacher

    def __repr__(self):
        return f"Subject({self.subject_id}, {self.name})"


class Session:
    def __init__(self, session_id: str, name: str, start_year: int, end_year: int):
        self.session_id = session_id
        self.name = name
        self.start_year = start_year
        self.end_year = end_year

    def __repr__(self):
        return f"Session({self.session_id}, {self.name})"


class Attendance:
    def __init__(self, attendance_id: str, student_id: str, subject_id: str,
                 date_: date, status: bool):
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.date = date_
        self.status = status  # True = present

    def __repr__(self):
        return f"Attendance({self.student_id}, {self.subject_id}, {self.date}, {self.status})"


class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 session_id: str, marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.marks = marks

    def __repr__(self):
        return f"Result({self.student_id}, {self.subject_id}, {self.marks})"


class Leave:
    def __init__(self, leave_id: str, requester_id: str, requester_type: str,
                 start_date: date, end_date: date, reason: str,
                 status: str = LeaveStatus.PENDING):
        self.leave_id = leave_id
        self.requester_id = requester_id
        self.requester_type = requester_type  # 'student' or 'staff'
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = status

    def __repr__(self):
        return f"Leave({self.requester_id}, {self.status})"


class Feedback:
    def __init__(self, feedback_id: str, sender_id: str, sender_type: str,
                 message: str, reply: str = "", status: str = FeedbackStatus.UNREAD):
        self.feedback_id = feedback_id
        self.sender_id = sender_id
        self.sender_type = sender_type
        self.message = message
        self.reply = reply
        self.status = status

    def __repr__(self):
        return f"Feedback({self.sender_id}, {self.status})"


# -----------------------------------------------------------------------------
# User hierarchy
# -----------------------------------------------------------------------------
class User(ABC):
    def __init__(self, user_id: str, username: str, password: str,
                 first_name: str, last_name: str):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name

    @abstractmethod
    def role(self) -> str:
        pass

    def __repr__(self):
        return f"{self.role()}({self.username})"


class Admin(User):
    def __init__(self, user_id: str, username: str, password: str,
                 first_name: str, last_name: str):
        super().__init__(user_id, username, password, first_name, last_name)

    def role(self) -> str:
        return "admin"


class Staff(User):
    def __init__(self, user_id: str, username: str, password: str,
                 first_name: str, last_name: str,
                 staff_id: Optional[str] = None):
        super().__init__(user_id, username, password, first_name, last_name)
        self.staff_id = staff_id or user_id  # can be same as user_id
        self._subjects_taught: List[str] = []  # subject_ids

    def role(self) -> str:
        return "staff"

    def add_subject(self, subject_id: str):
        if subject_id not in self._subjects_taught:
            self._subjects_taught.append(subject_id)

    def remove_subject(self, subject_id: str):
        if subject_id in self._subjects_taught:
            self._subjects_taught.remove(subject_id)

    def get_subjects(self) -> List[str]:
        return self._subjects_taught.copy()


class Student(User):
    def __init__(self, user_id: str, username: str, password: str,
                 first_name: str, last_name: str,
                 student_id: Optional[str] = None):
        super().__init__(user_id, username, password, first_name, last_name)
        self.student_id = student_id or user_id

    def role(self) -> str:
        return "student"


# -----------------------------------------------------------------------------
# Main management system
# -----------------------------------------------------------------------------
class StudentManagementSystem:
    def __init__(self):
        self._users: Dict[str, User] = {}           # key: username
        self._courses: Dict[str, Course] = {}       # key: course_id
        self._subjects: Dict[str, Subject] = {}     # key: subject_id
        self._sessions: Dict[str, Session] = {}     # key: session_id
        self._attendances: List[Attendance] = []
        self._results: List[Result] = []
        self._leaves: List[Leave] = []
        self._feedbacks: List[Feedback] = []
        self._current_user: Optional[User] = None

    # ---------------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------------
    def login(self, username: str, password: str) -> bool:
        user = self._users.get(username)
        if user and user.password == password:
            self._current_user = user
            return True
        return False

    def logout(self):
        self._current_user = None

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    # ---------------------------------------------------------------
    # Helper: id generation
    # ---------------------------------------------------------------
    @staticmethod
    def _generate_id(prefix: str = "") -> str:
        return prefix + str(uuid.uuid4())[:8]

    # ---------------------------------------------------------------
    # User management (admin)
    # ---------------------------------------------------------------
    def add_admin(self, username: str, password: str,
                  first_name: str, last_name: str) -> Optional[Admin]:
        if not self._is_admin():
            print("Permission denied.")
            return None
        if username in self._users:
            print("Username already exists.")
            return None
        user_id = self._generate_id("adm_")
        admin = Admin(user_id, username, password, first_name, last_name)
        self._users[username] = admin
        return admin

    def add_staff(self, username: str, password: str,
                  first_name: str, last_name: str) -> Optional[Staff]:
        if not self._is_admin():
            print("Permission denied.")
            return None
        if username in self._users:
            print("Username already exists.")
            return None
        user_id = self._generate_id("stf_")
        staff = Staff(user_id, username, password, first_name, last_name)
        self._users[username] = staff
        return staff

    def add_student(self, username: str, password: str,
                    first_name: str, last_name: str) -> Optional[Student]:
        if not self._is_admin():
            print("Permission denied.")
            return None
        if username in self._users:
            print("Username already exists.")
            return None
        user_id = self._generate_id("stu_")
        student = Student(user_id, username, password, first_name, last_name)
        self._users[username] = student
        return student

    def update_user(self, username: str, **kwargs) -> bool:
        user = self._users.get(username)
        if not user:
            print("User not found.")
            return False
        if not self._is_admin() and self._current_user != user:
            print("Permission denied.")
            return False
        for attr, value in kwargs.items():
            if hasattr(user, attr):
                setattr(user, attr, value)
        return True

    def delete_user(self, username: str) -> bool:
        if not self._is_admin():
            print("Permission denied.")
            return False
        if username not in self._users:
            print("User not found.")
            return False
        del self._users[username]
        return True

    def _is_admin(self) -> bool:
        return isinstance(self._current_user, Admin)

    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)

    # ---------------------------------------------------------------
    # Course management (admin)
    # ---------------------------------------------------------------
    def add_course(self, name: str) -> Optional[Course]:
        if not self._is_admin():
            print("Permission denied.")
            return None
        course_id = self._generate_id("crs_")
        course = Course(course_id, name)
        self._courses[course_id] = course
        return course

    def update_course(self, course_id: str, name: Optional[str] = None) -> bool:
        if not self._is_admin():
            print("Permission denied.")
            return False
        course = self._courses.get(course_id)
        if not course:
            print("Course not found.")
            return False
        if name is not None:
            course.name = name
        return True

    def delete_course(self, course_id: str) -> bool:
        if not self._is_admin():
            print("Permission denied.")
            return False
        if course_id not in self._courses:
            print("Course not found.")
            return False
        del self._courses[course_id]
        return True

    def get_course(self, course_id: str) -> Optional[Course]:
        return self._courses.get(course_id)

    def get_all_courses(self) -> Dict[str, Course]:
        return self._courses.copy()

    # ---------------------------------------------------------------
    # Subject management (admin)
    # ---------------------------------------------------------------
    def add_subject(self, name: str, course_id: Optional[str] = None,
                    staff_id: Optional[str] = None) -> Optional[Subject]:
        if not self._is_admin():
            print("Permission denied.")
            return None
        subject_id = self._generate_id("sub_")
        subject = Subject(subject_id, name, course_id, staff_id)
        self._subjects[subject_id] = subject
        # If staff assigned, automatically update staff's subjects list
        if staff_id:
            staff_user = self._find_staff_by_staff_id(staff_id)
            if staff_user:
                staff_user.add_subject(subject_id)
        return subject

    def update_subject(self, subject_id: str, **kwargs) -> bool:
        if not self._is_admin():
            print("Permission denied.")
            return False
        subject = self._subjects.get(subject_id)
        if not subject:
            print("Subject not found.")
            return False
        # handle staff_id change: remove from old staff and add to new
        if 'staff_id' in kwargs:
            new_staff = kwargs['staff_id']
            old_staff = subject.staff_id
            if old_staff:
                old_staff_user = self._find_staff_by_staff_id(old_staff)
                if old_staff_user:
                    old_staff_user.remove_subject(subject_id)
            if new_staff:
                new_staff_user = self._find_staff_by_staff_id(new_staff)
                if new_staff_user:
                    new_staff_user.add_subject(subject_id)
            subject.staff_id = new_staff
        for attr, value in kwargs.items():
            if attr != 'staff_id' and hasattr(subject, attr):
                setattr(subject, attr, value)
        return True

    def delete_subject(self, subject_id: str) -> bool:
        if not self._is_admin():
            print("Permission denied.")
            return False
        if subject_id not in self._subjects:
            print("Subject not found.")
            return False
        subject = self._subjects[subject_id]
        if subject.staff_id:
            staff_user = self._find_staff_by_staff_id(subject.staff_id)
            if staff_user:
                staff_user.remove_subject(subject_id)
        del self._subjects[subject_id]
        return True

    def get_subject(self, subject_id: str) -> Optional[Subject]:
        return self._subjects.get(subject_id)

    def get_all_subjects(self) -> Dict[str, Subject]:
        return self._subjects.copy()

    def _find_staff_by_staff_id(self, staff_id: str) -> Optional[Staff]:
        for user in self._users.values():
            if isinstance(user, Staff) and user.staff_id == staff_id:
                return user
        return None

    # ---------------------------------------------------------------
    # Session management (admin)
    # ---------------------------------------------------------------
    def add_session(self, name: str, start_year: int, end_year: int) -> Optional[Session]:
        if not self._is_admin():
            print("Permission denied.")
            return None
        session_id = self._generate_id("ses_")
        session = Session(session_id, name, start_year, end_year)
        self._sessions[session_id] = session
        return session

    def update_session(self, session_id: str, **kwargs) -> bool:
        if not self._is_admin():
            print("Permission denied.")
            return False
        session = self._sessions.get(session_id)
        if not session:
            print("Session not found.")
            return False
        for attr, value in kwargs.items():
            if hasattr(session, attr):
                setattr(session, attr, value)
        return True

    def delete_session(self, session_id: str) -> bool:
        if not self._is_admin():
            print("Permission denied.")
            return False
        if session_id not in self._sessions:
            print("Session not found.")
            return False
        del self._sessions[session_id]
        return True

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def get_all_sessions(self) -> Dict[str, Session]:
        return self._sessions.copy()

    # ---------------------------------------------------------------
    # Attendance (staff takes attendance, admin views)
    # ---------------------------------------------------------------
    def record_attendance(self, student_id: str, subject_id: str,
                          date_: date, status: bool) -> Optional[Attendance]:
        if not isinstance(self._current_user, Staff):
            print("Only staff can record attendance.")
            return None
        staff = self._current_user
        if subject_id not in staff.get_subjects():
            print("You do not teach this subject.")
            return None
        if student_id not in self._users:
            print("Student not found.")
            return None
        student = self._users[student_id]
        if not isinstance(student, Student):
            print("Not a student.")
            return None
        att_id = self._generate_id("att_")
        attendance = Attendance(att_id, student.student_id, subject_id, date_, status)
        self._attendances.append(attendance)
        return attendance

    def update_attendance(self, attendance_id: str, **kwargs) -> bool:
        if not isinstance(self._current_user, Staff):
            print("Only staff can update attendance.")
            return False
        attendance = self._find_attendance_by_id(attendance_id)
        if not attendance:
            print("Attendance not found.")
            return False
        if attendance.subject_id not in self._current_user.get_subjects():
            print("You do not teach this subject.")
            return False
        for attr, value in kwargs.items():
            if hasattr(attendance, attr):
                setattr(attendance, attr, value)
        return True

    def get_attendance_for_student(self, student_id: str) -> List[Attendance]:
        # anyone can use, but typically student or staff
        return [a for a in self._attendances if a.student_id == student_id]

    def get_attendance_for_subject(self, subject_id: str) -> List[Attendance]:
        return [a for a in self._attendances if a.subject_id == subject_id]

    def get_all_attendances(self) -> List[Attendance]:
        if not self._is_admin():
            print("Admin only.")
            return []
        return self._attendances.copy()

    def _find_attendance_by_id(self, att_id: str) -> Optional[Attendance]:
        for a in self._attendances:
            if a.attendance_id == att_id:
                return a
        return None

    # ---------------------------------------------------------------
    # Results (staff adds/updates, student views)
    # ---------------------------------------------------------------
    def add_result(self, student_id: str, subject_id: str,
                   session_id: str, marks: float) -> Optional[Result]:
        if not isinstance(self._current_user, Staff):
            print("Only staff can add results.")
            return None
        if subject_id not in self._current_user.get_subjects():
            print("You do not teach this subject.")
            return None
        result_id = self._generate_id("res_")
        result = Result(result_id, student_id, subject_id, session_id, marks)
        self._results.append(result)
        return result

    def update_result(self, result_id: str, **kwargs) -> bool:
        if not isinstance(self._current_user, Staff):
            print("Only staff can update results.")
            return False
        result = self._find_result_by_id(result_id)
        if not result:
            print("Result not found.")
            return False
        if result.subject_id not in self._current_user.get_subjects():
            print("You do not teach this subject.")
            return False
        for attr, value in kwargs.items():
            if hasattr(result, attr):
                setattr(result, attr, value)
        return True

    def get_results_for_student(self, student_id: str) -> List[Result]:
        # anyone
        return [r for r in self._results if r.student_id == student_id]

    def get_results_for_subject(self, subject_id: str) -> List[Result]:
        return [r for r in self._results if r.subject_id == subject_id]

    def get_all_results(self) -> List[Result]:
        if not self._is_admin():
            print("Admin only.")
            return []
        return self._results.copy()

    def _find_result_by_id(self, result_id: str) -> Optional[Result]:
        for r in self._results:
            if r.result_id == result_id:
                return r
        return None

    # ---------------------------------------------------------------
    # Leave management (student/staff apply, admin reviews)
    # ---------------------------------------------------------------
    def apply_leave(self, start_date: date, end_date: date,
                    reason: str) -> Optional[Leave]:
        user = self._current_user
        if not user:
            print("Not logged in.")
            return None
        if isinstance(user, Student):
            requester_id = user.student_id
            requester_type = 'student'
        elif isinstance(user, Staff):
            requester_id = user.staff_id
            requester_type = 'staff'
        else:
            print("Admins cannot apply for leave.")
            return None
        leave_id = self._generate_id("lve_")
        leave = Leave(leave_id, requester_id, requester_type,
                      start_date, end_date, reason)
        self._leaves.append(leave)
        return leave

    def review_leave(self, leave_id: str, action: str) -> bool:
        if not self._is_admin():
            print("Only admin can review leaves.")
            return False
        leave = self._find_leave_by_id(leave_id)
        if not leave:
            print("Leave not found.")
            return False
        if action in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
            leave.status = action
            return True
        print("Invalid action. Use 'approved' or 'rejected'.")
        return False

    def get_leave_for_user(self, user_id: str) -> List[Leave]:
        return [l for l in self._leaves if l.requester_id == user_id]

    def get_all_leaves(self) -> List[Leave]:
        if not self._is_admin():
            print("Admin only.")
            return []
        return self._leaves.copy()

    def _find_leave_by_id(self, leave_id: str) -> Optional[Leave]:
        for l in self._leaves:
            if l.leave_id == leave_id:
                return l
        return None

    # ---------------------------------------------------------------
    # Feedback (student/staff send, admin replies)
    # ---------------------------------------------------------------
    def send_feedback(self, message: str) -> Optional[Feedback]:
        user = self._current_user
        if not user:
            print("Not logged in.")
            return None
        if isinstance(user, Student):
            sender_id = user.student_id
            sender_type = 'student'
        elif isinstance(user, Staff):
            sender_id = user.staff_id
            sender_type = 'staff'
        else:
            print("Admins cannot send feedback.")
            return None
        feedback_id = self._generate_id("fbk_")
        feedback = Feedback(feedback_id, sender_id, sender_type, message)
        self._feedbacks.append(feedback)
        return feedback

    def reply_feedback(self, feedback_id: str, reply: str) -> bool:
        if not self._is_admin():
            print("Only admin can reply to feedback.")
            return False
        feedback = self._find_feedback_by_id(feedback_id)
        if not feedback:
            print("Feedback not found.")
            return False
        feedback.reply = reply
        feedback.status = FeedbackStatus.REPLIED
        return True

    def view_feedback_for_user(self, user_id: str) -> List[Feedback]:
        return [f for f in self._feedbacks if f.sender_id == user_id]

    def get_all_feedbacks(self) -> List[Feedback]:
        if not self._is_admin():
            print("Admin only.")
            return []
        return self._feedbacks.copy()

    def _find_feedback_by_id(self, feedback_id: str) -> Optional[Feedback]:
        for f in self._feedbacks:
            if f.feedback_id == feedback_id:
                return f
        return None

    # ---------------------------------------------------------------
    # Summary charts (return dictionary summaries)
    # ---------------------------------------------------------------
    def get_admin_dashboard(self) -> Dict:
        """Overall summary for admin."""
        if not self._is_admin():
            return {"error": "Permission denied"}

        # Student performance: average marks per subject
        perf = {}
        for subj_id, subj in self._subjects.items():
            results = self.get_results_for_subject(subj_id)
            if results:
                avg = sum(r.marks for r in results) / len(results)
                perf[subj.name] = avg
            else:
                perf[subj.name] = 0.0

        # Staff workload: number of subjects each staff teaches
        workload = {}
        for user in self._users.values():
            if isinstance(user, Staff):
                workload[user.username] = len(user.get_subjects())

        # Course enrollment: number of subjects in each course
        course_subjects = {}
        for subj in self._subjects.values():
            cid = subj.course_id or "No course"
            course_subjects.setdefault(cid, 0)
            course_subjects[cid] += 1

        # Leave summary
        leave_counts = {LeaveStatus.PENDING: 0, LeaveStatus.APPROVED: 0, LeaveStatus.REJECTED: 0}
        for lv in self._leaves:
            leave_counts[lv.status] += 1

        # Feedback summary
        feedback_counts = {FeedbackStatus.UNREAD: 0, FeedbackStatus.READ: 0, FeedbackStatus.REPLIED: 0}
        for fb in self._feedbacks:
            feedback_counts[fb.status] += 1

        return {
            "student_performance_by_subject": perf,
            "staff_workload": workload,
            "course_subject_count": course_subjects,
            "leave_summary": leave_counts,
            "feedback_summary": feedback_counts,
            "total_users": len(self._users),
            "total_courses": len(self._courses),
            "total_subjects": len(self._subjects),
            "total_sessions": len(self._sessions),
        }

    def get_staff_dashboard(self, staff_id: str) -> Dict:
        """Summary for a staff member: related to their subjects and students."""
        staff_user = self._find_staff_by_staff_id(staff_id)
        if not staff_user:
            return {"error": "Staff not found"}
        subj_ids = staff_user.get_subjects()
        # Performance of students in their subjects
        perf = {}
        for subj_id in subj_ids:
            subj = self._subjects.get(subj_id)
            if subj:
                results = self.get_results_for_subject(subj_id)
                avg = sum(r.marks for r in results) / len(results) if results else 0.0
                perf[subj.name] = avg
        # Attendance summary for their subjects (count of records)
        attendance_counts = {}
        for subj_id in subj_ids:
            atts = self.get_attendance_for_subject(subj_id)
            attendance_counts[self._subjects[subj_id].name] = len(atts)
        # Leave status of self
        my_leaves = self.get_leave_for_user(staff_id)
        leave_status = {LeaveStatus.PENDING: 0, LeaveStatus.APPROVED: 0, LeaveStatus.REJECTED: 0}
        for lv in my_leaves:
            leave_status[lv.status] += 1

        return {
            "subject_performance": perf,
            "subject_attendance_count": attendance_counts,
            "my_leave_status": leave_status,
            "subjects_assigned": subj_ids,
        }

    def get_student_dashboard(self, student_id: str) -> Dict:
        """Summary for a student: attendance, results, leave, feedback."""
        # Results
        results = self.get_results_for_student(student_id)
        result_summary = {}
        for r in results:
            subj = self._subjects.get(r.subject_id)
            name = subj.name if subj else r.subject_id
            result_summary[name] = r.marks
        # Attendance
        atts = self.get_attendance_for_student(student_id)
        total = len(atts)
        present = sum(1 for a in atts if a.status)
        attendance_percent = (present / total * 100) if total > 0 else 0.0
        # Leave
        my_leaves = self.get_leave_for_user(student_id)
        leave_status = {LeaveStatus.PENDING: 0, LeaveStatus.APPROVED: 0, LeaveStatus.REJECTED: 0}
        for lv in my_leaves:
            leave_status[lv.status] += 1
        # Feedback
        feed = self.view_feedback_for_user(student_id)
        feedback_count = len(feed)

        return {
            "results": result_summary,
            "attendance": {"total": total, "present": present, "percentage": attendance_percent},
            "leave_status": leave_status,
            "feedback_count": feedback_count,
        }


# -----------------------------------------------------------------------------
# Example usage (can be removed; kept to demonstrate runnable code)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sms = StudentManagementSystem()

    # Add an admin
    admin = sms.add_admin("admin", "admin123", "Admin", "User")
    sms.login("admin", "admin123")

    # Add courses, subjects, sessions
    c1 = sms.add_course("Computer Science")
    c2 = sms.add_course("Mathematics")
    sub1 = sms.add_subject("Data Structures", c1.course_id)
    sub2 = sms.add_subject("Algorithms", c1.course_id)
    sub3 = sms.add_subject("Linear Algebra", c2.course_id)
    sess = sms.add_session("2023-2024", 2023, 2024)

    # Add staff and assign to subjects
    staff1 = sms.add_staff("staff1", "pass", "John", "Doe")
    sms.update_subject(sub1.subject_id, staff_id=staff1.staff_id)
    sms.update_subject(sub2.subject_id, staff_id=staff1.staff_id)

    # Add students
    stu1 = sms.add_student("stu1", "pass", "Alice", "Smith")
    stu2 = sms.add_student("stu2", "pass", "Bob", "Brown")

    # Login as staff to record attendance and results
    sms.logout()
    sms.login("staff1", "pass")
    sms.record_attendance(stu1.student_id, sub1.subject_id, date.today(), True)
    sms.record_attendance(stu2.student_id, sub1.subject_id, date.today(), False)
    sms.add_result(stu1.student_id, sub1.subject_id, sess.session_id, 85.0)
    sms.add_result(stu2.student_id, sub1.subject_id, sess.session_id, 72.0)

    # Apply leave as staff
    sms.apply_leave(date.today(), date.today(), "Personal reason")

    # Login as student to apply leave and view dashboard
    sms.logout()
    sms.login("stu1", "pass")
    sms.apply_leave(date.today(), date.today(), "Sick")
    student_dash = sms.get_student_dashboard(stu1.student_id)
    print("Student Dashboard:", student_dash)

    # Login as admin to review leaves and see dashboard
    sms.logout()
    sms.login("admin", "admin123")
    leaves = sms.get_all_leaves()
    for leave in leaves:
        sms.review_leave(leave.leave_id, LeaveStatus.APPROVED)
    admin_dash = sms.get_admin_dashboard()
    print("Admin Dashboard:", admin_dash)