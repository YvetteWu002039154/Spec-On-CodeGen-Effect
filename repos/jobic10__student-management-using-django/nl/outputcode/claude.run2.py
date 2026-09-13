from datetime import datetime, date
from typing import Optional
import hashlib
import uuid


class User:
    def __init__(self, user_id: str, username: str, password: str, email: str, role: str):
        self.user_id = user_id
        self.username = username
        self._password_hash = self._hash_password(password)
        self.email = email
        self.role = role
        self.created_at = datetime.now()
        self.is_active = True

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self._password_hash == self._hash_password(password)

    def update_password(self, new_password: str):
        self._password_hash = self._hash_password(new_password)

    def __repr__(self):
        return f"User(id={self.user_id}, username={self.username}, role={self.role})"


class Admin(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 first_name: str, last_name: str):
        super().__init__(user_id, username, password, email, "admin")
        self.first_name = first_name
        self.last_name = last_name

    def __repr__(self):
        return f"Admin(id={self.user_id}, name={self.first_name} {self.last_name})"


class Staff(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 first_name: str, last_name: str, address: str, course_id: Optional[str] = None):
        super().__init__(user_id, username, password, email, "staff")
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.course_id = course_id
        self.subjects = []
        self.leave_requests = []
        self.feedbacks = []

    def __repr__(self):
        return f"Staff(id={self.user_id}, name={self.first_name} {self.last_name})"


class Student(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 first_name: str, last_name: str, address: str,
                 course_id: Optional[str] = None, session_id: Optional[str] = None):
        super().__init__(user_id, username, password, email, "student")
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.course_id = course_id
        self.session_id = session_id
        self.leave_requests = []
        self.feedbacks = []

    def __repr__(self):
        return f"Student(id={self.user_id}, name={self.first_name} {self.last_name})"


class Course:
    def __init__(self, course_id: str, name: str):
        self.course_id = course_id
        self.name = name
        self.created_at = datetime.now()
        self.subjects = []
        self.students = []
        self.staff_members = []

    def __repr__(self):
        return f"Course(id={self.course_id}, name={self.name})"


class Subject:
    def __init__(self, subject_id: str, name: str, course_id: str, staff_id: Optional[str] = None):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id
        self.created_at = datetime.now()

    def __repr__(self):
        return f"Subject(id={self.subject_id}, name={self.name})"


class Session:
    def __init__(self, session_id: str, start_year: int, end_year: int):
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year
        self.created_at = datetime.now()

    def __repr__(self):
        return f"Session(id={self.session_id}, {self.start_year}-{self.end_year})"


class AttendanceRecord:
    def __init__(self, attendance_id: str, subject_id: str, staff_id: str,
                 attendance_date: date, session_id: str):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.staff_id = staff_id
        self.attendance_date = attendance_date
        self.session_id = session_id
        self.created_at = datetime.now()
        self.student_records = {}

    def mark_student(self, student_id: str, status: bool):
        self.student_records[student_id] = status

    def get_student_status(self, student_id: str) -> Optional[bool]:
        return self.student_records.get(student_id)

    def __repr__(self):
        return f"AttendanceRecord(id={self.attendance_id}, date={self.attendance_date})"


class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 exam_marks: float, assignment_marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @property
    def total_marks(self) -> float:
        return self.exam_marks + self.assignment_marks

    def update_marks(self, exam_marks: float, assignment_marks: float):
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Result(id={self.result_id}, student={self.student_id}, total={self.total_marks})"


