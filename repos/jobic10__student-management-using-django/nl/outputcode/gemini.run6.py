from typing import List, Dict, Optional
from datetime import date
from enum import Enum

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

class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id

class Session:
    def __init__(self, session_id: int, start_year: str, end_year: str):
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year

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

        self._next_user_id = 1
        self._next_course_id = 1
        self._next_subject_id = 1
        self._next_session_id = 1
        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_leave_id = 1
        self._next_feedback_id = 1

    def admin_view_summary(self) -> Dict[str, int]:
        return {
            "total_students": len(self.students),
            "total_staff": len(self.staffs),
            "total_courses": len(self.courses),
            "total_subjects": len(self.subjects),
            "total_sessions": len(self.sessions),
            "total_leaves": len(self.leaves),
            "total_feedbacks": len(self.feedbacks)
        }

    def admin_add_staff(self, name: str, email: str) -> Staff:
        staff_id = self._next_user_id
        self._next_user_id += 1
        staff = Staff(staff_id, name, email)
        self.staffs[staff_id] = staff
        return staff

    def admin_update_staff(self, staff_id: int, name: str, email: str) -> Staff:
        if staff_id not in self.staffs:
            raise ValueError("Staff not found")
        self.staffs[staff_id].name = name
        self.staffs[staff_id].email = email
        return self.staffs[staff_id]

    def admin_delete_staff(self, staff_id: int) -> None:
        if staff_id not in self.staffs:
            raise ValueError("Staff not found")
        del self.staffs[staff_id]

    def admin_add_student(self, name: str, email: str, course_id: int, session_id: int) -> Student:
        if course_id not in self.courses:
            raise ValueError("Course not found")
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        student_id = self._next_user_id
        self._next_user_id += 1
        student = Student(student_id, name, email, course_id, session_id)
        self.students[student_id] = student
        return student

    def admin_update_student(self, student_id: int, name: str, email: str, course_id: int, session_id: int) -> Student:
        if student_id not in self.students:
            raise ValueError("Student not found")
        if course_id not in self.courses:
            raise ValueError("Course not found")
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        student = self.students[student_id]
        student.name = name
        student.email = email
        student.course_id = course_id
        student.session_id = session_id
        return student

    def admin_delete_student(self, student_id: int) -> None:
        if student_id not in self.students:
            raise ValueError("Student not found")
        del self.students[student_id]

    def admin_add_course(self, name: str) -> Course:
        course_id = self._next_course_id
        self._next_course_id += 1
        course = Course(course_id, name)
        self.courses[course_id] = course
        return course

    def admin_update_course(self, course_id: int, name: str) -> Course:
        if course_id not in self.courses:
            raise ValueError("Course not found")
        self.courses[course_id].name = name
        return self.courses[course_id]

    def admin_delete_course(self, course_id: int) -> None:
        if course_id not in self.courses:
            raise ValueError("Course not found")
        del self.courses[course_id]

    def admin_add_subject(self, name: str, course_id: int, staff_id: int) -> Subject:
        if course_id not in self.courses:
            raise ValueError("Course not found")
        if staff_id not in self.staffs:
            raise ValueError("Staff not found")
        subject_id = self._next_subject_id
        self._next_subject_id += 1
        subject = Subject(subject_id, name, course_id, staff_id)
        self.subjects[subject_id] = subject
        return subject

    def admin_update_subject(self, subject_id: int, name: str, course_id: int, staff_id: int) -> Subject:
        if subject_id not in self.subjects:
            raise ValueError("Subject not found")
        if course_id not in self.courses:
            raise ValueError("Course not found")
        if staff_id not in self.staffs:
            raise ValueError("Staff not found")
        subject = self.subjects[subject_id]
        subject.name = name
        subject.course_id = course_id
        subject.staff_id = staff_id
        return subject

    def admin_delete_subject(self, subject_id: int) -> None:
        if subject_id not in self.subjects:
            raise ValueError("Subject not found")
        del self.subjects[subject_id]

    def admin_add_session(self, start_year: str, end_year: str) -> Session:
        session_id = self._next_session_id
        self._next_session_id += 1
        session = Session(session_id, start_year, end_year)
        self.sessions[session_id] = session
        return session

    def admin_update_session(self, session_id: int, start_year: str, end_year: str) -> Session:
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        session = self.sessions[session_id]
        session.start_year = start_year
        session.end_year = end_year
        return session

    def admin_delete_session(self, session_id: int) -> None:
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        del self.sessions[session_id]

    def admin_view_student_attendance(self, student_id: int) -> List[Attendance]:
        if student_id not in self.students:
            raise ValueError("Student not found")
        return [att for att in self.attendances.values() if att.student_id == student_id]

    def admin_review_feedback(self) -> List[Feedback]:
        return list(self.feedbacks.values())

    def admin_reply_feedback(self, feedback_id: int, reply_message: str) -> Feedback:
        if feedback_id not in self.feedbacks:
            raise ValueError("Feedback not found")
        self.feedbacks[feedback_id].reply = reply_message
        return self.feedbacks[feedback_id]

    def admin_review_leave(self) -> List[Leave]:
        return list(self.leaves.values())

    def admin_approve_reject_leave(self, leave_id: int, status: LeaveStatus) -> Leave:
        if leave_id not in self.leaves:
            raise ValueError("Leave not found")
        self.leaves[leave_id].status = status
        return self.leaves[leave_id]

    def staff_view_summary(self, staff_id: int) -> Dict[str, int]:
        if staff_id not in self.staffs:
            raise ValueError("Staff not found")
        my_subjects = [sub for sub in self.subjects.values() if sub.staff_id == staff_id]
        my_course_ids = {sub.course_id for sub in my_subjects}
        my_students = [stu for stu in self.students.values() if stu.course_id in my_course_ids]
        my_leaves = [lv for lv in self.leaves.values() if lv.user_id == staff_id]

        return {
            "total_subjects": len(my_subjects),
            "total_students": len(my_students),
            "total_leaves": len(my_leaves)
        }

    def staff_take_attendance(self, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: AttendanceStatus) -> Attendance:
        if subject_id not in self.subjects:
            raise ValueError("Subject not found")
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        if student_id not in self.students:
            raise ValueError("Student not found")

        att_id = self._next_attendance_id
        self._next_attendance_id += 1
        attendance = Attendance(att_id, subject_id, session_id, attendance_date, student_id, status)
        self.attendances[att_id] = attendance
        return attendance

    def staff_update_attendance(self, attendance_id: int, status: AttendanceStatus) -> Attendance:
        if attendance_id not in self.attendances:
            raise ValueError("Attendance not found")
        self.attendances[attendance_id].status = status
        return self.attendances[attendance_id]

    def staff_add_result(self, student_id: int, subject_id: int, marks: float) -> Result:
        if student_id not in self.students:
            raise ValueError("Student not found")
        if subject_id not in self.subjects:
            raise ValueError("Subject not found")

        res_id = self._next_result_id
        self._next_result_id += 1
        result = Result(res_id, student_id, subject_id, marks)
        self.results[res_id] = result
        return result

    def staff_update_result(self, result_id: int, marks: float) -> Result:
        if result_id not in self.results:
            raise ValueError("Result not found")
        self.results[result_id].marks = marks
        return self.results[result_id]

    def staff_apply_leave(self, staff_id: int, leave_date: date, message: str) -> Leave:
        if staff_id not in self.staffs:
            raise ValueError("Staff not found")
        leave_id = self._next_leave_id
        self._next_leave_id += 1
        leave = Leave(leave_id, staff_id, leave_date, message)
        self.leaves[leave_id] = leave
        return leave

    def staff_send_feedback(self, staff_id: int, message: str) -> Feedback:
        if staff_id not in self.staffs:
            raise ValueError("Staff not found")
        fb_id = self._next_feedback_id
        self._next_feedback_id += 1
        feedback = Feedback(fb_id, staff_id, message)
        self.feedbacks[fb_id] = feedback
        return feedback

    def student_view_summary(self, student_id: int) -> Dict[str, int]:
        if student_id not in self.students:
            raise ValueError("Student not found")
        student = self.students[student_id]
        my_subjects = [sub for sub in self.subjects.values() if sub.course_id == student.course_id]
        my_attendance = [att for att in self.attendances.values() if att.student_id == student_id]
        my_leaves = [lv for lv in self.leaves.values() if lv.user_id == student_id]

        return {
            "total_subjects": len(my_subjects),
            "total_attendance_records": len(my_attendance),
            "total_leaves": len(my_leaves)
        }

    def student_view_attendance(self, student_id: int) -> List[Attendance]:
        if student_id not in self.students:
            raise ValueError("Student not found")
        return [att for att in self.attendances.values() if att.student_id == student_id]

    def student_view_result(self, student_id: int) -> List[Result]:
        if student_id not in self.students:
            raise ValueError("Student not found")
        return [res for res in self.results.values() if res.student_id == student_id]

    def student_apply_leave(self, student_id: int, leave_date: date, message: str) -> Leave:
        if student_id not in self.students:
            raise ValueError("Student not found")
        leave_id = self._next_leave_id
        self._next_leave_id += 1
        leave = Leave(leave_id, student_id, leave_date, message)
        self.leaves[leave_id] = leave
        return leave

    def student_send_feedback(self, student_id: int, message: str) -> Feedback:
        if student_id not in self.students:
            raise ValueError("Student not found")
        fb_id = self._next_feedback_id
        self._next_feedback_id += 1
        feedback = Feedback(fb_id, student_id, message)
        self.feedbacks[fb_id] = feedback
        return feedback