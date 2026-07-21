from typing import List, Dict, Optional, Any

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
        if start_year > end_year:
            raise ValueError("Start year cannot be greater than end year")
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year

class Attendance:
    def __init__(self, attendance_id: int, student_id: int, subject_id: int, date: str, status: str):
        if status not in ["Present", "Absent"]:
            raise ValueError("Status must be 'Present' or 'Absent'")
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.date = date
        self.status = status

class Result:
    def __init__(self, result_id: int, student_id: int, subject_id: int, marks: float):
        if marks < 0 or marks > 100:
            raise ValueError("Marks must be between 0 and 100")
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks

class Leave:
    def __init__(self, leave_id: int, user_id: int, date: str, message: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.date = date
        self.message = message
        self.status = "Pending"

class Feedback:
    def __init__(self, feedback_id: int, user_id: int, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.reply: Optional[str] = None

class User:
    def __init__(self, user_id: int, name: str, email: str, password: str, role: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.role = role

class Admin(User):
    def __init__(self, user_id: int, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, "Admin")

    def view_summary(self, system: "StudentManagementSystem") -> Dict[str, Any]:
        return {
            "total_students": len([u for u in system.users.values() if u.role == "Student"]),
            "total_staff": len([u for u in system.users.values() if u.role == "Staff"]),
            "total_courses": len(system.courses),
            "total_subjects": len(system.subjects),
            "total_leaves": len(system.leaves)
        }

    def add_staff(self, system: "StudentManagementSystem", name: str, email: str, password: str) -> "Staff":
        staff = Staff(system._next_user_id, name, email, password)
        system.users[staff.user_id] = staff
        system._next_user_id += 1
        return staff

    def update_staff(self, system: "StudentManagementSystem", staff_id: int, name: str, email: str) -> bool:
        staff = system.users.get(staff_id)
        if staff and staff.role == "Staff":
            staff.name = name
            staff.email = email
            return True
        return False

    def delete_staff(self, system: "StudentManagementSystem", staff_id: int) -> bool:
        if staff_id in system.users and system.users[staff_id].role == "Staff":
            del system.users[staff_id]
            return True
        return False

    def add_student(self, system: "StudentManagementSystem", name: str, email: str, password: str, course_id: int, session_id: int) -> "Student":
        if course_id not in system.courses:
            raise ValueError("Invalid course ID")
        if session_id not in system.sessions:
            raise ValueError("Invalid session ID")
        student = Student(system._next_user_id, name, email, password, course_id, session_id)
        system.users[student.user_id] = student
        system._next_user_id += 1
        return student

    def update_student(self, system: "StudentManagementSystem", student_id: int, name: str, email: str, course_id: int, session_id: int) -> bool:
        student = system.users.get(student_id)
        if student and student.role == "Student":
            if course_id not in system.courses or session_id not in system.sessions:
                raise ValueError("Invalid course or session ID")
            student.name = name
            student.email = email
            student.course_id = course_id
            student.session_id = session_id
            return True
        return False

    def delete_student(self, system: "StudentManagementSystem", student_id: int) -> bool:
        if student_id in system.users and system.users[student_id].role == "Student":
            del system.users[student_id]
            return True
        return False

    def add_course(self, system: "StudentManagementSystem", name: str) -> Course:
        course = Course(system._next_course_id, name)
        system.courses[course.course_id] = course
        system._next_course_id += 1
        return course

    def update_course(self, system: "StudentManagementSystem", course_id: int, name: str) -> bool:
        course = system.courses.get(course_id)
        if course:
            course.name = name
            return True
        return False

    def delete_course(self, system: "StudentManagementSystem", course_id: int) -> bool:
        if course_id in system.courses:
            del system.courses[course_id]
            return True
        return False

    def add_subject(self, system: "StudentManagementSystem", name: str, course_id: int, staff_id: int) -> Subject:
        if course_id not in system.courses:
            raise ValueError("Invalid course ID")
        if staff_id not in system.users or system.users[staff_id].role != "Staff":
            raise ValueError("Invalid staff ID")
        subject = Subject(system._next_subject_id, name, course_id, staff_id)
        system.subjects[subject.subject_id] = subject
        system._next_subject_id += 1
        return subject

    def update_subject(self, system: "StudentManagementSystem", subject_id: int, name: str, course_id: int, staff_id: int) -> bool:
        subject = system.subjects.get(subject_id)
        if subject:
            if course_id not in system.courses or staff_id not in system.users or system.users[staff_id].role != "Staff":
                raise ValueError("Invalid course or staff ID")
            subject.name = name
            subject.course_id = course_id
            subject.staff_id = staff_id
            return True
        return False

    def delete_subject(self, system: "StudentManagementSystem", subject_id: int) -> bool:
        if subject_id in system.subjects:
            del system.subjects[subject_id]
            return True
        return False

    def add_session(self, system: "StudentManagementSystem", start_year: int, end_year: int) -> Session:
        session = Session(system._next_session_id, start_year, end_year)
        system.sessions[session.session_id] = session
        system._next_session_id += 1
        return session

    def update_session(self, system: "StudentManagementSystem", session_id: int, start_year: int, end_year: int) -> bool:
        session = system.sessions.get(session_id)
        if session:
            if start_year > end_year:
                raise ValueError("Start year cannot be greater than end year")
            session.start_year = start_year
            session.end_year = end_year
            return True
        return False

    def delete_session(self, system: "StudentManagementSystem", session_id: int) -> bool:
        if session_id in system.sessions:
            del system.sessions[session_id]
            return True
        return False

    def view_student_attendance(self, system: "StudentManagementSystem", student_id: int) -> List[Attendance]:
        if student_id not in system.users or system.users[student_id].role != "Student":
            raise ValueError("Invalid student ID")
        return [a for a in system.attendances.values() if a.student_id == student_id]

    def review_feedback(self, system: "StudentManagementSystem", feedback_id: int, reply: str) -> bool:
        feedback = system.feedbacks.get(feedback_id)
        if feedback:
            feedback.reply = reply
            return True
        return False

    def review_leave(self, system: "StudentManagementSystem", leave_id: int, status: str) -> bool:
        if status not in ["Approved", "Rejected"]:
            raise ValueError("Status must be 'Approved' or 'Rejected'")
        leave = system.leaves.get(leave_id)
        if leave:
            leave.status = status
            return True
        return False

class Staff(User):
    def __init__(self, user_id: int, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, "Staff")

    def view_summary(self, system: "StudentManagementSystem") -> Dict[str, Any]:
        my_subjects = [s for s in system.subjects.values() if s.staff_id == self.user_id]
        my_leaves = [l for l in system.leaves.values() if l.user_id == self.user_id]
        course_ids = {s.course_id for s in my_subjects}
        my_students = [u for u in system.users.values() if u.role == "Student" and getattr(u, 'course_id', None) in course_ids]

        return {
            "total_my_students": len(my_students),
            "total_my_subjects": len(my_subjects),
            "total_my_leaves": len(my_leaves)
        }

    def take_attendance(self, system: "StudentManagementSystem", student_id: int, subject_id: int, date: str, status: str) -> Attendance:
        if student_id not in system.users or system.users[student_id].role != "Student":
            raise ValueError("Invalid student ID")
        if subject_id not in system.subjects:
            raise ValueError("Invalid subject ID")
        attendance = Attendance(system._next_attendance_id, student_id, subject_id, date, status)
        system.attendances[attendance.attendance_id] = attendance
        system._next_attendance_id += 1
        return attendance

    def update_attendance(self, system: "StudentManagementSystem", attendance_id: int, status: str) -> bool:
        if status not in ["Present", "Absent"]:
            raise ValueError("Status must be 'Present' or 'Absent'")
        attendance = system.attendances.get(attendance_id)
        if attendance:
            attendance.status = status
            return True
        return False

    def add_result(self, system: "StudentManagementSystem", student_id: int, subject_id: int, marks: float) -> Result:
        if student_id not in system.users or system.users[student_id].role != "Student":
            raise ValueError("Invalid student ID")
        if subject_id not in system.subjects:
            raise ValueError("Invalid subject ID")
        result = Result(system._next_result_id, student_id, subject_id, marks)
        system.results[result.result_id] = result
        system._next_result_id += 1
        return result

    def update_result(self, system: "StudentManagementSystem", result_id: int, marks: float) -> bool:
        if marks < 0 or marks > 100:
            raise ValueError("Marks must be between 0 and 100")
        result = system.results.get(result_id)
        if result:
            result.marks = marks
            return True
        return False

    def apply_leave(self, system: "StudentManagementSystem", date: str, message: str) -> Leave:
        leave = Leave(system._next_leave_id, self.user_id, date, message)
        system.leaves[leave.leave_id] = leave
        system._next_leave_id += 1
        return leave

    def send_feedback(self, system: "StudentManagementSystem", message: str) -> Feedback:
        feedback = Feedback(system._next_feedback_id, self.user_id, message)
        system.feedbacks[feedback.feedback_id] = feedback
        system._next_feedback_id += 1
        return feedback

class Student(User):
    def __init__(self, user_id: int, name: str, email: str, password: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email, password, "Student")
        self.course_id = course_id
        self.session_id = session_id

    def view_summary(self, system: "StudentManagementSystem") -> Dict[str, Any]:
        my_attendances = [a for a in system.attendances.values() if a.student_id == self.user_id]
        my_subjects = [s for s in system.subjects.values() if s.course_id == self.course_id]
        my_leaves = [l for l in system.leaves.values() if l.user_id == self.user_id]

        return {
            "total_attendances": len(my_attendances),
            "total_subjects": len(my_subjects),
            "total_leaves": len(my_leaves)
        }

    def view_attendance(self, system: "StudentManagementSystem") -> List[Attendance]:
        return [a for a in system.attendances.values() if a.student_id == self.user_id]

    def view_result(self, system: "StudentManagementSystem") -> List[Result]:
        return [r for r in system.results.values() if r.student_id == self.user_id]

    def apply_leave(self, system: "StudentManagementSystem", date: str, message: str) -> Leave:
        leave = Leave(system._next_leave_id, self.user_id, date, message)
        system.leaves[leave.leave_id] = leave
        system._next_leave_id += 1
        return leave

    def send_feedback(self, system: "StudentManagementSystem", message: str) -> Feedback:
        feedback = Feedback(system._next_feedback_id, self.user_id, message)
        system.feedbacks[feedback.feedback_id] = feedback
        system._next_feedback_id += 1
        return feedback

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

        self._next_user_id = 1
        self._next_course_id = 1
        self._next_subject_id = 1
        self._next_session_id = 1
        self._next_attendance_id = 1
        self._next_result_id = 1
        self._next_leave_id = 1
        self._next_feedback_id = 1