class LeaveRequest:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    def __init__(self, leave_id: str, user_id: str, user_type: str,
                 start_date: date, end_date: date, reason: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.user_type = user_type
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = self.PENDING
        self.admin_reply = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def approve(self, reply: str = ""):
        self.status = self.APPROVED
        self.admin_reply = reply
        self.updated_at = datetime.now()

    def reject(self, reply: str = ""):
        self.status = self.REJECTED
        self.admin_reply = reply
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"LeaveRequest(id={self.leave_id}, user={self.user_id}, status={self.status})"


class Feedback:
    def __init__(self, feedback_id: str, user_id: str, user_type: str, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.user_type = user_type
        self.message = message
        self.reply = ""
        self.is_replied = False
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_reply(self, reply: str):
        self.reply = reply
        self.is_replied = True
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Feedback(id={self.feedback_id}, user={self.user_id}, replied={self.is_replied})"


class StudentManagementSystem:
    def __init__(self):
        self.users = {}
        self.admins = {}
        self.staff_members = {}
        self.students = {}
        self.courses = {}
        self.subjects = {}
        self.sessions = {}
        self.attendance_records = {}
        self.results = {}
        self.leave_requests = {}
        self.feedbacks = {}
        self._initialize_default_admin()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _initialize_default_admin(self):
        admin = Admin(
            user_id=self._generate_id(),
            username="admin",
            password="admin123",
            email="admin@school.com",
            first_name="System",
            last_name="Admin"
        )
        self.admins[admin.user_id] = admin
        self.users[admin.username] = admin

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username)
        if user and user.verify_password(password) and user.is_active:
            return user
        return None

    def add_admin(self, username: str, password: str, email: str,
                  first_name: str, last_name: str) -> Admin:
        if username in self.users:
            raise ValueError(f"Username '{username}' already exists.")
        admin = Admin(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        self.admins[admin.user_id] = admin
        self.users[username] = admin
        return admin

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str, address: str,
                  course_id: Optional[str] = None) -> Staff:
        if username in self.users:
            raise ValueError(f"Username '{username}' already exists.")
        if course_id and course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' does not exist.")
        staff = Staff(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address,
            course_id=course_id
        )
        self.staff_members[staff.user_id] = staff
        self.users[username] = staff
        if course_id:
            self.courses[course_id].staff_members.append(staff.user_id)
        return staff

    def update_staff(self, staff_id: str, email: Optional[str] = None,
                     first_name: Optional[str] = None, last_name: Optional[str] = None,
                     address: Optional[str] = None, course_id: Optional[str] = None) -> Staff:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' does not exist.")
        staff = self.staff_members[staff_id]
        if email:
            staff.email = email
        if first_name:
            staff.first_name = first_name
        if last_name:
            staff.last_name = last_name
        if address:
            staff.address = address
        if course_id is not None:
            if course_id and course_id not in self.courses:
                raise ValueError(f"Course with id '{course_id}' does not exist.")
            if staff.course_id and staff.course_id in self.courses:
                course = self.courses[staff.course_id]
                if staff.user_id in course.staff_members:
                    course.staff_members.remove(staff.user_id)
            staff.course_id = course_id
            if course_id:
                self.courses[course_id].staff_members.append(staff.user_id)
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' does not exist.")
        staff = self.staff_members[staff_id]
        if staff.course_id and staff.course_id in self.courses:
            course = self.courses[staff.course_id]
            if staff.user_id in course.staff_members:
                course.staff_members.remove(staff.user_id)
        del self.users[staff.username]
        del self.staff_members[staff_id]
        return True

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str, address: str,
                    course_id: Optional[str] = None,
                    session_id: Optional[str] = None) -> Student:
        if username in self.users:
            raise ValueError(f"Username '{username}' already exists.")
        if course_id and course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' does not exist.")
        if session_id and session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist.")
        student = Student(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address,
            course_id=course_id,
            session_id=session_id
        )
        self.students[student.user_id] = student
        self.users[username] = student
        if course_id:
            self.courses[course_id].students.append(student.user_id)
        return student

    def update_student(self, student_id: str, email: Optional[str] = None,
                       first_name: Optional[str] = None, last_name: Optional[str] = None,
                       address: Optional[str] = None, course_id: Optional[str] = None,
                       session_id: Optional[str] = None) -> Student:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' does not exist.")
        student = self.students[student_id]
        if email:
            student.email = email
        if first_name:
            student.first_name = first_name
        if last_name:
            student.last_name = last_name
        if address:
            student.address = address
        if course_id is not None:
            if course_id and course_id not in self.courses:
                raise ValueError(f"Course with id '{course_id}' does not exist.")
            if student.course_id and student.course_id in self.courses:
                course = self.courses[student.course_id]
                if student.user_id in course.students:
                    course.students.remove(student.user_id)
            student.course_id = course_id
            if course_id:
                self.courses[course_id].students.append(student.user_id)
        if session_id is not None:
            if session_id and session_id not in self.sessions:
                raise ValueError(f"Session with id '{session_id}' does not exist.")
            student.session_id = session_id
        return student

    def delete_student(self, student_id: str) -> bool:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' does not exist.")
        student = self.students[student_id]
        if student.course_id and student.course_id in self.courses:
            course = self.courses[student.course_id]
            if student.user_id in course.students:
                course.students.remove(student.user_id)
        del self.users[student.username]
        del self.students[student_id]
        return True

    def add_course(self, name: str) -> Course:
        course = Course(course_id=self._generate_id(), name=name)
        self.courses[course.course_id] = course
        return course

    def update_course(self, course_id: str, name: str) -> Course:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' does not exist.")
        self.courses[course_id].name = name
        return self.courses[course_id]

    def delete_course(self, course_id: str) -> bool:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' does not exist.")
        del self.courses[course_id]
        return True

    def add_subject(self, name: str, course_id: str,
                    staff_id: Optional[str] = None) -> Subject:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' does not exist.")
        if staff_id and staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' does not exist.")
        subject = Subject(
            subject_id=self._generate_id(),
            name=name,
            course_id=course_id,
            staff_id=staff_id
        )
        self.subjects[subject.subject_id] = subject
        self.courses[course_id].subjects.append(subject.subject_id)
        if staff_id:
            self.staff_members[staff_id].subjects.append(subject.subject_id)
        return subject

    def update_subject(self, subject_id: str, name: Optional[str] = None,
                       course_id: Optional[str] = None,
                       staff_id: Optional[str] = None) -> Subject:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist.")
        subject = self.subjects[subject_id]
        if name:
            subject.name = name
        if course_id is not None:
            if course_id and course_id not in self.courses:
                raise ValueError(f"Course with id '{course_id}' does not exist.")
            if subject.course_id in self.courses:
                course = self.courses[subject.course_id]
                if subject_id in course.subjects:
                    course.subjects.remove(subject_id)
            subject.course_id = course_id
            if course_id:
                self.courses[course_id].subjects.append(subject_id)
        if staff_id is not None:
            if subject.staff_id and subject.staff_id in self.staff_members:
                staff = self.staff_members[subject.staff_id]
                if subject_id in staff.subjects:
                    staff.subjects.remove(subject_id)
            if staff_id and staff_id not in self.staff_members:
                raise ValueError(f"Staff with id '{staff_id}' does not exist.")
            subject.staff_id = staff_id
            if staff_id:
                self.staff_members[staff_id].subjects.append(subject_id)
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist.")
        subject = self.subjects[subject_id]
        if subject.course_id in self.courses:
            course = self.courses[subject.course_id]
            if subject_id in course.subjects:
                course.subjects.remove(subject_id)
        if subject.staff_id and subject.staff_id in self.staff_members:
            staff = self.staff_members[subject.staff_id]
            if subject_id in staff.subjects:
                staff.subjects.remove(subject_id)
        del self.subjects[subject_id]
        return True

    def add_session(self, start_year: int, end_year: int) -> Session:
        if end_year <= start_year:
            raise ValueError("End year must be greater than start year.")
        session = Session(
            session_id=self._generate_id(),
            start_year=start_year,
            end_year=end_year
        )
        self.sessions[session.session_id] = session
        return session

    def update_session(self, session_id: str, start_year: Optional[int] = None,
                       end_year: Optional[int] = None) -> Session:
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist.")
        session = self.sessions[session_id]
        if start_year:
            session.start_year = start_year
        if end_year:
            session.end_year = end_year
        if session.end_year <= session.start_year:
            raise ValueError("End year must be greater than start year.")
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist.")
        del self.sessions[session_id]
        return True

    def take_attendance(self, subject_id: str, staff_id: str,
                        attendance_date: date, session_id: str,
                        student_statuses: dict) -> AttendanceRecord:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist.")
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' does not exist.")
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist.")
        record = AttendanceRecord(
            attendance_id=self._generate_id(),
            subject_id=subject_id,
            staff_id=staff_id,
            attendance_date=attendance_date,
            session_id=session_id
        )
        for student_id, status in student_statuses.items():
            if student_id not in self.students:
                raise ValueError(f"Student with id '{student_id}' does not exist.")
            record.mark_student(student_id, status)
        self.attendance_records[record.attendance_id] = record
        return record

    def update_attendance(self, attendance_id: str,
                          student_statuses: dict) -> AttendanceRecord:
        if attendance_id not in self.attendance_records:
            raise ValueError(f"Attendance record with id '{attendance_id}' does not exist.")
        record = self.attendance_records[attendance_id]
        for student_id, status in student_statuses.items():
            if student_id not in self.students:
                raise ValueError(f"Student with id '{student_id}' does not exist.")
            record.mark_student(student_id, status)
        return record

    def get_student_attendance(self, student_id: str,
                               subject_id: Optional[str] = None) -> dict:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' does not exist.")
        attendance_summary = {
            "total": 0,
            "present": 0,
            "absent": 0,
            "records": []
        }
        for record in self.attendance_records.values():
            if subject_id and record.subject_id != subject_id:
                continue
            if student_id in record.student_records:
                status = record.student_records[student_id]
                attendance_summary["total"] += 1
                if status:
                    attendance_summary["present"] += 1
                else:
                    attendance_summary["absent"] += 1
                attendance_summary["records"].append({
                    "attendance_id": record.attendance_id,
                    "subject_id": record.subject_id,
                    "date": record.attendance_date,
                    "status": "Present" if status else "Absent"
                })
        return attendance_summary

    def get_subject_attendance(self, subject_id: str) -> dict:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist.")
        summary = {"records": [], "total_sessions": 0}
        for record in self.attendance_records.values():
            if record.subject_id == subject_id:
                summary["total_sessions"] += 1
                summary["records"].append({
                    "attendance_id": record.attendance_id,
                    "date": record.attendance_date,
                    "student_count": len(record.student_records),
                    "present_count": sum(1 for s in record.student_records.values() if s)
                })
        return summary

    def add_result(self, student_id: str, subject_id: str,
                   exam_marks: float, assignment_marks: float) -> Result:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' does not exist.")
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist.")
        for result in self.results.values():
            if result.student_id == student_id and result.subject_id == subject_id:
                raise ValueError("Result already exists. Use update_result instead.")
        result = Result(
            result_id=self._generate_id(),
            student_id=student_id,
            subject_id=subject_id,
            exam_marks=exam_marks,
            assignment_marks=assignment_marks
        )
        self.results[result.result_id] = result
        return result

    def update_result(self, result_id: str, exam_marks: float,
                      assignment_marks: float) -> Result:
        if result_id not in self.results:
            raise ValueError(f"Result with id '{result_id}' does not exist.")
        self.results[result_id].update_marks(exam_marks, assignment_marks)
        return self.results[result_id]

    def get_student_results(self, student_id: str) -> list:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' does not exist.")
        return [r for r in self.results.values() if r.student_id == student_id]

    def apply_leave(self, user_id: str, user_type: str,
                    start_date: date, end_date: date, reason: str) -> LeaveRequest:
        if user_type == "student" and user_id not in self.students:
            raise ValueError(f"Student with id '{user_id}' does not exist.")
        if user_type == "staff" and user_id not in self.staff_members:
            raise ValueError(f"Staff with id '{user_id}' does not exist.")
        if end_date < start_date:
            raise ValueError("End date cannot be before start date.")
        leave = LeaveRequest(
            leave_id=self._generate_id(),
            user_id=user_id,
            user_type=user_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        self.leave_requests[leave.leave_id] = leave
        if user_type == "student":
            self.students[user_id].leave_requests.append(leave.leave_id)
        elif user_type == "staff":
            self.staff_members[user_id].leave_requests.append(leave.leave_id)
        return leave

    def approve_leave(self, leave_id: str, reply: str = "") -> LeaveRequest:
        if leave_id not in self.leave_requests:
            raise ValueError(f"Leave request with id '{leave_id}' does not exist.")
        self.leave_requests[leave_id].approve(reply)
        return self.leave_requests[leave_id]

    def reject_leave(self, leave_id: str, reply: str = "") -> LeaveRequest:
        if leave_id not in self.leave_requests:
            raise ValueError(f"Leave request with id '{leave_id}' does not exist.")
        self.leave_requests[leave_id].reject(reply)
        return self.leave_requests[leave_id]

    def get_user_leave_requests(self, user_id: str) -> list:
        return [l for l in self.leave_requests.values() if l.user_id == user_id]

    def get_all_leave_requests(self, user_type: Optional[str] = None,
                               status: Optional[str] = None) -> list:
        results = list(self.leave_requests.values())
        if user_type:
            results = [l for l in results if l.user_type == user_type]
        if status:
            results = [l for l in results if l.status == status]
        return results

    def send_feedback(self, user_id: str, user_type: str, message: str) -> Feedback:
        if user_type == "student" and user_id not in self.students:
            raise ValueError(f"Student with id '{user_id}' does not exist.")
        if user_type == "staff" and user_id not in self.staff_members:
            raise ValueError(f"Staff with id '{user_id}' does not exist.")
        feedback = Feedback(
            feedback_id=self._generate_id(),
            user_id=user_id,
            user_type=user_type,
            message=message
        )
        self.feedbacks[feedback.feedback_id] = feedback
        if user_type == "student":
            self.students[user_id].feedbacks.append(feedback.feedback_id)
        elif user_type == "staff":
            self.staff_members[user_id].feedbacks.append(feedback.feedback_id)
        return feedback

    def reply_feedback(self, feedback_id: str, reply: str) -> Feedback:
        if feedback_id not in self.feedbacks:
            raise ValueError(f"Feedback with id '{feedback_id}' does not exist.")
        self.feedbacks[feedback_id].add_reply(reply)
        return self.feedbacks[feedback_id]

    def get_all_feedbacks(self, user_type: Optional[str] = None,
                          is_replied: Optional[bool] = None) -> list:
        results = list(self.feedbacks.values())
        if user_type:
            results = [f for f in results if f.user_type == user_type]
        if is_replied is not None:
            results = [f for f in results if f.is_replied == is_replied]
        return results

    def get_user_feedbacks(self, user_id: str) -> list:
        return [f for f in self.feedbacks.values() if f.user_id == user_id]

    def get_admin_summary(self) -> dict:
        total_students = len(self.students)
        total_staff = len(self.staff_members)
        total_courses = len(self.courses)
        total_subjects = len(self.subjects)
        total_sessions = len(self.sessions)
        pending_student_leaves = len([l for l in self.leave_requests.values()
                                      if l.user_type == "student" and l.status == LeaveRequest.PENDING])
        pending_staff_leaves = len([l for l in self.leave_requests.values()
                                    if l.user_type == "staff" and l.status == LeaveRequest.PENDING])
        unreplied_feedbacks = len([f for f in self.feedbacks.values() if not f.is_replied])
        course_summaries = []
        for course in self.courses.values():
            course_summaries.append({
                "course_id": course.course_id,
                "name": course.name,
                "student_count": len(course.students),
                "staff_count": len(course.staff_members),
                "subject_count": len(course.subjects)
            })
        return {
            "total_students": total_students,
            "total_staff": total_staff,
            "total_courses": total_courses,
            "total_subjects": total_subjects,
            "total_sessions": total_sessions,
            "pending_student_leaves": pending_student_leaves,
            "pending_staff_leaves": pending_staff_leaves,
            "unreplied_feedbacks": unreplied_feedbacks,
            "course_summaries": course_summaries
        }

    def get_staff_summary(self, staff_id: str) -> dict:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' does not exist.")
        staff = self.staff_members[staff_id]
        staff_subjects = [self.subjects[sid] for sid in staff.subjects if sid in self.subjects]
        total_students = set()
        for subject in staff_subjects:
            if subject.course_id in self.courses:
                for sid in self.courses[subject.course_id].students:
                    total_students.add(sid)
        leave_summary = {
            "total": len(staff.leave_requests),
            "pending": 0,
            "approved": 0,
            "rejected": 0
        }
        for lid in staff.leave_requests:
            if lid in self.leave_requests:
                status = self.leave_requests[lid].status
                leave_summary[status] += 1
        attendance_taken = len([r for r in self.attendance_records.values()
                                 if r.staff_id == staff_id])
        return {
            "staff_id": staff_id,
            "name": f"{staff.first_name} {staff.last_name}",
            "subjects": [{"subject_id": s.subject_id, "name": s.name} for s in staff_subjects],
            "total_subjects": len(staff_subjects),
            "total_students": len(total_students),
            "attendance_sessions_taken": attendance_taken,
            "leave_summary": leave_summary,
            "total_feedbacks_sent": len(staff.feedbacks)
        }

    def get_student_summary(self, student_id: str) -> dict:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' does not exist.")
        student = self.students[student_id]
        attendance_summary = self.get_student_attendance(student_id)
        results = self.get_student_results(student_id)
        leave_summary = {
            "total": len(student.leave_requests),
            "pending": 0,
            "approved": 0,
            "rejected": 0
        }
        for lid in student.leave_requests:
            if lid in self.leave_requests:
                status = self.leave_requests[lid].status
                leave_summary[status] += 1
        subjects_enrolled = []
        if student.course_id and student.course_id in self.courses:
            course = self.courses[student.course_id]
            for sid in course.subjects:
                if sid in self.subjects:
                    subjects_enrolled.append({
                        "subject_id": sid,
                        "name": self.subjects[sid].name
                    })
        return {
            "student_id": student_id,
            "name": f"{student.first_name} {student.last_name}",
            "course_id": student.course_id,
            "session_id": student.session_id,
            "attendance": {
                "total": attendance_summary["total"],
                "present": attendance_summary["present"],
                "absent": attendance_summary["absent"],
                "percentage": (attendance_summary["present"] / attendance_summary["total"] * 100)
                if attendance_summary["total"] > 0 else 0
            },
            "results": [{"subject_id": r.subject_id, "total_marks": r.total_marks} for r in results],
            "leave_summary": leave_summary,
            "subjects_enrolled": subjects_enrolled,
            "total_feedbacks_sent": len(student.feedbacks)
        }

    def get_all_students(self) -> list:
        return list(self.students.values())

    def get_all_staff(self) -> list:
        return list(self.staff_members.values())

    def get_all_courses(self) -> list:
        return list(self.courses.values())

    def get_all_subjects(self) -> list:
        return list(self.subjects.values())

    def get_all_sessions(self) -> list:
        return list(self.sessions.values())

    def get_students_by_course(self, course_id: str) -> list:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' does not exist.")
        return [self.students[sid] for sid in self.courses[course_id].students
                if sid in self.students]

    def get_subjects_by_course(self, course_id: str) -> list:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' does not exist.")
        return [self.subjects[sid] for sid in self.courses[course_id].subjects
                if sid in self.subjects]

    def get_subjects_by_staff(self, staff_id: str) -> list:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' does not exist.")
        return [self.subjects[sid] for sid in self.staff_members[staff_id].subjects
                if sid in self.subjects]

    def get_attendance_records_by_subject(self, subject_id: str) -> list:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist.")
        return [r for r in self.attendance_records.values() if r.subject_id == subject_id]

    def get_attendance_records_by_staff(self, staff_id: str) -> list:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' does not exist.")
        return [r for r in self.attendance_records.values() if r.staff_id == staff_id]

    def __repr__(self):
        return (f"StudentManagementSystem("
                f"students={len(self.students)}, "
                f"staff={len(self.staff_members)}, "
                f"courses={len(self.courses)}, "
                f"subjects={len(self.subjects)})")


if __name__ == "__main__":
    sms = StudentManagementSystem()

    print("=== Student Management System Demo ===\n")

    course1 = sms.add_course("Computer Science")
    course2 = sms.add_course("Mathematics")
    print(f"Added courses: {course1}, {course2}")

    session1 = sms.add_session(2023, 2024)
    session2 = sms.add_session(2024, 2025)
    print(f"Added sessions: {session1}, {session2}")

    staff1 = sms.add_staff(
        username="john_doe",
        password="staff123",
        email="john@school.com",
        first_name="John",
        last_name="Doe",
        address="123 Main St",
        course_id=course1.course_id
    )
    print(f"Added staff: {staff1}")

    subject1 = sms.add_subject("Python Programming", course1.course_id, staff1.user_id)
    subject2 = sms.add_subject("Data Structures", course1.course_id, staff1.user_id)
    print(f"Added subjects: {subject1}, {subject2}")

    student1 = sms.add_student(
        username="alice_smith",
        password="student123",
        email="alice@school.com",
        first_name="Alice",
        last_name="Smith",
        address="456 Oak Ave",
        course_id=course1.course_id,
        session_id=session1.session_id
    )
    student2 = sms.add_student(
        username="bob_jones",
        password="student123",
        email="bob@school.com",
        first_name="Bob",
        last_name="Jones",
        address="789 Pine Rd",
        course_id=course1.course_id,
        session_id=session1.session_id
    )
    print(f"Added students: {student1}, {student2}")

    attendance = sms.take_attendance(
        subject_id=subject1.subject_id,
        staff_id=staff1.user_id,
        attendance_date=date.today(),
        session_id=session1.session_id,
        student_statuses={
            student1.user_id: True,
            student2.user_id: False
        }
    )
    print(f"Recorded attendance: {attendance}")

    result1 = sms.add_result(student1.user_id, subject1.subject_id, 85.0, 15.0)
    result2 = sms.add_result(student2.user_id, subject1.subject_id, 70.0, 12.0)
    print(f"Added results: {result1}, {result2}")

    leave1 = sms.apply_leave(
        user_id=student1.user_id,
        user_type="student",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 3),
        reason="Medical appointment"
    )
    print(f"Leave applied: {leave1}")

    sms.approve_leave(leave1.leave_id, "Approved. Get well soon!")
    print(f"Leave status: {leave1.status}, Reply: {leave1.admin_reply}")

    feedback1 = sms.send_feedback(
        user_id=student1.user_id,
        user_type="student",
        message="The Python course is excellent!"
    )
    print(f"Feedback sent: {feedback1}")

    sms.reply_feedback(feedback1.feedback_id, "Thank you for your feedback!")
    print(f"Feedback replied: {feedback1.is_replied}, Reply: {feedback1.reply}")

    print("\n=== Admin Summary ===")
    summary = sms.get_admin_summary()
    for key, value in summary.items():
        if key != "course_summaries":
            print(f"  {key}: {value}")

    print("\n=== Student Summary ===")
    student_summary = sms.get_student_summary(student1.user_id)
    for key, value in student_summary.items():
        print(f"  {key}: {value}")

    print("\n=== Staff Summary ===")
    staff_summary = sms.get_staff_summary(staff1.user_id)
    for key, value in staff_summary.items():
        print(f"  {key}: {value}")

    user = sms.authenticate("alice_smith", "student123")
    print(f"\nAuthentication test: {user}")

    user_fail = sms.authenticate("alice_smith", "wrongpassword")
    print(f"Failed authentication: {user_fail}")