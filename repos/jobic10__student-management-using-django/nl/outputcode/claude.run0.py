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
        self.fcm_token = None

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
        self.fcm_token = None

    def __repr__(self):
        return f"Student(id={self.user_id}, name={self.first_name} {self.last_name})"


class Course:
    def __init__(self, course_id: str, course_name: str):
        self.course_id = course_id
        self.course_name = course_name
        self.created_at = datetime.now()

    def __repr__(self):
        return f"Course(id={self.course_id}, name={self.course_name})"


class Subject:
    def __init__(self, subject_id: str, subject_name: str, course_id: str, staff_id: str):
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.course_id = course_id
        self.staff_id = staff_id
        self.created_at = datetime.now()

    def __repr__(self):
        return f"Subject(id={self.subject_id}, name={self.subject_name})"


class Session:
    def __init__(self, session_id: str, session_start_year: int, session_end_year: int):
        if session_end_year <= session_start_year:
            raise ValueError("End year must be greater than start year")
        self.session_id = session_id
        self.session_start_year = session_start_year
        self.session_end_year = session_end_year

    def __repr__(self):
        return f"Session({self.session_start_year}-{self.session_end_year})"


class Attendance:
    def __init__(self, attendance_id: str, subject_id: str, staff_id: str,
                 attendance_date: date, session_id: str):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.staff_id = staff_id
        self.attendance_date = attendance_date
        self.session_id = session_id
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


class LeaveReportStudent:
    def __init__(self, leave_id: str, student_id: str, leave_date: str, leave_message: str):
        self.leave_id = leave_id
        self.student_id = student_id
        self.leave_date = leave_date
        self.leave_message = leave_message
        self.leave_status = 0  # 0=pending, 1=approved, -1=rejected
        self.created_at = datetime.now()

    def __repr__(self):
        return f"LeaveReportStudent(id={self.leave_id}, status={self.leave_status})"


class LeaveReportStaff:
    def __init__(self, leave_id: str, staff_id: str, leave_date: str, leave_message: str):
        self.leave_id = leave_id
        self.staff_id = staff_id
        self.leave_date = leave_date
        self.leave_message = leave_message
        self.leave_status = 0  # 0=pending, 1=approved, -1=rejected
        self.created_at = datetime.now()

    def __repr__(self):
        return f"LeaveReportStaff(id={self.leave_id}, status={self.leave_status})"


class FeedbackStudent:
    def __init__(self, feedback_id: str, student_id: str, feedback: str):
        self.feedback_id = feedback_id
        self.student_id = student_id
        self.feedback = feedback
        self.feedback_reply = ""
        self.created_at = datetime.now()

    def __repr__(self):
        return f"FeedbackStudent(id={self.feedback_id})"


class FeedbackStaff:
    def __init__(self, feedback_id: str, staff_id: str, feedback: str):
        self.feedback_id = feedback_id
        self.staff_id = staff_id
        self.feedback = feedback
        self.feedback_reply = ""
        self.created_at = datetime.now()

    def __repr__(self):
        return f"FeedbackStaff(id={self.feedback_id})"


