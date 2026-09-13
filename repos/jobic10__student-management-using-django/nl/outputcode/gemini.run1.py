from typing import List, Dict, Optional, Any
from datetime import date

class User:
    def __init__(self, user_id: int, name: str, email: str):
        self._user_id = user_id
        self._name = name
        self._email = email

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        self._email = value


class Admin(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email)


class Staff(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email)


class Student(User):
    def __init__(self, user_id: int, name: str, email: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email)
        self._course_id = course_id
        self._session_id = session_id

    @property
    def course_id(self) -> int:
        return self._course_id

    @course_id.setter
    def course_id(self, value: int) -> None:
        self._course_id = value

    @property
    def session_id(self) -> int:
        return self._session_id

    @session_id.setter
    def session_id(self, value: int) -> None:
        self._session_id = value


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
    def __init__(self, session_id: int, start_year: int, end_year: int):
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year


class Attendance:
    def __init__(self, attendance_id: int, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: bool):
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
    def __init__(self, leave_id: int, user_id: int, role: str, leave_date: date, message: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.role = role
        self.leave_date = leave_date
        self.message = message
        self.status = "Pending"


class Feedback:
    def __init__(self, feedback_id: int, user_id: int, role: str, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.role = role
        self.message = message
        self.reply = ""


class StudentManagementSystem:
    def __init__(self):
        self._admins: Dict[int, Admin] = {}
        self._staffs: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}
        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._sessions: Dict[int, Session] = {}
        self._attendances: Dict[int, Attendance] = {}
        self._results: Dict[int, Result] = {}
        self._leaves: Dict[int, Leave] = {}
        self._feedbacks: Dict[int, Feedback] = {}

        self._leave_id_counter = 1
        self._feedback_id_counter = 1
        self._attendance_id_counter = 1
        self._result_id_counter = 1

    def admin_view_summary(self) -> Dict[str, Any]:
        return {
            "total_students": len(self._students),
            "total_staff": len(self._staffs),
            "total_courses": len(self._courses),
            "total_subjects": len(self._subjects),
            "total_leaves": len(self._leaves),
            "pending_leaves": len([l for l in self._leaves.values() if l.status == "Pending"]),
            "pending_feedbacks": len([f for f in self._feedbacks.values() if not f.reply]),
            "total_results_recorded": len(self._results)
        }

    def add_staff(self, staff: Staff) -> None:
        self._staffs[staff.user_id] = staff

    def update_staff(self, user_id: int, name: Optional[str] = None, email: Optional[str] = None) -> None:
        if user_id in self._staffs:
            if name:
                self._staffs[user_id].name = name
            if email:
                self._staffs[user_id].email = email

    def delete_staff(self, user_id: int) -> None:
        if user_id in self._staffs:
            del self._staffs[user_id]

    def add_student(self, student: Student) -> None:
        self._students[student.user_id] = student

    def update_student(self, user_id: int, name: Optional[str] = None, email: Optional[str] = None, course_id: Optional[int] = None, session_id: Optional[int] = None) -> None:
        if user_id in self._students:
            if name:
                self._students[user_id].name = name
            if email:
                self._students[user_id].email = email
            if course_id:
                self._students[user_id].course_id = course_id
            if session_id:
                self._students[user_id].session_id = session_id

    def delete_student(self, user_id: int) -> None:
        if user_id in self._students:
            del self._students[user_id]

    def add_course(self, course: Course) -> None:
        self._courses[course.course_id] = course

    def update_course(self, course_id: int, name: str) -> None:
        if course_id in self._courses:
            self._courses[course_id].name = name

    def delete_course(self, course_id: int) -> None:
        if course_id in self._courses:
            del self._courses[course_id]

    def add_subject(self, subject: Subject) -> None:
        self._subjects[subject.subject_id] = subject

    def update_subject(self, subject_id: int, name: Optional[str] = None, course_id: Optional[int] = None, staff_id: Optional[int] = None) -> None:
        if subject_id in self._subjects:
            if name:
                self._subjects[subject_id].name = name
            if course_id:
                self._subjects[subject_id].course_id = course_id
            if staff_id:
                self._subjects[subject_id].staff_id = staff_id

    def delete_subject(self, subject_id: int) -> None:
        if subject_id in self._subjects:
            del self._subjects[subject_id]

    def add_session(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    def update_session(self, session_id: int, start_year: Optional[int] = None, end_year: Optional[int] = None) -> None:
        if session_id in self._sessions:
            if start_year:
                self._sessions[session_id].start_year = start_year
            if end_year:
                self._sessions[session_id].end_year = end_year

    def delete_session(self, session_id: int) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    def admin_view_attendance(self) -> List[Attendance]:
        return list(self._attendances.values())

    def admin_review_feedback(self, feedback_id: int, reply: str) -> None:
        if feedback_id in self._feedbacks:
            self._feedbacks[feedback_id].reply = reply

    def admin_review_leave(self, leave_id: int, status: str) -> None:
        if status in ["Approved", "Rejected"] and leave_id in self._leaves:
            self._leaves[leave_id].status = status

    def staff_view_summary(self, staff_id: int) -> Dict[str, Any]:
        staff_subjects = [s for s in self._subjects.values() if s.staff_id == staff_id]
        staff_students = [s for s in self._students.values() if s.course_id in [sub.course_id for sub in staff_subjects]]
        staff_leaves = [l for l in self._leaves.values() if l.user_id == staff_id and l.role == "Staff"]

        return {
            "total_subjects": len(staff_subjects),
            "total_students": len(staff_students),
            "total_leaves_applied": len(staff_leaves),
            "approved_leaves": len([l for l in staff_leaves if l.status == "Approved"]),
            "rejected_leaves": len([l for l in staff_leaves if l.status == "Rejected"]),
            "pending_leaves": len([l for l in staff_leaves if l.status == "Pending"])
        }

    def staff_take_attendance(self, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: bool) -> None:
        attendance = Attendance(self._attendance_id_counter, subject_id, session_id, attendance_date, student_id, status)
        self._attendances[self._attendance_id_counter] = attendance
        self._attendance_id_counter += 1

    def staff_update_attendance(self, attendance_id: int, status: bool) -> None:
        if attendance_id in self._attendances:
            self._attendances[attendance_id].status = status

    def staff_add_result(self, student_id: int, subject_id: int, marks: float) -> None:
        result = Result(self._result_id_counter, student_id, subject_id, marks)
        self._results[self._result_id_counter] = result
        self._result_id_counter += 1

    def staff_update_result(self, result_id: int, marks: float) -> None:
        if result_id in self._results:
            self._results[result_id].marks = marks

    def staff_apply_leave(self, staff_id: int, leave_date: date, message: str) -> None:
        leave = Leave(self._leave_id_counter, staff_id, "Staff", leave_date, message)
        self._leaves[self._leave_id_counter] = leave
        self._leave_id_counter += 1

    def staff_send_feedback(self, staff_id: int, message: str) -> None:
        feedback = Feedback(self._feedback_id_counter, staff_id, "Staff", message)
        self._feedbacks[self._feedback_id_counter] = feedback
        self._feedback_id_counter += 1

    def student_view_summary(self, student_id: int) -> Dict[str, Any]:
        student = self._students.get(student_id)
        if not student:
            return {}

        student_subjects = [s for s in self._subjects.values() if s.course_id == student.course_id]
        student_attendance = [a for a in self._attendances.values() if a.student_id == student_id]
        student_leaves = [l for l in self._leaves.values() if l.user_id == student_id and l.role == "Student"]

        return {
            "total_subjects": len(student_subjects),
            "total_attendance_records": len(student_attendance),
            "present_count": len([a for a in student_attendance if a.status]),
            "absent_count": len([a for a in student_attendance if not a.status]),
            "total_leaves_applied": len(student_leaves),
            "approved_leaves": len([l for l in student_leaves if l.status == "Approved"]),
            "rejected_leaves": len([l for l in student_leaves if l.status == "Rejected"]),
            "pending_leaves": len([l for l in student_leaves if l.status == "Pending"])
        }

    def student_view_attendance(self, student_id: int) -> List[Attendance]:
        return [a for a in self._attendances.values() if a.student_id == student_id]

    def student_view_result(self, student_id: int) -> List[Result]:
        return [r for r in self._results.values() if r.student_id == student_id]

    def student_apply_leave(self, student_id: int, leave_date: date, message: str) -> None:
        leave = Leave(self._leave_id_counter, student_id, "Student", leave_date, message)
        self._leaves[self._leave_id_counter] = leave
        self._leave_id_counter += 1

    def student_send_feedback(self, student_id: int, message: str) -> None:
        feedback = Feedback(self._feedback_id_counter, student_id, "Student", message)
        self._feedbacks[self._feedback_id_counter] = feedback
        self._feedback_id_counter += 1