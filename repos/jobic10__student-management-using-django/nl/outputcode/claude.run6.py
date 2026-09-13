from datetime import datetime, date
from typing import Optional
import hashlib
import uuid


# ─────────────────────────────────────────────
# Enumerations / Constants
# ─────────────────────────────────────────────

class UserRole:
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


class LeaveStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AttendanceStatus:
    PRESENT = "present"
    ABSENT = "absent"


# ─────────────────────────────────────────────
# Core Models
# ─────────────────────────────────────────────

class User:
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, role: str, first_name: str, last_name: str):
        self.user_id = user_id
        self.username = username
        self._password_hash = self._hash_password(password)
        self.email = email
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.created_at = datetime.now()
        self.is_active = True

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        return self._password_hash == self._hash_password(password)

    def change_password(self, old_password: str, new_password: str) -> bool:
        if self.verify_password(old_password):
            self._password_hash = self._hash_password(new_password)
            return True
        return False

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User id={self.user_id} username={self.username} role={self.role}>"


class Admin(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str):
        super().__init__(user_id, username, password, email,
                         UserRole.ADMIN, first_name, last_name)

    def __repr__(self):
        return f"<Admin id={self.user_id} name={self.get_full_name()}>"


class Course:
    def __init__(self, course_id: str, name: str, description: str = ""):
        self.course_id = course_id
        self.name = name
        self.description = description
        self.created_at = datetime.now()
        self.subjects: list = []

    def add_subject(self, subject) -> None:
        if subject not in self.subjects:
            self.subjects.append(subject)

    def remove_subject(self, subject) -> bool:
        if subject in self.subjects:
            self.subjects.remove(subject)
            return True
        return False

    def get_subjects(self) -> list:
        return list(self.subjects)

    def __repr__(self):
        return f"<Course id={self.course_id} name={self.name}>"


class Session:
    def __init__(self, session_id: str, start_year: int, end_year: int):
        if end_year <= start_year:
            raise ValueError("end_year must be greater than start_year")
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year
        self.created_at = datetime.now()

    def get_session_name(self) -> str:
        return f"{self.start_year}-{self.end_year}"

    def __repr__(self):
        return f"<Session {self.get_session_name()}>"


class Subject:
    def __init__(self, subject_id: str, name: str, course: Course,
                 staff=None, description: str = ""):
        self.subject_id = subject_id
        self.name = name
        self.course = course
        self.staff = staff
        self.description = description
        self.created_at = datetime.now()

    def assign_staff(self, staff) -> None:
        self.staff = staff

    def __repr__(self):
        return f"<Subject id={self.subject_id} name={self.name}>"


class Staff(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str,
                 address: str = "", course: Optional[Course] = None):
        super().__init__(user_id, username, password, email,
                         UserRole.STAFF, first_name, last_name)
        self.address = address
        self.course = course
        self.subjects: list[Subject] = []
        self.leave_applications: list = []
        self.feedbacks: list = []

    def get_subjects(self) -> list:
        return list(self.subjects)

    def get_students_in_subjects(self, student_list: list) -> list:
        result = []
        for student in student_list:
            for subject in self.subjects:
                if student.course == subject.course and student not in result:
                    result.append(student)
        return result

    def __repr__(self):
        return f"<Staff id={self.user_id} name={self.get_full_name()}>"


class Student(User):
    def __init__(self, user_id: str, username: str, password: str,
                 email: str, first_name: str, last_name: str,
                 course: Optional[Course] = None,
                 session: Optional[Session] = None,
                 address: str = "", gender: str = ""):
        super().__init__(user_id, username, password, email,
                         UserRole.STUDENT, first_name, last_name)
        self.course = course
        self.session = session
        self.address = address
        self.gender = gender
        self.leave_applications: list = []
        self.feedbacks: list = []
        self.results: list = []

    def get_attendance_summary(self, attendance_records: list) -> dict:
        student_records = [r for r in attendance_records if r.student == self]
        total = len(student_records)
        present = sum(1 for r in student_records if r.status == AttendanceStatus.PRESENT)
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0.0
        return {
            "total": total,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 2)
        }

    def __repr__(self):
        return f"<Student id={self.user_id} name={self.get_full_name()}>"


