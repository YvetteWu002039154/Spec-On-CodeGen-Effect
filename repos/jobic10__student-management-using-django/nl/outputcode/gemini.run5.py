from typing import List, Dict, Optional

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

class Leave:
    def __init__(self, leave_id: int, user_id: int, date: str, reason: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.date = date
        self.reason = reason
        self.status = "Pending"

class Feedback:
    def __init__(self, feedback_id: int, user_id: int, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.reply = ""

class Attendance:
    def __init__(self, attendance_id: int, student_id: int, subject_id: int, date: str, status: bool):
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.date = date
        self.status = status

class Result:
    def __init__(self, result_id: int, student_id: int, subject_id: int, marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks

class SystemDatabase:
    def __init__(self):
        self.staff: Dict[int, 'Staff'] = {}
        self.students: Dict[int, 'Student'] = {}
        self.courses: Dict[int, Course] = {}
        self.subjects: Dict[int, Subject] = {}
        self.sessions: Dict[int, Session] = {}
        self.attendances: Dict[int, Attendance] = {}
        self.results: Dict[int, Result] = {}
        self.leaves: Dict[int, Leave] = {}
        self.feedbacks: Dict[int, Feedback] = {}
        self._id_counter = 0

    def generate_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

class Admin(User):
    def view_overall_summary(self, db: SystemDatabase) -> Dict[str, int]:
        return {
            "total_students": len(db.students),
            "total_staff": len(db.staff),
            "total_courses": len(db.courses),
            "total_subjects": len(db.subjects),
            "total_leaves": len(db.leaves),
            "total_sessions": len(db.sessions)
        }

    def add_staff(self, db: SystemDatabase, staff: 'Staff') -> None:
        db.staff[staff.user_id] = staff

    def update_staff(self, db: SystemDatabase, staff_id: int, name: Optional[str] = None, email: Optional[str] = None) -> None:
        if staff_id in db.staff:
            if name is not None: db.staff[staff_id].name = name
            if email is not None: db.staff[staff_id].email = email

    def delete_staff(self, db: SystemDatabase, staff_id: int) -> None:
        if staff_id in db.staff:
            del db.staff[staff_id]

    def add_student(self, db: SystemDatabase, student: 'Student') -> None:
        db.students[student.user_id] = student

    def update_student(self, db: SystemDatabase, student_id: int, name: Optional[str] = None, email: Optional[str] = None, course_id: Optional[int] = None, session_id: Optional[int] = None) -> None:
        if student_id in db.students:
            if name is not None: db.students[student_id].name = name
            if email is not None: db.students[student_id].email = email
            if course_id is not None: db.students[student_id].course_id = course_id
            if session_id is not None: db.students[student_id].session_id = session_id

    def delete_student(self, db: SystemDatabase, student_id: int) -> None:
        if student_id in db.students:
            del db.students[student_id]

    def add_course(self, db: SystemDatabase, course: Course) -> None:
        db.courses[course.course_id] = course

    def update_course(self, db: SystemDatabase, course_id: int, name: str) -> None:
        if course_id in db.courses:
            db.courses[course_id].name = name

    def delete_course(self, db: SystemDatabase, course_id: int) -> None:
        if course_id in db.courses:
            del db.courses[course_id]

    def add_subject(self, db: SystemDatabase, subject: Subject) -> None:
        db.subjects[subject.subject_id] = subject

    def update_subject(self, db: SystemDatabase, subject_id: int, name: Optional[str] = None, course_id: Optional[int] = None, staff_id: Optional[int] = None) -> None:
        if subject_id in db.subjects:
            if name is not None: db.subjects[subject_id].name = name
            if course_id is not None: db.subjects[subject_id].course_id = course_id
            if staff_id is not None: db.subjects[subject_id].staff_id = staff_id

    def delete_subject(self, db: SystemDatabase, subject_id: int) -> None:
        if subject_id in db.subjects:
            del db.subjects[subject_id]

    def add_session(self, db: SystemDatabase, session: Session) -> None:
        db.sessions[session.session_id] = session

    def update_session(self, db: SystemDatabase, session_id: int, start_year: Optional[str] = None, end_year: Optional[str] = None) -> None:
        if session_id in db.sessions:
            if start_year is not None: db.sessions[session_id].start_year = start_year
            if end_year is not None: db.sessions[session_id].end_year = end_year

    def delete_session(self, db: SystemDatabase, session_id: int) -> None:
        if session_id in db.sessions:
            del db.sessions[session_id]

    def view_student_attendance(self, db: SystemDatabase, student_id: int) -> List[Attendance]:
        return [a for a in db.attendances.values() if a.student_id == student_id]

    def review_feedback(self, db: SystemDatabase) -> List[Feedback]:
        return list(db.feedbacks.values())

    def reply_feedback(self, db: SystemDatabase, feedback_id: int, reply: str) -> None:
        if feedback_id in db.feedbacks:
            db.feedbacks[feedback_id].reply = reply

    def review_leave(self, db: SystemDatabase) -> List[Leave]:
        return list(db.leaves.values())

    def approve_reject_leave(self, db: SystemDatabase, leave_id: int, status: str) -> None:
        if status not in ["Approved", "Rejected"]:
            raise ValueError("Status must be 'Approved' or 'Rejected'")
        if leave_id in db.leaves:
            db.leaves[leave_id].status = status

class Staff(User):
    def view_summary_charts(self, db: SystemDatabase) -> Dict[str, int]:
        my_subjects = [s for s in db.subjects.values() if s.staff_id == self.user_id]
        my_students = [s for s in db.students.values() if any(sub.course_id == s.course_id for sub in my_subjects)]
        my_leaves = [l for l in db.leaves.values() if l.user_id == self.user_id]
        return {
            "total_my_students": len(my_students),
            "total_my_subjects": len(my_subjects),
            "total_my_leaves": len(my_leaves)
        }

    def take_attendance(self, db: SystemDatabase, student_id: int, subject_id: int, date: str, status: bool) -> None:
        att_id = db.generate_id()
        db.attendances[att_id] = Attendance(att_id, student_id, subject_id, date, status)

    def update_attendance(self, db: SystemDatabase, attendance_id: int, status: bool) -> None:
        if attendance_id in db.attendances:
            db.attendances[attendance_id].status = status

    def add_result(self, db: SystemDatabase, student_id: int, subject_id: int, marks: float) -> None:
        res_id = db.generate_id()
        db.results[res_id] = Result(res_id, student_id, subject_id, marks)

    def update_result(self, db: SystemDatabase, result_id: int, marks: float) -> None:
        if result_id in db.results:
            db.results[result_id].marks = marks

    def apply_leave(self, db: SystemDatabase, date: str, reason: str) -> None:
        leave_id = db.generate_id()
        db.leaves[leave_id] = Leave(leave_id, self.user_id, date, reason)

    def send_feedback(self, db: SystemDatabase, message: str) -> None:
        fb_id = db.generate_id()
        db.feedbacks[fb_id] = Feedback(fb_id, self.user_id, message)

class Student(User):
    def __init__(self, user_id: int, name: str, email: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email)
        self.course_id = course_id
        self.session_id = session_id

    def view_summary_charts(self, db: SystemDatabase) -> Dict[str, int]:
        my_attendances = [a for a in db.attendances.values() if a.student_id == self.user_id]
        my_subjects = [s for s in db.subjects.values() if s.course_id == self.course_id]
        my_leaves = [l for l in db.leaves.values() if l.user_id == self.user_id]
        return {
            "total_attendances": len(my_attendances),
            "total_subjects": len(my_subjects),
            "total_leaves": len(my_leaves)
        }

    def view_attendance(self, db: SystemDatabase) -> List[Attendance]:
        return [a for a in db.attendances.values() if a.student_id == self.user_id]

    def view_result(self, db: SystemDatabase) -> List[Result]:
        return [r for r in db.results.values() if r.student_id == self.user_id]

    def apply_leave(self, db: SystemDatabase, date: str, reason: str) -> None:
        leave_id = db.generate_id()
        db.leaves[leave_id] = Leave(leave_id, self.user_id, date, reason)

    def send_feedback(self, db: SystemDatabase, message: str) -> None:
        fb_id = db.generate_id()
        db.feedbacks[fb_id] = Feedback(fb_id, self.user_id, message)