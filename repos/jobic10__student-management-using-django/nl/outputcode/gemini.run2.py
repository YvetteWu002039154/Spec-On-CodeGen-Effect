from enum import Enum
from typing import List, Dict, Optional
from datetime import date

class LeaveStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class AttendanceStatus(Enum):
    PRESENT = "Present"
    ABSENT = "Absent"

class Course:
    def __init__(self, course_id: int, name: str):
        self.course_id = course_id
        self.name = name

class Session:
    def __init__(self, session_id: int, start_year: str, end_year: str):
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year

class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id

class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

class Admin(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email)

class Staff(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email)

class Student(User):
    def __init__(self, user_id: int, name: str, email: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email)
        self.course_id = course_id
        self.session_id = session_id

class Attendance:
    def __init__(self, attendance_id: int, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: AttendanceStatus):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.attendance_date = attendance_date
        self.student_id = student_id
        self.status = status

class Result:
    def __init__(self, result_id: int, student_id: int, subject_id: int, marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks

class Leave:
    def __init__(self, leave_id: int, user_id: int, leave_date: date, message: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.leave_date = leave_date
        self.message = message
        self.status = LeaveStatus.PENDING

class Feedback:
    def __init__(self, feedback_id: int, user_id: int, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.reply: Optional[str] = None

class StudentManagementSystem:
    def __init__(self):
        self.admins: Dict[int, Admin] = {}
        self.staffs: Dict[int, Staff] = {}
        self.students: Dict[int, Student] = {}
        self.courses: Dict[int, Course] = {}
        self.subjects: Dict[int, Subject] = {}
        self.sessions: Dict[int, Session] = {}
        self.attendances: Dict[int, Attendance] = {}
        self.results: Dict[int, Result] = {}
        self.leaves: Dict[int, Leave] = {}
        self.feedbacks: Dict[int, Feedback] = {}

        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_leave_id = 1
        self._next_feedback_id = 1

    def get_admin_summary(self) -> Dict[str, int]:
        return {
            "total_students": len(self.students),
            "total_staff": len(self.staffs),
            "total_courses": len(self.courses),
            "total_subjects": len(self.subjects),
            "total_leaves": len(self.leaves),
            "total_feedbacks": len(self.feedbacks)
        }

    def add_staff(self, staff: Staff) -> None:
        self.staffs[staff.user_id] = staff

    def update_staff(self, user_id: int, name: str, email: str) -> None:
        if user_id in self.staffs:
            self.staffs[user_id].name = name
            self.staffs[user_id].email = email

    def delete_staff(self, user_id: int) -> None:
        if user_id in self.staffs:
            del self.staffs[user_id]

    def add_student(self, student: Student) -> None:
        self.students[student.user_id] = student

    def update_student(self, user_id: int, name: str, email: str, course_id: int, session_id: int) -> None:
        if user_id in self.students:
            self.students[user_id].name = name
            self.students[user_id].email = email
            self.students[user_id].course_id = course_id
            self.students[user_id].session_id = session_id

    def delete_student(self, user_id: int) -> None:
        if user_id in self.students:
            del self.students[user_id]

    def add_course(self, course: Course) -> None:
        self.courses[course.course_id] = course

    def update_course(self, course_id: int, name: str) -> None:
        if course_id in self.courses:
            self.courses[course_id].name = name

    def delete_course(self, course_id: int) -> None:
        if course_id in self.courses:
            del self.courses[course_id]

    def add_subject(self, subject: Subject) -> None:
        self.subjects[subject.subject_id] = subject

    def update_subject(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if subject_id in self.subjects:
            self.subjects[subject_id].name = name
            self.subjects[subject_id].course_id = course_id
            self.subjects[subject_id].staff_id = staff_id

    def delete_subject(self, subject_id: int) -> None:
        if subject_id in self.subjects:
            del self.subjects[subject_id]

    def add_session(self, session: Session) -> None:
        self.sessions[session.session_id] = session

    def update_session(self, session_id: int, start_year: str, end_year: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].start_year = start_year
            self.sessions[session_id].end_year = end_year

    def delete_session(self, session_id: int) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]

    def admin_view_student_attendance(self, student_id: int) -> List[Attendance]:
        return [a for a in self.attendances.values() if a.student_id == student_id]

    def review_and_reply_feedback(self, feedback_id: int, reply_message: str) -> None:
        if feedback_id in self.feedbacks:
            self.feedbacks[feedback_id].reply = reply_message

    def review_leave(self, leave_id: int, status: LeaveStatus) -> None:
        if leave_id in self.leaves:
            self.leaves[leave_id].status = status

    def get_staff_summary(self, staff_id: int) -> Dict[str, int]:
        staff_subjects = [s for s in self.subjects.values() if s.staff_id == staff_id]
        staff_course_ids = {s.course_id for s in staff_subjects}
        staff_students = [s for s in self.students.values() if s.course_id in staff_course_ids]
        staff_leaves = [l for l in self.leaves.values() if l.user_id == staff_id]
        
        return {
            "total_students_under_staff": len(staff_students),
            "total_subjects_taught": len(staff_subjects),
            "total_leaves_applied": len(staff_leaves)
        }

    def take_attendance(self, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: AttendanceStatus) -> None:
        attendance = Attendance(self._next_attendance_id, subject_id, session_id, attendance_date, student_id, status)
        self.attendances[self._next_attendance_id] = attendance
        self._next_attendance_id += 1

    def update_attendance(self, attendance_id: int, status: AttendanceStatus) -> None:
        if attendance_id in self.attendances:
            self.attendances[attendance_id].status = status

    def add_result(self, student_id: int, subject_id: int, marks: float) -> None:
        result = Result(self._next_result_id, student_id, subject_id, marks)
        self.results[self._next_result_id] = result
        self._next_result_id += 1

    def update_result(self, result_id: int, marks: float) -> None:
        if result_id in self.results:
            self.results[result_id].marks = marks

    def get_student_summary(self, student_id: int) -> Dict[str, int]:
        student = self.students.get(student_id)
        if not student:
            return {}
            
        student_subjects = [s for s in self.subjects.values() if s.course_id == student.course_id]
        student_attendance = [a for a in self.attendances.values() if a.student_id == student_id]
        student_leaves = [l for l in self.leaves.values() if l.user_id == student_id]
        
        return {
            "total_subjects": len(student_subjects),
            "total_attendance_records": len(student_attendance),
            "total_leaves_applied": len(student_leaves)
        }

    def student_view_attendance(self, student_id: int) -> List[Attendance]:
        return [a for a in self.attendances.values() if a.student_id == student_id]

    def student_view_result(self, student_id: int) -> List[Result]:
        return [r for r in self.results.values() if r.student_id == student_id]

    def apply_for_leave(self, user_id: int, leave_date: date, message: str) -> None:
        leave = Leave(self._next_leave_id, user_id, leave_date, message)
        self.leaves[self._next_leave_id] = leave
        self._next_leave_id += 1

    def send_feedback(self, user_id: int, message: str) -> None:
        feedback = Feedback(self._next_feedback_id, user_id, message)
        self.feedbacks[self._next_feedback_id] = feedback
        self._next_feedback_id += 1