# ─────────────────────────────────────────────
# Attendance
# ─────────────────────────────────────────────

class AttendanceSession:
    def __init__(self, session_id: str, subject: Subject,
                 staff: Staff, attendance_date: date):
        self.session_id = session_id
        self.subject = subject
        self.staff = staff
        self.attendance_date = attendance_date
        self.created_at = datetime.now()
        self.records: list = []

    def add_record(self, record) -> None:
        self.records.append(record)

    def get_records(self) -> list:
        return list(self.records)

    def __repr__(self):
        return (f"<AttendanceSession subject={self.subject.name} "
                f"date={self.attendance_date}>")


class AttendanceRecord:
    def __init__(self, record_id: str, attendance_session: AttendanceSession,
                 student: Student, status: str):
        if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
            raise ValueError(f"Invalid attendance status: {status}")
        self.record_id = record_id
        self.attendance_session = attendance_session
        self.student = student
        self.status = status
        self.created_at = datetime.now()

    def update_status(self, status: str) -> None:
        if status not in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT):
            raise ValueError(f"Invalid attendance status: {status}")
        self.status = status

    def __repr__(self):
        return (f"<AttendanceRecord student={self.student.get_full_name()} "
                f"status={self.status}>")


# ─────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────

class Result:
    def __init__(self, result_id: str, student: Student, subject: Subject,
                 session: Session, test_score: float, exam_score: float):
        self.result_id = result_id
        self.student = student
        self.subject = subject
        self.session = session
        self.test_score = test_score
        self.exam_score = exam_score
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def get_total_score(self) -> float:
        return self.test_score + self.exam_score

    def update_scores(self, test_score: float, exam_score: float) -> None:
        self.test_score = test_score
        self.exam_score = exam_score
        self.updated_at = datetime.now()

    def __repr__(self):
        return (f"<Result student={self.student.get_full_name()} "
                f"subject={self.subject.name} total={self.get_total_score()}>")


# ─────────────────────────────────────────────
# Leave Applications
# ─────────────────────────────────────────────

class LeaveApplication:
    def __init__(self, leave_id: str, applicant: User,
                 start_date: date, end_date: date, reason: str):
        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")
        self.leave_id = leave_id
        self.applicant = applicant
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = LeaveStatus.PENDING
        self.admin_reply: str = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def approve(self, reply: str = "") -> None:
        self.status = LeaveStatus.APPROVED
        self.admin_reply = reply
        self.updated_at = datetime.now()

    def reject(self, reply: str = "") -> None:
        self.status = LeaveStatus.REJECTED
        self.admin_reply = reply
        self.updated_at = datetime.now()

    def get_duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def __repr__(self):
        return (f"<LeaveApplication id={self.leave_id} "
                f"applicant={self.applicant.get_full_name()} "
                f"status={self.status}>")


# ─────────────────────────────────────────────
# Feedback
# ─────────────────────────────────────────────

class Feedback:
    def __init__(self, feedback_id: str, sender: User,
                 message: str, subject_line: str = ""):
        self.feedback_id = feedback_id
        self.sender = sender
        self.message = message
        self.subject_line = subject_line
        self.reply: str = ""
        self.is_replied: bool = False
        self.created_at = datetime.now()
        self.replied_at: Optional[datetime] = None

    def add_reply(self, reply: str) -> None:
        self.reply = reply
        self.is_replied = True
        self.replied_at = datetime.now()

    def __repr__(self):
        return (f"<Feedback id={self.feedback_id} "
                f"from={self.sender.get_full_name()} "
                f"replied={self.is_replied}>")


# ─────────────────────────────────────────────
# Summary / Analytics
# ─────────────────────────────────────────────

