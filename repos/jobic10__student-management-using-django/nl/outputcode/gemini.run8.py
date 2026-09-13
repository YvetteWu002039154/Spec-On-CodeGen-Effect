from typing import List, Dict, Optional, Any
from datetime import date

class Course:
    def __init__(self, course_id: int, name: str):
        self.id = course_id
        self.name = name

class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int):
        self.id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id

class Session:
    def __init__(self, session_id: int, start_year: str, end_year: str):
        self.id = session_id
        self.start_year = start_year
        self.end_year = end_year

class Attendance:
    def __init__(self, attendance_id: int, student_id: int, subject_id: int, date_val: date, status: str):
        self.id = attendance_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.date = date_val
        self.status = status

class Result:
    def __init__(self, result_id: int, student_id: int, subject_id: int, marks: float):
        self.id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks

class Leave:
    def __init__(self, leave_id: int, user_id: int, date_val: date, message: str):
        self.id = leave_id
        self.user_id = user_id
        self.date = date_val
        self.message = message
        self.status = "Pending"

class Feedback:
    def __init__(self, feedback_id: int, user_id: int, message: str):
        self.id = feedback_id
        self.user_id = user_id
        self.message = message
        self.reply: Optional[str] = None

class User:
    def __init__(self, user_id: int, name: str, email: str, role: str):
        self.id = user_id
        self.name = name
        self.email = email
        self.role = role

class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.courses: Dict[int, Course] = {}
        self.subjects: Dict[int, Subject] = {}
        self.sessions: Dict[int, Session] = {}
        self.attendances: Dict[int, Attendance] = {}
        self.results: Dict[int, Result] = {}
        self.leaves: Dict[int, Leave] = {}
        self.feedbacks: Dict[int, Feedback] = {}

        self._id_counters = {
            "user": 1,
            "course": 1,
            "subject": 1,
            "session": 1,
            "attendance": 1,
            "result": 1,
            "leave": 1,
            "feedback": 1
        }

    def generate_id(self, entity: str) -> int:
        current_id = self._id_counters[entity]
        self._id_counters[entity] += 1
        return current_id

