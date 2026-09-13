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
    def __init__(self, user_id: str, username: str, password: str, email: str):
        super().__init__(user_id, username, password, email, "admin")
        self.full_name = username

    def __repr__(self):
        return f"Admin(id={self.user_id}, username={self.username})"


class Staff(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 full_name: str, address: str, course_id: Optional[str] = None):
        super().__init__(user_id, username, password, email, "staff")
        self.full_name = full_name
        self.address = address
        self.course_id = course_id
        self.subjects = []
        self.leave_applications = []
        self.feedbacks = []

    def __repr__(self):
        return f"Staff(id={self.user_id}, name={self.full_name})"


class Student(User):
    def __init__(self, user_id: str, username: str, password: str, email: str,
                 full_name: str, address: str, course_id: str, session_id: str, gender: str):
        super().__init__(user_id, username, password, email, "student")
        self.full_name = full_name
        self.address = address
        self.course_id = course_id
        self.session_id = session_id
        self.gender = gender
        self.leave_applications = []
        self.feedbacks = []

    def __repr__(self):
        return f"Student(id={self.user_id}, name={self.full_name})"


class Course:
    def __init__(self, course_id: str, course_name: str):
        self.course_id = course_id
        self.course_name = course_name
        self.subjects = []
        self.students = []
        self.staff = []
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
        self.session_id = session_id
        self.session_start_year = session_start_year
        self.session_end_year = session_end_year
        self.created_at = datetime.now()

    def __repr__(self):
        return f"Session(id={self.session_id}, {self.session_start_year}-{self.session_end_year})"


class Attendance:
    def __init__(self, attendance_id: str, subject_id: str, staff_id: str, attendance_date: date):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.staff_id = staff_id
        self.attendance_date = attendance_date
        self.records = {}
        self.created_at = datetime.now()

    def mark_student(self, student_id: str, status: bool):
        self.records[student_id] = status

    def update_student(self, student_id: str, status: bool):
        if student_id in self.records:
            self.records[student_id] = status
        else:
            self.records[student_id] = status

    def get_student_status(self, student_id: str) -> Optional[bool]:
        return self.records.get(student_id)

    def __repr__(self):
        return f"Attendance(id={self.attendance_id}, subject={self.subject_id}, date={self.attendance_date})"


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

    def update(self, exam_marks: float, assignment_marks: float):
        self.exam_marks = exam_marks
        self.assignment_marks = assignment_marks
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Result(id={self.result_id}, student={self.student_id}, subject={self.subject_id}, total={self.total_marks})"


class LeaveApplication:
    def __init__(self, leave_id: str, applicant_id: str, applicant_type: str,
                 leave_date: str, leave_message: str):
        self.leave_id = leave_id
        self.applicant_id = applicant_id
        self.applicant_type = applicant_type
        self.leave_date = leave_date
        self.leave_message = leave_message
        self.status = "pending"
        self.admin_remark = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def approve(self, remark: str = ""):
        self.status = "approved"
        self.admin_remark = remark
        self.updated_at = datetime.now()

    def reject(self, remark: str = ""):
        self.status = "rejected"
        self.admin_remark = remark
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"LeaveApplication(id={self.leave_id}, applicant={self.applicant_id}, status={self.status})"


class Feedback:
    def __init__(self, feedback_id: str, sender_id: str, sender_type: str, feedback_message: str):
        self.feedback_id = feedback_id
        self.sender_id = sender_id
        self.sender_type = sender_type
        self.feedback_message = feedback_message
        self.reply = ""
        self.is_replied = False
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def reply_feedback(self, reply_message: str):
        self.reply = reply_message
        self.is_replied = True
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Feedback(id={self.feedback_id}, sender={self.sender_id}, replied={self.is_replied})"