class SummaryChart:
    def __init__(self, system):
        self._system = system

    def get_overall_summary(self) -> dict:
        system = self._system
        return {
            "total_students": len(system.students),
            "total_staff": len(system.staff_members),
            "total_courses": len(system.courses),
            "total_subjects": len(system.subjects),
            "total_sessions": len(system.sessions),
            "total_leave_applications": len(system.leave_applications),
            "pending_leaves": sum(
                1 for l in system.leave_applications
                if l.status == LeaveStatus.PENDING
            ),
            "total_feedbacks": len(system.feedbacks),
            "unreplied_feedbacks": sum(
                1 for f in system.feedbacks if not f.is_replied
            ),
        }

    def get_staff_summary(self, staff: Staff) -> dict:
        system = self._system
        students = staff.get_students_in_subjects(system.students)
        attendance_records = [
            r for r in system.attendance_records
            if r.attendance_session.staff == staff
        ]
        leave_apps = [
            l for l in system.leave_applications
            if l.applicant == staff
        ]
        feedbacks = [f for f in system.feedbacks if f.sender == staff]
        return {
            "staff_name": staff.get_full_name(),
            "total_subjects": len(staff.subjects),
            "total_students": len(students),
            "total_attendance_sessions": len(
                {r.attendance_session for r in attendance_records}
            ),
            "leave_applications": len(leave_apps),
            "pending_leaves": sum(
                1 for l in leave_apps if l.status == LeaveStatus.PENDING
            ),
            "approved_leaves": sum(
                1 for l in leave_apps if l.status == LeaveStatus.APPROVED
            ),
            "rejected_leaves": sum(
                1 for l in leave_apps if l.status == LeaveStatus.REJECTED
            ),
            "feedbacks_sent": len(feedbacks),
        }

    def get_student_summary(self, student: Student) -> dict:
        system = self._system
        attendance_summary = student.get_attendance_summary(
            system.attendance_records
        )
        leave_apps = [
            l for l in system.leave_applications
            if l.applicant == student
        ]
        results = [r for r in system.results if r.student == student]
        feedbacks = [f for f in system.feedbacks if f.sender == student]
        return {
            "student_name": student.get_full_name(),
            "course": student.course.name if student.course else None,
            "session": student.session.get_session_name() if student.session else None,
            "attendance": attendance_summary,
            "leave_applications": len(leave_apps),
            "pending_leaves": sum(
                1 for l in leave_apps if l.status == LeaveStatus.PENDING
            ),
            "approved_leaves": sum(
                1 for l in leave_apps if l.status == LeaveStatus.APPROVED
            ),
            "rejected_leaves": sum(
                1 for l in leave_apps if l.status == LeaveStatus.REJECTED
            ),
            "total_results": len(results),
            "feedbacks_sent": len(feedbacks),
        }


# ─────────────────────────────────────────────
# Main System / Facade
# ─────────────────────────────────────────────

