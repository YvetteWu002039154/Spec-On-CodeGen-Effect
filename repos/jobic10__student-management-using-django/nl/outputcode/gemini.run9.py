from typing import List, Dict, Optional
from datetime import date

class User:
    def __init__(self, user_id: int, name: str, email: str, role: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role

class Admin(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email, "Admin")

class Staff(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email, "Staff")

class Student(User):
    def __init__(self, user_id: int, name: str, email: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email, "Student")
        self.course_id = course_id
        self.session_id = session_id

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
    def __init__(self, attendance_id: int, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: str):
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
        self.status = "Pending"

class Feedback:
    def __init__(self, feedback_id: int, user_id: int, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.reply: Optional[str] = None

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

        self._user_id_counter = 1
        self._course_id_counter = 1
        self._subject_id_counter = 1
        self._session_id_counter = 1
        self._attendance_id_counter = 1
        self._result_id_counter = 1
        self._leave_id_counter = 1
        self._feedback_id_counter = 1

    def _generate_user_id(self) -> int:
        uid = self._user_id_counter
        self._user_id_counter += 1
        return uid

    def _verify_admin(self, user_id: int) -> None:
        user = self.users.get(user_id)
        if not user or user.role != "Admin":
            raise PermissionError("Admin privileges required.")

    def _verify_staff(self, user_id: int) -> None:
        user = self.users.get(user_id)
        if not user or user.role != "Staff":
            raise PermissionError("Staff privileges required.")

    def _verify_student(self, user_id: int) -> None:
        user = self.users.get(user_id)
        if not user or user.role != "Student":
            raise PermissionError("Student privileges required.")

    def add_admin(self, name: str, email: str) -> int:
        uid = self._generate_user_id()
        self.users[uid] = Admin(uid, name, email)
        return uid

    def get_admin_summary(self, admin_id: int) -> Dict[str, int]:
        self._verify_admin(admin_id)
        return {
            "total_students": sum(1 for u in self.users.values() if u.role == "Student"),
            "total_staff": sum(1 for u in self.users.values() if u.role == "Staff"),
            "total_courses": len(self.courses),
            "total_subjects": len(self.subjects),
            "total_leaves": len(self.leaves),
            "pending_leaves": sum(1 for l in self.leaves.values() if l.status == "Pending"),
            "pending_feedbacks": sum(1 for f in self.feedbacks.values() if f.reply is None)
        }

    def add_staff(self, admin_id: int, name: str, email: str) -> int:
        self._verify_admin(admin_id)
        uid = self._generate_user_id()
        self.users[uid] = Staff(uid, name, email)
        return uid

    def update_staff(self, admin_id: int, staff_id: int, name: str, email: str) -> None:
        self._verify_admin(admin_id)
        staff = self.users.get(staff_id)
        if not staff or staff.role != "Staff":
            raise ValueError("Staff member not found.")
        staff.name = name
        staff.email = email

    def delete_staff(self, admin_id: int, staff_id: int) -> None:
        self._verify_admin(admin_id)
        if staff_id in self.users and self.users[staff_id].role == "Staff":
            del self.users[staff_id]

    def add_student(self, admin_id: int, name: str, email: str, course_id: int, session_id: int) -> int:
        self._verify_admin(admin_id)
        if course_id not in self.courses or session_id not in self.sessions:
            raise ValueError("Invalid course or session ID.")
        uid = self._generate_user_id()
        self.users[uid] = Student(uid, name, email, course_id, session_id)
        return uid

    def update_student(self, admin_id: int, student_id: int, name: str, email: str, course_id: int, session_id: int) -> None:
        self._verify_admin(admin_id)
        student = self.users.get(student_id)
        if not student or student.role != "Student":
            raise ValueError("Student not found.")
        if course_id not in self.courses or session_id not in self.sessions:
            raise ValueError("Invalid course or session ID.")
        student.name = name
        student.email = email
        student.course_id = course_id
        student.session_id = session_id

    def delete_student(self, admin_id: int, student_id: int) -> None:
        self._verify_admin(admin_id)
        if student_id in self.users and self.users[student_id].role == "Student":
            del self.users[student_id]

    def add_course(self, admin_id: int, name: str) -> int:
        self._verify_admin(admin_id)
        cid = self._course_id_counter
        self._course_id_counter += 1
        self.courses[cid] = Course(cid, name)
        return cid

    def update_course(self, admin_id: int, course_id: int, name: str) -> None:
        self._verify_admin(admin_id)
        if course_id not in self.courses:
            raise ValueError("Course not found.")
        self.courses[course_id].name = name

    def delete_course(self, admin_id: int, course_id: int) -> None:
        self._verify_admin(admin_id)
        if course_id in self.courses:
            del self.courses[course_id]

    def add_subject(self, admin_id: int, name: str, course_id: int, staff_id: int) -> int:
        self._verify_admin(admin_id)
        if course_id not in self.courses:
            raise ValueError("Course not found.")
        staff = self.users.get(staff_id)
        if not staff or staff.role != "Staff":
            raise ValueError("Staff member not found.")
        sid = self._subject_id_counter
        self._subject_id_counter += 1
        self.subjects[sid] = Subject(sid, name, course_id, staff_id)
        return sid

    def update_subject(self, admin_id: int, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        self._verify_admin(admin_id)
        if subject_id not in self.subjects:
            raise ValueError("Subject not found.")
        if course_id not in self.courses:
            raise ValueError("Course not found.")
        staff = self.users.get(staff_id)
        if not staff or staff.role != "Staff":
            raise ValueError("Staff member not found.")
        subject = self.subjects[subject_id]
        subject.name = name
        subject.course_id = course_id
        subject.staff_id = staff_id

    def delete_subject(self, admin_id: int, subject_id: int) -> None:
        self._verify_admin(admin_id)
        if subject_id in self.subjects:
            del self.subjects[subject_id]

    def add_session(self, admin_id: int, start_year: str, end_year: str) -> int:
        self._verify_admin(admin_id)
        sid = self._session_id_counter
        self._session_id_counter += 1
        self.sessions[sid] = Session(sid, start_year, end_year)
        return sid

    def update_session(self, admin_id: int, session_id: int, start_year: str, end_year: str) -> None:
        self._verify_admin(admin_id)
        if session_id not in self.sessions:
            raise ValueError("Session not found.")
        session = self.sessions[session_id]
        session.start_year = start_year
        session.end_year = end_year

    def delete_session(self, admin_id: int, session_id: int) -> None:
        self._verify_admin(admin_id)
        if session_id in self.sessions:
            del self.sessions[session_id]

    def view_all_attendance(self, admin_id: int) -> List[Attendance]:
        self._verify_admin(admin_id)
        return list(self.attendances.values())

    def review_feedback(self, admin_id: int, feedback_id: int, reply: str) -> None:
        self._verify_admin(admin_id)
        if feedback_id not in self.feedbacks:
            raise ValueError("Feedback not found.")
        self.feedbacks[feedback_id].reply = reply

    def review_leave(self, admin_id: int, leave_id: int, status: str) -> None:
        self._verify_admin(admin_id)
        if status not in ["Approved", "Rejected"]:
            raise ValueError("Status must be 'Approved' or 'Rejected'.")
        if leave_id not in self.leaves:
            raise ValueError("Leave record not found.")
        self.leaves[leave_id].status = status

    def get_staff_summary(self, staff_id: int) -> Dict[str, int]:
        self._verify_staff(staff_id)
        my_subjects = [s for s in self.subjects.values() if s.staff_id == staff_id]
        my_leaves = [l for l in self.leaves.values() if l.user_id == staff_id]
        return {
            "total_subjects": len(my_subjects),
            "total_leaves_applied": len(my_leaves),
            "approved_leaves": sum(1 for l in my_leaves if l.status == "Approved"),
            "rejected_leaves": sum(1 for l in my_leaves if l.status == "Rejected"),
            "pending_leaves": sum(1 for l in my_leaves if l.status == "Pending")
        }

    def take_attendance(self, staff_id: int, subject_id: int, session_id: int, attendance_date: date, student_id: int, status: str) -> int:
        self._verify_staff(staff_id)
        subject = self.subjects.get(subject_id)
        if not subject or subject.staff_id != staff_id:
            raise PermissionError("Staff not assigned to this subject.")
        if status not in ["Present", "Absent"]:
            raise ValueError("Status must be 'Present' or 'Absent'.")
        
        aid = self._attendance_id_counter
        self._attendance_id_counter += 1
        self.attendances[aid] = Attendance(aid, subject_id, session_id, attendance_date, student_id, status)
        return aid

    def update_attendance(self, staff_id: int, attendance_id: int, status: str) -> None:
        self._verify_staff(staff_id)
        attendance = self.attendances.get(attendance_id)
        if not attendance:
            raise ValueError("Attendance record not found.")
        subject = self.subjects.get(attendance.subject_id)
        if not subject or subject.staff_id != staff_id:
            raise PermissionError("Staff not assigned to this subject.")
        if status not in ["Present", "Absent"]:
            raise ValueError("Status must be 'Present' or 'Absent'.")
        attendance.status = status

    def add_result(self, staff_id: int, student_id: int, subject_id: int, marks: float) -> int:
        self._verify_staff(staff_id)
        subject = self.subjects.get(subject_id)
        if not subject or subject.staff_id != staff_id:
            raise PermissionError("Staff not assigned to this subject.")
        
        rid = self._result_id_counter
        self._result_id_counter += 1
        self.results[rid] = Result(rid, student_id, subject_id, marks)
        return rid

    def update_result(self, staff_id: int, result_id: int, marks: float) -> None:
        self._verify_staff(staff_id)
        result = self.results.get(result_id)
        if not result:
            raise ValueError("Result not found.")
        subject = self.subjects.get(result.subject_id)
        if not subject or subject.staff_id != staff_id:
            raise PermissionError("Staff not assigned to this subject.")
        result.marks = marks

    def get_student_summary(self, student_id: int) -> Dict[str, int]:
        self._verify_student(student_id)
        my_attendance = [a for a in self.attendances.values() if a.student_id == student_id]
        my_leaves = [l for l in self.leaves.values() if l.user_id == student_id]
        student = self.users[student_id]
        my_subjects = [s for s in self.subjects.values() if s.course_id == student.course_id]
        
        return {
            "total_subjects": len(my_subjects),
            "total_attendance_classes": len(my_attendance),
            "present_count": sum(1 for a in my_attendance if a.status == "Present"),
            "absent_count": sum(1 for a in my_attendance if a.status == "Absent"),
            "total_leaves_applied": len(my_leaves),
            "approved_leaves": sum(1 for l in my_leaves if l.status == "Approved")
        }

    def view_my_attendance(self, student_id: int) -> List[Attendance]:
        self._verify_student(student_id)
        return [a for a in self.attendances.values() if a.student_id == student_id]

    def view_my_results(self, student_id: int) -> List[Result]:
        self._verify_student(student_id)
        return [r for r in self.results.values() if r.student_id == student_id]

    def apply_leave(self, user_id: int, leave_date: date, message: str) -> int:
        user = self.users.get(user_id)
        if not user or user.role not in ["Staff", "Student"]:
            raise PermissionError("Only Staff or Students can apply for leave.")
        
        lid = self._leave_id_counter
        self._leave_id_counter += 1
        self.leaves[lid] = Leave(lid, user_id, leave_date, message)
        return lid

    def send_feedback(self, user_id: int, message: str) -> int:
        user = self.users.get(user_id)
        if not user or user.role not in ["Staff", "Student"]:
            raise PermissionError("Only Staff or Students can send feedback.")
        
        fid = self._feedback_id_counter
        self._feedback_id_counter += 1
        self.feedbacks[fid] = Feedback(fid, user_id, message)
        return fid