class StudentManagementSystem:
    def __init__(self):
        self.users = {}
        self.admins = {}
        self.staff_members = {}
        self.students = {}
        self.courses = {}
        self.subjects = {}
        self.sessions = {}
        self.attendances = {}
        self.results = {}
        self.leave_applications = {}
        self.feedbacks = {}
        self._initialize_default_admin()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _initialize_default_admin(self):
        admin = Admin(
            user_id=self._generate_id(),
            username="admin",
            password="admin123",
            email="admin@school.com"
        )
        self.admins[admin.user_id] = admin
        self.users[admin.user_id] = admin

    def authenticate(self, username: str, password: str) -> Optional[User]:
        for user in self.users.values():
            if user.username == username and user.verify_password(password):
                if user.is_active:
                    return user
        return None

    def add_staff(self, username: str, password: str, email: str,
                  full_name: str, address: str, course_id: Optional[str] = None) -> Staff:
        if course_id and course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Username {username} already exists")
            if user.email == email:
                raise ValueError(f"Email {email} already exists")
        staff = Staff(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            full_name=full_name,
            address=address,
            course_id=course_id
        )
        self.staff_members[staff.user_id] = staff
        self.users[staff.user_id] = staff
        if course_id and course_id in self.courses:
            self.courses[course_id].staff.append(staff.user_id)
        return staff

    def update_staff(self, staff_id: str, full_name: Optional[str] = None,
                     email: Optional[str] = None, address: Optional[str] = None,
                     course_id: Optional[str] = None, password: Optional[str] = None) -> Staff:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        staff = self.staff_members[staff_id]
        if full_name:
            staff.full_name = full_name
        if email:
            for user in self.users.values():
                if user.email == email and user.user_id != staff_id:
                    raise ValueError(f"Email {email} already exists")
            staff.email = email
        if address:
            staff.address = address
        if course_id is not None:
            if course_id and course_id not in self.courses:
                raise ValueError(f"Course with id {course_id} does not exist")
            if staff.course_id and staff.course_id in self.courses:
                course = self.courses[staff.course_id]
                if staff_id in course.staff:
                    course.staff.remove(staff_id)
            staff.course_id = course_id
            if course_id and course_id in self.courses:
                if staff_id not in self.courses[course_id].staff:
                    self.courses[course_id].staff.append(staff_id)
        if password:
            staff.update_password(password)
        return staff

    def delete_staff(self, staff_id: str) -> bool:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        staff = self.staff_members[staff_id]
        if staff.course_id and staff.course_id in self.courses:
            course = self.courses[staff.course_id]
            if staff_id in course.staff:
                course.staff.remove(staff_id)
        del self.staff_members[staff_id]
        del self.users[staff_id]
        return True

    def get_all_staff(self) -> list:
        return list(self.staff_members.values())

    def get_staff_by_id(self, staff_id: str) -> Optional[Staff]:
        return self.staff_members.get(staff_id)

    def add_student(self, username: str, password: str, email: str,
                    full_name: str, address: str, course_id: str,
                    session_id: str, gender: str) -> Student:
        if course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        if session_id not in self.sessions:
            raise ValueError(f"Session with id {session_id} does not exist")
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Username {username} already exists")
            if user.email == email:
                raise ValueError(f"Email {email} already exists")
        student = Student(
            user_id=self._generate_id(),
            username=username,
            password=password,
            email=email,
            full_name=full_name,
            address=address,
            course_id=course_id,
            session_id=session_id,
            gender=gender
        )
        self.students[student.user_id] = student
        self.users[student.user_id] = student
        self.courses[course_id].students.append(student.user_id)
        return student

    def update_student(self, student_id: str, full_name: Optional[str] = None,
                       email: Optional[str] = None, address: Optional[str] = None,
                       course_id: Optional[str] = None, session_id: Optional[str] = None,
                       gender: Optional[str] = None, password: Optional[str] = None) -> Student:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        student = self.students[student_id]
        if full_name:
            student.full_name = full_name
        if email:
            for user in self.users.values():
                if user.email == email and user.user_id != student_id:
                    raise ValueError(f"Email {email} already exists")
            student.email = email
        if address:
            student.address = address
        if course_id is not None:
            if course_id not in self.courses:
                raise ValueError(f"Course with id {course_id} does not exist")
            if student.course_id in self.courses:
                old_course = self.courses[student.course_id]
                if student_id in old_course.students:
                    old_course.students.remove(student_id)
            student.course_id = course_id
            if student_id not in self.courses[course_id].students:
                self.courses[course_id].students.append(student_id)
        if session_id is not None:
            if session_id not in self.sessions:
                raise ValueError(f"Session with id {session_id} does not exist")
            student.session_id = session_id
        if gender:
            student.gender = gender
        if password:
            student.update_password(password)
        return student

    def delete_student(self, student_id: str) -> bool:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        student = self.students[student_id]
        if student.course_id in self.courses:
            course = self.courses[student.course_id]
            if student_id in course.students:
                course.students.remove(student_id)
        del self.students[student_id]
        del self.users[student_id]
        return True

    def get_all_students(self) -> list:
        return list(self.students.values())

    def get_student_by_id(self, student_id: str) -> Optional[Student]:
        return self.students.get(student_id)

    def add_course(self, course_name: str) -> Course:
        for course in self.courses.values():
            if course.course_name.lower() == course_name.lower():
                raise ValueError(f"Course {course_name} already exists")
        course = Course(
            course_id=self._generate_id(),
            course_name=course_name
        )
        self.courses[course.course_id] = course
        return course

    def update_course(self, course_id: str, course_name: str) -> Course:
        if course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        for cid, course in self.courses.items():
            if course.course_name.lower() == course_name.lower() and cid != course_id:
                raise ValueError(f"Course {course_name} already exists")
        self.courses[course_id].course_name = course_name
        return self.courses[course_id]

    def delete_course(self, course_id: str) -> bool:
        if course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        del self.courses[course_id]
        return True

    def get_all_courses(self) -> list:
        return list(self.courses.values())

    def get_course_by_id(self, course_id: str) -> Optional[Course]:
        return self.courses.get(course_id)

    def add_subject(self, subject_name: str, course_id: str, staff_id: str) -> Subject:
        if course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        subject = Subject(
            subject_id=self._generate_id(),
            subject_name=subject_name,
            course_id=course_id,
            staff_id=staff_id
        )
        self.subjects[subject.subject_id] = subject
        self.courses[course_id].subjects.append(subject.subject_id)
        if subject.subject_id not in self.staff_members[staff_id].subjects:
            self.staff_members[staff_id].subjects.append(subject.subject_id)
        return subject

    def update_subject(self, subject_id: str, subject_name: Optional[str] = None,
                       course_id: Optional[str] = None, staff_id: Optional[str] = None) -> Subject:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id {subject_id} does not exist")
        subject = self.subjects[subject_id]
        if subject_name:
            subject.subject_name = subject_name
        if course_id is not None:
            if course_id not in self.courses:
                raise ValueError(f"Course with id {course_id} does not exist")
            if subject.course_id in self.courses:
                old_course = self.courses[subject.course_id]
                if subject_id in old_course.subjects:
                    old_course.subjects.remove(subject_id)
            subject.course_id = course_id
            if subject_id not in self.courses[course_id].subjects:
                self.courses[course_id].subjects.append(subject_id)
        if staff_id is not None:
            if staff_id not in self.staff_members:
                raise ValueError(f"Staff with id {staff_id} does not exist")
            old_staff = self.staff_members.get(subject.staff_id)
            if old_staff and subject_id in old_staff.subjects:
                old_staff.subjects.remove(subject_id)
            subject.staff_id = staff_id
            if subject_id not in self.staff_members[staff_id].subjects:
                self.staff_members[staff_id].subjects.append(subject_id)
        return subject

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id {subject_id} does not exist")
        subject = self.subjects[subject_id]
        if subject.course_id in self.courses:
            course = self.courses[subject.course_id]
            if subject_id in course.subjects:
                course.subjects.remove(subject_id)
        if subject.staff_id in self.staff_members:
            staff = self.staff_members[subject.staff_id]
            if subject_id in staff.subjects:
                staff.subjects.remove(subject_id)
        del self.subjects[subject_id]
        return True

    def get_all_subjects(self) -> list:
        return list(self.subjects.values())

    def get_subject_by_id(self, subject_id: str) -> Optional[Subject]:
        return self.subjects.get(subject_id)

    def get_subjects_by_staff(self, staff_id: str) -> list:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        return [self.subjects[sid] for sid in self.staff_members[staff_id].subjects if sid in self.subjects]

    def get_subjects_by_course(self, course_id: str) -> list:
        if course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        return [self.subjects[sid] for sid in self.courses[course_id].subjects if sid in self.subjects]

    def add_session(self, session_start_year: int, session_end_year: int) -> Session:
        if session_end_year <= session_start_year:
            raise ValueError("Session end year must be greater than start year")
        for session in self.sessions.values():
            if session.session_start_year == session_start_year and session.session_end_year == session_end_year:
                raise ValueError(f"Session {session_start_year}-{session_end_year} already exists")
        session = Session(
            session_id=self._generate_id(),
            session_start_year=session_start_year,
            session_end_year=session_end_year
        )
        self.sessions[session.session_id] = session
        return session

    def update_session(self, session_id: str, session_start_year: Optional[int] = None,
                       session_end_year: Optional[int] = None) -> Session:
        if session_id not in self.sessions:
            raise ValueError(f"Session with id {session_id} does not exist")
        session = self.sessions[session_id]
        new_start = session_start_year if session_start_year is not None else session.session_start_year
        new_end = session_end_year if session_end_year is not None else session.session_end_year
        if new_end <= new_start:
            raise ValueError("Session end year must be greater than start year")
        session.session_start_year = new_start
        session.session_end_year = new_end
        return session

    def delete_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            raise ValueError(f"Session with id {session_id} does not exist")
        del self.sessions[session_id]
        return True

    def get_all_sessions(self) -> list:
        return list(self.sessions.values())

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def take_attendance(self, subject_id: str, staff_id: str,
                        attendance_date: date, student_attendance: dict) -> Attendance:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id {subject_id} does not exist")
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        subject = self.subjects[subject_id]
        if subject.staff_id != staff_id:
            raise ValueError(f"Staff {staff_id} is not assigned to subject {subject_id}")
        attendance = Attendance(
            attendance_id=self._generate_id(),
            subject_id=subject_id,
            staff_id=staff_id,
            attendance_date=attendance_date
        )
        for student_id, status in student_attendance.items():
            if student_id not in self.students:
                raise ValueError(f"Student with id {student_id} does not exist")
            attendance.mark_student(student_id, status)
        self.attendances[attendance.attendance_id] = attendance
        return attendance

    def update_attendance(self, attendance_id: str, student_attendance: dict) -> Attendance:
        if attendance_id not in self.attendances:
            raise ValueError(f"Attendance with id {attendance_id} does not exist")
        attendance = self.attendances[attendance_id]
        for student_id, status in student_attendance.items():
            if student_id not in self.students:
                raise ValueError(f"Student with id {student_id} does not exist")
            attendance.update_student(student_id, status)
        return attendance

    def get_attendance_by_subject(self, subject_id: str) -> list:
        return [att for att in self.attendances.values() if att.subject_id == subject_id]

    def get_attendance_by_student(self, student_id: str) -> dict:
        result = {}
        for att in self.attendances.values():
            if student_id in att.records:
                if att.subject_id not in result:
                    result[att.subject_id] = []
                result[att.subject_id].append({
                    'date': att.attendance_date,
                    'status': att.records[student_id],
                    'attendance_id': att.attendance_id
                })
        return result

    def get_student_attendance_summary(self, student_id: str) -> dict:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        attendance_data = self.get_attendance_by_student(student_id)
        summary = {}
        for subject_id, records in attendance_data.items():
            total = len(records)
            present = sum(1 for r in records if r['status'])
            absent = total - present
            percentage = (present / total * 100) if total > 0 else 0
            summary[subject_id] = {
                'total_classes': total,
                'present': present,
                'absent': absent,
                'percentage': round(percentage, 2)
            }
        return summary

    def add_result(self, student_id: str, subject_id: str,
                   exam_marks: float, assignment_marks: float) -> Result:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id {subject_id} does not exist")
        for result in self.results.values():
            if result.student_id == student_id and result.subject_id == subject_id:
                raise ValueError(f"Result already exists for student {student_id} and subject {subject_id}")
        result = Result(
            result_id=self._generate_id(),
            student_id=student_id,
            subject_id=subject_id,
            exam_marks=exam_marks,
            assignment_marks=assignment_marks
        )
        self.results[result.result_id] = result
        return result

    def update_result(self, result_id: str, exam_marks: Optional[float] = None,
                      assignment_marks: Optional[float] = None) -> Result:
        if result_id not in self.results:
            raise ValueError(f"Result with id {result_id} does not exist")
        result = self.results[result_id]
        new_exam = exam_marks if exam_marks is not None else result.exam_marks
        new_assignment = assignment_marks if assignment_marks is not None else result.assignment_marks
        result.update(new_exam, new_assignment)
        return result

    def get_results_by_student(self, student_id: str) -> list:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        return [r for r in self.results.values() if r.student_id == student_id]

    def get_results_by_subject(self, subject_id: str) -> list:
        if subject_id not in self.subjects:
            raise ValueError(f"Subject with id {subject_id} does not exist")
        return [r for r in self.results.values() if r.subject_id == subject_id]

    def apply_leave_student(self, student_id: str, leave_date: str, leave_message: str) -> LeaveApplication:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        leave = LeaveApplication(
            leave_id=self._generate_id(),
            applicant_id=student_id,
            applicant_type="student",
            leave_date=leave_date,
            leave_message=leave_message
        )
        self.leave_applications[leave.leave_id] = leave
        self.students[student_id].leave_applications.append(leave.leave_id)
        return leave

    def apply_leave_staff(self, staff_id: str, leave_date: str, leave_message: str) -> LeaveApplication:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        leave = LeaveApplication(
            leave_id=self._generate_id(),
            applicant_id=staff_id,
            applicant_type="staff",
            leave_date=leave_date,
            leave_message=leave_message
        )
        self.leave_applications[leave.leave_id] = leave
        self.staff_members[staff_id].leave_applications.append(leave.leave_id)
        return leave

    def approve_leave(self, leave_id: str, remark: str = "") -> LeaveApplication:
        if leave_id not in self.leave_applications:
            raise ValueError(f"Leave application with id {leave_id} does not exist")
        self.leave_applications[leave_id].approve(remark)
        return self.leave_applications[leave_id]

    def reject_leave(self, leave_id: str, remark: str = "") -> LeaveApplication:
        if leave_id not in self.leave_applications:
            raise ValueError(f"Leave application with id {leave_id} does not exist")
        self.leave_applications[leave_id].reject(remark)
        return self.leave_applications[leave_id]

    def get_all_leave_applications(self) -> list:
        return list(self.leave_applications.values())

    def get_leave_by_applicant(self, applicant_id: str) -> list:
        return [la for la in self.leave_applications.values() if la.applicant_id == applicant_id]

    def get_pending_leave_applications(self) -> list:
        return [la for la in self.leave_applications.values() if la.status == "pending"]

    def send_feedback_student(self, student_id: str, feedback_message: str) -> Feedback:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        feedback = Feedback(
            feedback_id=self._generate_id(),
            sender_id=student_id,
            sender_type="student",
            feedback_message=feedback_message
        )
        self.feedbacks[feedback.feedback_id] = feedback
        self.students[student_id].feedbacks.append(feedback.feedback_id)
        return feedback

    def send_feedback_staff(self, staff_id: str, feedback_message: str) -> Feedback:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        feedback = Feedback(
            feedback_id=self._generate_id(),
            sender_id=staff_id,
            sender_type="staff",
            feedback_message=feedback_message
        )
        self.feedbacks[feedback.feedback_id] = feedback
        self.staff_members[staff_id].feedbacks.append(feedback.feedback_id)
        return feedback

    def reply_feedback(self, feedback_id: str, reply_message: str) -> Feedback:
        if feedback_id not in self.feedbacks:
            raise ValueError(f"Feedback with id {feedback_id} does not exist")
        self.feedbacks[feedback_id].reply_feedback(reply_message)
        return self.feedbacks[feedback_id]

    def get_all_feedbacks(self) -> list:
        return list(self.feedbacks.values())

    def get_feedbacks_by_sender(self, sender_id: str) -> list:
        return [fb for fb in self.feedbacks.values() if fb.sender_id == sender_id]

    def get_unreplied_feedbacks(self) -> list:
        return [fb for fb in self.feedbacks.values() if not fb.is_replied]

    def get_admin_summary(self) -> dict:
        total_students = len(self.students)
        total_staff = len(self.staff_members)
        total_courses = len(self.courses)
        total_subjects = len(self.subjects)
        total_sessions = len(self.sessions)
        pending_leaves = len(self.get_pending_leave_applications())
        unreplied_feedbacks = len(self.get_unreplied_feedbacks())

        student_leave_count = sum(1 for la in self.leave_applications.values() if la.applicant_type == "student")
        staff_leave_count = sum(1 for la in self.leave_applications.values() if la.applicant_type == "staff")
        approved_leaves = sum(1 for la in self.leave_applications.values() if la.status == "approved")
        rejected_leaves = sum(1 for la in self.leave_applications.values() if la.status == "rejected")

        course_summary = []
        for course in self.courses.values():
            course_summary.append({
                'course_id': course.course_id,
                'course_name': course.course_name,
                'total_students': len(course.students),
                'total_staff': len(course.staff),
                'total_subjects': len(course.subjects)
            })

        return {
            'total_students': total_students,
            'total_staff': total_staff,
            'total_courses': total_courses,
            'total_subjects': total_subjects,
            'total_sessions': total_sessions,
            'pending_leaves': pending_leaves,
            'unreplied_feedbacks': unreplied_feedbacks,
            'student_leave_count': student_leave_count,
            'staff_leave_count': staff_leave_count,
            'approved_leaves': approved_leaves,
            'rejected_leaves': rejected_leaves,
            'course_summary': course_summary
        }

    def get_staff_summary(self, staff_id: str) -> dict:
        if staff_id not in self.staff_members:
            raise ValueError(f"Staff with id {staff_id} does not exist")
        staff = self.staff_members[staff_id]
        staff_subjects = self.get_subjects_by_staff(staff_id)
        total_subjects = len(staff_subjects)

        students_in_course = []
        if staff.course_id and staff.course_id in self.courses:
            course = self.courses[staff.course_id]
            students_in_course = course.students

        total_students = len(students_in_course)

        leave_apps = self.get_leave_by_applicant(staff_id)
        pending_leaves = sum(1 for la in leave_apps if la.status == "pending")
        approved_leaves = sum(1 for la in leave_apps if la.status == "approved")
        rejected_leaves = sum(1 for la in leave_apps if la.status == "rejected")

        attendance_taken = sum(1 for att in self.attendances.values() if att.staff_id == staff_id)

        subject_details = []
        for subject in staff_subjects:
            subject_attendances = self.get_attendance_by_subject(subject.subject_id)
            subject_results = self.get_results_by_subject(subject.subject_id)
            subject_details.append({
                'subject_id': subject.subject_id,
                'subject_name': subject.subject_name,
                'total_attendance_sessions': len(subject_attendances),
                'total_results': len(subject_results)
            })

        return {
            'staff_id': staff_id,
            'staff_name': staff.full_name,
            'course_id': staff.course_id,
            'total_subjects': total_subjects,
            'total_students': total_students,
            'attendance_taken': attendance_taken,
            'leave_applications': {
                'total': len(leave_apps),
                'pending': pending_leaves,
                'approved': approved_leaves,
                'rejected': rejected_leaves
            },
            'subject_details': subject_details
        }

    def get_student_summary(self, student_id: str) -> dict:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        student = self.students[student_id]
        attendance_summary = self.get_student_attendance_summary(student_id)
        results = self.get_results_by_student(student_id)
        leave_apps = self.get_leave_by_applicant(student_id)
        pending_leaves = sum(1 for la in leave_apps if la.status == "pending")
        approved_leaves = sum(1 for la in leave_apps if la.status == "approved")
        rejected_leaves = sum(1 for la in leave_apps if la.status == "rejected")

        overall_attendance = 0
        if attendance_summary:
            total_present = sum(v['present'] for v in attendance_summary.values())
            total_classes = sum(v['total_classes'] for v in attendance_summary.values())
            overall_attendance = (total_present / total_classes * 100) if total_classes > 0 else 0

        result_details = []
        for result in results:
            subject_name = ""
            if result.subject_id in self.subjects:
                subject_name = self.subjects[result.subject_id].subject_name
            result_details.append({
                'subject_id': result.subject_id,
                'subject_name': subject_name,
                'exam_marks': result.exam_marks,
                'assignment_marks': result.assignment_marks,
                'total_marks': result.total_marks
            })

        return {
            'student_id': student_id,
            'student_name': student.full_name,
            'course_id': student.course_id,
            'session_id': student.session_id,
            'overall_attendance_percentage': round(overall_attendance, 2),
            'attendance_by_subject': attendance_summary,
            'results': result_details,
            'leave_applications': {
                'total': len(leave_apps),
                'pending': pending_leaves,
                'approved': approved_leaves,
                'rejected': rejected_leaves
            }
        }

    def view_student_attendance(self, student_id: str) -> dict:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        return self.get_attendance_by_student(student_id)

    def view_student_results(self, student_id: str) -> list:
        if student_id not in self.students:
            raise ValueError(f"Student with id {student_id} does not exist")
        return self.get_results_by_student(student_id)

    def get_students_by_course(self, course_id: str) -> list:
        if course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        return [self.students[sid] for sid in self.courses[course_id].students if sid in self.students]

    def get_staff_by_course(self, course_id: str) -> list:
        if course_id not in self.courses:
            raise ValueError(f"Course with id {course_id} does not exist")
        return [self.staff_members[sid] for sid in self.courses[course_id].staff if sid in self.staff_members]