class StudentManagementSystem:
    def __init__(self):
        self.admins: list[Admin] = []
        self.staff_members: list[Staff] = []
        self.students: list[Student] = []
        self.courses: list[Course] = []
        self.subjects: list[Subject] = []
        self.sessions: list[Session] = []
        self.attendance_sessions: list[AttendanceSession] = []
        self.attendance_records: list[AttendanceRecord] = []
        self.leave_applications: list[LeaveApplication] = []
        self.feedbacks: list[Feedback] = []
        self.results: list[Result] = []
        self._summary = SummaryChart(self)
        self._init_default_admin()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _init_default_admin(self) -> None:
        admin = Admin(
            user_id=self._generate_id(),
            username="admin",
            password="admin123",
            email="admin@sms.com",
            first_name="System",
            last_name="Admin"
        )
        self.admins.append(admin)

    # ── Authentication ──────────────────────────

    def authenticate(self, username: str, password: str) -> Optional[User]:
        all_users: list[User] = (
            list(self.admins) +
            list(self.staff_members) +
            list(self.students)
        )
        for user in all_users:
            if user.username == username and user.verify_password(password):
                return user
        return None

    # ── Admin Management ────────────────────────

    def add_admin(self, username: str, password: str, email: str,
                  first_name: str, last_name: str) -> Admin:
        if self._username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        admin = Admin(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        self.admins.append(admin)
        return admin

    # ── Staff Management ────────────────────────

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str,
                  address: str = "",
                  course: Optional[Course] = None) -> Staff:
        if self._username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        staff = Staff(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address,
            course=course
        )
        self.staff_members.append(staff)
        return staff

    def update_staff(self, staff: Staff, first_name: Optional[str] = None,
                     last_name: Optional[str] = None,
                     email: Optional[str] = None,
                     address: Optional[str] = None,
                     course: Optional[Course] = None) -> Staff:
        if first_name is not None:
            staff.first_name = first_name
        if last_name is not None:
            staff.last_name = last_name
        if email is not None:
            staff.email = email
        if address is not None:
            staff.address = address
        if course is not None:
            staff.course = course
        return staff

    def delete_staff(self, staff: Staff) -> bool:
        if staff in self.staff_members:
            self.staff_members.remove(staff)
            return True
        return False

    def get_staff_by_id(self, user_id: str) -> Optional[Staff]:
        for s in self.staff_members:
            if s.user_id == user_id:
                return s
        return None

    def get_all_staff(self) -> list[Staff]:
        return list(self.staff_members)

    # ── Student Management ──────────────────────

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str,
                    course: Optional[Course] = None,
                    session: Optional[Session] = None,
                    address: str = "", gender: str = "") -> Student:
        if self._username_exists(username):
            raise ValueError(f"Username '{username}' already exists")
        student = Student(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            course=course,
            session=session,
            address=address,
            gender=gender
        )
        self.students.append(student)
        return student

    def update_student(self, student: Student,
                       first_name: Optional[str] = None,
                       last_name: Optional[str] = None,
                       email: Optional[str] = None,
                       address: Optional[str] = None,
                       gender: Optional[str] = None,
                       course: Optional[Course] = None,
                       session: Optional[Session] = None) -> Student:
        if first_name is not None:
            student.first_name = first_name
        if last_name is not None:
            student.last_name = last_name
        if email is not None:
            student.email = email
        if address is not None:
            student.address = address
        if gender is not None:
            student.gender = gender
        if course is not None:
            student.course = course
        if session is not None:
            student.session = session
        return student

    def delete_student(self, student: Student) -> bool:
        if student in self.students:
            self.students.remove(student)
            return True
        return False

    def get_student_by_id(self, user_id: str) -> Optional[Student]:
        for s in self.students:
            if s.user_id == user_id:
                return s
        return None

    def get_all_students(self) -> list[Student]:
        return list(self.students)

    def get_students_by_course(self, course: Course) -> list[Student]:
        return [s for s in self.students if s.course == course]

    # ── Course Management ───────────────────────

    def add_course(self, name: str, description: str = "") -> Course:
        course = Course(
            course_id=self._generate_id(),
            name=name,
            description=description
        )
        self.courses.append(course)
        return course

    def update_course(self, course: Course, name: Optional[str] = None,
                      description: Optional[str] = None) -> Course:
        if name is not None:
            course.name = name
        if description is not None:
            course.description = description
        return course

    def delete_course(self, course: Course) -> bool:
        if course in self.courses:
            self.courses.remove(course)
            return True
        return False

    def get_course_by_id(self, course_id: str) -> Optional[Course]:
        for c in self.courses:
            if c.course_id == course_id:
                return c
        return None

    def get_all_courses(self) -> list[Course]:
        return list(self.courses)

    # ── Subject Management ──────────────────────

    def add_subject(self, name: str, course: Course,
                    staff: Optional[Staff] = None,
                    description: str = "") -> Subject:
        subject = Subject(
            subject_id=self._generate_id(),
            name=name,
            course=course,
            staff=staff,
            description=description
        )
        self.subjects.append(subject)
        course.add_subject(subject)
        if staff and subject not in staff.subjects:
            staff.subjects.append(subject)
        return subject

    def update_subject(self, subject: Subject, name: Optional[str] = None,
                       course: Optional[Course] = None,
                       staff: Optional[Staff] = None,
                       description: Optional[str] = None) -> Subject:
        if name is not None:
            subject.name = name
        if description is not None:
            subject.description = description
        if course is not None:
            if subject.course:
                subject.course.remove_subject(subject)
            subject.course = course
            course.add_subject(subject)
        if staff is not None:
            if subject.staff and subject in subject.staff.subjects:
                subject.staff.subjects.remove(subject)
            subject.staff = staff
            if subject not in staff.subjects:
                staff.subjects.append(subject)
        return subject

    def delete_subject(self, subject: Subject) -> bool:
        if subject in self.subjects:
            self.subjects.remove(subject)
            if subject.course:
                subject.course.remove_subject(subject)
            if subject.staff and subject in subject.staff.subjects:
                subject.staff.subjects.remove(subject)
            return True
        return False

    def get_subject_by_id(self, subject_id: str) -> Optional[Subject]:
        for s in self.subjects:
            if s.subject_id == subject_id:
                return s
        return None

    def get_all_subjects(self) -> list[Subject]:
        return list(self.subjects)

    def get_subjects_by_course(self, course: Course) -> list[Subject]:
        return [s for s in self.subjects if s.course == course]

    # ── Session Management ──────────────────────

    def add_session(self, start_year: int, end_year: int) -> Session:
        session = Session(
            session_id=self._generate_id(),
            start_year=start_year,
            end_year=end_year
        )
        self.sessions.append(session)
        return session

    def update_session(self, session: Session,
                       start_year: Optional[int] = None,
                       end_year: Optional[int] = None) -> Session:
        new_start = start_year if start_year is not None else session.start_year
        new_end = end_year if end_year is not None else session.end_year
        if new_end <= new_start:
            raise ValueError("end_year must be greater than start_year")
        session.start_year = new_start
        session.end_year = new_end
        return session

    def delete_session(self, session: Session) -> bool:
        if session in self.sessions:
            self.sessions.remove(session)
            return True
        return False

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        for s in self.sessions:
            if s.session_id == session_id:
                return s
        return None

    def get_all_sessions(self) -> list[Session]:
        return list(self.sessions)

    # ── Attendance Management ───────────────────

    def create_attendance_session(self, subject: Subject, staff: Staff,
                                  attendance_date: Optional[date] = None) -> AttendanceSession:
        if attendance_date is None:
            attendance_date = date.today()
        att_session = AttendanceSession(
            session_id=self._generate_id(),
            subject=subject,
            staff=staff,
            attendance_date=attendance_date
        )
        self.attendance_sessions.append(att_session)
        return att_session

    def take_attendance(self, attendance_session: AttendanceSession,
                        student: Student, status: str) -> AttendanceRecord:
        record = AttendanceRecord(
            record_id=self._generate_id(),
            attendance_session=attendance_session,
            student=student,
            status=status
        )
        attendance_session.add_record(record)
        self.attendance_records.append(record)
        return record

    def update_attendance(self, record: AttendanceRecord, status: str) -> AttendanceRecord:
        record.update_status(status)
        return record

    def get_attendance_by_subject(self, subject: Subject) -> list[AttendanceRecord]:
        return [r for r in self.attendance_records
                if r.attendance_session.subject == subject]

    def get_attendance_by_student(self, student: Student) -> list[AttendanceRecord]:
        return [r for r in self.attendance_records if r.student == student]

    def get_attendance_by_staff(self, staff: Staff) -> list[AttendanceRecord]:
        return [r for r in self.attendance_records
                if r.attendance_session.staff == staff]

    def get_all_attendance_sessions(self) -> list[AttendanceSession]:
        return list(self.attendance_sessions)

    # ── Result Management ───────────────────────

    def add_result(self, student: Student, subject: Subject,
                   session: Session, test_score: float,
                   exam_score: float) -> Result:
        existing = self._find_result(student, subject, session)
        if existing:
            existing.update_scores(test_score, exam_score)
            return existing
        result = Result(
            result_id=self._generate_id(),
            student=student,
            subject=subject,
            session=session,
            test_score=test_score,
            exam_score=exam_score
        )
        self.results.append(result)
        student.results.append(result)
        return result

    def update_result(self, result: Result, test_score: Optional[float] = None,
                      exam_score: Optional[float] = None) -> Result:
        new_test = test_score if test_score is not None else result.test_score
        new_exam = exam_score if exam_score is not None else result.exam_score
        result.update_scores(new_test, new_exam)
        return result

    def get_results_by_student(self, student: Student) -> list[Result]:
        return [r for r in self.results if r.student == student]

    def get_results_by_subject(self, subject: Subject) -> list[Result]:
        return [r for r in self.results if r.subject == subject]

    def _find_result(self, student: Student, subject: Subject,
                     session: Session) -> Optional[Result]:
        for r in self.results:
            if r.student == student and r.subject == subject and r.session == session:
                return r
        return None

    # ── Leave Management ────────────────────────

    def apply_for_leave(self, applicant: User, start_date: date,
                        end_date: date, reason: str) -> LeaveApplication:
        leave = LeaveApplication(
            leave_id=self._generate_id(),
            applicant=applicant,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        self.leave_applications.append(leave)
        if isinstance(applicant, Student):
            applicant.leave_applications.append(leave)
        elif isinstance(applicant, Staff):
            applicant.leave_applications.append(leave)
        return leave

    def approve_leave(self, leave: LeaveApplication, reply: str = "") -> LeaveApplication:
        leave.approve(reply)
        return leave

    def reject_leave(self, leave: LeaveApplication, reply: str = "") -> LeaveApplication:
        leave.reject(reply)
        return leave

    def get_all_leave_applications(self) -> list[LeaveApplication]:
        return list(self.leave_applications)

    def get_leave_by_applicant(self, applicant: User) -> list[LeaveApplication]:
        return [l for l in self.leave_applications if l.applicant == applicant]

    def get_pending_leaves(self) -> list[LeaveApplication]:
        return [l for l in self.leave_applications
                if l.status == LeaveStatus.PENDING]

    def get_leave_by_id(self, leave_id: str) -> Optional[LeaveApplication]:
        for l in self.leave_applications:
            if l.leave_id == leave_id:
                return l
        return None

    # ── Feedback Management ─────────────────────

    def send_feedback(self, sender: User, message: str,
                      subject_line: str = "") -> Feedback:
        feedback = Feedback(
            feedback_id=self._generate_id(),
            sender=sender,
            message=message,
            subject_line=subject_line
        )
        self.feedbacks.append(feedback)
        if isinstance(sender, Student):
            sender.feedbacks.append(feedback)
        elif isinstance(sender, Staff):
            sender.feedbacks.append(feedback)
        return feedback

    def reply_feedback(self, feedback: Feedback, reply: str) -> Feedback:
        feedback.add_reply(reply)
        return feedback

    def get_all_feedbacks(self) -> list[Feedback]:
        return list(self.feedbacks)

    def get_feedbacks_by_sender(self, sender: User) -> list[Feedback]:
        return [f for f in self.feedbacks if f.sender == sender]

    def get_unreplied_feedbacks(self) -> list[Feedback]:
        return [f for f in self.feedbacks if not f.is_replied]

    def get_feedback_by_id(self, feedback_id: str) -> Optional[Feedback]:
        for f in self.feedbacks:
            if f.feedback_id == feedback_id:
                return f
        return None

    # ── Summary / Charts ────────────────────────

    def get_overall_summary(self) -> dict:
        return self._summary.get_overall_summary()

    def get_staff_summary(self, staff: Staff) -> dict:
        return self._summary.get_staff_summary(staff)

    def get_student_summary(self, student: Student) -> dict:
        return self._summary.get_student_summary(student)

    # ── Helpers ─────────────────────────────────

    def _username_exists(self, username: str) -> bool:
        all_users: list[User] = (
            list(self.admins) +
            list(self.staff_members) +
            list(self.students)
        )
        return any(u.username == username for u in all_users)

    def get_user_by_username(self, username: str) -> Optional[User]:
        all_users: list[User] = (
            list(self.admins) +
            list(self.staff_members) +
            list(self.students)
        )
        for u in all_users:
            if u.username == username:
                return u
        return None

    def __repr__(self):
        return (f"<StudentManagementSystem "
                f"students={len(self.students)} "
                f"staff={len(self.staff_members)} "
                f"courses={len(self.courses)}>")


# ─────────────────────────────────────────────
# Demo / Entry Point
# ─────────────────────────────────────────────

def main():
    sms = StudentManagementSystem()

    # ── Authenticate default admin ──
    admin_user = sms.authenticate("admin", "admin123")
    assert admin_user is not None
    assert admin_user.role == UserRole.ADMIN
    print(f"Authenticated: {admin_user}")

    # ── Courses ──
    cs_course = sms.add_course("Computer Science", "CS degree programme")
    math_course = sms.add_course("Mathematics", "Pure Mathematics")
    print(f"Courses: {sms.get_all_courses()}")

    # ── Sessions ──
    session_2023 = sms.add_session(2023, 2024)
    session_2024 = sms.add_session(2024, 2025)
    print(f"Sessions: {sms.get_all_sessions()}")

    # ── Staff ──
    staff1 = sms.add_staff(
        username="jdoe_staff",
        password="pass123",
        email="jdoe@sms.com",
        first_name="John",
        last_name="Doe",
        address="123 Main St",
        course=cs_course
    )
    print(f"Staff added: {staff1}")

    # ── Subjects ──
    subj_python = sms.add_subject("Python Programming", cs_course, staff1,
                                  "Intro to Python")
    subj_algo = sms.add_subject("Algorithms", cs_course, staff1,
                                "Data Structures & Algorithms")
    print(f"Subjects: {sms.get_all_subjects()}")
    print(f"Staff subjects: {staff1.get_subjects()}")

    # ── Students ──
    student1 = sms.add_student(
        username="alice",
        password="alice123",
        email="alice@sms.com",
        first_name="Alice",
        last_name="Smith",
        course=cs_course,
        session=session_2023,
        gender="Female"
    )
    student2 = sms.add_student(
        username="bob",
        password="bob123",
        email="bob@sms.com",
        first_name="Bob",
        last_name="Jones",
        course=cs_course,
        session=session_2023,
        gender="Male"
    )
    print(f"Students: {sms.get_all_students()}")

    # ── Attendance ──
    att_session = sms.create_attendance_session(subj_python, staff1)
    rec1 = sms.take_attendance(att_session, student1, AttendanceStatus.PRESENT)
    rec2 = sms.take_attendance(att_session, student2, AttendanceStatus.ABSENT)
    print(f"Attendance records: {att_session.get_records()}")

    att_session2 = sms.create_attendance_session(subj_python, staff1)
    sms.take_attendance(att_session2, student1, AttendanceStatus.PRESENT)
    sms.take_attendance(att_session2, student2, AttendanceStatus.PRESENT)

    print(f"Alice attendance: {student1.get_attendance_summary(sms.attendance_records)}")
    print(f"Bob attendance: {student2.get_attendance_summary(sms.attendance_records)}")

    # ── Update attendance ──
    sms.update_attendance(rec2, AttendanceStatus.PRESENT)
    print(f"Bob updated attendance: {student2.get_attendance_summary(sms.attendance_records)}")

    # ── Results ──
    result1 = sms.add_result(student1, subj_python, session_2023,
                             test_score=35.0, exam_score=55.0)
    result2 = sms.add_result(student2, subj_python, session_2023,
                             test_score=28.0, exam_score=48.0)
    print(f"Alice result: {result1} total={result1.get_total_score()}")
    print(f"Bob result: {result2} total={result2.get_total_score()}")

    sms.update_result(result2, exam_score=52.0)
    print(f"Bob updated result total={result2.get_total_score()}")

    # ── Leave Applications ──
    leave1 = sms.apply_for_leave(
        student1,
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 5),
        reason="Medical appointment"
    )
    leave2 = sms.apply_for_leave(
        staff1,
        start_date=date(2024, 3, 10),
        end_date=date(2024, 3, 12),
        reason="Family event"
    )
    print(f"Pending leaves: {sms.get_pending_leaves()}")

    sms.approve_leave(leave1, reply="Approved. Get well soon.")
    sms.reject_leave(leave2, reply="Insufficient notice period.")
    print(f"Leave1 status: {leave1.status}, reply: {leave1.admin_reply}")
    print(f"Leave2 status: {leave2.status}, reply: {leave2.admin_reply}")

    # ── Feedback ──
    fb1 = sms.send_feedback(student1, "The Python course is excellent!", "Course Feedback")
    fb2 = sms.send_feedback(staff1, "Need more lab resources.", "Resource Request")
    print(f"Unreplied feedbacks: {sms.get_unreplied_feedbacks()}")

    sms.reply_feedback(fb1, "Thank you for your kind words!")
    sms.reply_feedback(fb2, "We will look into this.")
    print(f"FB1 replied: {fb1.is_replied}, reply: {fb1.reply}")

    # ── Summaries ──
    print("\n=== Overall Summary ===")
    overall = sms.get_overall_summary()
    for k, v in overall.items():
        print(f"  {k}: {v}")

    print("\n=== Staff Summary (John Doe) ===")
    staff_summary = sms.get_staff_summary(staff1)
    for k, v in staff_summary.items():
        print(f"  {k}: {v}")

    print("\n=== Student Summary (Alice) ===")
    student_summary = sms.get_student_summary(student1)
    for k, v in student_summary.items():
        print(f"  {k}: {v}")

    # ── Update / Delete ──
    sms.update_student(student2, first_name="Robert")
    print(f"Updated student2 name: {student2.get_full_name()}")

    sms.update_staff(staff1, address="456 New Ave")
    print(f"Updated staff1 address: {staff1.address}")

    sms.update_course(cs_course, description="Updated CS description")
    print(f"Updated course: {cs_course.description}")

    sms.update_session(session_2024, start_year=2024, end_year=2026)
    print(f"Updated session: {session_2024.get_session_name()}")

    # ── Delete operations ──
    math_staff = sms.add_staff("mstaff", "pass", "m@sms.com", "Mary", "Brown")
    math_subj = sms.add_subject("Calculus", math_course, math_staff)
    print(f"Before delete subjects: {len(sms.subjects)}")
    sms.delete_subject(math_subj)
    print(f"After delete subject: {len(sms.subjects)}")

    temp_student = sms.add_student("temp", "pass", "t@sms.com", "Temp", "User")
    print(f"Before delete students: {len(sms.students)}")
    sms.delete_student(temp_student)
    print(f"After delete student: {len(sms.students)}")

    sms.delete_staff(math_staff)
    print(f"After delete staff: {len(sms.staff_members)}")

    sms.delete_course(math_course)
    print(f"After delete course: {len(sms.courses)}")

    sms.delete_session(session_2024)
    print(f"After delete session: {len(sms.sessions)}")

    print(f"\nFinal system state: {sms}")


if __name__ == "__main__":
    main()