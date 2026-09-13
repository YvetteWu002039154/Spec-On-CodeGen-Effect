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
                 first_name: str, last_name: str, address: str, gender: str,
                 course_id: Optional[str] = None):
        super().__init__(user_id, username, password, email, "staff")
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.gender = gender
        self.course_id = course_id
        self.profile_pic = None

    def __repr__(self):
        return f"Staff(id={self.user_id}, name={self.first_name} {self.last_name})"


class Student(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 first_name: str, last_name: str, address: str, gender: str,
                 course_id: Optional[str] = None, session_id: Optional[str] = None):
        super().__init__(user_id, username, password, email, "student")
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.gender = gender
        self.course_id = course_id
        self.session_id = session_id
        self.profile_pic = None

    def __repr__(self):
        return f"Student(id={self.user_id}, name={self.first_name} {self.last_name})"


class Course:
    def __init__(self, course_id: str, name: str):
        self.course_id = course_id
        self.name = name
        self.created_at = datetime.now()

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

    def __repr__(self):
        return f"Session(id={self.session_id}, {self.start_year}-{self.end_year})"


class Attendance:
    def __init__(self, attendance_id: str, subject_id: str, staff_id: str,
                 session_id: str, attendance_date: date):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.staff_id = staff_id
        self.session_id = session_id
        self.attendance_date = attendance_date
        self.created_at = datetime.now()

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
        return f"AttendanceReport(student={self.student_id}, status={self.status})"


