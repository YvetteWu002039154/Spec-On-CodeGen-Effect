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

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"Admin(id={self.user_id}, name={self.get_full_name()})"


class Staff(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 first_name: str, last_name: str, address: str):
        super().__init__(user_id, username, password, email, "staff")
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.subjects: list = []
        self.leave_applications: list = []
        self.feedbacks: list = []
        self.attendance_records: list = []

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"Staff(id={self.user_id}, name={self.get_full_name()})"


class Student(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 first_name: str, last_name: str, address: str,
                 course_id: str, session_id: str, gender: str):
        super().__init__(user_id, username, password, email, "student")
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.course_id = course_id
        self.session_id = session_id
        self.gender = gender
        self.leave_applications: list = []
        self.feedbacks: list = []
        self.attendance_records: list = []
        self.results: list = []

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"Student(id={self.user_id}, name={self.get_full_name()})"


class Course:
    def __init__(self, course_id: str, name: str, created_at: Optional[datetime] = None):
        self.course_id = course_id
        self.name = name
        self.created_at = created_at or datetime.now()
        self.subjects: list = []
        self.students: list = []

    def __repr__(self):
        return f"Course(id={self.course_id}, name={self.name})"


class Subject:
    def __init__(self, subject_id: str, name: str, course_id: str, staff_id: str,
                 created_at: Optional[datetime] = None):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id
        self.created_at = created_at or datetime.now()
        self.attendance_records: list = []
        self.results: list = []

    def __repr__(self):
        return f"Subject(id={self.subject_id}, name={self.name})"


class Session:
    def __init__(self, session_id: str, start_year: int, end_year: int):
        if end_year <= start_year:
            raise ValueError("End year must be greater than start year")
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year
        self.students: list = []

    def get_session_name(self) -> str:
        return f"{self.start_year}-{self.end_year}"

    def __repr__(self):
        return f"Session(id={self.session_id}, years={self.get_session_name()})"


class Attendance:
    def __init__(self, attendance_id: str, subject_id: str, staff_id: str,
                 attendance_date: date, session_id: str):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.staff_id = staff_id
        self.attendance_date = attendance_date
        self.session_id = session_id
        self.created_at = datetime.now()
        self.attendance_reports: list = []

    def __repr__(self):
        return f"Attendance(id={self.attendance_id}, date={self.attendance_date})"


class AttendanceReport:
    def __init__(self, report_id: str, student_id: str, attendance_id: str, status: bool):
        self.report_id = report_id
        self.student_id = student_id
        self.attendance_id = attendance_id
        self.status = status
        self.created_at = datetime.now()

    def __repr__(self):
        return f"AttendanceReport(student={self.student_id}, status={'Present' if self.status else 'Absent'})"


class LeaveApplication:
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

    def __init__(self, leave_id: str, applicant_id: str, applicant_type: str,
                 start_date: date, end_date: date, message: str):
        if end_date < start_date:
            raise ValueError("End date cannot be before start date")
        self.leave_id = leave_id
        self.applicant_id = applicant_id
        self.applicant_type = applicant_type
        self.start_date = start_date
        self.end_date = end_date
        self.message = message
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

    def get_duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def __repr__(self):
        return f"LeaveApplication(id={self.leave_id}, status={self.status})"


class Feedback:
    def __init__(self, feedback_id: str, sender_id: str, sender_type: str, message: str):
        self.feedback_id = feedback_id
        self.sender_id = sender_id
        self.sender_type = sender_type
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
        return f"Feedback(id={self.feedback_id}, sender={self.sender_id}, replied={self.is_replied})"


