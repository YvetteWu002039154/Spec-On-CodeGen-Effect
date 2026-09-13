from typing import List, Dict, Optional, Union, Literal
from datetime import date, datetime
from abc import ABC, abstractmethod
import uuid

# ------------------------------------------------------------
# Data Store (simulated in-memory databases)
# ------------------------------------------------------------
class DataStore:
    users: List['User'] = []
    courses: List['Course'] = []
    subjects: List['Subject'] = []
    sessions: List['Session'] = []
    attendances: List['Attendance'] = []
    results: List['Result'] = []
    leaves: List['Leave'] = []
    feedbacks: List['Feedback'] = []

# ------------------------------------------------------------
# Base User & Authentication
# ------------------------------------------------------------
class User(ABC):
    def __init__(self, user_id: str, name: str, email: str, password: str, user_type: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.user_type = user_type  # 'admin', 'staff', 'student'

    @staticmethod
    def authenticate(email: str, password: str) -> Optional['User']:
        for user in DataStore.users:
            if user.email == email and user.password == password:
                return user
        return None

    @abstractmethod
    def get_dashboard_summary(self) -> Dict:
        pass

    def __repr__(self):
        return f"{self.user_type.capitalize()}({self.user_id}: {self.name})"

# ------------------------------------------------------------
# Admin
# ------------------------------------------------------------
class Admin(User):
    def __init__(self, name: str, email: str, password: str):
        super().__init__(str(uuid.uuid4()), name, email, password, 'admin')

    def get_dashboard_summary(self) -> Dict:
        """See Overall Summary Charts (returns data, not actual charts)"""
        total_students = sum(1 for u in DataStore.users if u.user_type == 'student')
        total_staff = sum(1 for u in DataStore.users if u.user_type == 'staff')
        return {
            "total_students": total_students,
            "total_staff": total_staff,
            "total_courses": len(DataStore.courses),
            "total_subjects": len(DataStore.subjects),
            "total_sessions": len(DataStore.sessions),
            "pending_leaves": sum(1 for l in DataStore.leaves if l.status == 'pending'),
            "unreplied_feedback": sum(1 for f in DataStore.feedbacks if f.reply is None),
            # Placeholder for performance summaries
            "average_attendance": "calculate from attendance data",
            "average_marks": "calculate from results data"
        }

    # ------ Staff management ------
    def add_staff(self, name: str, email: str, password: str) -> 'Staff':
        if any(u.email == email for u in DataStore.users):
            raise ValueError("Email already registered")
        staff = Staff(name, email, password)
        DataStore.users.append(staff)
        return staff

    def update_staff(self, staff_id: str, name: str = None, email: str = None, password: str = None) -> None:
        staff = self._find_user(staff_id, 'staff')
        if name:
            staff.name = name
        if email:
            if any(u.email == email and u.user_id != staff_id for u in DataStore.users):
                raise ValueError("Email already in use")
            staff.email = email
        if password:
            staff.password = password

    def delete_staff(self, staff_id: str) -> None:
        staff = self._find_user(staff_id, 'staff')
        DataStore.users.remove(staff)
        # Clean up related subjects, attendances, etc. (optional cascade)
        DataStore.subjects = [s for s in DataStore.subjects if s.staff_id != staff_id]

    # ------ Student management ------
    def add_student(self, name: str, email: str, password: str) -> 'Student':
        if any(u.email == email for u in DataStore.users):
            raise ValueError("Email already registered")
        student = Student(name, email, password)
        DataStore.users.append(student)
        return student

    def update_student(self, student_id: str, name: str = None, email: str = None, password: str = None) -> None:
        student = self._find_user(student_id, 'student')
        if name:
            student.name = name
        if email:
            if any(u.email == email and u.user_id != student_id for u in DataStore.users):
                raise ValueError("Email already in use")
            student.email = email
        if password:
            student.password = password

    def delete_student(self, student_id: str) -> None:
        student = self._find_user(student_id, 'student')
        DataStore.users.remove(student)
        # Remove associated data
        DataStore.attendances = [a for a in DataStore.attendances if a.student_id != student_id]
        DataStore.results = [r for r in DataStore.results if r.student_id != student_id]
        DataStore.leaves = [l for l in DataStore.leaves if l.user_id != student_id]
        DataStore.feedbacks = [f for f in DataStore.feedbacks if f.user_id != student_id]

    # ------ Course management ------
    def add_course(self, name: str) -> 'Course':
        course = Course(name)
        DataStore.courses.append(course)
        return course

    def update_course(self, course_id: str, name: str) -> None:
        course = self._find_course(course_id)
        course.name = name

    def delete_course(self, course_id: str) -> None:
        course = self._find_course(course_id)
        DataStore.courses.remove(course)
        # Cascade delete subjects of this course
        DataStore.subjects = [s for s in DataStore.subjects if s.course_id != course_id]

    # ------ Subject management ------
    def add_subject(self, name: str, course_id: str, staff_id: str) -> 'Subject':
        self._find_course(course_id)  # ensure course exists
        self._find_user(staff_id, 'staff')  # ensure staff exists
        subject = Subject(name, course_id, staff_id)
        DataStore.subjects.append(subject)
        return subject

    def update_subject(self, subject_id: str, name: str = None, course_id: str = None, staff_id: str = None) -> None:
        subject = self._find_subject(subject_id)
        if name:
            subject.name = name
        if course_id:
            self._find_course(course_id)
            subject.course_id = course_id
        if staff_id:
            self._find_user(staff_id, 'staff')
            subject.staff_id = staff_id

    def delete_subject(self, subject_id: str) -> None:
        subject = self._find_subject(subject_id)
        DataStore.subjects.remove(subject)
        # Clean related attendances and results
        DataStore.attendances = [a for a in DataStore.attendances if a.subject_id != subject_id]
        DataStore.results = [r for r in DataStore.results if r.subject_id != subject_id]

    # ------ Session management ------
    def add_session(self, name: str, start_date: date, end_date: date) -> 'Session':
        if end_date <= start_date:
            raise ValueError("End date must be after start date")
        session = Session(name, start_date, end_date)
        DataStore.sessions.append(session)
        return session

    def update_session(self, session_id: str, name: str = None, start_date: date = None, end_date: date = None) -> None:
        session = self._find_session(session_id)
        if name:
            session.name = name
        if start_date:
            session.start_date = start_date
        if end_date:
            session.end_date = end_date
        if session.end_date <= session.start_date:
            raise ValueError("End date must be after start date")

    def delete_session(self, session_id: str) -> None:
        session = self._find_session(session_id)
        DataStore.sessions.remove(session)
        DataStore.attendances = [a for a in DataStore.attendances if a.session_id != session_id]

    # ------ View Student Attendance ------
    def view_student_attendance(self, student_id: str) -> List['Attendance']:
        self._find_user(student_id, 'student')
        return [a for a in DataStore.attendances if a.student_id == student_id]

    # ------ Feedback review ------
    def review_feedback(self, feedback_id: str, reply: str) -> None:
        fb = self._find_feedback(feedback_id)
        fb.reply = reply
        fb.reviewed_at = datetime.now()

    # ------ Leave review ------
    def review_leave(self, leave_id: str, status: Literal['approved', 'rejected']) -> None:
        le = self._find_leave(leave_id)
        if le.status != 'pending':
            raise ValueError("Leave already reviewed")
        le.status = status
        le.reviewed_at = datetime.now()

    # ------ Helper finders ------
    def _find_user(self, user_id: str, user_type: str = None) -> User:
        user = next((u for u in DataStore.users if u.user_id == user_id and (user_type is None or u.user_type == user_type)), None)
        if not user:
            raise ValueError(f"{user_type.capitalize() if user_type else 'User'} not found")
        return user

    def _find_course(self, course_id: str) -> 'Course':
        course = next((c for c in DataStore.courses if c.course_id == course_id), None)
        if not course:
            raise ValueError("Course not found")
        return course

    def _find_subject(self, subject_id: str) -> 'Subject':
        subject = next((s for s in DataStore.subjects if s.subject_id == subject_id), None)
        if not subject:
            raise ValueError("Subject not found")
        return subject

    def _find_session(self, session_id: str) -> 'Session':
        session = next((s for s in DataStore.sessions if s.session_id == session_id), None)
        if not session:
            raise ValueError("Session not found")
        return session

    def _find_feedback(self, feedback_id: str) -> 'Feedback':
        fb = next((f for f in DataStore.feedbacks if f.feedback_id == feedback_id), None)
        if not fb:
            raise ValueError("Feedback not found")
        return fb

    def _find_leave(self, leave_id: str) -> 'Leave':
        le = next((l for l in DataStore.leaves if l.leave_id == leave_id), None)
        if not le:
            raise ValueError("Leave not found")
        return le

# ------------------------------------------------------------
# Staff
# ------------------------------------------------------------
class Staff(User):
    def __init__(self, name: str, email: str, password: str):
        super().__init__(str(uuid.uuid4()), name, email, password, 'staff')

    def get_dashboard_summary(self) -> Dict:
        """Summary charts related to their students, subjects, leave status, etc."""
        my_subjects = self._my_subjects()
        subject_ids = [s.subject_id for s in my_subjects]
        my_students = set()
        # Students who have attendance or results in my subjects
        for a in DataStore.attendances:
            if a.subject_id in subject_ids:
                my_students.add(a.student_id)
        for r in DataStore.results:
            if r.subject_id in subject_ids:
                my_students.add(r.student_id)
        pending_leaves = sum(1 for l in DataStore.leaves if l.user_id == self.user_id and l.status == 'pending')
        return {
            "my_subjects": len(my_subjects),
            "my_students": len(my_students),
            "total_attendances_taken": sum(1 for a in DataStore.attendances if a.subject_id in subject_ids),
            "total_results_added": sum(1 for r in DataStore.results if r.subject_id in subject_ids),
            "pending_leaves": pending_leaves,
            "unreplied_feedback": sum(1 for f in DataStore.feedbacks if f.user_id == self.user_id and f.reply is None)
        }

    def take_attendance(self, session_id: str, subject_id: str, date: date, student_statuses: Dict[str, str]) -> List['Attendance']:
        """student_statuses: {student_id: 'present'/'absent'}"""
        self._ensure_my_subject(subject_id)
        session = self._find_session(session_id)
        records = []
        for student_id, status in student_statuses.items():
            student = self._find_student(student_id)
            if status not in ('present', 'absent'):
                raise ValueError(f"Invalid status for {student_id}: {status}")
            # Check duplicate
            if any(a.student_id == student_id and a.subject_id == subject_id and a.session_id == session_id and a.date == date for a in DataStore.attendances):
                raise ValueError(f"Attendance already recorded for {student.name} on {date}")
            att = Attendance(student_id, subject_id, session_id, date, status)
            DataStore.attendances.append(att)
            records.append(att)
        return records

    def update_attendance(self, attendance_id: str, status: str) -> 'Attendance':
        att = self._find_attendance(attendance_id)
        if status not in ('present', 'absent'):
            raise ValueError("Status must be 'present' or 'absent'")
        att.status = status
        return att

    def add_result(self, student_id: str, subject_id: str, exam_name: str, marks: float, out_of: float) -> 'Result':
        self._ensure_my_subject(subject_id)
        self._find_student(student_id)
        if marks > out_of:
            raise ValueError("Marks cannot exceed out_of")
        result = Result(student_id, subject_id, exam_name, marks, out_of)
        DataStore.results.append(result)
        return result

    def update_result(self, result_id: str, marks: float) -> 'Result':
        result = self._find_result(result_id)
        self._ensure_my_subject(result.subject_id)
        if marks > result.out_of:
            raise ValueError("Marks cannot exceed out_of")
        result.marks = marks
        return result

    def apply_leave(self, start_date: date, end_date: date, reason: str) -> 'Leave':
        if end_date < start_date:
            raise ValueError("End date cannot be before start date")
        leave = Leave(self.user_id, 'staff', start_date, end_date, reason)
        DataStore.leaves.append(leave)
        return leave

    def send_feedback(self, message: str) -> 'Feedback':
        fb = Feedback(self.user_id, 'staff', message)
        DataStore.feedbacks.append(fb)
        return fb

    # ------ Private helpers ------
    def _my_subjects(self) -> List['Subject']:
        return [s for s in DataStore.subjects if s.staff_id == self.user_id]

    def _ensure_my_subject(self, subject_id: str) -> 'Subject':
        subject = next((s for s in DataStore.subjects if s.subject_id == subject_id and s.staff_id == self.user_id), None)
        if not subject:
            raise ValueError("You do not teach this subject")
        return subject

    def _find_student(self, student_id: str) -> 'Student':
        student = next((u for u in DataStore.users if u.user_id == student_id and u.user_type == 'student'), None)
        if not student:
            raise ValueError("Student not found")
        return student

    def _find_attendance(self, attendance_id: str) -> 'Attendance':
        att = next((a for a in DataStore.attendances if a.attendance_id == attendance_id), None)
        if not att:
            raise ValueError("Attendance record not found")
        # Staff can only view his own subject's attendances
        if att.subject_id not in [s.subject_id for s in self._my_subjects()]:
            raise ValueError("Access denied")
        return att

    def _find_result(self, result_id: str) -> 'Result':
        res = next((r for r in DataStore.results if r.result_id == result_id), None)
        if not res:
            raise ValueError("Result not found")
        if res.subject_id not in [s.subject_id for s in self._my_subjects()]:
            raise ValueError("Access denied")
        return res

    def _find_session(self, session_id: str) -> 'Session':
        session = next((s for s in DataStore.sessions if s.session_id == session_id), None)
        if not session:
            raise ValueError("Session not found")
        return session

# ------------------------------------------------------------
# Student
# ------------------------------------------------------------
class Student(User):
    def __init__(self, name: str, email: str, password: str):
        super().__init__(str(uuid.uuid4()), name, email, password, 'student')

    def get_dashboard_summary(self) -> Dict:
        """Summary charts related to their attendance, subjects, leave, etc."""
        my_attendance = self.view_attendance()
        my_results = self.view_result()
        pending_leaves = sum(1 for l in DataStore.leaves if l.user_id == self.user_id and l.status == 'pending')
        return {
            "total_attendance_records": len(my_attendance),
            "present_count": sum(1 for a in my_attendance if a.status == 'present'),
            "absent_count": sum(1 for a in my_attendance if a.status == 'absent'),
            "total_results": len(my_results),
            "pending_leaves": pending_leaves,
            "unreplied_feedback": sum(1 for f in DataStore.feedbacks if f.user_id == self.user_id and f.reply is None)
        }

    def view_attendance(self) -> List['Attendance']:
        return [a for a in DataStore.attendances if a.student_id == self.user_id]

    def view_result(self) -> List['Result']:
        return [r for r in DataStore.results if r.student_id == self.user_id]

    def apply_leave(self, start_date: date, end_date: date, reason: str) -> 'Leave':
        if end_date < start_date:
            raise ValueError("End date cannot be before start date")
        leave = Leave(self.user_id, 'student', start_date, end_date, reason)
        DataStore.leaves.append(leave)
        return leave

    def send_feedback(self, message: str) -> 'Feedback':
        fb = Feedback(self.user_id, 'student', message)
        DataStore.feedbacks.append(fb)
        return fb

# ------------------------------------------------------------
# Entity models
# ------------------------------------------------------------
class Course:
    def __init__(self, name: str):
        self.course_id = str(uuid.uuid4())
        self.name = name

    def __repr__(self):
        return f"Course({self.course_id}: {self.name})"

class Subject:
    def __init__(self, name: str, course_id: str, staff_id: str):
        self.subject_id = str(uuid.uuid4())
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id

    def __repr__(self):
        return f"Subject({self.subject_id}: {self.name}, course={self.course_id}, staff={self.staff_id})"

class Session:
    def __init__(self, name: str, start_date: date, end_date: date):
        self.session_id = str(uuid.uuid4())
        self.name = name
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return f"Session({self.session_id}: {self.name} [{self.start_date} - {self.end_date}])"

class Attendance:
    def __init__(self, student_id: str, subject_id: str, session_id: str, date: date, status: str):
        self.attendance_id = str(uuid.uuid4())
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.date = date
        self.status = status  # 'present' or 'absent'

    def __repr__(self):
        return f"Attendance({self.attendance_id}: student={self.student_id}, subj={self.subject_id}, {self.date} -> {self.status})"

class Result:
    def __init__(self, student_id: str, subject_id: str, exam_name: str, marks: float, out_of: float):
        self.result_id = str(uuid.uuid4())
        self.student_id = student_id
        self.subject_id = subject_id
        self.exam_name = exam_name
        self.marks = marks
        self.out_of = out_of

    def __repr__(self):
        return f"Result({self.result_id}: student={self.student_id}, subj={self.subject_id}, exam={self.exam_name}, {self.marks}/{self.out_of})"

class Leave:
    def __init__(self, user_id: str, leave_type: str, start_date: date, end_date: date, reason: str):
        self.leave_id = str(uuid.uuid4())
        self.user_id = user_id
        self.leave_type = leave_type  # 'staff' or 'student'
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status: Literal['pending', 'approved', 'rejected'] = 'pending'
        self.created_at = datetime.now()
        self.reviewed_at: Optional[datetime] = None

    def __repr__(self):
        return f"Leave({self.leave_id}: {self.leave_type} {self.user_id}, {self.start_date}-{self.end_date}, status={self.status})"

class Feedback:
    def __init__(self, user_id: str, feedback_type: str, message: str):
        self.feedback_id = str(uuid.uuid4())
        self.user_id = user_id
        self.feedback_type = feedback_type  # 'staff' or 'student'
        self.message = message
        self.reply: Optional[str] = None
        self.created_at = datetime.now()
        self.reviewed_at: Optional[datetime] = None

    def __repr__(self):
        return f"Feedback({self.feedback_id}: {self.feedback_type} {self.user_id}, msg={self.message[:30]}... reply={self.reply})"

# ------------------------------------------------------------
# Demonstration (to keep the implementation runnable)
# ------------------------------------------------------------
if __name__ == "__main__":
    # Setup initial data
    admin = Admin("Admin User", "admin@school.com", "admin123")
    DataStore.users.append(admin)

    # Admin adds staff and student
    staff1 = admin.add_staff("John Teacher", "john@school.com", "pass123")
    student1 = admin.add_student("Alice Student", "alice@school.com", "pass123")

    # Create a course, subject, session
    course1 = admin.add_course("Computer Science")
    session1 = admin.add_session("2024 Fall", date(2024, 9, 1), date(2024, 12, 20))
    subject1 = admin.add_subject("Python Programming", course1.course_id, staff1.user_id)

    # Staff takes attendance
    staff1.take_attendance(session1.session_id, subject1.subject_id, date(2024, 10, 1), {student1.user_id: "present"})
    # Staff adds result
    staff1.add_result(student1.user_id, subject1.subject_id, "Midterm", 85, 100)

    # Student applies leave, sends feedback
    leave1 = student1.apply_leave(date(2024, 11, 10), date(2024, 11, 12), "Family event")
    feedback1 = student1.send_feedback("Need more practical sessions")

    # Admin reviews leave and feedback
    admin.review_leave(leave1.leave_id, "approved")
    admin.review_feedback(feedback1.feedback_id, "We will consider that. Thank you.")

    # Print some summaries
    print("Admin Dashboard:", admin.get_dashboard_summary())
    print("Staff Dashboard:", staff1.get_dashboard_summary())
    print("Student Dashboard:", student1.get_dashboard_summary())
    print("Student Attendance:", student1.view_attendance())
    print("Student Results:", student1.view_result())
    print("Leaves:", DataStore.leaves)
    print("Feedbacks:", DataStore.feedbacks)