class StudentResult:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 subject_exam_marks: float, subject_assignment_marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.subject_exam_marks = subject_exam_marks
        self.subject_assignment_marks = subject_assignment_marks
        self.created_at = datetime.now()

    @property
    def total_marks(self) -> float:
        return self.subject_exam_marks + self.subject_assignment_marks

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
        self._leave_reports_student: dict[str, LeaveReportStudent] = {}
        self._leave_reports_staff: dict[str, LeaveReportStaff] = {}
        self._feedback_students: dict[str, FeedbackStudent] = {}
        self._feedback_staff: dict[str, FeedbackStaff] = {}
        self._student_results: dict[str, StudentResult] = {}
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
        self._users[admin.user_id] = admin

    def authenticate(self, username: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username and user.verify_password(password) and user.is_active:
                return user
        return None

    # ==================== ADMIN OPERATIONS ====================

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str, address: str,
                  course_id: Optional[str] = None) -> Staff:
        if self._username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        if self._email_exists(email):
            raise ValueError(f"Email '{email}' already exists")
        if course_id and course_id not in self._courses:
            raise ValueError(f"Course with id '{course_id}' does not exist")
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
        self._users[staff.user_id] = staff
        return staff

    def update_staff(self, staff_id: str, first_name: Optional[str] = None,
                     last_name: Optional[str] = None, address: Optional[str] = None,
                     email: Optional[str] = None, course_id: Optional[str] = None,
                     password: Optional[str] = None) -> Staff:
        staff = self._get_staff_by_id(staff_id)
        if first_name:
            staff.first_name = first_name
        if last_name:
            staff.last_name = last_name
        if address:
            staff.address = address
        if email:
            if self._email_exists(email) and staff.email != email:
                raise ValueError(f"Email '{email}' already exists")
            staff.email = email
        if course_id:
            if course_id not in self._courses:
                raise ValueError(f"Course with id '{course_id}' does not exist")
            staff.course_id = course_id
        if password:
            staff.update_password(password)
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        staff = self._get_staff_by_id(staff_id)
        del self._users[staff_id]
        return True

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str, address: str,
                    course_id: Optional[str] = None,
                    session_id: Optional[str] = None) -> Student:
        if self._username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        if self._email_exists(email):
            raise ValueError(f"Email '{email}' already exists")
        if course_id and course_id not in self._courses:
            raise ValueError(f"Course with id '{course_id}' does not exist")
        if session_id and session_id not in self._sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist")
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
        self._users[student.user_id] = student
        return student

    def update_student(self, student_id: str, first_name: Optional[str] = None,
                       last_name: Optional[str] = None, address: Optional[str] = None,
                       email: Optional[str] = None, course_id: Optional[str] = None,
                       session_id: Optional[str] = None, password: Optional[str] = None) -> Student:
        student = self._get_student_by_id(student_id)
        if first_name:
            student.first_name = first_name
        if last_name:
            student.last_name = last_name
        if address:
            student.address = address
        if email:
            if self._email_exists(email) and student.email != email:
                raise ValueError(f"Email '{email}' already exists")
            student.email = email
        if course_id:
            if course_id not in self._courses:
                raise ValueError(f"Course with id '{course_id}' does not exist")
            student.course_id = course_id
        if session_id:
            if session_id not in self._sessions:
                raise ValueError(f"Session with id '{session_id}' does not exist")
            student.session_id = session_id
        if password:
            student.update_password(password)
        return student

    def delete_student(self, student_id: str) -> bool:
        self._get_student_by_id(student_id)
        del self._users[student_id]
        return True

    def add_course(self, course_name: str) -> Course:
        for course in self._courses.values():
            if course.course_name.lower() == course_name.lower():
                raise ValueError(f"Course '{course_name}' already exists")
        course = Course(course_id=self._generate_id(), course_name=course_name)
        self._courses[course.course_id] = course
        return course

    def update_course(self, course_id: str, course_name: str) -> Course:
        if course_id not in self._courses:
            raise ValueError(f"Course with id '{course_id}' does not exist")
        self._courses[course_id].course_name = course_name
        return self._courses[course_id]

    def delete_course(self, course_id: str) -> bool:
        if course_id not in self._courses:
            raise ValueError(f"Course with id '{course_id}' does not exist")
        del self._courses[course_id]
        return True

    def add_subject(self, subject_name: str, course_id: str, staff_id: str) -> Subject:
        if course_id not in self._courses:
            raise ValueError(f"Course with id '{course_id}' does not exist")
        self._get_staff_by_id(staff_id)
        subject = Subject(
            subject_id=self._generate_id(),
            subject_name=subject_name,
            course_id=course_id,
            staff_id=staff_id
        )
        self._subjects[subject.subject_id] = subject
        return subject

    def update_subject(self, subject_id: str, subject_name: Optional[str] = None,
                       course_id: Optional[str] = None, staff_id: Optional[str] = None) -> Subject:
        if subject_id not in self._subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist")
        subject = self._subjects[subject_id]
        if subject_name:
            subject.subject_name = subject_name
        if course_id:
            if course_id not in self._courses:
                raise ValueError(f"Course with id '{course_id}' does not exist")
            subject.course_id = course_id
        if staff_id:
            self._get_staff_by_id(staff_id)
            subject.staff_id = staff_id
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id not in self._subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist")
        del self._subjects[subject_id]
        return True

    def add_session(self, session_start_year: int, session_end_year: int) -> Session:
        session = Session(
            session_id=self._generate_id(),
            session_start_year=session_start_year,
            session_end_year=session_end_year
        )
        self._sessions[session.session_id] = session
        return session

    def update_session(self, session_id: str, session_start_year: Optional[int] = None,
                       session_end_year: Optional[int] = None) -> Session:
        if session_id not in self._sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist")
        session = self._sessions[session_id]
        start = session_start_year if session_start_year else session.session_start_year
        end = session_end_year if session_end_year else session.session_end_year
        if end <= start:
            raise ValueError("End year must be greater than start year")
        session.session_start_year = start
        session.session_end_year = end
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist")
        del self._sessions[session_id]
        return True

    def view_student_attendance(self, student_id: Optional[str] = None,
                                subject_id: Optional[str] = None) -> list[dict]:
        results = []
        for report in self._attendance_reports.values():
            if student_id and report.student_id != student_id:
                continue
            attendance = self._attendances.get(report.attendance_id)
            if not attendance:
                continue
            if subject_id and attendance.subject_id != subject_id:
                continue
            student = self._users.get(report.student_id)
            subject = self._subjects.get(attendance.subject_id)
            results.append({
                "report_id": report.report_id,
                "student_id": report.student_id,
                "student_name": f"{student.first_name} {student.last_name}" if student else "Unknown",
                "subject_id": attendance.subject_id,
                "subject_name": subject.subject_name if subject else "Unknown",
                "attendance_date": attendance.attendance_date,
                "status": report.status
            })
        return results

    def review_student_feedback(self, feedback_id: str) -> Optional[FeedbackStudent]:
        return self._feedback_students.get(feedback_id)

    def reply_student_feedback(self, feedback_id: str, reply: str) -> FeedbackStudent:
        feedback = self._feedback_students.get(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback with id '{feedback_id}' does not exist")
        feedback.feedback_reply = reply
        return feedback

    def review_staff_feedback(self, feedback_id: str) -> Optional[FeedbackStaff]:
        return self._feedback_staff.get(feedback_id)

    def reply_staff_feedback(self, feedback_id: str, reply: str) -> FeedbackStaff:
        feedback = self._feedback_staff.get(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback with id '{feedback_id}' does not exist")
        feedback.feedback_reply = reply
        return feedback

    def approve_student_leave(self, leave_id: str) -> LeaveReportStudent:
        leave = self._leave_reports_student.get(leave_id)
        if not leave:
            raise ValueError(f"Leave report with id '{leave_id}' does not exist")
        leave.leave_status = 1
        return leave

    def reject_student_leave(self, leave_id: str) -> LeaveReportStudent:
        leave = self._leave_reports_student.get(leave_id)
        if not leave:
            raise ValueError(f"Leave report with id '{leave_id}' does not exist")
        leave.leave_status = -1
        return leave

    def approve_staff_leave(self, leave_id: str) -> LeaveReportStaff:
        leave = self._leave_reports_staff.get(leave_id)
        if not leave:
            raise ValueError(f"Leave report with id '{leave_id}' does not exist")
        leave.leave_status = 1
        return leave

    def reject_staff_leave(self, leave_id: str) -> LeaveReportStaff:
        leave = self._leave_reports_staff.get(leave_id)
        if not leave:
            raise ValueError(f"Leave report with id '{leave_id}' does not exist")
        leave.leave_status = -1
        return leave

    def get_admin_summary(self) -> dict:
        students = [u for u in self._users.values() if isinstance(u, Student)]
        staff_list = [u for u in self._users.values() if isinstance(u, Staff)]
        total_attendance = len(self._attendance_reports)
        present_count = sum(1 for r in self._attendance_reports.values() if r.status)
        attendance_percentage = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        pending_student_leaves = sum(1 for l in self._leave_reports_student.values() if l.leave_status == 0)
        pending_staff_leaves = sum(1 for l in self._leave_reports_staff.values() if l.leave_status == 0)
        return {
            "total_students": len(students),
            "total_staff": len(staff_list),
            "total_courses": len(self._courses),
            "total_subjects": len(self._subjects),
            "total_sessions": len(self._sessions),
            "total_attendance_records": total_attendance,
            "overall_attendance_percentage": round(attendance_percentage, 2),
            "pending_student_leaves": pending_student_leaves,
            "pending_staff_leaves": pending_staff_leaves,
            "total_student_feedbacks": len(self._feedback_students),
            "total_staff_feedbacks": len(self._feedback_staff)
        }

    # ==================== STAFF OPERATIONS ====================

    def take_attendance(self, staff_id: str, subject_id: str, session_id: str,
                        attendance_date: date, student_statuses: dict[str, bool]) -> Attendance:
        self._get_staff_by_id(staff_id)
        if subject_id not in self._subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist")
        if session_id not in self._sessions:
            raise ValueError(f"Session with id '{session_id}' does not exist")
        subject = self._subjects[subject_id]
        if subject.staff_id != staff_id:
            raise ValueError("Staff is not assigned to this subject")
        attendance = Attendance(
            attendance_id=self._generate_id(),
            subject_id=subject_id,
            staff_id=staff_id,
            attendance_date=attendance_date,
            session_id=session_id
        )
        self._attendances[attendance.attendance_id] = attendance
        for student_id, status in student_statuses.items():
            self._get_student_by_id(student_id)
            report = AttendanceReport(
                report_id=self._generate_id(),
                student_id=student_id,
                attendance_id=attendance.attendance_id,
                status=status
            )
            self._attendance_reports[report.report_id] = report
        return attendance

    def update_attendance(self, attendance_id: str, staff_id: str,
                          student_statuses: dict[str, bool]) -> Attendance:
        if attendance_id not in self._attendances:
            raise ValueError(f"Attendance with id '{attendance_id}' does not exist")
        attendance = self._attendances[attendance_id]
        if attendance.staff_id != staff_id:
            raise ValueError("Staff is not authorized to update this attendance")
        existing_reports = {r.student_id: r for r in self._attendance_reports.values()
                            if r.attendance_id == attendance_id}
        for student_id, status in student_statuses.items():
            if student_id in existing_reports:
                existing_reports[student_id].status = status
            else:
                self._get_student_by_id(student_id)
                report = AttendanceReport(
                    report_id=self._generate_id(),
                    student_id=student_id,
                    attendance_id=attendance_id,
                    status=status
                )
                self._attendance_reports[report.report_id] = report
        return attendance

    def add_result(self, staff_id: str, student_id: str, subject_id: str,
                   exam_marks: float, assignment_marks: float) -> StudentResult:
        self._get_staff_by_id(staff_id)
        self._get_student_by_id(student_id)
        if subject_id not in self._subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist")
        subject = self._subjects[subject_id]
        if subject.staff_id != staff_id:
            raise ValueError("Staff is not assigned to this subject")
        existing_result = self._get_result_by_student_subject(student_id, subject_id)
        if existing_result:
            raise ValueError(f"Result already exists for student '{student_id}' in subject '{subject_id}'. Use update_result instead.")
        result = StudentResult(
            result_id=self._generate_id(),
            student_id=student_id,
            subject_id=subject_id,
            subject_exam_marks=exam_marks,
            subject_assignment_marks=assignment_marks
        )
        self._student_results[result.result_id] = result
        return result

    def update_result(self, staff_id: str, student_id: str, subject_id: str,
                      exam_marks: Optional[float] = None,
                      assignment_marks: Optional[float] = None) -> StudentResult:
        self._get_staff_by_id(staff_id)
        subject = self._subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' does not exist")
        if subject.staff_id != staff_id:
            raise ValueError("Staff is not assigned to this subject")
        result = self._get_result_by_student_subject(student_id, subject_id)
        if not result:
            raise ValueError(f"No result found for student '{student_id}' in subject '{subject_id}'")
        if exam_marks is not None:
            result.subject_exam_marks = exam_marks
        if assignment_marks is not None:
            result.subject_assignment_marks = assignment_marks
        return result

    def staff_apply_leave(self, staff_id: str, leave_date: str, leave_message: str) -> LeaveReportStaff:
        self._get_staff_by_id(staff_id)
        leave = LeaveReportStaff(
            leave_id=self._generate_id(),
            staff_id=staff_id,
            leave_date=leave_date,
            leave_message=leave_message
        )
        self._leave_reports_staff[leave.leave_id] = leave
        return leave

    def staff_send_feedback(self, staff_id: str, feedback_message: str) -> FeedbackStaff:
        self._get_staff_by_id(staff_id)
        feedback = FeedbackStaff(
            feedback_id=self._generate_id(),
            staff_id=staff_id,
            feedback=feedback_message
        )
        self._feedback_staff[feedback.feedback_id] = feedback
        return feedback

    def get_staff_summary(self, staff_id: str) -> dict:
        self._get_staff_by_id(staff_id)
        staff_subjects = [s for s in self._subjects.values() if s.staff_id == staff_id]
        subject_ids = {s.subject_id for s in staff_subjects}
        staff_attendances = [a for a in self._attendances.values() if a.subject_id in subject_ids]
        attendance_ids = {a.attendance_id for a in staff_attendances}
        reports = [r for r in self._attendance_reports.values() if r.attendance_id in attendance_ids]
        total_reports = len(reports)
        present_count = sum(1 for r in reports if r.status)
        attendance_percentage = (present_count / total_reports * 100) if total_reports > 0 else 0
        staff_leaves = [l for l in self._leave_reports_staff.values() if l.staff_id == staff_id]
        pending_leaves = sum(1 for l in staff_leaves if l.leave_status == 0)
        approved_leaves = sum(1 for l in staff_leaves if l.leave_status == 1)
        rejected_leaves = sum(1 for l in staff_leaves if l.leave_status == -1)
        student_ids = set()
        for report in reports:
            student_ids.add(report.student_id)
        return {
            "staff_id": staff_id,
            "total_subjects": len(staff_subjects),
            "total_students": len(student_ids),
            "total_attendance_taken": len(staff_attendances),
            "overall_attendance_percentage": round(attendance_percentage, 2),
            "total_leaves": len(staff_leaves),
            "pending_leaves": pending_leaves,
            "approved_leaves": approved_leaves,
            "rejected_leaves": rejected_leaves
        }

    # ==================== STUDENT OPERATIONS ====================

    def student_view_attendance(self, student_id: str,
                                subject_id: Optional[str] = None) -> list[dict]:
        self._get_student_by_id(student_id)
        results = []
        for report in self._attendance_reports.values():
            if report.student_id != student_id:
                continue
            attendance = self._attendances.get(report.attendance_id)
            if not attendance:
                continue
            if subject_id and attendance.subject_id != subject_id:
                continue
            subject = self._subjects.get(attendance.subject_id)
            results.append({
                "report_id": report.report_id,
                "subject_id": attendance.subject_id,
                "subject_name": subject.subject_name if subject else "Unknown",
                "attendance_date": attendance.attendance_date,
                "status": report.status
            })
        return results

    def student_view_result(self, student_id: str) -> list[dict]:
        self._get_student_by_id(student_id)
        results = []
        for result in self._student_results.values():
            if result.student_id != student_id:
                continue
            subject = self._subjects.get(result.subject_id)
            results.append({
                "result_id": result.result_id,
                "subject_id": result.subject_id,
                "subject_name": subject.subject_name if subject else "Unknown",
                "exam_marks": result.subject_exam_marks,
                "assignment_marks": result.subject_assignment_marks,
                "total_marks": result.total_marks
            })
        return results

    def student_apply_leave(self, student_id: str, leave_date: str,
                            leave_message: str) -> LeaveReportStudent:
        self._get_student_by_id(student_id)
        leave = LeaveReportStudent(
            leave_id=self._generate_id(),
            student_id=student_id,
            leave_date=leave_date,
            leave_message=leave_message
        )
        self._leave_reports_student[leave.leave_id] = leave
        return leave

    def student_send_feedback(self, student_id: str, feedback_message: str) -> FeedbackStudent:
        self._get_student_by_id(student_id)
        feedback = FeedbackStudent(
            feedback_id=self._generate_id(),
            student_id=student_id,
            feedback=feedback_message
        )
        self._feedback_students[feedback.feedback_id] = feedback
        return feedback

    def get_student_summary(self, student_id: str) -> dict:
        student = self._get_student_by_id(student_id)
        reports = [r for r in self._attendance_reports.values() if r.student_id == student_id]
        total_classes = len(reports)
        present_count = sum(1 for r in reports if r.status)
        attendance_percentage = (present_count / total_classes * 100) if total_classes > 0 else 0
        student_leaves = [l for l in self._leave_reports_student.values() if l.student_id == student_id]
        pending_leaves = sum(1 for l in student_leaves if l.leave_status == 0)
        approved_leaves = sum(1 for l in student_leaves if l.leave_status == 1)
        rejected_leaves = sum(1 for l in student_leaves if l.leave_status == -1)
        results = [r for r in self._student_results.values() if r.student_id == student_id]
        total_marks = sum(r.total_marks for r in results)
        avg_marks = (total_marks / len(results)) if results else 0
        course = self._courses.get(student.course_id) if student.course_id else None
        session = self._sessions.get(student.session_id) if student.session_id else None
        subjects_in_course = []
        if student.course_id:
            subjects_in_course = [s for s in self._subjects.values() if s.course_id == student.course_id]
        return {
            "student_id": student_id,
            "student_name": f"{student.first_name} {student.last_name}",
            "course": course.course_name if course else "Not Assigned",
            "session": str(session) if session else "Not Assigned",
            "total_subjects": len(subjects_in_course),
            "total_classes": total_classes,
            "classes_attended": present_count,
            "attendance_percentage": round(attendance_percentage, 2),
            "total_leaves": len(student_leaves),
            "pending_leaves": pending_leaves,
            "approved_leaves": approved_leaves,
            "rejected_leaves": rejected_leaves,
            "total_results": len(results),
            "average_marks": round(avg_marks, 2)
        }

    # ==================== QUERY METHODS ====================

    def get_all_students(self) -> list[Student]:
        return [u for u in self._users.values() if isinstance(u, Student)]

    def get_all_staff(self) -> list[Staff]:
        return [u for u in self._users.values() if isinstance(u, Staff)]

    def get_all_courses(self) -> list[Course]:
        return list(self._courses.values())

    def get_all_subjects(self) -> list[Subject]:
        return list(self._subjects.values())

    def get_all_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def get_subjects_by_course(self, course_id: str) -> list[Subject]:
        return [s for s in self._subjects.values() if s.course_id == course_id]

    def get_subjects_by_staff(self, staff_id: str) -> list[Subject]:
        return [s for s in self._subjects.values() if s.staff_id == staff_id]

    def get_students_by_course(self, course_id: str) -> list[Student]:
        return [u for u in self._users.values()
                if isinstance(u, Student) and u.course_id == course_id]

    def get_all_student_leaves(self) -> list[LeaveReportStudent]:
        return list(self._leave_reports_student.values())

    def get_all_staff_leaves(self) -> list[LeaveReportStaff]:
        return list(self._leave_reports_staff.values())

    def get_all_student_feedbacks(self) -> list[FeedbackStudent]:
        return list(self._feedback_students.values())

    def get_all_staff_feedbacks(self) -> list[FeedbackStaff]:
        return list(self._feedback_staff.values())

    def get_student_leave_status(self, student_id: str) -> list[LeaveReportStudent]:
        self._get_student_by_id(student_id)
        return [l for l in self._leave_reports_student.values() if l.student_id == student_id]

    def get_staff_leave_status(self, staff_id: str) -> list[LeaveReportStaff]:
        self._get_staff_by_id(staff_id)
        return [l for l in self._leave_reports_staff.values() if l.staff_id == staff_id]

    def get_attendance_by_subject(self, subject_id: str) -> list[Attendance]:
        return [a for a in self._attendances.values() if a.subject_id == subject_id]

    def get_attendance_summary_by_subject(self, subject_id: str) -> dict:
        if subject_id not in self._subjects:
            raise ValueError(f"Subject with id '{subject_id}' does not exist")
        subject_attendances = self.get_attendance_by_subject(subject_id)
        attendance_ids = {a.attendance_id for a in subject_attendances}
        reports = [r for r in self._attendance_reports.values() if r.attendance_id in attendance_ids]
        total = len(reports)
        present = sum(1 for r in reports if r.status)
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0
        return {
            "subject_id": subject_id,
            "subject_name": self._subjects[subject_id].subject_name,
            "total_records": total,
            "present": present,
            "absent": absent,
            "attendance_percentage": round(percentage, 2)
        }

    # ==================== HELPER METHODS ====================

    def _username_exists(self, username: str) -> bool:
        return any(u.username == username for u in self._users.values())

    def _email_exists(self, email: str) -> bool:
        return any(u.email == email for u in self._users.values())

    def _get_staff_by_id(self, staff_id: str) -> Staff:
        user = self._users.get(staff_id)
        if not user or not isinstance(user, Staff):
            raise ValueError(f"Staff with id '{staff_id}' does not exist")
        return user

    def _get_student_by_id(self, student_id: str) -> Student:
        user = self._users.get(student_id)
        if not user or not isinstance(user, Student):
            raise ValueError(f"Student with id '{student_id}' does not exist")
        return user

    def _get_result_by_student_subject(self, student_id: str,
                                       subject_id: str) -> Optional[StudentResult]:
        for result in self._student_results.values():
            if result.student_id == student_id and result.subject_id == subject_id:
                return result
        return None


def main():
    sms = StudentManagementSystem()

    print("=== Student Management System Demo ===\n")

    admin_user = sms.authenticate("admin", "admin123")
    print(f"Authenticated: {admin_user}\n")

    print("--- Adding Courses ---")
    cs_course = sms.add_course("Computer Science")
    math_course = sms.add_course("Mathematics")
    print(f"Added: {cs_course}")
    print(f"Added: {math_course}\n")

    print("--- Adding Sessions ---")
    session_2023 = sms.add_session(2023, 2024)
    session_2024 = sms.add_session(2024, 2025)
    print(f"Added: {session_2023}")
    print(f"Added: {session_2024}\n")

    print("--- Adding Staff ---")
    staff1 = sms.add_staff(
        username="john_doe",
        password="staff123",
        email="john@school.com",
        first_name="John",
        last_name="Doe",
        address="123 Main St",
        course_id=cs_course.course_id
    )
    staff2 = sms.add_staff(
        username="jane_smith",
        password="staff456",
        email="jane@school.com",
        first_name="Jane",
        last_name="Smith",
        address="456 Oak Ave",
        course_id=math_course.course_id
    )
    print(f"Added: {staff1}")
    print(f"Added: {staff2}\n")

    print("--- Adding Subjects ---")
    subject1 = sms.add_subject("Python Programming", cs_course.course_id, staff1.user_id)
    subject2 = sms.add_subject("Data Structures", cs_course.course_id, staff1.user_id)
    subject3 = sms.add_subject("Calculus", math_course.course_id, staff2.user_id)
    print(f"Added: {subject1}")
    print(f"Added: {subject2}")
    print(f"Added: {subject3}\n")

    print("--- Adding Students ---")
    student1 = sms.add_student(
        username="alice",
        password="student123",
        email="alice@school.com",
        first_name="Alice",
        last_name="Johnson",
        address="789 Pine Rd",
        course_id=cs_course.course_id,
        session_id=session_2024.session_id
    )
    student2 = sms.add_student(
        username="bob",
        password="student456",
        email="bob@school.com",
        first_name="Bob",
        last_name="Williams",
        address="321 Elm St",
        course_id=cs_course.course_id,
        session_id=session_2024.session_id
    )
    student3 = sms.add_student(
        username="charlie",
        password="student789",
        email="charlie@school.com",
        first_name="Charlie",
        last_name="Brown",
        address="654 Maple Dr",
        course_id=math_course.course_id,
        session_id=session_2023.session_id
    )
    print(f"Added: {student1}")
    print(f"Added: {student2}")
    print(f"Added: {student3}\n")

    print("--- Taking Attendance ---")
    attendance1 = sms.take_attendance(
        staff_id=staff1.user_id,
        subject_id=subject1.subject_id,
        session_id=session_2024.session_id,
        attendance_date=date(2024, 1, 15),
        student_statuses={
            student1.user_id: True,
            student2.user_id: False
        }
    )
    print(f"Attendance taken: {attendance1}")

    attendance2 = sms.take_attendance(
        staff_id=staff1.user_id,
        subject_id=subject1.subject_id,
        session_id=session_2024.session_id,
        attendance_date=date(2024, 1, 16),
        student_statuses={
            student1.user_id: True,
            student2.user_id: True
        }
    )
    print(f"Attendance taken: {attendance2}\n")

    print("--- Adding Results ---")
    result1 = sms.add_result(
        staff_id=staff1.user_id,
        student_id=student1.user_id,
        subject_id=subject1.subject_id,
        exam_marks=85.0,
        assignment_marks=18.0
    )
    result2 = sms.add_result(
        staff_id=staff1.user_id,
        student_id=student2.user_id,
        subject_id=subject1.subject_id,
        exam_marks=72.0,
        assignment_marks=15.0
    )
    print(f"Added: {result1}")
    print(f"Added: {result2}\n")

    print("--- Student Applying for Leave ---")
    leave1 = sms.student_apply_leave(
        student_id=student1.user_id,
        leave_date="2024-01-20",
        leave_message="Medical appointment"
    )
    print(f"Leave applied: {leave1}")

    print("--- Admin Approving Leave ---")
    approved_leave = sms.approve_student_leave(leave1.leave_id)
    print(f"Leave approved, status: {approved_leave.leave_status}\n")

    print("--- Student Sending Feedback ---")
    feedback1 = sms.student_send_feedback(
        student_id=student1.user_id,
        feedback_message="The Python course is very helpful!"
    )
    print(f"Feedback sent: {feedback1}")

    print("--- Admin Replying to Feedback ---")
    replied_feedback = sms.reply_student_feedback(
        feedback_id=feedback1.feedback_id,
        reply="Thank you for your positive feedback!"
    )
    print(f"Reply: {replied_feedback.feedback_reply}\n")

    print("--- Staff Applying for Leave ---")
    staff_leave = sms.staff_apply_leave(
        staff_id=staff1.user_id,
        leave_date="2024-01-25",
        leave_message="Family emergency"
    )
    print(f"Staff leave applied: {staff_leave}")

    print("--- Admin Rejecting Staff Leave ---")
    rejected_leave = sms.reject_staff_leave(staff_leave.leave_id)
    print(f"Staff leave rejected, status: {rejected_leave.leave_status}\n")

    print("--- Staff Sending Feedback ---")
    staff_feedback = sms.staff_send_feedback(
        staff_id=staff1.user_id,
        feedback_message="Need more resources for the lab."
    )
    print(f"Staff feedback sent: {staff_feedback}")

    print("--- Admin Replying to Staff Feedback ---")
    replied_staff_feedback = sms.reply_staff_feedback(
        feedback_id=staff_feedback.feedback_id,
        reply="We will look into providing more resources."
    )
    print(f"Reply: {replied_staff_feedback.feedback_reply}\n")

    print("--- Student Viewing Attendance ---")
    alice_attendance = sms.student_view_attendance(student1.user_id)
    for record in alice_attendance:
        print(f"  Subject: {record['subject_name']}, Date: {record['attendance_date']}, Present: {record['status']}")
    print()

    print("--- Student Viewing Results ---")
    alice_results = sms.student_view_result(student1.user_id)
    for result in alice_results:
        print(f"  Subject: {result['subject_name']}, Exam: {result['exam_marks']}, "
              f"Assignment: {result['assignment_marks']}, Total: {result['total_marks']}")
    print()

    print("--- Admin Summary ---")
    admin_summary = sms.get_admin_summary()
    for key, value in admin_summary.items():
        print(f"  {key}: {value}")
    print()

    print("--- Student Summary (Alice) ---")
    alice_summary = sms.get_student_summary(student1.user_id)
    for key, value in alice_summary.items():
        print(f"  {key}: {value}")
    print()

    print("--- Staff Summary (John Doe) ---")
    staff_summary = sms.get_staff_summary(staff1.user_id)
    for key, value in staff_summary.items():
        print(f"  {key}: {value}")
    print()

    print("--- Attendance Summary by Subject ---")
    att_summary = sms.get_attendance_summary_by_subject(subject1.subject_id)
    for key, value in att_summary.items():
        print(f"  {key}: {value}")
    print()

    print("--- Updating Course ---")
    updated_course = sms.update_course(cs_course.course_id, "Computer Science & Engineering")
    print(f"Updated: {updated_course}\n")

    print("--- Updating Subject ---")
    updated_subject = sms.update_subject(subject1.subject_id, subject_name="Advanced Python Programming")
    print(f"Updated: {updated_subject}\n")

    print("--- Updating Result ---")
    updated_result = sms.update_result(
        staff_id=staff1.user_id,
        student_id=student1.user_id,
        subject_id=subject1.subject_id,
        exam_marks=90.0
    )
    print(f"Updated: {updated_result}\n")

    print("--- Updating Attendance ---")
    updated_attendance = sms.update_attendance(
        attendance_id=attendance1.attendance_id,
        staff_id=staff1.user_id,
        student_statuses={student2.user_id: True}
    )
    print(f"Updated attendance: {updated_attendance}\n")

    print("--- Admin Viewing All Student Attendance ---")
    all_attendance = sms.view_student_attendance()
    print(f"Total attendance records: {len(all_attendance)}\n")

    print("--- Deleting Student ---")
    sms.delete_student(student3.user_id)
    print(f"Student {student3.first_name} deleted")
    print(f"Total students now: {len(sms.get_all_students())}\n")

    print("--- Deleting Subject ---")
    sms.delete_subject(subject3.subject_id)
    print(f"Subject {subject3.subject_name} deleted")
    print(f"Total subjects now: {len(sms.get_all_subjects())}\n")

    print("--- Deleting Course ---")
    sms.delete_course(math_course.course_id)
    print(f"Course {math_course.course_name} deleted")
    print(f"Total courses now: {len(sms.get_all_courses())}\n")

    print("--- Deleting Session ---")
    sms.delete_session(session_2023.session_id)
    print(f"Session {session_2023} deleted")
    print(f"Total sessions now: {len(sms.get_all_sessions())}\n")

    print("--- Deleting Staff ---")
    sms.delete_staff(staff2.user_id)
    print(f"Staff {staff2.first_name} deleted")
    print(f"Total staff now: {len(sms.get_all_staff())}\n")

    print("=== Demo Complete ===")


if __name__ == "__main__":
    main()