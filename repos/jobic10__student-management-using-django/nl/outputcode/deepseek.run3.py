from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union
import uuid

# =================== Enums and Exceptions ===================

class Role(Enum):
    ADMIN = auto()
    STAFF = auto()
    STUDENT = auto()

class LeaveStatus(Enum):
    PENDING = auto()
    APPROVED = auto()
    REJECTED = auto()

class AttendanceStatus(Enum):
    PRESENT = auto()
    ABSENT = auto()

class Grade(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

class AuthorizationError(Exception):
    """Raised when a user lacks permission for an operation."""
    pass

class NotFoundError(Exception):
    """Raised when an entity is not found."""
    pass

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

# =================== User Classes ===================

class User(ABC):
    def __init__(self, user_id: str, name: str, email: str, password: str, role: Role):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._password = password
        self._role = role

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        self._email = value

    def check_password(self, password: str) -> bool:
        return self._password == password

    @property
    def role(self) -> Role:
        return self._role

class AdminUser(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, Role.ADMIN)

class Staff(User):
    def __init__(self, user_id: str, name: str, email: str, password: str, subjects: Optional[List[str]] = None):
        super().__init__(user_id, name, email, password, Role.STAFF)
        self._subjects = subjects if subjects is not None else []  # list of subject_ids they teach

    @property
    def subjects(self) -> List[str]:
        return self._subjects

    def add_subject(self, subject_id: str):
        if subject_id not in self._subjects:
            self._subjects.append(subject_id)

    def remove_subject(self, subject_id: str):
        if subject_id in self._subjects:
            self._subjects.remove(subject_id)

class Student(User):
    def __init__(self, user_id: str, name: str, email: str, password: str, subjects: Optional[List[str]] = None):
        super().__init__(user_id, name, email, password, Role.STUDENT)
        self._subjects = subjects if subjects is not None else []  # enrolled subject_ids

    @property
    def subjects(self) -> List[str]:
        return self._subjects

    def enroll_subject(self, subject_id: str):
        if subject_id not in self._subjects:
            self._subjects.append(subject_id)

    def unenroll_subject(self, subject_id: str):
        if subject_id in self._subjects:
            self._subjects.remove(subject_id)

# =================== Academic Entities ===================

class Course:
    def __init__(self, course_id: str, name: str, description: str = ""):
        self._course_id = course_id
        self._name = name
        self._description = description

    @property
    def course_id(self) -> str:
        return self._course_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value

class Subject:
    def __init__(self, subject_id: str, name: str, description: str, course_id: str):
        self._subject_id = subject_id
        self._name = name
        self._description = description
        self._course_id = course_id

    @property
    def subject_id(self) -> str:
        return self._subject_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value

    @property
    def course_id(self) -> str:
        return self._course_id

    @course_id.setter
    def course_id(self, value: str):
        self._course_id = value

class Session:
    def __init__(self, session_id: str, name: str, start_date: date, end_date: date):
        self._session_id = session_id
        self._name = name
        self._start_date = start_date
        self._end_date = end_date

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def start_date(self) -> date:
        return self._start_date

    @start_date.setter
    def start_date(self, value: date):
        self._start_date = value

    @property
    def end_date(self) -> date:
        return self._end_date

    @end_date.setter
    def end_date(self, value: date):
        self._end_date = value

# =================== Operational Entities ===================

class Attendance:
    def __init__(self, attendance_id: str, student_id: str, subject_id: str, session_id: str, attendance_date: date, status: AttendanceStatus):
        self._attendance_id = attendance_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._session_id = session_id
        self._attendance_date = attendance_date
        self._status = status

    @property
    def attendance_id(self) -> str:
        return self._attendance_id

    @property
    def student_id(self) -> str:
        return self._student_id

    @property
    def subject_id(self) -> str:
        return self._subject_id

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def attendance_date(self) -> date:
        return self._attendance_date

    @property
    def status(self) -> AttendanceStatus:
        return self._status

    @status.setter
    def status(self, value: AttendanceStatus):
        self._status = value

class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str, session_id: str, marks: float, grade: Grade):
        self._result_id = result_id
        self._student_id = student_id
        self._subject_id = subject_id
        self._session_id = session_id
        self._marks = marks
        self._grade = grade

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def student_id(self) -> str:
        return self._student_id

    @property
    def subject_id(self) -> str:
        return self._subject_id

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def marks(self) -> float:
        return self._marks

    @marks.setter
    def marks(self, value: float):
        self._marks = value

    @property
    def grade(self) -> Grade:
        return self._grade

    @grade.setter
    def grade(self, value: Grade):
        self._grade = value