class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 exam_score: float, assignment_score: float):
        if not (0 <= exam_score <= 100):
            raise ValueError("Exam score must be between 0 and 100")
        if not (0 <= assignment_score <= 100):
            raise ValueError("Assignment score must be between 0 and 100")
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.exam_score = exam_score
        self.assignment_score = assignment_score
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def get_total_score(self) -> float:
        return self.exam_score + self.assignment_score

    def get_grade(self) -> str:
        total = self.get_total_score()
        if total >= 160:
            return "A"
        elif total >= 140:
            return "B"
        elif total >= 120:
            return "C"
        elif total >= 100:
            return "D"
        else:
            return "F"

    def update_scores(self, exam_score: float, assignment_score: float):
        if not (0 <= exam_score <= 100):
            raise ValueError("Exam score must be between 0 and 100")
        if not (0 <= assignment_score <= 100):
            raise ValueError("Assignment score must be between 0 and 100")
        self.exam_score = exam_score
        self.assignment_score = assignment_score
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Result(student={self.student_id}, subject={self.subject_id}, total={self.get_total_score()})"


class StudentManagementSystem:
    def __init__(self):
        self.users: dict = {}
        self.admins: dict = {}
        self.staff_members: dict = {}
        self.students: dict = {}
        self.courses: dict = {}
        self.subjects: dict = {}
        self.sessions: dict = {}
        self.attendances: dict = {}
        self.attendance_reports: dict = {}
        self.leave_applications: dict = {}
        self.feedbacks: dict = {}
        self.results: dict = {}
        self._current_user: Optional[User] = None

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def login(self, username: str, password: str) -> Optional[User]:
        for user in self.users.values():
            if user.username == username and user.verify_password(password):
                self._current_user = user
                return user
        return None

    def logout(self):
        self._current_user = None

    def get_current_user(self) -> Optional[User]:
        return self._current_user

    def add_admin(self, username: str, password: str, email: str,
                  first_name: str, last_name: str) -> Admin:
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists")
            if user.email == email:
                raise ValueError(f"Email '{email}' already exists")
        admin_id = self._generate_id()
        admin = Admin(admin_id, username, password, email, first_name, last_name)
        self.users[admin_id] = admin
        self.admins[admin_id] = admin
        return admin

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str, address: str) -> Staff:
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists")
            if user.email == email:
                raise ValueError(f"Email '{email}' already exists")
        staff_id = self._generate_id()
        staff = Staff(staff_id, username, password, email, first_name, last_name, address)
        self.users[staff_id] = staff
        self.staff_members[staff_id] = staff
        return staff

    def update_staff(self, staff_id: str, email: Optional[str] = None,
                     first_name: Optional[str] = None, last_name: Optional[str] = None,
                     address: Optional[str] = None, password: Optional[str] = None) -> Staff:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' not found")
        staff = self.staff_members[staff_id]
        if email:
            for user in self.users.values():
                if user.email == email and user.user_id != staff_id:
                    raise ValueError(f"Email '{email}' already exists")
            staff.email = email
        if first_name:
            staff.first_name = first_name
        if last_name:
            staff.last_name = last_name
        if address:
            staff.address = address
        if password:
            staff.update_password(password)
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' not found")
        staff = self.staff_members[staff_id]
        for subject in self.subjects.values():
            if subject.staff_id == staff_id:
                raise ValueError(f"Cannot delete staff assigned to subjects")
        del self.staff_members[staff_id]
        del self.users[staff_id]
        return True

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str, address: str,
                    course_id: str, session_id: str, gender: str) -> Student:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists")
            if user.email == email:
                raise ValueError(f"Email '{email}' already exists")
        student_id = self._generate_id()
        student = Student(student_id, username, password, email, first_name, last_name,
                          address, course_id, session_id, gender)
        self.users[student_id] = student
        self.students[student_id] = student
        self.courses[course_id].students.append(student_id)
        self.sessions[session_id].students.append(student_id)
        return student

    def update_student(self, student_id: str, email: Optional[str] = None,
                       first_name: Optional[str] = None, last_name: Optional[str] = None,
                       address: Optional[str] = None, course_id: Optional[str] = None,
                       session_id: Optional[str] = None, gender: Optional[str] = None,
                       password: Optional[str] = None) -> Student:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' not found")
        student = self.students[student_id]
        if email:
            for user in self.users.values():
                if user.email == email and user.user_id != student_id:
                    raise ValueError(f"Email '{email}' already exists")
            student.email = email
        if first_name:
            student.first_name = first_name
        if last_name:
            student.last_name = last_name
        if address:
            student.address = address
        if course_id:
            if course_id not in self.courses:
                raise ValueError(f"Course with id '{course_id}' not found")
            old_course = self.courses.get(student.course_id)
            if old_course and student_id in old_course.students:
                old_course.students.remove(student_id)
            student.course_id = course_id
            self.courses[course_id].students.append(student_id)
        if session_id:
            if session_id not in self.sessions:
                raise ValueError(f"Session with id '{session_id}' not found")
            old_session = self.sessions.get(student.session_id)
            if old_session and student_id in old_session.students:
                old_session.students.remove(student_id)
            student.session_id = session_id
            self.sessions[session_id].students.append(student_id)
        if gender:
            student.gender = gender
        if password:
            student.update_password(password)
        return student

    def delete_student(self, student_id: str) -> bool:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' not found")
        student = self.students[student_id]
        course = self.courses.get(student.course_id)
        if course and student_id in course.students:
            course.students.remove(student_id)
        session = self.sessions.get(student.session_id)
        if session and student_id in session.students:
            session.students.remove(student_id)
        del self.students[student_id]
        del self.users[student_id]
        return True

    def add_course(self, name: str) -> Course:
        for course in self.courses.values():
            if course.name.lower() == name.lower():
                raise ValueError(f"Course '{name}' already exists")
        course_id = self._generate_id()
        course = Course(course_id, name)
        self.courses[course_id] = course
        return course

    def update_course(self, course_id: str, name: str) -> Course:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        for cid, course in self.courses.items():
            if course.name.lower() == name.lower() and cid != course_id:
                raise ValueError(f"Course '{name}' already exists")
        self.courses[course_id].name = name
        return self.courses[course_id]

    def delete_course(self, course_id: str) -> bool:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        course = self.courses[course_id]
        if course.students:
            raise ValueError("Cannot delete course with enrolled students")
        if course.subjects:
            raise ValueError("Cannot delete course with associated subjects")
        del self.courses[course_id]
        return True

    def add_subject(self, name: str, course_id: str, staff_id: str) -> Subject:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' not found")
        subject_id = self._generate_id()
        subject = Subject(subject_id, name, course_id, staff_id)
        self.subjects[subject_id] = subject
        self.courses[course_id].subjects.append(subject_id)
        self.staff_members[staff_id].subjects.append(subject_id)
        return subject

    def update_subject(self, subject_id: str, name: Optional[str] = None,
                       course_id: Optional[str] = None, staff_id: Optional[str] = None) -> Subject:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        subject = self.subjects[subject_id]
        if name:
            subject.name = name
        if course_id:
            if course_id not in self.courses:
                raise ValueError(f"Course with id '{course_id}' not found")
            old_course = self.courses.get(subject.course_id)
            if old_course and subject_id in old_course.subjects:
                old_course.subjects.remove(subject_id)
            subject.course_id = course_id
            self.courses[course_id].subjects.append(subject_id)
        if staff_id:
            if staff_id not in self.staff_members:
                raise ValueError(f"Staff with id '{staff_id}' not found")
            old_staff = self.staff_members.get(subject.staff_id)
            if old_staff and subject_id in old_staff.subjects:
                old_staff.subjects.remove(subject_id)
            subject.staff_id = staff_id
            self.staff_members[staff_id].subjects.append(subject_id)
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        subject = self.subjects[subject_id]
        course = self.courses.get(subject.course_id)
        if course and subject_id in course.subjects:
            course.subjects.remove(subject_id)
        staff = self.staff_members.get(subject.staff_id)
        if staff and subject_id in staff.subjects:
            staff.subjects.remove(subject_id)
        del self.subjects[subject_id]
        return True

    def add_session(self, start_year: int, end_year: int) -> Session:
        for session in self.sessions.values():
            if session.start_year == start_year and session.end_year == end_year:
                raise ValueError(f"Session {start_year}-{end_year} already exists")
        session_id = self._generate_id()
        session = Session(session_id, start_year, end_year)
        self.sessions[session_id] = session
        return session

    def update_session(self, session_id: str, start_year: int, end_year: int) -> Session:
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        for sid, session in self.sessions.items():
            if session.start_year == start_year and session.end_year == end_year and sid != session_id:
                raise ValueError(f"Session {start_year}-{end_year} already exists")
        session = self.sessions[session_id]
        if end_year <= start_year:
            raise ValueError("End year must be greater than start year")
        session.start_year = start_year
        session.end_year = end_year
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        session = self.sessions[session_id]
        if session.students:
            raise ValueError("Cannot delete session with enrolled students")
        del self.sessions[session_id]
        return True

    def take_attendance(self, subject_id: str, staff_id: str, session_id: str,
                        attendance_date: date, student_statuses: dict) -> Attendance:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' not found")
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        subject = self.subjects[subject_id]
        if subject.staff_id != staff_id:
            raise ValueError("Staff is not assigned to this subject")
        attendance_id = self._generate_id()
        attendance = Attendance(attendance_id, subject_id, staff_id, attendance_date, session_id)
        self.attendances[attendance_id] = attendance
        for student_id, status in student_statuses.items():
            if student_id not in self.students:
                raise ValueError(f"Student with id '{student_id}' not found")
            report_id = self._generate_id()
            report = AttendanceReport(report_id, student_id, attendance_id, status)
            self.attendance_reports[report_id] = report
            attendance.attendance_reports.append(report_id)
            self.students[student_id].attendance_records.append(report_id)
        subject.attendance_records.append(attendance_id)
        self.staff_members[staff_id].attendance_records.append(attendance_id)
        return attendance

    def update_attendance(self, attendance_id: str, student_statuses: dict) -> Attendance:
        if attendance_id not in self.attendances:
            raise ValueError(f"Attendance with id '{attendance_id}' not found")
        attendance = self.attendances[attendance_id]
        existing_reports = {}
        for report_id in attendance.attendance_reports:
            report = self.attendance_reports[report_id]
            existing_reports[report.student_id] = report
        for student_id, status in student_statuses.items():
            if student_id not in self.students:
                raise ValueError(f"Student with id '{student_id}' not found")
            if student_id in existing_reports:
                existing_reports[student_id].status = status
            else:
                report_id = self._generate_id()
                report = AttendanceReport(report_id, student_id, attendance_id, status)
                self.attendance_reports[report_id] = report
                attendance.attendance_reports.append(report_id)
                self.students[student_id].attendance_records.append(report_id)
        return attendance

    def get_student_attendance(self, student_id: str) -> list:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' not found")
        student = self.students[student_id]
        result = []
        for report_id in student.attendance_records:
            report = self.attendance_reports.get(report_id)
            if report:
                attendance = self.attendances.get(report.attendance_id)
                subject = self.subjects.get(attendance.subject_id) if attendance else None
                result.append({
                    "report_id": report_id,
                    "attendance_id": report.attendance_id,
                    "subject_name": subject.name if subject else "Unknown",
                    "date": attendance.attendance_date if attendance else None,
                    "status": "Present" if report.status else "Absent"
                })
        return result

    def get_attendance_by_subject(self, subject_id: str) -> list:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        subject = self.subjects[subject_id]
        result = []
        for attendance_id in subject.attendance_records:
            attendance = self.attendances.get(attendance_id)
            if attendance:
                reports = []
                for report_id in attendance.attendance_reports:
                    report = self.attendance_reports.get(report_id)
                    if report:
                        student = self.students.get(report.student_id)
                        reports.append({
                            "student_name": student.get_full_name() if student else "Unknown",
                            "student_id": report.student_id,
                            "status": "Present" if report.status else "Absent"
                        })
                result.append({
                    "attendance_id": attendance_id,
                    "date": attendance.attendance_date,
                    "reports": reports
                })
        return result

    def add_result(self, student_id: str, subject_id: str,
                   exam_score: float, assignment_score: float) -> Result:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' not found")
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        for result in self.results.values():
            if result.student_id == student_id and result.subject_id == subject_id:
                raise ValueError("Result already exists for this student and subject. Use update_result instead.")
        result_id = self._generate_id()
        result = Result(result_id, student_id, subject_id, exam_score, assignment_score)
        self.results[result_id] = result
        self.students[student_id].results.append(result_id)
        self.subjects[subject_id].results.append(result_id)
        return result

    def update_result(self, student_id: str, subject_id: str,
                      exam_score: float, assignment_score: float) -> Result:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' not found")
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        for result in self.results.values():
            if result.student_id == student_id and result.subject_id == subject_id:
                result.update_scores(exam_score, assignment_score)
                return result
        raise ValueError("Result not found for this student and subject. Use add_result instead.")

    def get_student_results(self, student_id: str) -> list:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' not found")
        student = self.students[student_id]
        result_list = []
        for result_id in student.results:
            result = self.results.get(result_id)
            if result:
                subject = self.subjects.get(result.subject_id)
                result_list.append({
                    "result_id": result_id,
                    "subject_name": subject.name if subject else "Unknown",
                    "exam_score": result.exam_score,
                    "assignment_score": result.assignment_score,
                    "total_score": result.get_total_score(),
                    "grade": result.get_grade()
                })
        return result_list

    def apply_leave(self, applicant_id: str, applicant_type: str,
                    start_date: date, end_date: date, message: str) -> LeaveApplication:
        if applicant_type == "student" and applicant_id not in self.students:
            raise ValueError(f"Student with id '{applicant_id}' not found")
        if applicant_type == "staff" and applicant_id not in self.staff_members:
            raise ValueError(f"Staff with id '{applicant_id}' not found")
        leave_id = self._generate_id()
        leave = LeaveApplication(leave_id, applicant_id, applicant_type, start_date, end_date, message)
        self.leave_applications[leave_id] = leave
        if applicant_type == "student":
            self.students[applicant_id].leave_applications.append(leave_id)
        elif applicant_type == "staff":
            self.staff_members[applicant_id].leave_applications.append(leave_id)
        return leave

    def approve_leave(self, leave_id: str, reply: str = "") -> LeaveApplication:
        if leave_id not in self.leave_applications:
            raise ValueError(f"Leave application with id '{leave_id}' not found")
        leave = self.leave_applications[leave_id]
        if leave.status != LeaveApplication.PENDING:
            raise ValueError("Leave application is not in pending status")
        leave.approve(reply)
        return leave

    def reject_leave(self, leave_id: str, reply: str = "") -> LeaveApplication:
        if leave_id not in self.leave_applications:
            raise ValueError(f"Leave application with id '{leave_id}' not found")
        leave = self.leave_applications[leave_id]
        if leave.status != LeaveApplication.PENDING:
            raise ValueError("Leave application is not in pending status")
        leave.reject(reply)
        return leave

    def get_leave_applications(self, applicant_id: Optional[str] = None,
                                applicant_type: Optional[str] = None,
                                status: Optional[str] = None) -> list:
        result = []
        for leave in self.leave_applications.values():
            if applicant_id and leave.applicant_id != applicant_id:
                continue
            if applicant_type and leave.applicant_type != applicant_type:
                continue
            if status and leave.status != status:
                continue
            result.append(leave)
        return result

    def send_feedback(self, sender_id: str, sender_type: str, message: str) -> Feedback:
        if sender_type == "student" and sender_id not in self.students:
            raise ValueError(f"Student with id '{sender_id}' not found")
        if sender_type == "staff" and sender_id not in self.staff_members:
            raise ValueError(f"Staff with id '{sender_id}' not found")
        feedback_id = self._generate_id()
        feedback = Feedback(feedback_id, sender_id, sender_type, message)
        self.feedbacks[feedback_id] = feedback
        if sender_type == "student":
            self.students[sender_id].feedbacks.append(feedback_id)
        elif sender_type == "staff":
            self.staff_members[sender_id].feedbacks.append(feedback_id)
        return feedback

    def reply_feedback(self, feedback_id: str, reply: str) -> Feedback:
        if feedback_id not in self.feedbacks:
            raise ValueError(f"Feedback with id '{feedback_id}' not found")
        feedback = self.feedbacks[feedback_id]
        feedback.add_reply(reply)
        return feedback

    def get_feedbacks(self, sender_id: Optional[str] = None,
                      sender_type: Optional[str] = None,
                      is_replied: Optional[bool] = None) -> list:
        result = []
        for feedback in self.feedbacks.values():
            if sender_id and feedback.sender_id != sender_id:
                continue
            if sender_type and feedback.sender_type != sender_type:
                continue
            if is_replied is not None and feedback.is_replied != is_replied:
                continue
            result.append(feedback)
        return result

    def get_admin_summary(self) -> dict:
        total_students = len(self.students)
        total_staff = len(self.staff_members)
        total_courses = len(self.courses)
        total_subjects = len(self.subjects)
        total_sessions = len(self.sessions)
        pending_student_leaves = len([l for l in self.leave_applications.values()
                                       if l.applicant_type == "student" and l.status == LeaveApplication.PENDING])
        pending_staff_leaves = len([l for l in self.leave_applications.values()
                                     if l.applicant_type == "staff" and l.status == LeaveApplication.PENDING])
        unreplied_feedbacks = len([f for f in self.feedbacks.values() if not f.is_replied])
        total_attendance_records = len(self.attendances)
        student_gender_distribution = {}
        for student in self.students.values():
            gender = student.gender
            student_gender_distribution[gender] = student_gender_distribution.get(gender, 0) + 1
        course_enrollment = {}
        for course_id, course in self.courses.items():
            course_enrollment[course.name] = len(course.students)
        subject_per_course = {}
        for course_id, course in self.courses.items():
            subject_per_course[course.name] = len(course.subjects)
        return {
            "total_students": total_students,
            "total_staff": total_staff,
            "total_courses": total_courses,
            "total_subjects": total_subjects,
            "total_sessions": total_sessions,
            "pending_student_leaves": pending_student_leaves,
            "pending_staff_leaves": pending_staff_leaves,
            "unreplied_feedbacks": unreplied_feedbacks,
            "total_attendance_records": total_attendance_records,
            "student_gender_distribution": student_gender_distribution,
            "course_enrollment": course_enrollment,
            "subject_per_course": subject_per_course
        }

    def get_staff_summary(self, staff_id: str) -> dict:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' not found")
        staff = self.staff_members[staff_id]
        assigned_subjects = []
        total_students_taught = set()
        for subject_id in staff.subjects:
            subject = self.subjects.get(subject_id)
            if subject:
                course = self.courses.get(subject.course_id)
                if course:
                    for student_id in course.students:
                        total_students_taught.add(student_id)
                assigned_subjects.append({
                    "subject_id": subject_id,
                    "subject_name": subject.name,
                    "course_name": course.name if course else "Unknown",
                    "attendance_count": len(subject.attendance_records)
                })
        leave_status = {
            "pending": 0,
            "approved": 0,
            "rejected": 0
        }
        for leave_id in staff.leave_applications:
            leave = self.leave_applications.get(leave_id)
            if leave:
                if leave.status == LeaveApplication.PENDING:
                    leave_status["pending"] += 1
                elif leave.status == LeaveApplication.APPROVED:
                    leave_status["approved"] += 1
                elif leave.status == LeaveApplication.REJECTED:
                    leave_status["rejected"] += 1
        feedback_count = len(staff.feedbacks)
        replied_feedbacks = len([fid for fid in staff.feedbacks
                                  if self.feedbacks.get(fid) and self.feedbacks[fid].is_replied])
        return {
            "staff_name": staff.get_full_name(),
            "total_subjects": len(staff.subjects),
            "assigned_subjects": assigned_subjects,
            "total_students_taught": len(total_students_taught),
            "total_attendance_taken": len(staff.attendance_records),
            "leave_status": leave_status,
            "total_feedbacks_sent": feedback_count,
            "feedbacks_replied": replied_feedbacks
        }

    def get_student_summary(self, student_id: str) -> dict:
        if student_id not in self.students:
            raise ValueError(f"Student with id '{student_id}' not found")
        student = self.students[student_id]
        course = self.courses.get(student.course_id)
        session = self.sessions.get(student.session_id)
        total_present = 0
        total_absent = 0
        for report_id in student.attendance_records:
            report = self.attendance_reports.get(report_id)
            if report:
                if report.status:
                    total_present += 1
                else:
                    total_absent += 1
        total_attendance = total_present + total_absent
        attendance_percentage = (total_present / total_attendance * 100) if total_attendance > 0 else 0
        results_summary = []
        for result_id in student.results:
            result = self.results.get(result_id)
            if result:
                subject = self.subjects.get(result.subject_id)
                results_summary.append({
                    "subject_name": subject.name if subject else "Unknown",
                    "exam_score": result.exam_score,
                    "assignment_score": result.assignment_score,
                    "total_score": result.get_total_score(),
                    "grade": result.get_grade()
                })
        leave_status = {
            "pending": 0,
            "approved": 0,
            "rejected": 0
        }
        for leave_id in student.leave_applications:
            leave = self.leave_applications.get(leave_id)
            if leave:
                if leave.status == LeaveApplication.PENDING:
                    leave_status["pending"] += 1
                elif leave.status == LeaveApplication.APPROVED:
                    leave_status["approved"] += 1
                elif leave.status == LeaveApplication.REJECTED:
                    leave_status["rejected"] += 1
        feedback_count = len(student.feedbacks)
        replied_feedbacks = len([fid for fid in student.feedbacks
                                  if self.feedbacks.get(fid) and self.feedbacks[fid].is_replied])
        return {
            "student_name": student.get_full_name(),
            "course_name": course.name if course else "Unknown",
            "session": session.get_session_name() if session else "Unknown",
            "total_present": total_present,
            "total_absent": total_absent,
            "attendance_percentage": round(attendance_percentage, 2),
            "results": results_summary,
            "leave_status": leave_status,
            "total_feedbacks_sent": feedback_count,
            "feedbacks_replied": replied_feedbacks
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
            raise ValueError(f"Course with id '{course_id}' not found")
        course = self.courses[course_id]
        return [self.students[sid] for sid in course.students if sid in self.students]

    def get_subjects_by_course(self, course_id: str) -> list:
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        course = self.courses[course_id]
        return [self.subjects[sid] for sid in course.subjects if sid in self.subjects]

    def get_subjects_by_staff(self, staff_id: str) -> list:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id '{staff_id}' not found")
        staff = self.staff_members[staff_id]
        return [self.subjects[sid] for sid in staff.subjects if sid in self.subjects]

    def get_students_by_session(self, session_id: str) -> list:
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        session = self.sessions[session_id]
        return [self.students[sid] for sid in session.students if sid in self.students]

    def get_staff_performance_summary(self) -> list:
        performance = []
        for staff_id, staff in self.staff_members.items():
            total_attendance_taken = len(staff.attendance_records)
            total_subjects = len(staff.subjects)
            performance.append({
                "staff_id": staff_id,
                "staff_name": staff.get_full_name(),
                "total_subjects": total_subjects,
                "total_attendance_taken": total_attendance_taken
            })
        return performance

    def get_student_performance_summary(self) -> list:
        performance = []
        for student_id, student in self.students.items():
            total_present = sum(1 for rid in student.attendance_records
                                if self.attendance_reports.get(rid) and self.attendance_reports[rid].status)
            total_attendance = len(student.attendance_records)
            attendance_pct = (total_present / total_attendance * 100) if total_attendance > 0 else 0
            avg_score = 0
            if student.results:
                scores = [self.results[rid].get_total_score() for rid in student.results if rid in self.results]
                avg_score = sum(scores) / len(scores) if scores else 0
            course = self.courses.get(student.course_id)
            performance.append({
                "student_id": student_id,
                "student_name": student.get_full_name(),
                "course_name": course.name if course else "Unknown",
                "attendance_percentage": round(attendance_pct, 2),
                "average_score": round(avg_score, 2)
            })
        return performance


def main():
    sms = StudentManagementSystem()

    admin = sms.add_admin(
        username="admin1",
        password="admin123",
        email="admin@school.com",
        first_name="John",
        last_name="Doe"
    )
    print(f"Created admin: {admin}")

    staff1 = sms.add_staff(
        username="staff1",
        password="staff123",
        email="staff1@school.com",
        first_name="Jane",
        last_name="Smith",
        address="123 Main St"
    )
    print(f"Created staff: {staff1}")

    course1 = sms.add_course("Computer Science")
    course2 = sms.add_course("Mathematics")
    print(f"Created courses: {course1}, {course2}")

    session1 = sms.add_session(2023, 2024)
    print(f"Created session: {session1}")

    subject1 = sms.add_subject("Python Programming", course1.course_id, staff1.user_id)
    subject2 = sms.add_subject("Data Structures", course1.course_id, staff1.user_id)
    print(f"Created subjects: {subject1}, {subject2}")

    student1 = sms.add_student(
        username="student1",
        password="student123",
        email="student1@school.com",
        first_name="Alice",
        last_name="Johnson",
        address="456 Oak Ave",
        course_id=course1.course_id,
        session_id=session1.session_id,
        gender="Female"
    )
    student2 = sms.add_student(
        username="student2",
        password="student123",
        email="student2@school.com",
        first_name="Bob",
        last_name="Williams",
        address="789 Pine Rd",
        course_id=course1.course_id,
        session_id=session1.session_id,
        gender="Male"
    )
    print(f"Created students: {student1}, {student2}")

    attendance = sms.take_attendance(
        subject_id=subject1.subject_id,
        staff_id=staff1.user_id,
        session_id=session1.session_id,
        attendance_date=date.today(),
        student_statuses={
            student1.user_id: True,
            student2.user_id: False
        }
    )
    print(f"Recorded attendance: {attendance}")

    result1 = sms.add_result(student1.user_id, subject1.subject_id, 85.0, 90.0)
    result2 = sms.add_result(student2.user_id, subject1.subject_id, 70.0, 75.0)
    print(f"Added results: {result1}, {result2}")

    leave1 = sms.apply_leave(
        applicant_id=student1.user_id,
        applicant_type="student",
        start_date=date(2024, 1, 15),
        end_date=date(2024, 1, 17),
        message="Medical appointment"
    )
    print(f"Applied leave: {leave1}")

    approved_leave = sms.approve_leave(leave1.leave_id, "Approved. Get well soon!")
    print(f"Approved leave: {approved_leave}")

    feedback1 = sms.send_feedback(
        sender_id=student1.user_id,
        sender_type="student",
        message="The course material is very helpful!"
    )
    print(f"Sent feedback: {feedback1}")

    replied_feedback = sms.reply_feedback(feedback1.feedback_id, "Thank you for your feedback!")
    print(f"Replied feedback: {replied_feedback}")

    admin_summary = sms.get_admin_summary()
    print(f"\nAdmin Summary:")
    for key, value in admin_summary.items():
        print(f"  {key}: {value}")

    staff_summary = sms.get_staff_summary(staff1.user_id)
    print(f"\nStaff Summary for {staff1.get_full_name()}:")
    for key, value in staff_summary.items():
        print(f"  {key}: {value}")

    student_summary = sms.get_student_summary(student1.user_id)
    print(f"\nStudent Summary for {student1.get_full_name()}:")
    for key, value in student_summary.items():
        print(f"  {key}: {value}")

    student_attendance = sms.get_student_attendance(student1.user_id)
    print(f"\nAttendance for {student1.get_full_name()}: {student_attendance}")

    student_results = sms.get_student_results(student1.user_id)
    print(f"\nResults for {student1.get_full_name()}: {student_results}")

    user = sms.login("admin1", "admin123")
    print(f"\nLogged in as: {user}")
    sms.logout()
    print(f"Logged out. Current user: {sms.get_current_user()}")


if __name__ == "__main__":
    main()