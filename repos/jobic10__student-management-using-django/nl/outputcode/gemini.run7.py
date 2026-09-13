from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Any
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

class User:
    def __init__(self, user_id: int, name: str, email: str, password: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password

class Admin(User):
    def view_overall_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        return {
            "total_students": len(system.students),
            "total_staff": len(system.staffs),
            "total_courses": len(system.courses),
            "total_subjects": len(system.subjects),
            "total_leaves": len(system.leaves)
        }

    def add_staff(self, system: StudentManagementSystem, name: str, email: str, password: str) -> Staff:
        return system.add_staff(name, email, password)

    def update_staff(self, system: StudentManagementSystem, staff_id: int, name: str, email: str, password: str) -> Optional[Staff]:
        return system.update_staff(staff_id, name, email, password)

    def delete_staff(self, system: StudentManagementSystem, staff_id: int) -> bool:
        return system.delete_staff(staff_id)

    def add_student(self, system: StudentManagementSystem, name: str, email: str, password: str, course_id: int, session_id: int) -> Student:
        return system.add_student(name, email, password, course_id, session_id)

    def update_student(self, system: StudentManagementSystem, student_id: int, name: str, email: str, password: str, course_id: int, session_id: int) -> Optional[Student]:
        return system.update_student(student_id, name, email, password, course_id, session_id)

    def delete_student(self, system: StudentManagementSystem, student_id: int) -> bool:
        return system.delete_student(student_id)

    def add_course(self, system: StudentManagementSystem, name: str) -> Course:
        return system.add_course(name)

    def update_course(self, system: StudentManagementSystem, course_id: int, name: str) -> Optional[Course]:
        return system.update_course(course_id, name)

    def delete_course(self, system: StudentManagementSystem, course_id: int) -> bool:
        return system.delete_course(course_id)

    def add_subject(self, system: StudentManagementSystem, name: str, course_id: int, staff_id: int) -> Subject:
        return system.add_subject(name, course_id, staff_id)

    def update_subject(self, system: StudentManagementSystem, subject_id: int, name: str, course_id: int, staff_id: int) -> Optional[Subject]:
        return system.update_subject(subject_id, name, course_id, staff_id)

    def delete_subject(self, system: StudentManagementSystem, subject_id: int) -> bool:
        return system.delete_subject(subject_id)

    def add_session(self, system: StudentManagementSystem, start_year: str, end_year: str) -> Session:
        return system.add_session(start_year, end_year)

    def update_session(self, system: StudentManagementSystem, session_id: int, start_year: str, end_year: str) -> Optional[Session]:
        return system.update_session(session_id, start_year, end_year)

    def delete_session(self, system: StudentManagementSystem, session_id: int) -> bool:
        return system.delete_session(session_id)

    def view_student_attendance(self, system: StudentManagementSystem, student_id: int) -> List[Attendance]:
        return [att for att in system.attendances.values() if att.student_id == student_id]

    def review_feedback(self, system: StudentManagementSystem) -> List[Feedback]:
        return list(system.feedbacks.values())

    def reply_feedback(self, system: StudentManagementSystem, feedback_id: int, reply: str) -> Optional[Feedback]:
        feedback = system.feedbacks.get(feedback_id)
        if feedback:
            feedback.reply = reply
        return feedback

    def review_leave(self, system: StudentManagementSystem) -> List[Leave]:
        return list(system.leaves.values())

    def approve_leave(self, system: StudentManagementSystem, leave_id: int) -> Optional[Leave]:
        leave = system.leaves.get(leave_id)
        if leave:
            leave.status = LeaveStatus.APPROVED
        return leave

    def reject_leave(self, system: StudentManagementSystem, leave_id: int) -> Optional[Leave]:
        leave = system.leaves.get(leave_id)
        if leave:
            leave.status = LeaveStatus.REJECTED
        return leave

class Staff(User):
    def view_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        my_subjects = [sub for sub in system.subjects.values() if sub.staff_id == self.user_id]
        my_course_ids = {sub.course_id for sub in my_subjects}
        my_students = [stu for stu in system.students.values() if stu.course_id in my_course_ids]
        my_leaves = [lv for lv in system.leaves.values() if lv.user_id == self.user_id]
        
        return {
            "total_my_students": len(my_students),
            "total_my_subjects": len(my_subjects),
            "my_leaves_status": {lv.leave_id: lv.status.value for lv in my_leaves}
        }

    def take_attendance(self, system: StudentManagementSystem, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: AttendanceStatus) -> Attendance:
        return system.add_attendance(subject_id, session_id, attendance_date, student_id, status)

    def update_attendance(self, system: StudentManagementSystem, attendance_id: int, status: AttendanceStatus) -> Optional[Attendance]:
        att = system.attendances.get(attendance_id)
        if att:
            att.status = status
        return att

    def add_result(self, system: StudentManagementSystem, student_id: int, subject_id: int, marks: float) -> Result:
        return system.add_result(student_id, subject_id, marks)

    def update_result(self, system: StudentManagementSystem, result_id: int, marks: float) -> Optional[Result]:
        res = system.results.get(result_id)
        if res:
            res.marks = marks
        return res

    def apply_leave(self, system: StudentManagementSystem, leave_date: date, message: str) -> Leave:
        return system.add_leave(self.user_id, leave_date, message)

    def send_feedback(self, system: StudentManagementSystem, message: str) -> Feedback:
        return system.add_feedback(self.user_id, message)

class Student(User):
    def __init__(self, user_id: int, name: str, email: str, password: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email, password)
        self.course_id = course_id
        self.session_id = session_id

    def view_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        my_attendances = [att for att in system.attendances.values() if att.student_id == self.user_id]
        my_subjects = [sub for sub in system.subjects.values() if sub.course_id == self.course_id]
        my_leaves = [lv for lv in system.leaves.values() if lv.user_id == self.user_id]
        
        return {
            "total_attendance_records": len(my_attendances),
            "total_subjects": len(my_subjects),
            "my_leaves_status": {lv.leave_id: lv.status.value for lv in my_leaves}
        }

    def view_attendance(self, system: StudentManagementSystem) -> List[Attendance]:
        return [att for att in system.attendances.values() if att.student_id == self.user_id]

    def view_result(self, system: StudentManagementSystem) -> List[Result]:
        return [res for res in system.results.values() if res.student_id == self.user_id]

    def apply_leave(self, system: StudentManagementSystem, leave_date: date, message: str) -> Leave:
        return system.add_leave(self.user_id, leave_date, message)

    def send_feedback(self, system: StudentManagementSystem, message: str) -> Feedback:
        return system.add_feedback(self.user_id, message)

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
        
        self._user_id_counter = 1
        self._course_id_counter = 1
        self._subject_id_counter = 1
        self._session_id_counter = 1
        self._attendance_id_counter = 1
        self._result_id_counter = 1
        self._leave_id_counter = 1
        self._feedback_id_counter = 1

    def add_admin(self, name: str, email: str, password: str) -> Admin:
        admin = Admin(self._user_id_counter, name, email, password)
        self.admins[self._user_id_counter] = admin
        self._user_id_counter += 1
        return admin

    def add_staff(self, name: str, email: str, password: str) -> Staff:
        staff = Staff(self._user_id_counter, name, email, password)
        self.staffs[self._user_id_counter] = staff
        self._user_id_counter += 1
        return staff

    def update_staff(self, staff_id: int, name: str, email: str, password: str) -> Optional[Staff]:
        if staff_id in self.staffs:
            staff = self.staffs[staff_id]
            staff.name = name
            staff.email = email
            staff.password = password
            return staff
        return None

    def delete_staff(self, staff_id: int) -> bool:
        if staff_id in self.staffs:
            del self.staffs[staff_id]
            return True
        return False

    def add_student(self, name: str, email: str, password: str, course_id: int, session_id: int) -> Student:
        student = Student(self._user_id_counter, name, email, password, course_id, session_id)
        self.students[self._user_id_counter] = student
        self._user_id_counter += 1
        return student

    def update_student(self, student_id: int, name: str, email: str, password: str, course_id: int, session_id: int) -> Optional[Student]:
        if student_id in self.students:
            student = self.students[student_id]
            student.name = name
            student.email = email
            student.password = password
            student.course_id = course_id
            student.session_id = session_id
            return student
        return None

    def delete_student(self, student_id: int) -> bool:
        if student_id in self.students:
            del self.students[student_id]
            return True
        return False

    def add_course(self, name: str) -> Course:
        course = Course(self._course_id_counter, name)
        self.courses[self._course_id_counter] = course
        self._course_id_counter += 1
        return course

    def update_course(self, course_id: int, name: str) -> Optional[Course]:
        if course_id in self.courses:
            course = self.courses[course_id]
            course.name = name
            return course
        return None

    def delete_course(self, course_id: int) -> bool:
        if course_id in self.courses:
            del self.courses[course_id]
            return True
        return False

    def add_subject(self, name: str, course_id: int, staff_id: int) -> Subject:
        subject = Subject(self._subject_id_counter, name, course_id, staff_id)
        self.subjects[self._subject_id_counter] = subject
        self._subject_id_counter += 1
        return subject

    def update_subject(self, subject_id: int, name: str, course_id: int, staff_id: int) -> Optional[Subject]:
        if subject_id in self.subjects:
            subject = self.subjects[subject_id]
            subject.name = name
            subject.course_id = course_id
            subject.staff_id = staff_id
            return subject
        return None

    def delete_subject(self, subject_id: int) -> bool:
        if subject_id in self.subjects:
            del self.subjects[subject_id]
            return True
        return False

    def add_session(self, start_year: str, end_year: str) -> Session:
        session = Session(self._session_id_counter, start_year, end_year)
        self.sessions[self._session_id_counter] = session
        self._session_id_counter += 1
        return session

    def update_session(self, session_id: int, start_year: str, end_year: str) -> Optional[Session]:
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.start_year = start_year
            session.end_year = end_year
            return session
        return None

    def delete_session(self, session_id: int) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def add_attendance(self, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: AttendanceStatus) -> Attendance:
        attendance = Attendance(self._attendance_id_counter, subject_id, session_id, attendance_date, student_id, status)
        self.attendances[self._attendance_id_counter] = attendance
        self._attendance_id_counter += 1
        return attendance

    def add_result(self, student_id: int, subject_id: int, marks: float) -> Result:
        result = Result(self._result_id_counter, student_id, subject_id, marks)
        self.results[self._result_id_counter] = result
        self._result_id_counter += 1
        return result

    def add_leave(self, user_id: int, leave_date: date, message: str) -> Leave:
        leave = Leave(self._leave_id_counter, user_id, leave_date, message)
        self.leaves[self._leave_id_counter] = leave
        self._leave_id_counter += 1
        return leave

    def add_feedback(self, user_id: int, message: str) -> Feedback:
        feedback = Feedback(self._feedback_id_counter, user_id, message)
        self.feedbacks[self._feedback_id_counter] = feedback
        self._feedback_id_counter += 1
        return feedback