class Admin(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email, "Admin")

    def view_overall_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        return {
            "total_students": sum(1 for u in system.users.values() if isinstance(u, Student)),
            "total_staff": sum(1 for u in system.users.values() if isinstance(u, Staff)),
            "total_courses": len(system.courses),
            "total_subjects": len(system.subjects),
            "total_leaves": len(system.leaves)
        }

    def add_staff(self, system: StudentManagementSystem, name: str, email: str) -> 'Staff':
        staff_id = system.generate_id("user")
        staff = Staff(staff_id, name, email)
        system.users[staff_id] = staff
        return staff

    def update_staff(self, system: StudentManagementSystem, staff_id: int, name: str, email: str) -> None:
        if staff_id in system.users and isinstance(system.users[staff_id], Staff):
            system.users[staff_id].name = name
            system.users[staff_id].email = email
        else:
            raise ValueError("Staff member not found.")

    def delete_staff(self, system: StudentManagementSystem, staff_id: int) -> None:
        if staff_id in system.users and isinstance(system.users[staff_id], Staff):
            del system.users[staff_id]
        else:
            raise ValueError("Staff member not found.")

    def add_student(self, system: StudentManagementSystem, name: str, email: str, course_id: int, session_id: int) -> 'Student':
        student_id = system.generate_id("user")
        student = Student(student_id, name, email, course_id, session_id)
        system.users[student_id] = student
        return student

    def update_student(self, system: StudentManagementSystem, student_id: int, name: str, email: str, course_id: int, session_id: int) -> None:
        if student_id in system.users and isinstance(system.users[student_id], Student):
            student = system.users[student_id]
            student.name = name
            student.email = email
            student.course_id = course_id
            student.session_id = session_id
        else:
            raise ValueError("Student not found.")

    def delete_student(self, system: StudentManagementSystem, student_id: int) -> None:
        if student_id in system.users and isinstance(system.users[student_id], Student):
            del system.users[student_id]
        else:
            raise ValueError("Student not found.")

    def add_course(self, system: StudentManagementSystem, name: str) -> Course:
        course_id = system.generate_id("course")
        course = Course(course_id, name)
        system.courses[course_id] = course
        return course

    def update_course(self, system: StudentManagementSystem, course_id: int, name: str) -> None:
        if course_id in system.courses:
            system.courses[course_id].name = name
        else:
            raise ValueError("Course not found.")

    def delete_course(self, system: StudentManagementSystem, course_id: int) -> None:
        if course_id in system.courses:
            del system.courses[course_id]
        else:
            raise ValueError("Course not found.")

    def add_subject(self, system: StudentManagementSystem, name: str, course_id: int, staff_id: int) -> Subject:
        subject_id = system.generate_id("subject")
        subject = Subject(subject_id, name, course_id, staff_id)
        system.subjects[subject_id] = subject
        return subject

    def update_subject(self, system: StudentManagementSystem, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if subject_id in system.subjects:
            subject = system.subjects[subject_id]
            subject.name = name
            subject.course_id = course_id
            subject.staff_id = staff_id
        else:
            raise ValueError("Subject not found.")

    def delete_subject(self, system: StudentManagementSystem, subject_id: int) -> None:
        if subject_id in system.subjects:
            del system.subjects[subject_id]
        else:
            raise ValueError("Subject not found.")

    def add_session(self, system: StudentManagementSystem, start_year: str, end_year: str) -> Session:
        session_id = system.generate_id("session")
        session = Session(session_id, start_year, end_year)
        system.sessions[session_id] = session
        return session

    def update_session(self, system: StudentManagementSystem, session_id: int, start_year: str, end_year: str) -> None:
        if session_id in system.sessions:
            session = system.sessions[session_id]
            session.start_year = start_year
            session.end_year = end_year
        else:
            raise ValueError("Session not found.")

    def delete_session(self, system: StudentManagementSystem, session_id: int) -> None:
        if session_id in system.sessions:
            del system.sessions[session_id]
        else:
            raise ValueError("Session not found.")

    def view_student_attendance(self, system: StudentManagementSystem, student_id: int) -> List[Attendance]:
        return [a for a in system.attendances.values() if a.student_id == student_id]

    def review_feedback(self, system: StudentManagementSystem) -> List[Feedback]:
        return list(system.feedbacks.values())

    def reply_feedback(self, system: StudentManagementSystem, feedback_id: int, reply_message: str) -> None:
        if feedback_id in system.feedbacks:
            system.feedbacks[feedback_id].reply = reply_message
        else:
            raise ValueError("Feedback not found.")

    def review_leaves(self, system: StudentManagementSystem) -> List[Leave]:
        return list(system.leaves.values())

    def approve_reject_leave(self, system: StudentManagementSystem, leave_id: int, status: str) -> None:
        if status not in ["Approved", "Rejected"]:
            raise ValueError("Status must be 'Approved' or 'Rejected'.")
        if leave_id in system.leaves:
            system.leaves[leave_id].status = status
        else:
            raise ValueError("Leave not found.")

class Staff(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email, "Staff")

    def view_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        my_subjects = [s for s in system.subjects.values() if s.staff_id == self.id]
        my_course_ids = {s.course_id for s in my_subjects}
        my_students = [u for u in system.users.values() if isinstance(u, Student) and u.course_id in my_course_ids]
        my_leaves = [l for l in system.leaves.values() if l.user_id == self.id]

        return {
            "total_my_students": len(my_students),
            "total_my_subjects": len(my_subjects),
            "my_leaves_status": {l.id: l.status for l in my_leaves}
        }

    def take_attendance(self, system: StudentManagementSystem, student_id: int, subject_id: int, date_val: date, status: str) -> Attendance:
        att_id = system.generate_id("attendance")
        attendance = Attendance(att_id, student_id, subject_id, date_val, status)
        system.attendances[att_id] = attendance
        return attendance

    def update_attendance(self, system: StudentManagementSystem, attendance_id: int, status: str) -> None:
        if attendance_id in system.attendances:
            system.attendances[attendance_id].status = status
        else:
            raise ValueError("Attendance record not found.")

    def add_result(self, system: StudentManagementSystem, student_id: int, subject_id: int, marks: float) -> Result:
        result_id = system.generate_id("result")
        result = Result(result_id, student_id, subject_id, marks)
        system.results[result_id] = result
        return result

    def update_result(self, system: StudentManagementSystem, result_id: int, marks: float) -> None:
        if result_id in system.results:
            system.results[result_id].marks = marks
        else:
            raise ValueError("Result not found.")

    def apply_leave(self, system: StudentManagementSystem, date_val: date, message: str) -> Leave:
        leave_id = system.generate_id("leave")
        leave = Leave(leave_id, self.id, date_val, message)
        system.leaves[leave_id] = leave
        return leave

    def send_feedback(self, system: StudentManagementSystem, message: str) -> Feedback:
        feedback_id = system.generate_id("feedback")
        feedback = Feedback(feedback_id, self.id, message)
        system.feedbacks[feedback_id] = feedback
        return feedback

class Student(User):
    def __init__(self, user_id: int, name: str, email: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email, "Student")
        self.course_id = course_id
        self.session_id = session_id

    def view_summary(self, system: StudentManagementSystem) -> Dict[str, Any]:
        my_attendances = [a for a in system.attendances.values() if a.student_id == self.id]
        my_subjects = [s for s in system.subjects.values() if s.course_id == self.course_id]
        my_leaves = [l for l in system.leaves.values() if l.user_id == self.id]

        return {
            "total_attendances": len(my_attendances),
            "total_subjects": len(my_subjects),
            "my_leaves_status": {l.id: l.status for l in my_leaves}
        }

    def view_attendance(self, system: StudentManagementSystem) -> List[Attendance]:
        return [a for a in system.attendances.values() if a.student_id == self.id]

    def view_result(self, system: StudentManagementSystem) -> List[Result]:
        return [r for r in system.results.values() if r.student_id == self.id]

    def apply_leave(self, system: StudentManagementSystem, date_val: date, message: str) -> Leave:
        leave_id = system.generate_id("leave")
        leave = Leave(leave_id, self.id, date_val, message)
        system.leaves[leave_id] = leave
        return leave

    def send_feedback(self, system: StudentManagementSystem, message: str) -> Feedback:
        feedback_id = system.generate_id("feedback")
        feedback = Feedback(feedback_id, self.id, message)
        system.feedbacks[feedback_id] = feedback
        return feedback