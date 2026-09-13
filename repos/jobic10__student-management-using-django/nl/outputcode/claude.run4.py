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

    def __repr__(self):
        return f"Subject(id={self.subject_id}, name={self.name}, course_id={self.course_id})"


class Session:
    def __init__(self, session_id: str, start_year: int, end_year: int):
        if end_year <= start_year:
            raise ValueError("End year must be greater than start year")
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year

    def get_session_name(self) -> str:
        return f"{self.start_year}-{self.end_year}"

    def __repr__(self):
        return f"Session(id={self.session_id}, {self.get_session_name()})"


class Attendance:
    def __init__(self, attendance_id: str, subject_id: str, staff_id: str,
                 attendance_date: date, session_id: str):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.staff_id = staff_id
        self.attendance_date = attendance_date
        self.session_id = session_id
        self.records: list = []
        self.created_at = datetime.now()

    def __repr__(self):
        return f"Attendance(id={self.attendance_id}, subject={self.subject_id}, date={self.attendance_date})"


class AttendanceRecord:
    def __init__(self, record_id: str, attendance_id: str, student_id: str, status: bool):
        self.record_id = record_id
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.status = status

    def __repr__(self):
        return f"AttendanceRecord(student={self.student_id}, status={'Present' if self.status else 'Absent'})"


class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 exam_marks: float, assignment_marks: float):
        if exam_marks < 0 or exam_marks > 100:
            raise ValueError("Exam marks must be between 0 and 100")
        if assignment_marks < 0 or assignment_marks > 100:
            raise ValueError("Assignment marks must be between 0 and 100")
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def get_total_marks(self) -> float:
        return self.exam_marks + self.assignment_marks

    def update_marks(self, exam_marks: float, assignment_marks: float):
        if exam_marks < 0 or exam_marks > 100:
            raise ValueError("Exam marks must be between 0 and 100")
        if assignment_marks < 0 or assignment_marks > 100:
            raise ValueError("Assignment marks must be between 0 and 100")
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Result(student={self.student_id}, subject={self.subject_id}, total={self.get_total_marks()})"


class LeaveApplication:
    STATUSES = ["pending", "approved", "rejected"]

    def __init__(self, leave_id: str, applicant_id: str, applicant_type: str,
                 start_date: date, end_date: date, reason: str):
        if end_date < start_date:
            raise ValueError("End date must be on or after start date")
        if applicant_type not in ["student", "staff"]:
            raise ValueError("Applicant type must be 'student' or 'staff'")
        self.leave_id = leave_id
        self.applicant_id = applicant_id
        self.applicant_type = applicant_type
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = "pending"
        self.admin_reply = ""
        self.applied_at = datetime.now()
        self.updated_at = datetime.now()

    def approve(self, reply: str = ""):
        self.status = "approved"
        self.admin_reply = reply
        self.updated_at = datetime.now()

    def reject(self, reply: str = ""):
        self.status = "rejected"
        self.admin_reply = reply
        self.updated_at = datetime.now()

    def get_duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def __repr__(self):
        return f"LeaveApplication(id={self.leave_id}, applicant={self.applicant_id}, status={self.status})"


class Feedback:
    def __init__(self, feedback_id: str, sender_id: str, sender_type: str, message: str):
        if sender_type not in ["student", "staff"]:
            raise ValueError("Sender type must be 'student' or 'staff'")
        self.feedback_id = feedback_id
        self.sender_id = sender_id
        self.sender_type = sender_type
        self.message = message
        self.reply = ""
        self.is_replied = False
        self.sent_at = datetime.now()
        self.replied_at: Optional[datetime] = None

    def add_reply(self, reply: str):
        if not reply.strip():
            raise ValueError("Reply cannot be empty")
        self.reply = reply
        self.is_replied = True
        self.replied_at = datetime.now()

    def __repr__(self):
        return f"Feedback(id={self.feedback_id}, sender={self.sender_id}, replied={self.is_replied})"