class Leave:
    def __init__(self, leave_id: str, user_id: str, user_type: Role, start_date: date, end_date: date, reason: str, status: LeaveStatus = LeaveStatus.PENDING, reply: str = ""):
        self._leave_id = leave_id
        self._user_id = user_id
        self._user_type = user_type
        self._start_date = start_date
        self._end_date = end_date
        self._reason = reason
        self._status = status
        self._reply = reply

    @property
    def leave_id(self) -> str:
        return self._leave_id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def user_type(self) -> Role:
        return self._user_type

    @property
    def start_date(self) -> date:
        return self._start_date

    @property
    def end_date(self) -> date:
        return self._end_date

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def status(self) -> LeaveStatus:
        return self._status

    @status.setter
    def status(self, value: LeaveStatus):
        self._status = value

    @property
    def reply(self) -> str:
        return self._reply

    @reply.setter
    def reply(self, value: str):
        self._reply = value

class Feedback:
    def __init__(self, feedback_id: str, user_id: str, user_type: Role, message: str, reply: str = ""):
        self._feedback_id = feedback_id
        self._user_id = user_id
        self._user_type = user_type
        self._message = message
        self._reply = reply

    @property
    def feedback_id(self) -> str:
        return self._feedback_id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def user_type(self) -> Role:
        return self._user_type

    @property
    def message(self) -> str:
        return self._message

    @property
    def reply(self) -> str:
        return self._reply

    @reply.setter
    def reply(self, value: str):
        self._reply = value

# =================== Core System ===================