class LeaveReport:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    def __init__(self, leave_id: str, user_id: str, user_type: str,
                 leave_date: str, leave_message: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.user_type = user_type
        self.leave_date = leave_date
        self.leave_message = leave_message
        self.status = self.PENDING
        self.created_at = datetime.now()
        self.admin_reply = None
        self.replied_at = None

    def approve(self, reply: str = ""):
        self.status = self.APPROVED
        self.admin_reply = reply
        self.replied_at = datetime.now()

    def reject(self, reply: str = ""):
        self.status = self.REJECTED
        self.admin_reply = reply
        self.replied_at = datetime.now()

    def __repr__(self):
        return f"LeaveReport(id={self.leave_id}, user={self.user_id}, status={self.status})"


class FeedbackReport:
    def __init__(self, feedback_id: str, user_id: str, user_type: str, feedback: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.user_type = user_type
        self.feedback = feedback
        self.reply = None
        self.created_at = datetime.now()
        self.replied_at = None

    def add_reply(self, reply: str):
        self.reply = reply
        self.replied_at = datetime.now()

    def __repr__(self):
        return f"FeedbackReport(id={self.feedback_id}, user={self.user_id})"


class StudentResult:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 session_id: str, exam_marks: float, assignment_marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @property
    def total_marks(self) -> float:
        return self.exam_marks + self.assignment_marks

    def update(self, exam_marks: float, assignment_marks: float):
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"StudentResult(student={self.student_id}, subject={self.subject_id}, total={self.total_marks})"


class StudentManagementSystem:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._courses: dict[str, Course] = {}
        self._subjects: dict[str, Subject] = {}
        self._sessions: dict[str, Session] = {}
        self._attendances: dict[str, Attendance] = {}
        self._attendance_reports: dict[str, AttendanceReport] = {}
        self._leave_reports: dict[str, LeaveReport] = {}
        self._feedback_reports: dict[str, FeedbackReport] = {}
        self._student_results: dict[str, StudentResult] = {}
        self._current_user: Optional[User] = None
        self._initialize_default_admin()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _initialize_default_admin(self):
        admin = Admin(
            user_id=self._generate_id(),
            username="admin",
            password="admin123",
            email="admin@sms.com",
            first_name="System",
            last_name="Admin"
        )
        self._users[admin.user_id] = admin

    def login(self, username: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username and user.verify_password(password) and user.is_active:
                self._current_user = user
                return user
        return None

    def logout(self):
        self._current_user = None

    def get_current_user(self) -> Optional[User]:
        return self._current_user

    def _require_role(self, *roles: str):
        if self._current_user is None:
            raise PermissionError("No user is logged in.")
        if self._current_user.role not in roles:
            raise PermissionError(f"Access denied. Required roles: {roles}")

    # ==================== Admin: Staff Management ====================

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str, address: str,
                  gender: str, course_id: Optional[str] = None) -> Staff:
        self._require_role("admin")
        if any(u.username == username for u in self._users.values()):
            raise ValueError(f"Username '{username}' already exists.")
        if any(u.email == email for u in self._users.values()):
            raise ValueError(f"Email '{email}' already exists.")
        if course_id and course_id not in self._courses:
            raise ValueError(f"Course '{course_id}' not found.")
        staff = Staff(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address,
            gender=gender,
            course_id=course_id
        )
        self._users[staff.user_id] = staff
        return staff

    def update_staff(self, staff_id: str, first_name: Optional[str] = None,
                     last_name: Optional[str] = None, address: Optional[str] = None,
                     gender: Optional[str] = None, course_id: Optional[str] = None,
                     email: Optional[str] = None, password: Optional[str] = None) -> Staff:
        self._require_role("admin")
        staff = self._get_staff_by_id(staff_id)
        if first_name:
            staff.first_name = first_name
        if last_name:
            staff.last_name = last_name
        if address:
            staff.address = address
        if gender:
            staff.gender = gender
        if course_id:
            if course_id not in self._courses:
                raise ValueError(f"Course '{course_id}' not found.")
            staff.course_id = course_id
        if email:
            if any(u.email == email and u.user_id != staff_id for u in self._users.values()):
                raise ValueError(f"Email '{email}' already exists.")
            staff.email = email
        if password:
            staff.update_password(password)
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        self._require_role("admin")
        staff = self._get_staff_by_id(staff_id)
        del self._users[staff_id]
        return True

    def get_all_staff(self) -> list[Staff]:
        self._require_role("admin")
        return [u for u in self._users.values() if isinstance(u, Staff)]

    def _get_staff_by_id(self, staff_id: str) -> Staff:
        user = self._users.get(staff_id)
        if not user or not isinstance(user, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found.")
        return user

    # ==================== Admin: Student Management ====================

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str, address: str,
                    gender: str, course_id: Optional[str] = None,
                    session_id: Optional[str] = None) -> Student:
        self._require_role("admin")
        if any(u.username == username for u in self._users.values()):
            raise ValueError(f"Username '{username}' already exists.")
        if any(u.email == email for u in self._users.values()):
            raise ValueError(f"Email '{email}' already exists.")
        if course_id and course_id not in self._courses:
            raise ValueError(f"Course '{course_id}' not found.")
        if session_id and session_id not in self._sessions:
            raise ValueError(f"Session '{session_id}' not found.")
        student = Student(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address,
            gender=gender,
            course_id=course_id,
            session_id=session_id
        )
        self._users[student.user_id] = student
        return student

    def update_student(self, student_id: str, first_name: Optional[str] = None,
                       last_name: Optional[str] = None, address: Optional[str] = None,
                       gender: Optional[str] = None, course_id: Optional[str] = None,
                       session_id: Optional[str] = None, email: Optional[str] = None,
                       password: Optional[str] = None) -> Student:
        self._require_role("admin")
        student = self._get_student_by_id(student_id)
        if first_name:
            student.first_name = first_name
        if last_name:
            student.last_name = last_name
        if address:
            student.address = address
        if gender:
            student.gender = gender
        if course_id:
            if course_id not in self._courses:
                raise ValueError(f"Course '{course_id}' not found.")
            student.course_id = course_id
        if session_id:
            if session_id not in self._sessions:
                raise ValueError(f"Session '{session_id}' not found.")
            student.session_id = session_id
        if email:
            if any(u.email == email and u.user_id != student_id for u in self._users.values()):
                raise ValueError(f"Email '{email}' already exists.")
            student.email = email
        if password:
            student.update_password(password)
        return student

    def delete_student(self, student_id: str) -> bool:
        self._require_role("admin")
        self._get_student_by_id(student_id)
        del self._users[student_id]
        return True

    def get_all_students(self) -> list[Student]:
        self._require_role("admin", "staff")
        return [u for u in self._users.values() if isinstance(u, Student)]

    def _get_student_by_id(self, student_id: str) -> Student:
        user = self._users.get(student_id)
        if not user or not isinstance(user, Student):
            raise ValueError(f"Student with id '{student_id}' not found.")
        return user

    # ==================== Admin: Course Management ====================

    def add_course(self, name: str) -> Course:
        self._require_role("admin")
        if any(c.name == name for c in self._courses.values()):
            raise ValueError(f"Course '{name}' already exists.")
        course = Course(course_id=self._generate_id(), name=name)
        self._courses[course.course_id] = course
        return course

    def update_course(self, course_id: str, name: str) -> Course:
        self._require_role("admin")
        course = self._get_course_by_id(course_id)
        if any(c.name == name and c.course_id != course_id for c in self._courses.values()):
            raise ValueError(f"Course '{name}' already exists.")
        course.name = name
        return course

    def delete_course(self, course_id: str) -> bool:
        self._require_role("admin")
        self._get_course_by_id(course_id)
        del self._courses[course_id]
        return True

    def get_all_courses(self) -> list[Course]:
        return list(self._courses.values())

    def _get_course_by_id(self, course_id: str) -> Course:
        course = self._courses.get(course_id)
        if not course:
            raise ValueError(f"Course with id '{course_id}' not found.")
        return course

    # ==================== Admin: Subject Management ====================

    def add_subject(self, name: str, course_id: str, staff_id: Optional[str] = None) -> Subject:
        self._require_role("admin")
        if course_id not in self._courses:
            raise ValueError(f"Course '{course_id}' not found.")
        if staff_id and staff_id not in self._users:
            raise ValueError(f"Staff '{staff_id}' not found.")
        subject = Subject(
            subject_id=self._generate_id(),
            name=name,
            course_id=course_id,
            staff_id=staff_id
        )
        self._subjects[subject.subject_id] = subject
        return subject

    def update_subject(self, subject_id: str, name: Optional[str] = None,
                       course_id: Optional[str] = None, staff_id: Optional[str] = None) -> Subject:
        self._require_role("admin")
        subject = self._get_subject_by_id(subject_id)
        if name:
            subject.name = name
        if course_id:
            if course_id not in self._courses:
                raise ValueError(f"Course '{course_id}' not found.")
            subject.course_id = course_id
        if staff_id:
            if staff_id not in self._users:
                raise ValueError(f"Staff '{staff_id}' not found.")
            subject.staff_id = staff_id
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        self._require_role("admin")
        self._get_subject_by_id(subject_id)
        del self._subjects[subject_id]
        return True

    def get_all_subjects(self) -> list[Subject]:
        return list(self._subjects.values())

    def _get_subject_by_id(self, subject_id: str) -> Subject:
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found.")
        return subject

    # ==================== Admin: Session Management ====================

    def add_session(self, start_year: int, end_year: int) -> Session:
        self._require_role("admin")
        if end_year <= start_year:
            raise ValueError("End year must be greater than start year.")
        if any(s.start_year == start_year and s.end_year == end_year for s in self._sessions.values()):
            raise ValueError(f"Session {start_year}-{end_year} already exists.")
        session = Session(session_id=self._generate_id(), start_year=start_year, end_year=end_year)
        self._sessions[session.session_id] = session
        return session

    def update_session(self, session_id: str, start_year: Optional[int] = None,
                       end_year: Optional[int] = None) -> Session:
        self._require_role("admin")
        session = self._get_session_by_id(session_id)
        if start_year:
            session.start_year = start_year
        if end_year:
            session.end_year = end_year
        if session.end_year <= session.start_year:
            raise ValueError("End year must be greater than start year.")
        return session

    def delete_session(self, session_id: str) -> bool:
        self._require_role("admin")
        self._get_session_by_id(session_id)
        del self._sessions[session_id]
        return True

    def get_all_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def _get_session_by_id(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session with id '{session_id}' not found.")
        return session

    # ==================== Admin: Leave Management ====================

    def get_all_leave_reports(self) -> list[LeaveReport]:
        self._require_role("admin")
        return list(self._leave_reports.values())

    def get_pending_leave_reports(self) -> list[LeaveReport]:
        self._require_role("admin")
        return [lr for lr in self._leave_reports.values() if lr.status == LeaveReport.PENDING]

    def approve_leave(self, leave_id: str, reply: str = "") -> LeaveReport:
        self._require_role("admin")
        leave = self._get_leave_by_id(leave_id)
        leave.approve(reply)
        return leave

    def reject_leave(self, leave_id: str, reply: str = "") -> LeaveReport:
        self._require_role("admin")
        leave = self._get_leave_by_id(leave_id)
        leave.reject(reply)
        return leave

    def _get_leave_by_id(self, leave_id: str) -> LeaveReport:
        leave = self._leave_reports.get(leave_id)
        if not leave:
            raise ValueError(f"Leave report with id '{leave_id}' not found.")
        return leave

    # ==================== Admin: Feedback Management ====================

    def get_all_feedback_reports(self) -> list[FeedbackReport]:
        self._require_role("admin")
        return list(self._feedback_reports.values())

    def reply_feedback(self, feedback_id: str, reply: str) -> FeedbackReport:
        self._require_role("admin")
        feedback = self._get_feedback_by_id(feedback_id)
        feedback.add_reply(reply)
        return feedback

    def _get_feedback_by_id(self, feedback_id: str) -> FeedbackReport:
        feedback = self._feedback_reports.get(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback with id '{feedback_id}' not found.")
        return feedback

    # ==================== Admin: View Attendance ====================

    def admin_view_attendance(self, subject_id: Optional[str] = None,
                              session_id: Optional[str] = None) -> list[dict]:
        self._require_role("admin")
        return self._get_attendance_summary(subject_id=subject_id, session_id=session_id)

    def _get_attendance_summary(self, subject_id: Optional[str] = None,
                                session_id: Optional[str] = None) -> list[dict]:
        results = []
        for report in self._attendance_reports.values():
            attendance = self._attendances.get(report.attendance_id)
            if not attendance:
                continue
            if subject_id and attendance.subject_id != subject_id:
                continue
            if session_id and attendance.session_id != session_id:
                continue
            student = self._users.get(report.student_id)
            subject = self._subjects.get(attendance.subject_id)
            results.append({
                "report_id": report.report_id,
                "student_id": report.student_id,
                "student_name": f"{student.first_name} {student.last_name}" if student else "Unknown",
                "subject": subject.name if subject else "Unknown",
                "date": attendance.attendance_date,
                "status": "Present" if report.status else "Absent"
            })
        return results

    # ==================== Admin: Summary ====================

    def get_admin_summary(self) -> dict:
        self._require_role("admin")
        all_students = [u for u in self._users.values() if isinstance(u, Student)]
        all_staff = [u for u in self._users.values() if isinstance(u, Staff)]
        total_attendance = len(self._attendance_reports)
        present_count = sum(1 for r in self._attendance_reports.values() if r.status)
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        pending_leaves = sum(1 for l in self._leave_reports.values() if l.status == LeaveReport.PENDING)
        unanswered_feedbacks = sum(1 for f in self._feedback_reports.values() if f.reply is None)
        return {
            "total_students": len(all_students),
            "total_staff": len(all_staff),
            "total_courses": len(self._courses),
            "total_subjects": len(self._subjects),
            "total_sessions": len(self._sessions),
            "total_attendance_records": total_attendance,
            "overall_attendance_rate": round(attendance_rate, 2),
            "pending_leaves": pending_leaves,
            "unanswered_feedbacks": unanswered_feedbacks
        }

    # ==================== Staff: Attendance Management ====================

    def take_attendance(self, subject_id: str, session_id: str,
                        attendance_date: date, student_statuses: dict[str, bool]) -> Attendance:
        self._require_role("staff")
        staff = self._current_user
        if subject_id not in self._subjects:
            raise ValueError(f"Subject '{subject_id}' not found.")
        if session_id not in self._sessions:
            raise ValueError(f"Session '{session_id}' not found.")
        subject = self._subjects[subject_id]
        if subject.staff_id and subject.staff_id != staff.user_id:
            raise PermissionError("You are not assigned to this subject.")
        attendance = Attendance(
            attendance_id=self._generate_id(),
            subject_id=subject_id,
            staff_id=staff.user_id,
            session_id=session_id,
            attendance_date=attendance_date
        )
        self._attendances[attendance.attendance_id] = attendance
        for student_id, status in student_statuses.items():
            if student_id not in self._users:
                raise ValueError(f"Student '{student_id}' not found.")
            report = AttendanceReport(
                report_id=self._generate_id(),
                student_id=student_id,
                attendance_id=attendance.attendance_id,
                status=status
            )
            self._attendance_reports[report.report_id] = report
        return attendance

    def update_attendance(self, attendance_id: str, student_statuses: dict[str, bool]) -> Attendance:
        self._require_role("staff")
        attendance = self._attendances.get(attendance_id)
        if not attendance:
            raise ValueError(f"Attendance '{attendance_id}' not found.")
        if attendance.staff_id != self._current_user.user_id:
            raise PermissionError("You can only update your own attendance records.")
        existing_reports = {r.student_id: r for r in self._attendance_reports.values()
                            if r.attendance_id == attendance_id}
        for student_id, status in student_statuses.items():
            if student_id in existing_reports:
                existing_reports[student_id].status = status
            else:
                if student_id not in self._users:
                    raise ValueError(f"Student '{student_id}' not found.")
                report = AttendanceReport(
                    report_id=self._generate_id(),
                    student_id=student_id,
                    attendance_id=attendance_id,
                    status=status
                )
                self._attendance_reports[report.report_id] = report
        return attendance

    def get_staff_attendance_records(self) -> list[Attendance]:
        self._require_role("staff")
        return [a for a in self._attendances.values() if a.staff_id == self._current_user.user_id]

    # ==================== Staff: Result Management ====================

    def add_result(self, student_id: str, subject_id: str, session_id: str,
                   exam_marks: float, assignment_marks: float) -> StudentResult:
        self._require_role("staff")
        if student_id not in self._users:
            raise ValueError(f"Student '{student_id}' not found.")
        if subject_id not in self._subjects:
            raise ValueError(f"Subject '{subject_id}' not found.")
        if session_id not in self._sessions:
            raise ValueError(f"Session '{session_id}' not found.")
        existing = self._find_result(student_id, subject_id, session_id)
        if existing:
            raise ValueError("Result already exists. Use update_result instead.")
        result = StudentResult(
            result_id=self._generate_id(),
            student_id=student_id,
            subject_id=subject_id,
            session_id=session_id,
            exam_marks=exam_marks,
            assignment_marks=assignment_marks
        )
        self._student_results[result.result_id] = result
        return result

    def update_result(self, student_id: str, subject_id: str, session_id: str,
                      exam_marks: float, assignment_marks: float) -> StudentResult:
        self._require_role("staff")
        result = self._find_result(student_id, subject_id, session_id)
        if not result:
            raise ValueError("Result not found. Use add_result instead.")
        result.update(exam_marks, assignment_marks)
        return result

    def _find_result(self, student_id: str, subject_id: str, session_id: str) -> Optional[StudentResult]:
        for result in self._student_results.values():
            if (result.student_id == student_id and
                    result.subject_id == subject_id and
                    result.session_id == session_id):
                return result
        return None

    def get_staff_summary(self) -> dict:
        self._require_role("staff")
        staff = self._current_user
        staff_subjects = [s for s in self._subjects.values() if s.staff_id == staff.user_id]
        subject_ids = {s.subject_id for s in staff_subjects}
        staff_attendances = [a for a in self._attendances.values() if a.staff_id == staff.user_id]
        attendance_ids = {a.attendance_id for a in staff_attendances}
        attendance_reports = [r for r in self._attendance_reports.values()
                              if r.attendance_id in attendance_ids]
        total = len(attendance_reports)
        present = sum(1 for r in attendance_reports if r.status)
        rate = (present / total * 100) if total > 0 else 0
        staff_leaves = [l for l in self._leave_reports.values() if l.user_id == staff.user_id]
        pending_leaves = sum(1 for l in staff_leaves if l.status == LeaveReport.PENDING)
        approved_leaves = sum(1 for l in staff_leaves if l.status == LeaveReport.APPROVED)
        return {
            "staff_name": f"{staff.first_name} {staff.last_name}",
            "total_subjects": len(staff_subjects),
            "total_attendance_taken": len(staff_attendances),
            "student_attendance_rate": round(rate, 2),
            "total_leaves_applied": len(staff_leaves),
            "pending_leaves": pending_leaves,
            "approved_leaves": approved_leaves
        }

    # ==================== Staff: Leave & Feedback ====================

    def staff_apply_leave(self, leave_date: str, leave_message: str) -> LeaveReport:
        self._require_role("staff")
        leave = LeaveReport(
            leave_id=self._generate_id(),
            user_id=self._current_user.user_id,
            user_type="staff",
            leave_date=leave_date,
            leave_message=leave_message
        )
        self._leave_reports[leave.leave_id] = leave
        return leave

    def staff_send_feedback(self, feedback: str) -> FeedbackReport:
        self._require_role("staff")
        fb = FeedbackReport(
            feedback_id=self._generate_id(),
            user_id=self._current_user.user_id,
            user_type="staff",
            feedback=feedback
        )
        self._feedback_reports[fb.feedback_id] = fb
        return fb

    def get_staff_leave_status(self) -> list[LeaveReport]:
        self._require_role("staff")
        return [l for l in self._leave_reports.values() if l.user_id == self._current_user.user_id]

    # ==================== Student: View Attendance ====================

    def student_view_attendance(self, subject_id: Optional[str] = None) -> list[dict]:
        self._require_role("student")
        student = self._current_user
        results = []
        for report in self._attendance_reports.values():
            if report.student_id != student.user_id:
                continue
            attendance = self._attendances.get(report.attendance_id)
            if not attendance:
                continue
            if subject_id and attendance.subject_id != subject_id:
                continue
            subject = self._subjects.get(attendance.subject_id)
            results.append({
                "subject": subject.name if subject else "Unknown",
                "date": attendance.attendance_date,
                "status": "Present" if report.status else "Absent"
            })
        return results

    def student_get_attendance_summary(self) -> dict:
        self._require_role("student")
        student = self._current_user
        reports = [r for r in self._attendance_reports.values() if r.student_id == student.user_id]
        total = len(reports)
        present = sum(1 for r in reports if r.status)
        absent = total - present
        rate = (present / total * 100) if total > 0 else 0
        return {
            "total_classes": total,
            "present": present,
            "absent": absent,
            "attendance_rate": round(rate, 2)
        }

    # ==================== Student: View Result ====================

    def student_view_results(self) -> list[dict]:
        self._require_role("student")
        student = self._current_user
        results = []
        for result in self._student_results.values():
            if result.student_id != student.user_id:
                continue
            subject = self._subjects.get(result.subject_id)
            session = self._sessions.get(result.session_id)
            results.append({
                "subject": subject.name if subject else "Unknown",
                "session": f"{session.start_year}-{session.end_year}" if session else "Unknown",
                "exam_marks": result.exam_marks,
                "assignment_marks": result.assignment_marks,
                "total_marks": result.total_marks
            })
        return results

    # ==================== Student: Leave & Feedback ====================

    def student_apply_leave(self, leave_date: str, leave_message: str) -> LeaveReport:
        self._require_role("student")
        leave = LeaveReport(
            leave_id=self._generate_id(),
            user_id=self._current_user.user_id,
            user_type="student",
            leave_date=leave_date,
            leave_message=leave_message
        )
        self._leave_reports[leave.leave_id] = leave
        return leave

    def student_send_feedback(self, feedback: str) -> FeedbackReport:
        self._require_role("student")
        fb = FeedbackReport(
            feedback_id=self._generate_id(),
            user_id=self._current_user.user_id,
            user_type="student",
            feedback=feedback
        )
        self._feedback_reports[fb.feedback_id] = fb
        return fb

    def get_student_leave_status(self) -> list[LeaveReport]:
        self._require_role("student")
        return [l for l in self._leave_reports.values() if l.user_id == self._current_user.user_id]

    def get_student_summary(self) -> dict:
        self._require_role("student")
        student = self._current_user
        attendance_summary = self.student_get_attendance_summary()
        results = [r for r in self._student_results.values() if r.student_id == student.user_id]
        leaves = [l for l in self._leave_reports.values() if l.user_id == student.user_id]
        pending_leaves = sum(1 for l in leaves if l.status == LeaveReport.PENDING)
        approved_leaves = sum(1 for l in leaves if l.status == LeaveReport.APPROVED)
        course = self._courses.get(student.course_id) if student.course_id else None
        session = self._sessions.get(student.session_id) if student.session_id else None
        return {
            "student_name": f"{student.first_name} {student.last_name}",
            "course": course.name if course else "Not Enrolled",
            "session": f"{session.start_year}-{session.end_year}" if session else "Not Assigned",
            "attendance_rate": attendance_summary["attendance_rate"],
            "total_subjects_with_results": len(results),
            "total_leaves_applied": len(leaves),
            "pending_leaves": pending_leaves,
            "approved_leaves": approved_leaves
        }


def main():
    sms = StudentManagementSystem()

    print("=== Student Management System Demo ===\n")

    admin = sms.login("admin", "admin123")
    print(f"Logged in as: {admin}")

    course1 = sms.add_course("Computer Science")
    course2 = sms.add_course("Mathematics")
    print(f"\nAdded courses: {course1}, {course2}")

    session1 = sms.add_session(2023, 2024)
    session2 = sms.add_session(2024, 2025)
    print(f"Added sessions: {session1}, {session2}")

    staff1 = sms.add_staff(
        username="john_doe",
        password="staff123",
        email="john@sms.com",
        first_name="John",
        last_name="Doe",
        address="123 Main St",
        gender="Male",
        course_id=course1.course_id
    )
    print(f"\nAdded staff: {staff1}")

    subject1 = sms.add_subject("Data Structures", course1.course_id, staff1.user_id)
    subject2 = sms.add_subject("Algorithms", course1.course_id, staff1.user_id)
    print(f"Added subjects: {subject1}, {subject2}")

    student1 = sms.add_student(
        username="alice",
        password="student123",
        email="alice@sms.com",
        first_name="Alice",
        last_name="Smith",
        address="456 Oak Ave",
        gender="Female",
        course_id=course1.course_id,
        session_id=session1.session_id
    )
    student2 = sms.add_student(
        username="bob",
        password="student123",
        email="bob@sms.com",
        first_name="Bob",
        last_name="Johnson",
        address="789 Pine Rd",
        gender="Male",
        course_id=course1.course_id,
        session_id=session1.session_id
    )
    print(f"Added students: {student1}, {student2}")

    print(f"\nAdmin Summary: {sms.get_admin_summary()}")

    sms.logout()
    print("\n--- Logged out admin ---")

    staff_user = sms.login("john_doe", "staff123")
    print(f"Logged in as: {staff_user}")

    attendance = sms.take_attendance(
        subject_id=subject1.subject_id,
        session_id=session1.session_id,
        attendance_date=date.today(),
        student_statuses={
            student1.user_id: True,
            student2.user_id: False
        }
    )
    print(f"Attendance taken: {attendance}")

    result1 = sms.add_result(
        student_id=student1.user_id,
        subject_id=subject1.subject_id,
        session_id=session1.session_id,
        exam_marks=85.0,
        assignment_marks=15.0
    )
    print(f"Result added: {result1}")

    leave = sms.staff_apply_leave("2024-12-25", "Christmas holiday")
    print(f"Leave applied: {leave}")

    feedback = sms.staff_send_feedback("Need more resources for the lab.")
    print(f"Feedback sent: {feedback}")

    print(f"\nStaff Summary: {sms.get_staff_summary()}")

    sms.logout()
    print("\n--- Logged out staff ---")

    student_user = sms.login("alice", "student123")
    print(f"Logged in as: {student_user}")

    attendance_records = sms.student_view_attendance()
    print(f"Attendance records: {attendance_records}")

    results = sms.student_view_results()
    print(f"Results: {results}")

    student_leave = sms.student_apply_leave("2024-12-26", "Family event")
    print(f"Leave applied: {student_leave}")

    student_feedback = sms.student_send_feedback("The course material is very helpful!")
    print(f"Feedback sent: {student_feedback}")

    print(f"\nStudent Summary: {sms.get_student_summary()}")

    sms.logout()
    print("\n--- Logged out student ---")

    admin = sms.login("admin", "admin123")
    print(f"Logged in as: {admin}")

    all_leaves = sms.get_all_leave_reports()
    print(f"\nAll leave reports: {all_leaves}")

    for leave_report in all_leaves:
        sms.approve_leave(leave_report.leave_id, "Approved. Enjoy your time off.")
        print(f"Approved leave: {leave_report}")

    all_feedbacks = sms.get_all_feedback_reports()
    for fb in all_feedbacks:
        sms.reply_feedback(fb.feedback_id, "Thank you for your feedback!")
        print(f"Replied to feedback: {fb}")

    attendance_view = sms.admin_view_attendance()
    print(f"\nAttendance view: {attendance_view}")

    print(f"\nFinal Admin Summary: {sms.get_admin_summary()}")

    sms.logout()
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()