def main():
    sms = StudentManagementSystem()

    print("=== Student Management System Demo ===\n")

    print("--- Admin Authentication ---")
    admin_user = sms.authenticate("admin", "admin123")
    if admin_user:
        print(f"Admin logged in: {admin_user}")
    else:
        print("Authentication failed")

    print("\n--- Adding Sessions ---")
    session1 = sms.add_session(2023, 2024)
    session2 = sms.add_session(2024, 2025)
    print(f"Added: {session1}")
    print(f"Added: {session2}")

    print("\n--- Adding Courses ---")
    course1 = sms.add_course("Computer Science")
    course2 = sms.add_course("Mathematics")
    print(f"Added: {course1}")
    print(f"Added: {course2}")

    print("\n--- Adding Staff ---")
    staff1 = sms.add_staff(
        username="john_doe",
        password="staff123",
        email="john@school.com",
        full_name="John Doe",
        address="123 Main St",
        course_id=course1.course_id
    )
    staff2 = sms.add_staff(
        username="jane_smith",
        password="staff456",
        email="jane@school.com",
        full_name="Jane Smith",
        address="456 Oak Ave",
        course_id=course2.course_id
    )
    print(f"Added: {staff1}")
    print(f"Added: {staff2}")

    print("\n--- Adding Subjects ---")
    subject1 = sms.add_subject("Python Programming", course1.course_id, staff1.user_id)
    subject2 = sms.add_subject("Data Structures", course1.course_id, staff1.user_id)
    subject3 = sms.add_subject("Calculus", course2.course_id, staff2.user_id)
    print(f"Added: {subject1}")
    print(f"Added: {subject2}")
    print(f"Added: {subject3}")

    print("\n--- Adding Students ---")
    student1 = sms.add_student(
        username="alice",
        password="student123",
        email="alice@student.com",
        full_name="Alice Johnson",
        address="789 Pine Rd",
        course_id=course1.course_id,
        session_id=session1.session_id,
        gender="Female"
    )
    student2 = sms.add_student(
        username="bob",
        password="student456",
        email="bob@student.com",
        full_name="Bob Williams",
        address="321 Elm St",
        course_id=course1.course_id,
        session_id=session1.session_id,
        gender="Male"
    )
    print(f"Added: {student1}")
    print(f"Added: {student2}")

    print("\n--- Staff Authentication ---")
    staff_user = sms.authenticate("john_doe", "staff123")
    if staff_user:
        print(f"Staff logged in: {staff_user}")

    print("\n--- Taking Attendance ---")
    attendance1 = sms.take_attendance(
        subject_id=subject1.subject_id,
        staff_id=staff1.user_id,
        attendance_date=date(2024, 1, 15),
        student_attendance={
            student1.user_id: True,
            student2.user_id: False
        }
    )
    print(f"Attendance taken: {attendance1}")

    attendance2 = sms.take_attendance(
        subject_id=subject1.subject_id,
        staff_id=staff1.user_id,
        attendance_date=date(2024, 1, 16),
        student_attendance={
            student1.user_id: True,
            student2.user_id: True
        }
    )
    print(f"Attendance taken: {attendance2}")

    print("\n--- Adding Results ---")
    result1 = sms.add_result(student1.user_id, subject1.subject_id, 85.0, 20.0)
    result2 = sms.add_result(student2.user_id, subject1.subject_id, 70.0, 18.0)
    result3 = sms.add_result(student1.user_id, subject2.subject_id, 90.0, 22.0)
    print(f"Added: {result1}")
    print(f"Added: {result2}")
    print(f"Added: {result3}")

    print("\n--- Updating Result ---")
    updated_result = sms.update_result(result1.result_id, exam_marks=88.0)
    print(f"Updated: {updated_result}")

    print("\n--- Student Leave Application ---")
    student_leave = sms.apply_leave_student(
        student_id=student1.user_id,
        leave_date="2024-01-20",
        leave_message="Medical appointment"
    )
    print(f"Leave applied: {student_leave}")

    print("\n--- Staff Leave Application ---")
    staff_leave = sms.apply_leave_staff(
        staff_id=staff1.user_id,
        leave_date="2024-01-22",
        leave_message="Family emergency"
    )
    print(f"Leave applied: {staff_leave}")

    print("\n--- Admin Approving/Rejecting Leave ---")
    approved = sms.approve_leave(student_leave.leave_id, "Approved for medical reasons")
    print(f"Leave approved: {approved}")
    rejected = sms.reject_leave(staff_leave.leave_id, "Insufficient notice")
    print(f"Leave rejected: {rejected}")

    print("\n--- Student Feedback ---")
    student_feedback = sms.send_feedback_student(
        student_id=student1.user_id,
        feedback_message="The Python course is very helpful!"
    )
    print(f"Feedback sent: {student_feedback}")

    print("\n--- Staff Feedback ---")
    staff_feedback = sms.send_feedback_staff(
        staff_id=staff1.user_id,
        feedback_message="Need more resources for teaching"
    )
    print(f"Feedback sent: {staff_feedback}")

    print("\n--- Admin Replying to Feedback ---")
    replied = sms.reply_feedback(student_feedback.feedback_id, "Thank you for your feedback!")
    print(f"Feedback replied: {replied}")

    print("\n--- Admin Summary ---")
    admin_summary = sms.get_admin_summary()
    print(f"Total Students: {admin_summary['total_students']}")
    print(f"Total Staff: {admin_summary['total_staff']}")
    print(f"Total Courses: {admin_summary['total_courses']}")
    print(f"Total Subjects: {admin_summary['total_subjects']}")
    print(f"Total Sessions: {admin_summary['total_sessions']}")
    print(f"Pending Leaves: {admin_summary['pending_leaves']}")
    print(f"Unreplied Feedbacks: {admin_summary['unreplied_feedbacks']}")
    print(f"Approved Leaves: {admin_summary['approved_leaves']}")
    print(f"Rejected Leaves: {admin_summary['rejected_leaves']}")

    print("\n--- Staff Summary ---")
    staff_summary = sms.get_staff_summary(staff1.user_id)
    print(f"Staff Name: {staff_summary['staff_name']}")
    print(f"Total Subjects: {staff_summary['total_subjects']}")
    print(f"Total Students: {staff_summary['total_students']}")
    print(f"Attendance Sessions Taken: {staff_summary['attendance_taken']}")
    print(f"Leave Applications: {staff_summary['leave_applications']}")

    print("\n--- Student Summary ---")
    student_summary = sms.get_student_summary(student1.user_id)
    print(f"Student Name: {student_summary['student_name']}")
    print(f"Overall Attendance: {student_summary['overall_attendance_percentage']}%")
    print(f"Results: {student_summary['results']}")
    print(f"Leave Applications: {student_summary['leave_applications']}")

    print("\n--- Student Viewing Attendance ---")
    student_attendance = sms.view_student_attendance(student1.user_id)
    for subject_id, records in student_attendance.items():
        subject_name = sms.subjects[subject_id].subject_name if subject_id in sms.subjects else subject_id
        print(f"Subject: {subject_name}")
        for record in records:
            status = "Present" if record['status'] else "Absent"
            print(f"  Date: {record['date']}, Status: {status}")

    print("\n--- Student Viewing Results ---")
    student_results = sms.view_student_results(student1.user_id)
    for result in student_results:
        subject_name = sms.subjects[result.subject_id].subject_name if result.subject_id in sms.subjects else result.subject_id
        print(f"Subject: {subject_name}, Exam: {result.exam_marks}, Assignment: {result.assignment_marks}, Total: {result.total_marks}")

    print("\n--- Updating Staff ---")
    updated_staff = sms.update_staff(staff1.user_id, full_name="John Doe Jr.", address="999 New St")
    print(f"Updated Staff: {updated_staff}, Name: {updated_staff.full_name}")

    print("\n--- Updating Student ---")
    updated_student = sms.update_student(student2.user_id, address="555 New Ave")
    print(f"Updated Student: {updated_student}, Address: {updated_student.address}")

    print("\n--- Updating Course ---")
    updated_course = sms.update_course(course1.course_id, "Computer Science & Engineering")
    print(f"Updated Course: {updated_course}")

    print("\n--- Updating Subject ---")
    updated_subject = sms.update_subject(subject1.subject_id, subject_name="Advanced Python Programming")
    print(f"Updated Subject: {updated_subject}")

    print("\n--- Updating Session ---")
    updated_session = sms.update_session(session2.session_id, session_start_year=2024, session_end_year=2026)
    print(f"Updated Session: {updated_session}")

    print("\n--- Updating Attendance ---")
    updated_attendance = sms.update_attendance(attendance1.attendance_id, {student2.user_id: True})
    print(f"Updated Attendance: {updated_attendance}")
    print(f"Student2 status now: {updated_attendance.get_student_status(student2.user_id)}")

    print("\n--- Getting All Pending Leaves ---")
    pending = sms.get_pending_leave_applications()
    print(f"Pending leave applications: {len(pending)}")

    print("\n--- Getting Unreplied Feedbacks ---")
    unreplied = sms.get_unreplied_feedbacks()
    print(f"Unreplied feedbacks: {len(unreplied)}")
    for fb in unreplied:
        print(f"  {fb}")

    print("\n--- Deleting Operations ---")
    new_course = sms.add_course("Physics")
    print(f"Added course for deletion: {new_course}")
    deleted = sms.delete_course(new_course.course_id)
    print(f"Course deleted: {deleted}")

    new_session = sms.add_session(2025, 2026)
    print(f"Added session for deletion: {new_session}")
    deleted = sms.delete_session(new_session.session_id)
    print(f"Session deleted: {deleted}")

    new_staff = sms.add_staff("temp_staff", "pass123", "temp@school.com", "Temp Staff", "Temp Address")
    print(f"Added staff for deletion: {new_staff}")
    deleted = sms.delete_staff(new_staff.user_id)
    print(f"Staff deleted: {deleted}")

    new_student = sms.add_student(
        "temp_student", "pass123", "temp_student@school.com",
        "Temp Student", "Temp Address", course1.course_id, session1.session_id, "Male"
    )
    print(f"Added student for deletion: {new_student}")
    deleted = sms.delete_student(new_student.user_id)
    print(f"Student deleted: {deleted}")

    new_subject = sms.add_subject("Temp Subject", course1.course_id, staff1.user_id)
    print(f"Added subject for deletion: {new_subject}")
    deleted = sms.delete_subject(new_subject.subject_id)
    print(f"Subject deleted: {deleted}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()