class StudentManagementSystem:
    def __init__(self):
        self.users: dict[str, User] = {}
        self.courses: dict[str, Course] = {}
        self.subjects: dict[str, Subject] = {}
        self.sessions: dict[str, Session] = {}
        self.attendances: dict[str, Attendance] = {}
        self.attendance_records: dict[str, AttendanceRecord] = {}
        self.results: dict[str, Result] = {}
        self.leave_applications: dict[str, LeaveApplication] = {}
        self.feedbacks: dict[str, Feedback] = {}
        self.current_user: Optional[User] = None
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
        self.users[admin.user_id] = admin

    def login(self, username: str, password: str) -> Optional[User]:
        for user in self.users.values():
            if user.username == username and user.verify_password(password) and user.is_active:
                self.current_user = user
                return user
        return None

    def logout(self):
        self.current_user = None

    def _require_role(self, *roles):
        if self.current_user is None:
            raise PermissionError("No user is logged in")
        if self.current_user.role not in roles:
            raise PermissionError(f"Access denied. Required role(s): {roles}")

    # ==================== ADMIN: Staff Management ====================

    def add_staff(self, username: str, password: str, email: str,
                  first_name: str, last_name: str, address: str) -> Staff:
        self._require_role("admin")
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists")
            if user.email == email:
                raise ValueError(f"Email '{email}' already exists")
        staff = Staff(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address
        )
        self.users[staff.user_id] = staff
        return staff

    def update_staff(self, staff_id: str, first_name: Optional[str] = None,
                     last_name: Optional[str] = None, email: Optional[str] = None,
                     address: Optional[str] = None, password: Optional[str] = None) -> Staff:
        self._require_role("admin")
        staff = self.users.get(staff_id)
        if not staff or not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        if first_name:
            staff.first_name = first_name
        if last_name:
            staff.last_name = last_name
        if email:
            for user in self.users.values():
                if user.email == email and user.user_id != staff_id:
                    raise ValueError(f"Email '{email}' already exists")
            staff.email = email
        if address:
            staff.address = address
        if password:
            staff.update_password(password)
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        self._require_role("admin")
        staff = self.users.get(staff_id)
        if not staff or not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        del self.users[staff_id]
        return True

    def get_all_staff(self) -> list[Staff]:
        self._require_role("admin")
        return [u for u in self.users.values() if isinstance(u, Staff)]

    def get_staff_by_id(self, staff_id: str) -> Optional[Staff]:
        user = self.users.get(staff_id)
        if isinstance(user, Staff):
            return user
        return None

    # ==================== ADMIN: Student Management ====================

    def add_student(self, username: str, password: str, email: str,
                    first_name: str, last_name: str, address: str,
                    course_id: str, session_id: str, gender: str) -> Student:
        self._require_role("admin")
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        if gender not in ["male", "female", "other"]:
            raise ValueError("Gender must be 'male', 'female', or 'other'")
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists")
            if user.email == email:
                raise ValueError(f"Email '{email}' already exists")
        student = Student(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            address=address,
            course_id=course_id,
            session_id=session_id,
            gender=gender
        )
        self.users[student.user_id] = student
        self.courses[course_id].students.append(student.user_id)
        return student

    def update_student(self, student_id: str, first_name: Optional[str] = None,
                       last_name: Optional[str] = None, email: Optional[str] = None,
                       address: Optional[str] = None, course_id: Optional[str] = None,
                       session_id: Optional[str] = None, gender: Optional[str] = None,
                       password: Optional[str] = None) -> Student:
        self._require_role("admin")
        student = self.users.get(student_id)
        if not student or not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        if first_name:
            student.first_name = first_name
        if last_name:
            student.last_name = last_name
        if email:
            for user in self.users.values():
                if user.email == email and user.user_id != student_id:
                    raise ValueError(f"Email '{email}' already exists")
            student.email = email
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
            student.session_id = session_id
        if gender:
            if gender not in ["male", "female", "other"]:
                raise ValueError("Gender must be 'male', 'female', or 'other'")
            student.gender = gender
        if password:
            student.update_password(password)
        return student

    def delete_student(self, student_id: str) -> bool:
        self._require_role("admin")
        student = self.users.get(student_id)
        if not student or not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        course = self.courses.get(student.course_id)
        if course and student_id in course.students:
            course.students.remove(student_id)
        del self.users[student_id]
        return True

    def get_all_students(self) -> list[Student]:
        self._require_role("admin")
        return [u for u in self.users.values() if isinstance(u, Student)]

    def get_student_by_id(self, student_id: str) -> Optional[Student]:
        user = self.users.get(student_id)
        if isinstance(user, Student):
            return user
        return None

    # ==================== ADMIN: Course Management ====================

    def add_course(self, name: str) -> Course:
        self._require_role("admin")
        for course in self.courses.values():
            if course.name.lower() == name.lower():
                raise ValueError(f"Course '{name}' already exists")
        course = Course(course_id=self._generate_id(), name=name)
        self.courses[course.course_id] = course
        return course

    def update_course(self, course_id: str, name: str) -> Course:
        self._require_role("admin")
        course = self.courses.get(course_id)
        if not course:
            raise ValueError(f"Course with id '{course_id}' not found")
        for c in self.courses.values():
            if c.name.lower() == name.lower() and c.course_id != course_id:
                raise ValueError(f"Course '{name}' already exists")
        course.name = name
        return course

    def delete_course(self, course_id: str) -> bool:
        self._require_role("admin")
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        subjects_in_course = [s for s in self.subjects.values() if s.course_id == course_id]
        if subjects_in_course:
            raise ValueError("Cannot delete course with associated subjects")
        students_in_course = [u for u in self.users.values()
                              if isinstance(u, Student) and u.course_id == course_id]
        if students_in_course:
            raise ValueError("Cannot delete course with enrolled students")
        del self.courses[course_id]
        return True

    def get_all_courses(self) -> list[Course]:
        return list(self.courses.values())

    def get_course_by_id(self, course_id: str) -> Optional[Course]:
        return self.courses.get(course_id)

    # ==================== ADMIN: Subject Management ====================

    def add_subject(self, name: str, course_id: str, staff_id: str) -> Subject:
        self._require_role("admin")
        if course_id not in self.courses:
            raise ValueError(f"Course with id '{course_id}' not found")
        staff = self.users.get(staff_id)
        if not staff or not isinstance(staff, Staff):
            raise ValueError(f"Staff with id '{staff_id}' not found")
        subject = Subject(
            subject_id=self._generate_id(),
            name=name,
            course_id=course_id,
            staff_id=staff_id
        )
        self.subjects[subject.subject_id] = subject
        self.courses[course_id].subjects.append(subject.subject_id)
        staff.subjects.append(subject.subject_id)
        return subject

    def update_subject(self, subject_id: str, name: Optional[str] = None,
                       course_id: Optional[str] = None, staff_id: Optional[str] = None) -> Subject:
        self._require_role("admin")
        subject = self.subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
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
            new_staff = self.users.get(staff_id)
            if not new_staff or not isinstance(new_staff, Staff):
                raise ValueError(f"Staff with id '{staff_id}' not found")
            old_staff = self.users.get(subject.staff_id)
            if old_staff and isinstance(old_staff, Staff) and subject_id in old_staff.subjects:
                old_staff.subjects.remove(subject_id)
            subject.staff_id = staff_id
            new_staff.subjects.append(subject_id)
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        self._require_role("admin")
        subject = self.subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        course = self.courses.get(subject.course_id)
        if course and subject_id in course.subjects:
            course.subjects.remove(subject_id)
        staff = self.users.get(subject.staff_id)
        if staff and isinstance(staff, Staff) and subject_id in staff.subjects:
            staff.subjects.remove(subject_id)
        del self.subjects[subject_id]
        return True

    def get_all_subjects(self) -> list[Subject]:
        return list(self.subjects.values())

    def get_subject_by_id(self, subject_id: str) -> Optional[Subject]:
        return self.subjects.get(subject_id)

    def get_subjects_by_course(self, course_id: str) -> list[Subject]:
        return [s for s in self.subjects.values() if s.course_id == course_id]

    def get_subjects_by_staff(self, staff_id: str) -> list[Subject]:
        return [s for s in self.subjects.values() if s.staff_id == staff_id]

    # ==================== ADMIN: Session Management ====================

    def add_session(self, start_year: int, end_year: int) -> Session:
        self._require_role("admin")
        for session in self.sessions.values():
            if session.start_year == start_year and session.end_year == end_year:
                raise ValueError(f"Session {start_year}-{end_year} already exists")
        session = Session(
            session_id=self._generate_id(),
            start_year=start_year,
            end_year=end_year
        )
        self.sessions[session.session_id] = session
        return session

    def update_session(self, session_id: str, start_year: int, end_year: int) -> Session:
        self._require_role("admin")
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session with id '{session_id}' not found")
        if end_year <= start_year:
            raise ValueError("End year must be greater than start year")
        session.start_year = start_year
        session.end_year = end_year
        return session

    def delete_session(self, session_id: str) -> bool:
        self._require_role("admin")
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        students_in_session = [u for u in self.users.values()
                               if isinstance(u, Student) and u.session_id == session_id]
        if students_in_session:
            raise ValueError("Cannot delete session with enrolled students")
        del self.sessions[session_id]
        return True

    def get_all_sessions(self) -> list[Session]:
        return list(self.sessions.values())

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    # ==================== ADMIN: View Attendance ====================

    def get_all_attendance(self) -> list[Attendance]:
        self._require_role("admin")
        return list(self.attendances.values())

    def get_attendance_by_subject(self, subject_id: str) -> list[Attendance]:
        self._require_role("admin")
        return [a for a in self.attendances.values() if a.subject_id == subject_id]

    def get_student_attendance_summary(self, student_id: str) -> dict:
        self._require_role("admin", "staff", "student")
        if self.current_user.role == "student" and self.current_user.user_id != student_id:
            raise PermissionError("Students can only view their own attendance")
        total = 0
        present = 0
        for record in self.attendance_records.values():
            if record.student_id == student_id:
                total += 1
                if record.status:
                    present += 1
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0
        return {
            "student_id": student_id,
            "total_classes": total,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 2)
        }

    # ==================== ADMIN: Leave Management ====================

    def get_all_leave_applications(self) -> list[LeaveApplication]:
        self._require_role("admin")
        return list(self.leave_applications.values())

    def get_pending_leave_applications(self) -> list[LeaveApplication]:
        self._require_role("admin")
        return [la for la in self.leave_applications.values() if la.status == "pending"]

    def approve_leave(self, leave_id: str, reply: str = "") -> LeaveApplication:
        self._require_role("admin")
        leave = self.leave_applications.get(leave_id)
        if not leave:
            raise ValueError(f"Leave application with id '{leave_id}' not found")
        if leave.status != "pending":
            raise ValueError("Only pending leave applications can be approved")
        leave.approve(reply)
        return leave

    def reject_leave(self, leave_id: str, reply: str = "") -> LeaveApplication:
        self._require_role("admin")
        leave = self.leave_applications.get(leave_id)
        if not leave:
            raise ValueError(f"Leave application with id '{leave_id}' not found")
        if leave.status != "pending":
            raise ValueError("Only pending leave applications can be rejected")
        leave.reject(reply)
        return leave

    # ==================== ADMIN: Feedback Management ====================

    def get_all_feedbacks(self) -> list[Feedback]:
        self._require_role("admin")
        return list(self.feedbacks.values())

    def reply_feedback(self, feedback_id: str, reply: str) -> Feedback:
        self._require_role("admin")
        feedback = self.feedbacks.get(feedback_id)
        if not feedback:
            raise ValueError(f"Feedback with id '{feedback_id}' not found")
        feedback.add_reply(reply)
        return feedback

    # ==================== ADMIN: Summary/Dashboard ====================

    def get_admin_summary(self) -> dict:
        self._require_role("admin")
        all_students = [u for u in self.users.values() if isinstance(u, Student)]
        all_staff = [u for u in self.users.values() if isinstance(u, Staff)]
        pending_leaves = [la for la in self.leave_applications.values() if la.status == "pending"]
        unreplied_feedbacks = [f for f in self.feedbacks.values() if not f.is_replied]
        return {
            "total_students": len(all_students),
            "total_staff": len(all_staff),
            "total_courses": len(self.courses),
            "total_subjects": len(self.subjects),
            "total_sessions": len(self.sessions),
            "total_leave_applications": len(self.leave_applications),
            "pending_leave_applications": len(pending_leaves),
            "total_feedbacks": len(self.feedbacks),
            "unreplied_feedbacks": len(unreplied_feedbacks),
            "total_attendance_records": len(self.attendances)
        }

    # ==================== STAFF: Attendance Management ====================

    def take_attendance(self, subject_id: str, attendance_date: date,
                        session_id: str, student_statuses: dict[str, bool]) -> Attendance:
        self._require_role("staff")
        subject = self.subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        if subject.staff_id != self.current_user.user_id:
            raise PermissionError("Staff can only take attendance for their own subjects")
        if session_id not in self.sessions:
            raise ValueError(f"Session with id '{session_id}' not found")
        existing = [a for a in self.attendances.values()
                    if a.subject_id == subject_id and a.attendance_date == attendance_date
                    and a.session_id == session_id]
        if existing:
            raise ValueError("Attendance already taken for this subject on this date")
        attendance = Attendance(
            attendance_id=self._generate_id(),
            subject_id=subject_id,
            staff_id=self.current_user.user_id,
            attendance_date=attendance_date,
            session_id=session_id
        )
        self.attendances[attendance.attendance_id] = attendance
        for student_id, status in student_statuses.items():
            student = self.users.get(student_id)
            if not student or not isinstance(student, Student):
                raise ValueError(f"Student with id '{student_id}' not found")
            record = AttendanceRecord(
                record_id=self._generate_id(),
                attendance_id=attendance.attendance_id,
                student_id=student_id,
                status=status
            )
            self.attendance_records[record.record_id] = record
            attendance.records.append(record.record_id)
        return attendance

    def update_attendance(self, attendance_id: str,
                          student_statuses: dict[str, bool]) -> Attendance:
        self._require_role("staff")
        attendance = self.attendances.get(attendance_id)
        if not attendance:
            raise ValueError(f"Attendance with id '{attendance_id}' not found")
        if attendance.staff_id != self.current_user.user_id:
            raise PermissionError("Staff can only update their own attendance records")
        for record_id in attendance.records:
            record = self.attendance_records.get(record_id)
            if record and record.student_id in student_statuses:
                record.status = student_statuses[record.student_id]
        return attendance

    def get_staff_attendance_records(self, staff_id: Optional[str] = None) -> list[Attendance]:
        self._require_role("staff", "admin")
        target_id = staff_id if staff_id else self.current_user.user_id
        return [a for a in self.attendances.values() if a.staff_id == target_id]

    # ==================== STAFF: Result Management ====================

    def add_result(self, student_id: str, subject_id: str,
                   exam_marks: float, assignment_marks: float) -> Result:
        self._require_role("staff")
        subject = self.subjects.get(subject_id)
        if not subject:
            raise ValueError(f"Subject with id '{subject_id}' not found")
        if subject.staff_id != self.current_user.user_id:
            raise PermissionError("Staff can only add results for their own subjects")
        student = self.users.get(student_id)
        if not student or not isinstance(student, Student):
            raise ValueError(f"Student with id '{student_id}' not found")
        existing = [r for r in self.results.values()
                    if r.student_id == student_id and r.subject_id == subject_id]
        if existing:
            raise ValueError("Result already exists for this student and subject")
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
        self._require_role("staff")
        result = self.results.get(result_id)
        if not result:
            raise ValueError(f"Result with id '{result_id}' not found")
        subject = self.subjects.get(result.subject_id)
        if not subject or subject.staff_id != self.current_user.user_id:
            raise PermissionError("Staff can only update results for their own subjects")
        result.update_marks(exam_marks, assignment_marks)
        return result

    def get_results_by_subject(self, subject_id: str) -> list[Result]:
        self._require_role("staff", "admin")
        return [r for r in self.results.values() if r.subject_id == subject_id]

    def get_results_by_student(self, student_id: str) -> list[Result]:
        self._require_role("staff", "admin", "student")
        if self.current_user.role == "student" and self.current_user.user_id != student_id:
            raise PermissionError("Students can only view their own results")
        return [r for r in self.results.values() if r.student_id == student_id]

    # ==================== STAFF: Summary/Dashboard ====================

    def get_staff_summary(self) -> dict:
        self._require_role("staff")
        staff_id = self.current_user.user_id
        staff_subjects = [s for s in self.subjects.values() if s.staff_id == staff_id]
        subject_ids = [s.subject_id for s in staff_subjects]
        staff_attendances = [a for a in self.attendances.values() if a.staff_id == staff_id]
        staff_leaves = [la for la in self.leave_applications.values()
                        if la.applicant_id == staff_id]
        pending_leaves = [la for la in staff_leaves if la.status == "pending"]
        approved_leaves = [la for la in staff_leaves if la.status == "approved"]
        rejected_leaves = [la for la in staff_leaves if la.status == "rejected"]
        student_ids_set = set()
        for subject in staff_subjects:
            course = self.courses.get(subject.course_id)
            if course:
                for sid in course.students:
                    student_ids_set.add(sid)
        return {
            "staff_id": staff_id,
            "total_subjects": len(staff_subjects),
            "total_students": len(student_ids_set),
            "total_attendance_taken": len(staff_attendances),
            "total_leave_applications": len(staff_leaves),
            "pending_leaves": len(pending_leaves),
            "approved_leaves": len(approved_leaves),
            "rejected_leaves": len(rejected_leaves)
        }

    # ==================== STUDENT: View Attendance ====================

    def get_student_attendance(self, student_id: Optional[str] = None) -> list[AttendanceRecord]:
        self._require_role("student", "admin", "staff")
        target_id = student_id if student_id else self.current_user.user_id
        if self.current_user.role == "student" and self.current_user.user_id != target_id:
            raise PermissionError("Students can only view their own attendance")
        return [r for r in self.attendance_records.values() if r.student_id == target_id]

    def get_student_attendance_by_subject(self, subject_id: str,
                                          student_id: Optional[str] = None) -> dict:
        self._require_role("student", "admin", "staff")
        target_id = student_id if student_id else self.current_user.user_id
        if self.current_user.role == "student" and self.current_user.user_id != target_id:
            raise PermissionError("Students can only view their own attendance")
        subject_attendances = [a for a in self.attendances.values()
                               if a.subject_id == subject_id]
        attendance_ids = {a.attendance_id for a in subject_attendances}
        student_records = [r for r in self.attendance_records.values()
                           if r.student_id == target_id and r.attendance_id in attendance_ids]
        total = len(student_records)
        present = sum(1 for r in student_records if r.status)
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0
        return {
            "subject_id": subject_id,
            "student_id": target_id,
            "total_classes": total,
            "present": present,
            "absent": absent,
            "percentage": round(percentage, 2),
            "records": student_records
        }

    # ==================== STUDENT: Summary/Dashboard ====================

    def get_student_summary(self) -> dict:
        self._require_role("student")
        student_id = self.current_user.user_id
        student = self.users.get(student_id)
        if not isinstance(student, Student):
            raise ValueError("Current user is not a student")
        course = self.courses.get(student.course_id)
        course_subjects = self.get_subjects_by_course(student.course_id) if course else []
        student_records = [r for r in self.attendance_records.values()
                           if r.student_id == student_id]
        total_classes = len(student_records)
        present_classes = sum(1 for r in student_records if r.status)
        attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
        student_results = [r for r in self.results.values() if r.student_id == student_id]
        student_leaves = [la for la in self.leave_applications.values()
                          if la.applicant_id == student_id]
        pending_leaves = [la for la in student_leaves if la.status == "pending"]
        approved_leaves = [la for la in student_leaves if la.status == "approved"]
        rejected_leaves = [la for la in student_leaves if la.status == "rejected"]
        return {
            "student_id": student_id,
            "course": course.name if course else None,
            "total_subjects": len(course_subjects),
            "total_classes": total_classes,
            "present_classes": present_classes,
            "absent_classes": total_classes - present_classes,
            "attendance_percentage": round(attendance_percentage, 2),
            "total_results": len(student_results),
            "total_leave_applications": len(student_leaves),
            "pending_leaves": len(pending_leaves),
            "approved_leaves": len(approved_leaves),
            "rejected_leaves": len(rejected_leaves)
        }

    # ==================== LEAVE: Apply ====================

    def apply_for_leave(self, start_date: date, end_date: date, reason: str) -> LeaveApplication:
        self._require_role("student", "staff")
        if not reason.strip():
            raise ValueError("Reason cannot be empty")
        applicant_type = self.current_user.role
        leave = LeaveApplication(
            leave_id=self._generate_id(),
            applicant_id=self.current_user.user_id,
            applicant_type=applicant_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        self.leave_applications[leave.leave_id] = leave
        user = self.users.get(self.current_user.user_id)
        if hasattr(user, 'leave_applications'):
            user.leave_applications.append(leave.leave_id)
        return leave

    def get_my_leave_applications(self) -> list[LeaveApplication]:
        self._require_role("student", "staff")
        return [la for la in self.leave_applications.values()
                if la.applicant_id == self.current_user.user_id]

    def get_leave_application_by_id(self, leave_id: str) -> Optional[LeaveApplication]:
        return self.leave_applications.get(leave_id)

    # ==================== FEEDBACK: Send ====================

    def send_feedback(self, message: str) -> Feedback:
        self._require_role("student", "staff")
        if not message.strip():
            raise ValueError("Feedback message cannot be empty")
        sender_type = self.current_user.role
        feedback = Feedback(
            feedback_id=self._generate_id(),
            sender_id=self.current_user.user_id,
            sender_type=sender_type,
            message=message
        )
        self.feedbacks[feedback.feedback_id] = feedback
        user = self.users.get(self.current_user.user_id)
        if hasattr(user, 'feedbacks'):
            user.feedbacks.append(feedback.feedback_id)
        return feedback

    def get_my_feedbacks(self) -> list[Feedback]:
        self._require_role("student", "staff")
        return [f for f in self.feedbacks.values()
                if f.sender_id == self.current_user.user_id]

    def get_feedback_by_id(self, feedback_id: str) -> Optional[Feedback]:
        return self.feedbacks.get(feedback_id)

    # ==================== UTILITY METHODS ====================

    def get_students_by_course(self, course_id: str) -> list[Student]:
        return [u for u in self.users.values()
                if isinstance(u, Student) and u.course_id == course_id]

    def get_students_by_session(self, session_id: str) -> list[Student]:
        return [u for u in self.users.values()
                if isinstance(u, Student) and u.session_id == session_id]

    def get_staff_performance_summary(self) -> list[dict]:
        self._require_role("admin")
        summaries = []
        all_staff = [u for u in self.users.values() if isinstance(u, Staff)]
        for staff in all_staff:
            staff_subjects = [s for s in self.subjects.values() if s.staff_id == staff.user_id]
            staff_attendances = [a for a in self.attendances.values()
                                 if a.staff_id == staff.user_id]
            staff_leaves = [la for la in self.leave_applications.values()
                            if la.applicant_id == staff.user_id]
            summaries.append({
                "staff_id": staff.user_id,
                "name": staff.get_full_name(),
                "total_subjects": len(staff_subjects),
                "total_attendance_taken": len(staff_attendances),
                "total_leave_applications": len(staff_leaves)
            })
        return summaries

    def get_student_performance_summary(self) -> list[dict]:
        self._require_role("admin")
        summaries = []
        all_students = [u for u in self.users.values() if isinstance(u, Student)]
        for student in all_students:
            student_records = [r for r in self.attendance_records.values()
                               if r.student_id == student.user_id]
            total_classes = len(student_records)
            present_classes = sum(1 for r in student_records if r.status)
            attendance_pct = (present_classes / total_classes * 100) if total_classes > 0 else 0
            student_results = [r for r in self.results.values()
                               if r.student_id == student.user_id]
            avg_marks = 0
            if student_results:
                avg_marks = sum(r.get_total_marks() for r in student_results) / len(student_results)
            summaries.append({
                "student_id": student.user_id,
                "name": student.get_full_name(),
                "course_id": student.course_id,
                "attendance_percentage": round(attendance_pct, 2),
                "average_marks": round(avg_marks, 2),
                "total_results": len(student_results)
            })
        return summaries

    def __repr__(self):
        return (f"StudentManagementSystem("
                f"users={len(self.users)}, "
                f"courses={len(self.courses)}, "
                f"subjects={len(self.subjects)}, "
                f"sessions={len(self.sessions)})")


def main():
    sms = StudentManagementSystem()

    print("=== Student Management System Demo ===\n")

    admin_user = sms.login("admin", "admin123")
    print(f"Logged in as: {admin_user}")

    session1 = sms.add_session(2023, 2024)
    session2 = sms.add_session(2024, 2025)
    print(f"\nSessions created: {session1}, {session2}")

    course1 = sms.add_course("Computer Science")
    course2 = sms.add_course("Mathematics")
    print(f"Courses created: {course1}, {course2}")

    staff1 = sms.add_staff(
        username="john_doe",
        password="staff123",
        email="john@sms.com",
        first_name="John",
        last_name="Doe",
        address="123 Main St"
    )
    staff2 = sms.add_staff(
        username="jane_smith",
        password="staff123",
        email="jane@sms.com",
        first_name="Jane",
        last_name="Smith",
        address="456 Oak Ave"
    )
    print(f"\nStaff created: {staff1}, {staff2}")

    subject1 = sms.add_subject("Python Programming", course1.course_id, staff1.user_id)
    subject2 = sms.add_subject("Data Structures", course1.course_id, staff1.user_id)
    subject3 = sms.add_subject("Calculus", course2.course_id, staff2.user_id)
    print(f"\nSubjects created: {subject1}, {subject2}, {subject3}")

    student1 = sms.add_student(
        username="alice",
        password="student123",
        email="alice@sms.com",
        first_name="Alice",
        last_name="Johnson",
        address="789 Pine Rd",
        course_id=course1.course_id,
        session_id=session1.session_id,
        gender="female"
    )
    student2 = sms.add_student(
        username="bob",
        password="student123",
        email="bob@sms.com",
        first_name="Bob",
        last_name="Williams",
        address="321 Elm St",
        course_id=course1.course_id,
        session_id=session1.session_id,
        gender="male"
    )
    print(f"\nStudents created: {student1}, {student2}")

    print(f"\nAdmin Summary: {sms.get_admin_summary()}")

    sms.logout()
    print("\n--- Logged out admin ---")

    staff_user = sms.login("john_doe", "staff123")
    print(f"Logged in as: {staff_user}")

    today = date.today()
    attendance = sms.take_attendance(
        subject_id=subject1.subject_id,
        attendance_date=today,
        session_id=session1.session_id,
        student_statuses={
            student1.user_id: True,
            student2.user_id: False
        }
    )
    print(f"\nAttendance taken: {attendance}")

    result1 = sms.add_result(student1.user_id, subject1.subject_id, 85.0, 90.0)
    result2 = sms.add_result(student2.user_id, subject1.subject_id, 70.0, 75.0)
    print(f"\nResults added: {result1}, {result2}")

    leave_app = sms.apply_for_leave(
        start_date=date(2024, 12, 20),
        end_date=date(2024, 12, 25),
        reason="Family vacation"
    )
    print(f"\nLeave application: {leave_app}")

    feedback = sms.send_feedback("The course material is very helpful!")
    print(f"Feedback sent: {feedback}")

    print(f"\nStaff Summary: {sms.get_staff_summary()}")

    sms.logout()
    print("\n--- Logged out staff ---")

    student_user = sms.login("alice", "student123")
    print(f"Logged in as: {student_user}")

    my_attendance = sms.get_student_attendance()
    print(f"\nMy attendance records: {my_attendance}")

    my_results = sms.get_results_by_student(student1.user_id)
    print(f"My results: {my_results}")
    for r in my_results:
        print(f"  Subject: {r.subject_id}, Total: {r.get_total_marks()}")

    student_leave = sms.apply_for_leave(
        start_date=date(2024, 12, 15),
        end_date=date(2024, 12, 16),
        reason="Medical appointment"
    )
    print(f"\nStudent leave application: {student_leave}")

    student_feedback = sms.send_feedback("I need more practice problems for the exam.")
    print(f"Student feedback: {student_feedback}")

    att_summary = sms.get_student_attendance_summary(student1.user_id)
    print(f"\nAttendance summary: {att_summary}")

    print(f"\nStudent Summary: {sms.get_student_summary()}")

    sms.logout()
    print("\n--- Logged out student ---")

    admin_user = sms.login("admin", "admin123")
    print(f"Logged in as: {admin_user}")

    pending_leaves = sms.get_pending_leave_applications()
    print(f"\nPending leave applications: {len(pending_leaves)}")

    for leave in pending_leaves:
        approved = sms.approve_leave(leave.leave_id, "Approved. Enjoy your time off!")
        print(f"Approved leave: {approved}")

    feedbacks = sms.get_all_feedbacks()
    print(f"\nAll feedbacks: {len(feedbacks)}")
    for fb in feedbacks:
        replied = sms.reply_feedback(fb.feedback_id, "Thank you for your feedback!")
        print(f"Replied to feedback: {replied}")

    staff_perf = sms.get_staff_performance_summary()
    print(f"\nStaff Performance Summary:")
    for sp in staff_perf:
        print(f"  {sp}")

    student_perf = sms.get_student_performance_summary()
    print(f"\nStudent Performance Summary:")
    for sp in student_perf:
        print(f"  {sp}")

    print(f"\nFinal Admin Summary: {sms.get_admin_summary()}")

    print(f"\nSystem: {sms}")


if __name__ == "__main__":
    main()