class StudentManagementSystem:
    def __init__(self):
        self._users: Dict[str, User] = {}   # key: user_id
        self._courses: Dict[str, Course] = {}
        self._subjects: Dict[str, Subject] = {}
        self._sessions: Dict[str, Session] = {}
        self._attendances: Dict[str, Attendance] = {}
        self._results: Dict[str, Result] = {}
        self._leaves: Dict[str, Leave] = {}
        self._feedbacks: Dict[str, Feedback] = {}
        self._login_users: Dict[str, User] = {}  # user_id -> user (session simulation)

    def _generate_id(self, prefix: str = "") -> str:
        return prefix + str(uuid.uuid4().hex[:8])

    # ------------------ Authentication ------------------
    def register_user(self, user: User):
        if user.user_id in self._users:
            raise ValidationError("User ID already exists")
        self._users[user.user_id] = user

    def login(self, user_id: str, password: str) -> User:
        user = self._users.get(user_id)
        if not user or not user.check_password(password):
            raise ValidationError("Invalid credentials")
        self._login_users[user_id] = user
        return user

    def logout(self, user_id: str):
        self._login_users.pop(user_id, None)

    def get_current_user(self, user_id: str) -> Optional[User]:
        return self._login_users.get(user_id)

    # ------------------ Authorization helpers ------------------
    def _require_admin(self, user: User):
        if user.role != Role.ADMIN:
            raise AuthorizationError("Admin role required")

    def _require_staff(self, user: User):
        if user.role != Role.STAFF:
            raise AuthorizationError("Staff role required")

    def _require_student(self, user: User):
        if user.role != Role.STUDENT:
            raise AuthorizationError("Student role required")

    # ------------------ Admin: Summary Charts (return data dicts) ------------------
    def student_performance_summary(self, admin: User) -> Dict[str, Any]:
        self._require_admin(admin)
        summary = {"total_students": 0, "average_marks": 0.0, "grade_distribution": {g.name: 0 for g in Grade}}
        students = [u for u in self._users.values() if u.role == Role.STUDENT]
        summary["total_students"] = len(students)
        all_marks = []
        for res in self._results.values():
            all_marks.append(res.marks)
            summary["grade_distribution"][res.grade.name] += 1
        if all_marks:
            summary["average_marks"] = sum(all_marks) / len(all_marks)
        else:
            summary["average_marks"] = 0.0
        return summary

    def staff_performance_summary(self, admin: User) -> Dict[str, Any]:
        self._require_admin(admin)
        staff_count = sum(1 for u in self._users.values() if u.role == Role.STAFF)
        subjects_taught = set()
        for user in self._users.values():
            if isinstance(user, Staff):
                subjects_taught.update(user.subjects)
        return {"total_staff": staff_count, "total_subjects_covered": len(subjects_taught)}

    def course_summary(self, admin: User) -> Dict[str, int]:
        self._require_admin(admin)
        return {"total_courses": len(self._courses)}

    def subject_summary(self, admin: User) -> Dict[str, int]:
        self._require_admin(admin)
        return {"total_subjects": len(self._subjects)}

    def leave_summary(self, admin: User) -> Dict[str, int]:
        self._require_admin(admin)
        pending = sum(1 for lv in self._leaves.values() if lv.status == LeaveStatus.PENDING)
        approved = sum(1 for lv in self._leaves.values() if lv.status == LeaveStatus.APPROVED)
        rejected = sum(1 for lv in self._leaves.values() if lv.status == LeaveStatus.REJECTED)
        return {"pending": pending, "approved": approved, "rejected": rejected}

    # ------------------ Admin: Manage Staff ------------------
    def add_staff(self, admin: User, name: str, email: str, password: str) -> Staff:
        self._require_admin(admin)
        staff_id = self._generate_id("STAFF_")
        staff = Staff(staff_id, name, email, password)
        self.register_user(staff)
        return staff

    def update_staff(self, admin: User, staff_id: str, name: str = None, email: str = None, password: str = None):
        self._require_admin(admin)
        user = self._users.get(staff_id)
        if not user or user.role != Role.STAFF:
            raise NotFoundError("Staff not found")
        staff: Staff = user
        if name is not None:
            staff.name = name
        if email is not None:
            staff.email = email
        if password is not None:
            staff._password = password  # Bypass property for simplicity

    def delete_staff(self, admin: User, staff_id: str):
        self._require_admin(admin)
        user = self._users.pop(staff_id, None)
        if not user or user.role != Role.STAFF:
            raise NotFoundError("Staff not found")

    # ------------------ Admin: Manage Students ------------------
    def add_student(self, admin: User, name: str, email: str, password: str) -> Student:
        self._require_admin(admin)
        student_id = self._generate_id("STU_")
        student = Student(student_id, name, email, password)
        self.register_user(student)
        return student

    def update_student(self, admin: User, student_id: str, name: str = None, email: str = None, password: str = None):
        self._require_admin(admin)
        user = self._users.get(student_id)
        if not user or user.role != Role.STUDENT:
            raise NotFoundError("Student not found")
        student: Student = user
        if name is not None:
            student.name = name
        if email is not None:
            student.email = email
        if password is not None:
            student._password = password

    def delete_student(self, admin: User, student_id: str):
        self._require_admin(admin)
        user = self._users.pop(student_id, None)
        if not user or user.role != Role.STUDENT:
            raise NotFoundError("Student not found")

    # ------------------ Admin: Manage Courses ------------------
    def add_course(self, admin: User, name: str, description: str = "") -> Course:
        self._require_admin(admin)
        course_id = self._generate_id("COURSE_")
        course = Course(course_id, name, description)
        self._courses[course_id] = course
        return course

    def update_course(self, admin: User, course_id: str, name: str = None, description: str = None):
        self._require_admin(admin)
        course = self._courses.get(course_id)
        if not course:
            raise NotFoundError("Course not found")
        if name is not None:
            course.name = name
        if description is not None:
            course.description = description

    def delete_course(self, admin: User, course_id: str):
        self._require_admin(admin)
        if course_id not in self._courses:
            raise NotFoundError("Course not found")
        del self._courses[course_id]
        # optionally remove subjects associated with this course

    # ------------------ Admin: Manage Subjects ------------------
    def add_subject(self, admin: User, name: str, description: str, course_id: str) -> Subject:
        self._require_admin(admin)
        if course_id not in self._courses:
            raise ValidationError("Course does not exist")
        subject_id = self._generate_id("SUB_")
        subject = Subject(subject_id, name, description, course_id)
        self._subjects[subject_id] = subject
        return subject

    def update_subject(self, admin: User, subject_id: str, name: str = None, description: str = None, course_id: str = None):
        self._require_admin(admin)
        subject = self._subjects.get(subject_id)
        if not subject:
            raise NotFoundError("Subject not found")
        if name is not None:
            subject.name = name
        if description is not None:
            subject.description = description
        if course_id is not None:
            if course_id not in self._courses:
                raise ValidationError("Course does not exist")
            subject.course_id = course_id

    def delete_subject(self, admin: User, subject_id: str):
        self._require_admin(admin)
        if subject_id not in self._subjects:
            raise NotFoundError("Subject not found")
        del self._subjects[subject_id]

    # ------------------ Admin: Manage Sessions ------------------
    def add_session(self, admin: User, name: str, start_date: date, end_date: date) -> Session:
        self._require_admin(admin)
        session_id = self._generate_id("SESS_")
        session = Session(session_id, name, start_date, end_date)
        self._sessions[session_id] = session
        return session

    def update_session(self, admin: User, session_id: str, name: str = None, start_date: date = None, end_date: date = None):
        self._require_admin(admin)
        session = self._sessions.get(session_id)
        if not session:
            raise NotFoundError("Session not found")
        if name is not None:
            session.name = name
        if start_date is not None:
            session.start_date = start_date
        if end_date is not None:
            session.end_date = end_date

    def delete_session(self, admin: User, session_id: str):
        self._require_admin(admin)
        if session_id not in self._sessions:
            raise NotFoundError("Session not found")
        del self._sessions[session_id]

    # ------------------ Admin: View Student Attendance ------------------
    def view_student_attendance(self, admin: User, student_id: str) -> List[Attendance]:
        self._require_admin(admin)
        if student_id not in self._users or self._users[student_id].role != Role.STUDENT:
            raise NotFoundError("Student not found")
        return [att for att in self._attendances.values() if att.student_id == student_id]

    # ------------------ Admin: Review Feedback ------------------
    def get_all_feedback(self, admin: User) -> List[Feedback]:
        self._require_admin(admin)
        return list(self._feedbacks.values())

    def reply_feedback(self, admin: User, feedback_id: str, reply: str):
        self._require_admin(admin)
        fb = self._feedbacks.get(feedback_id)
        if not fb:
            raise NotFoundError("Feedback not found")
        fb.reply = reply

    # ------------------ Admin: Review Leave ------------------
    def get_all_leaves(self, admin: User) -> List[Leave]:
        self._require_admin(admin)
        return list(self._leaves.values())

    def process_leave(self, admin: User, leave_id: str, approved: bool, reply: str = ""):
        self._require_admin(admin)
        leave = self._leaves.get(leave_id)
        if not leave:
            raise NotFoundError("Leave not found")
        leave.status = LeaveStatus.APPROVED if approved else LeaveStatus.REJECTED
        leave.reply = reply

    # ------------------ Staff: Charts ------------------
    def staff_student_summary(self, staff: User) -> Dict[str, Any]:
        self._require_staff(staff)
        staff_obj: Staff = staff
        subjects = staff_obj.subjects
        students_set = set()
        for subj_id in subjects:
            # find all students enrolled in this subject
            for user in self._users.values():
                if isinstance(user, Student) and subj_id in user.subjects:
                    students_set.add(user.user_id)
        summary = {
            "your_subjects": len(subjects),
            "students_taught": len(students_set)
        }
        return summary

    def staff_leave_status(self, staff: User) -> List[Leave]:
        self._require_staff(staff)
        return [lv for lv in self._leaves.values() if lv.user_id == staff.user_id]

    # ------------------ Staff: Take/Update Attendance ------------------
    def take_attendance(self, staff: User, student_id: str, subject_id: str, session_id: str, attendance_date: date, status: AttendanceStatus) -> Attendance:
        self._require_staff(staff)
        staff_obj: Staff = staff
        if subject_id not in staff_obj.subjects:
            raise AuthorizationError("You do not teach this subject")
        if student_id not in self._users or self._users[student_id].role != Role.STUDENT:
            raise ValidationError("Student not found")
        student: Student = self._users[student_id]
        if subject_id not in student.subjects:
            raise ValidationError("Student is not enrolled in this subject")
        if session_id not in self._sessions:
            raise ValidationError("Session not found")
        # Check if attendance already exists for same date/subject/student
        existing = [att for att in self._attendances.values()
                    if (att.student_id == student_id and att.subject_id == subject_id
                        and att.attendance_date == attendance_date
                        and att.session_id == session_id)]
        if existing:
            # update
            att = existing[0]
            att.status = status
            return att
        att_id = self._generate_id("ATT_")
        att = Attendance(att_id, student_id, subject_id, session_id, attendance_date, status)
        self._attendances[att_id] = att
        return att

    # ------------------ Staff: Add/Update Result ------------------
    def add_result(self, staff: User, student_id: str, subject_id: str, session_id: str, marks: float, grade: Grade) -> Result:
        self._require_staff(staff)
        staff_obj: Staff = staff
        if subject_id not in staff_obj.subjects:
            raise AuthorizationError("You do not teach this subject")
        if student_id not in self._users or self._users[student_id].role != Role.STUDENT:
            raise ValidationError("Student not found")
        student: Student = self._users[student_id]
        if subject_id not in student.subjects:
            raise ValidationError("Student is not enrolled in this subject")
        if session_id not in self._sessions:
            raise ValidationError("Session not found")
        # Unique result per student/subject/session; update if exists
        existing = [res for res in self._results.values()
                    if res.student_id == student_id and res.subject_id == subject_id and res.session_id == session_id]
        if existing:
            res = existing[0]
            res.marks = marks
            res.grade = grade
            return res
        res_id = self._generate_id("RES_")
        res = Result(res_id, student_id, subject_id, session_id, marks, grade)
        self._results[res_id] = res
        return res

    # ------------------ Staff: Apply Leave ------------------
    def apply_leave(self, staff: User, start_date: date, end_date: date, reason: str) -> Leave:
        self._require_staff(staff)
        leave_id = self._generate_id("LV_")
        leave = Leave(leave_id, staff.user_id, Role.STAFF, start_date, end_date, reason)
        self._leaves[leave_id] = leave
        return leave

    # ------------------ Staff: Send Feedback ------------------
    def send_feedback(self, staff: User, message: str) -> Feedback:
        self._require_staff(staff)
        fb_id = self._generate_id("FB_")
        fb = Feedback(fb_id, staff.user_id, Role.STAFF, message)
        self._feedbacks[fb_id] = fb
        return fb

    # ------------------ Student: Charts ------------------
    def student_attendance_summary(self, student: User) -> Dict[str, int]:
        self._require_student(student)
        atts = [att for att in self._attendances.values() if att.student_id == student.user_id]
        present = sum(1 for a in atts if a.status == AttendanceStatus.PRESENT)
        absent = len(atts) - present
        return {"total_records": len(atts), "present": present, "absent": absent}

    def student_results_summary(self, student: User) -> List[Result]:
        self._require_student(student)
        return [res for res in self._results.values() if res.student_id == student.user_id]

    def student_leave_status(self, student: User) -> List[Leave]:
        self._require_student(student)
        return [lv for lv in self._leaves.values() if lv.user_id == student.user_id]

    # ------------------ Student: View Attendance ------------------
    def view_attendance(self, student: User) -> List[Attendance]:
        self._require_student(student)
        return [att for att in self._attendances.values() if att.student_id == student.user_id]

    # ------------------ Student: View Result ------------------
    def view_results(self, student: User) -> List[Result]:
        self._require_student(student)
        return [res for res in self._results.values() if res.student_id == student.user_id]

    # ------------------ Student: Apply Leave ------------------
    def student_apply_leave(self, student: User, start_date: date, end_date: date, reason: str) -> Leave:
        self._require_student(student)
        leave_id = self._generate_id("LV_")
        leave = Leave(leave_id, student.user_id, Role.STUDENT, start_date, end_date, reason)
        self._leaves[leave_id] = leave
        return leave

    # ------------------ Student: Send Feedback ------------------
    def student_send_feedback(self, student: User, message: str) -> Feedback:
        self._require_student(student)
        fb_id = self._generate_id("FB_")
        fb = Feedback(fb_id, student.user_id, Role.STUDENT, message)
        self._feedbacks[fb_id] = fb
        return fb

    # ------------------ Helper: enroll student into subject (admin) ------------------
    def enroll_student_in_subject(self, admin: User, student_id: str, subject_id: str):
        self._require_admin(admin)
        student = self._users.get(student_id)
        if not student or student.role != Role.STUDENT:
            raise NotFoundError("Student not found")
        if subject_id not in self._subjects:
            raise NotFoundError("Subject not found")
        student.enroll_subject(subject_id)

    def assign_subject_to_staff(self, admin: User, staff_id: str, subject_id: str):
        self._require_admin(admin)
        staff = self._users.get(staff_id)
        if not staff or staff.role != Role.STAFF:
            raise NotFoundError("Staff not found")
        if subject_id not in self._subjects:
            raise NotFoundError("Subject not found")
        staff.add_subject(subject_id)

