from typing import List, Dict, Optional, Any
from datetime import date

class Course:
    def __init__(self, course_id: str, name: str):
        self.course_id = course_id
        self.name = name

class Subject:
    def __init__(self, subject_id: str, name: str, course_id: str, staff_id: str):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id

class Session:
    def __init__(self, session_id: str, start_year: int, end_year: int):
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year

class Attendance:
    def __init__(self, attendance_id: str, student_id: str, subject_id: str, attendance_date: date, status: str):
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.date = attendance_date
        self.status = status

class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str, marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks

class Leave:
    def __init__(self, leave_id: str, user_id: str, leave_date: date, reason: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.leave_date = leave_date
        self.reason = reason
        self.status = "Pending"

class Feedback:
    def __init__(self, feedback_id: str, user_id: str, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.reply: Optional[str] = None

class StudentManagementSystem:
    def __init__(self):
        self.admins: Dict[str, 'Admin'] = {}
        self.staffs: Dict[str, 'Staff'] = {}
        self.students: Dict[str, 'Student'] = {}
        self.courses: Dict[str, Course] = {}
        self.subjects: Dict[str, Subject] = {}
        self.sessions: Dict[str, Session] = {}
        self.attendances: Dict[str, Attendance] = {}
        self.results: Dict[str, Result] = {}
        self.leaves: Dict[str, Leave] = {}
        self.feedbacks: Dict[str, Feedback] = {}
        self._id_counter = 1

    def generate_id(self, prefix: str) -> str:
        new_id = f"{prefix}{self._id_counter}"
        self._id_counter += 1
        return new_id

class User:
    def __init__(self, user_id: str, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

class Admin(User):
    def __init__(self, user_id: str, name: str, email: str):
        super().__init__(user_id, name, email)

    def view_overall_summary(self, system: StudentManagementSystem) -> Dict[str, int]:
        return {
            "total_students": len(system.students),
            "total_staff": len(system.staffs),
            "total_courses": len(system.courses),
            "total_subjects": len(system.subjects),
            "total_leaves": len(system.leaves),
            "total_sessions": len(system.sessions)
        }

    def add_staff(self, system: StudentManagementSystem, staff: 'Staff') -> None:
        system.staffs[staff.user_id] = staff

    def update_staff(self, system: StudentManagementSystem, staff_id: str, name: Optional[str] = None, email: Optional[str] = None) -> None:
        if staff_id in system.staffs:
            if name:
                system.staffs[staff_id].name = name
            if email:
                system.staffs[staff_id].email = email

    def delete_staff(self, system: StudentManagementSystem, staff_id: str) -> None:
        if staff_id in system.staffs:
            del system.staffs[staff_id]

    def add_student(self, system: StudentManagementSystem, student: 'Student') -> None:
        system.students[student.user_id] = student

    def update_student(self, system: StudentManagementSystem, student_id: str, name: Optional[str] = None, email: Optional[str] = None) -> None:
        if student_id in system.students:
            if name:
                system.students[student_id].name = name
            if email:
                system.students[student_id].email = email

    def delete_student(self, system: StudentManagementSystem, student_id: str) -> None:
        if student_id in system.students:
            del system.students[student_id]

    def add_course(self, system: StudentManagementSystem, course: Course) -> None:
        system.courses[course.course_id] = course

    def update_course(self, system: StudentManagementSystem, course_id: str, name: str) -> None:
        if course_id in system.courses:
            system.courses[course_id].name = name

    def delete_course(self, system: StudentManagementSystem, course_id: str) -> None:
        if course_id in system.courses:
            del system.courses[course_id]

    def add_subject(self, system: StudentManagementSystem, subject: Subject) -> None:
        system.subjects[subject.subject_id] = subject

    def update_subject(self, system: StudentManagementSystem, subject_id: str, name: Optional[str] = None, course_id: Optional[str] = None, staff_id: Optional[str] = None) -> None:
        if subject_id in system.subjects:
            if name:
                system.subjects[subject_id].name = name
            if course_id:
                system.subjects[subject_id].course_id = course_id
            if staff_id:
                system.subjects[subject_id].staff_id = staff_id

    def delete_subject(self, system: StudentManagementSystem, subject_id: str) -> None:
        if subject_id in system.subjects:
            del system.subjects[subject_id]

    def add_session(self, system: StudentManagementSystem, session: Session) -> None:
        system.sessions[session.session_id] = session

    def update_session(self, system: StudentManagementSystem, session_id: str, start_year: Optional[int] = None, end_year: Optional[int] = None) -> None:
        if session_id in system.sessions:
            if start_year:
                system.sessions[session_id].start_year = start_year
            if end_year:
                system.sessions[session_id].end_year = end_year

    def delete_session(self, system: StudentManagementSystem, session_id: str) -> None:
        if session_id in system.sessions:
            del system.sessions[session_id]

    def view_student_attendance(self, system: StudentManagementSystem, student_id: str) -> List[Attendance]:
        return [att for att in system.attendances.values() if att.student_id == student_id]

    def review_feedback(self, system: StudentManagementSystem) -> List[Feedback]:
        return list(system.feedbacks.values())

    def reply_feedback(self, system: StudentManagementSystem, feedback_id: str, reply: str) -> None:
        if feedback_id in system.feedbacks:
            system.feedbacks[feedback_id].reply = reply

    def review_leave(self, system: StudentManagementSystem) -> List[Leave]:
        return list(system.leaves.values())

    def approve_reject_leave(self, system: StudentManagementSystem, leave_id: str, status: str) -> None:
        if status in ["Approved", "Rejected"] and leave_id in system.leaves:
            system.leaves[leave_id].status = status

class Staff(User):
    def __init__(self, user_id: str, name: str, email: str):
        super().__init__(user_id, name, email)

    def view_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        my_subjects = [sub for sub in system.subjects.values() if sub.staff_id == self.user_id]
        my_leaves = [lv for lv in system.leaves.values() if lv.user_id == self.user_id]
        my_students = set()
        for sub in my_subjects:
            for student in system.students.values():
                if student.course_id == sub.course_id:
                    my_students.add(student.user_id)
                    
        return {
            "total_students_in_subjects": len(my_students),
            "total_subjects": len(my_subjects),
            "total_leaves_applied": len(my_leaves),
            "leave_status": {lv.leave_id: lv.status for lv in my_leaves}
        }

    def take_attendance(self, system: StudentManagementSystem, student_id: str, subject_id: str, att_date: date, status: str) -> None:
        att_id = system.generate_id("ATT")
        attendance = Attendance(att_id, student_id, subject_id, att_date, status)
        system.attendances[att_id] = attendance

    def update_attendance(self, system: StudentManagementSystem, attendance_id: str, status: str) -> None:
        if attendance_id in system.attendances:
            system.attendances[attendance_id].status = status

    def add_result(self, system: StudentManagementSystem, student_id: str, subject_id: str, marks: float) -> None:
        res_id = system.generate_id("RES")
        result = Result(res_id, student_id, subject_id, marks)
        system.results[res_id] = result

    def update_result(self, system: StudentManagementSystem, result_id: str, marks: float) -> None:
        if result_id in system.results:
            system.results[result_id].marks = marks

    def apply_leave(self, system: StudentManagementSystem, leave_date: date, reason: str) -> None:
        leave_id = system.generate_id("LV")
        leave = Leave(leave_id, self.user_id, leave_date, reason)
        system.leaves[leave_id] = leave

    def send_feedback(self, system: StudentManagementSystem, message: str) -> None:
        fb_id = system.generate_id("FB")
        feedback = Feedback(fb_id, self.user_id, message)
        system.feedbacks[fb_id] = feedback

class Student(User):
    def __init__(self, user_id: str, name: str, email: str, course_id: str, session_id: str):
        super().__init__(user_id, name, email)
        self.course_id = course_id
        self.session_id = session_id

    def view_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        my_attendance = self.view_attendance(system)
        my_leaves = [lv for lv in system.leaves.values() if lv.user_id == self.user_id]
        my_subjects = [sub for sub in system.subjects.values() if sub.course_id == self.course_id]
        
        present_count = sum(1 for att in my_attendance if att.status.lower() == "present")
        
        return {
            "total_attendance_records": len(my_attendance),
            "present_count": present_count,
            "total_subjects": len(my_subjects),
            "total_leaves_applied": len(my_leaves),
            "leave_status": {lv.leave_id: lv.status for lv in my_leaves}
        }

    def view_attendance(self, system: StudentManagementSystem) -> List[Attendance]:
        return [att for att in system.attendances.values() if att.student_id == self.user_id]

    def view_result(self, system: StudentManagementSystem) -> List[Result]:
        return [res for res in system.results.values() if res.student_id == self.user_id]

    def apply_leave(self, system: StudentManagementSystem, leave_date: date, reason: str) -> None:
        leave_id = system.generate_id("LV")
        leave = Leave(leave_id, self.user_id, leave_date, reason)
        system.leaves[leave_id] = leave

    def send_feedback(self, system: StudentManagementSystem, message: str) -> None:
        fb_id = system.generate_id("FB")
        feedback = Feedback(fb_id, self.user_id, message)
        system.feedbacks[fb_id] = feedback