# =================== Demo / Main ===================

if __name__ == "__main__":
    sms = StudentManagementSystem()

    # Register an admin
    admin = AdminUser("admin1", "Admin User", "admin@school.com", "admin123")
    sms.register_user(admin)

    admin_session = sms.login("admin1", "admin123")

    # Admin adds courses and subjects
    course = sms.add_course(admin_session, "Computer Science", "CS program")
    subject1 = sms.add_subject(admin_session, "Data Structures", "DS course", course.course_id)
    subject2 = sms.add_subject(admin_session, "Algorithms", "Algo course", course.course_id)
    sms.add_session(admin_session, "2024-2025", date(2024, 9, 1), date(2025, 6, 30))

    # Admin adds staff and student
    staff = sms.add_staff(admin_session, "Dr. Smith", "smith@school.com", "staff123")
    student = sms.add_student(admin_session, "John Doe", "john@school.com", "student123")

    # Enroll student and assign subject to staff
    sms.enroll_student_in_subject(admin_session, student.user_id, subject1.subjdict_id)
    sms.enroll_student_in_subject(admin_session, student.user_id, subject2.subjdict_id)
    sms.assign_subject_to_staff(admin_session, staff.user_id, subject1.subjdict_id)

    sms.logout("admin1")

    # Staff login
    staff_session = sms.login(staff.user_id, "staff123")
    # Staff takes attendance
    sms.take_attendance(staff_session, student.user_id, subject1.subjdict_id, "SESS_", date.today(), AttendanceStatus.PRESENT)
    # Staff adds result
    sms.add_result(staff_session, student.user_id, subject1.subjdict_id, "SESS_", 85.5, Grade.A)
    # Staff applies leave
    sms.apply_leave(staff_session, date.today(), date.today(), "Personal")
    sms.send_feedback(staff_session, "Need more resources")
    sms.logout(staff.user_id)

    # Student login
    student_session = sms.login(student.user_id, "student123")
    print("Student attendance summary:", sms.student_attendance_summary(student_session))
    print("Student results:", sms.view_results(student_session))
    sms.student_apply_leave(student_session, date.today(), date.today(), "Sick")
    sms.student_send_feedback(student_session, "Enjoying classes")
    sms.logout(student.user_id)

    # Admin reviews
    admin2 = sms.login("admin1", "admin123")
    print("Leave summary:", sms.leave_summary(admin2))
    print("All feedback:", [(f.feedback_id, f.message) for f in sms.get_all_feedback(admin2)])
    # Process some leaves
    leaves = sms.get_all_leaves(admin2)
    if leaves:
        sms.process_leave(admin2, leaves[0].leave_id, True, "Granted")
    print("Updated leave summary:", sms.leave_summary(admin2))
    sms.logout("admin1")