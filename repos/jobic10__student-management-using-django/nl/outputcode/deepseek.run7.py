from __future__ import annotations
from typing import List, Dict, Optional, Union, Any
from enum import Enum
from datetime import date, datetime
import uuid


class Role(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


class AttendanceStatus(Enum):
    PRESENT = "present"
    ABSENT = "absent"


class LeaveStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User:
    def __init__(self, user_id: str, name: str, email: str, password: str, role: Role):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.role = role

    def __repr__(self):
        return f"<User {self.user_id} {self.name} ({self.role.value})>"


class Staff(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, Role.STAFF)
        self.subjects: List[str] = []  # subject ids they teach


class Student(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, Role.STUDENT)
        self.subjects: List[str] = []  # subject ids enrolled


class Admin(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, Role.ADMIN)


class Course:
    def __init__(self, course_id: str, name: str, description: str = ""):
        self.course_id = course_id
        self.name = name
        self.description = description
        self.subjects: List[str] = []  # subject ids belonging to this course

    def add_subject(self, subject_id: str):
        if subject_id not in self.subjects:
            self.subjects.append(subject_id)

    def remove_subject(self, subject_id: str):
        if subject_id in self.subjects:
            self.subjects.remove(subject_id)

    def __repr__(self):
        return f"<Course {self.course_id}: {self.name}>"


class Subject:
    def __init__(self, subject_id: str, name: str, course_id: Optional[str] = None):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id

    def __repr__(self):
        return f"<Subject {self.subject_id}: {self.name}>"


class Session:
    def __init__(self, session_id: str, name: str, start_date: date, end_date: date):
        self.session_id = session_id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return f"<Session {self.session_id}: {self.name}>"


class AttendanceRecord:
    def __init__(
        self,
        attendance_id: str,
        student_id: str,
        subject_id: str,
        session_id: str,
        date: date,
        status: AttendanceStatus,
    ):
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.date = date
        self.status = status

    def __repr__(self):
        return f"<Attendance {self.attendance_id}: {self.student_id} {self.subject_id} {self.date} {self.status.value}>"


class ResultRecord:
    def __init__(
        self,
        result_id: str,
        student_id: str,
        subject_id: str,
        session_id: str,
        marks: float,
    ):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.marks = marks

    def __repr__(self):
        return f"<Result {self.result_id}: {self.student_id} {self.subject_id} {self.marks}>"


class LeaveApplication:
    def __init__(
        self,
        leave_id: str,
        user_id: str,
        start_date: date,
        end_date: date,
        reason: str,
        status: LeaveStatus = LeaveStatus.PENDING,
        response_text: Optional[str] = None,
    ):
        self.leave_id = leave_id
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = status
        self.response_text = response_text

    def __repr__(self):
        return f"<Leave {self.leave_id}: {self.user_id} {self.status.value}>"


class Feedback:
    def __init__(
        self,
        feedback_id: str,
        user_id: str,
        message: str,
        date: date,
        reply: Optional[str] = None,
    ):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.date = date
        self.reply = reply

    def __repr__(self):
        return f"<Feedback {self.feedback_id}: {self.user_id}>"


class StudentManagementSystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.courses: Dict[str, Course] = {}
        self.subjects: Dict[str, Subject] = {}
        self.sessions: Dict[str, Session] = {}
        self.attendances: Dict[str, AttendanceRecord] = {}
        self.results: Dict[str, ResultRecord] = {}
        self.leaves: Dict[str, LeaveApplication] = {}
        self.feedbacks: Dict[str, Feedback] = {}

    # --------------------- AUTHENTICATION ---------------------
    def login(self, email: str, password: str) -> Optional[User]:
        for user in self.users.values():
            if user.email == email and user.password == password:
                return user
        return None

    def register_admin(self, name: str, email: str, password: str) -> Admin:
        uid = self._generate_id("ADM")
        admin = Admin(uid, name, email, password)
        self.users[uid] = admin
        return admin

    def register_staff(self, name: str, email: str, password: str) -> Staff:
        uid = self._generate_id("STF")
        staff = Staff(uid, name, email, password)
        self.users[uid] = staff
        return staff

    def register_student(self, name: str, email: str, password: str) -> Student:
        uid = self._generate_id("STU")
        student = Student(uid, name, email, password)
        self.users[uid] = student
        return student

    # --------------------- ADMIN ACTIONS ---------------------
    def _check_admin(self, user: User):
        if user.role != Role.ADMIN:
            raise PermissionError("Only admins can perform this operation")

    def get_overall_student_performance_chart(self, user: User) -> Dict[str, Any]:
        self._check_admin(user)
        chart: Dict[str, Any] = {}
        subject_marks: Dict[str, List[float]] = {}
        for res in self.results.values():
            subject_marks.setdefault(res.subject_id, []).append(res.marks)
        for subj_id, marks in subject_marks.items():
            subj_name = self.subjects[subj_id].name if subj_id in self.subjects else subj_id
            chart[subj_name] = {
                "average": sum(marks) / len(marks),
                "max": max(marks),
                "min": min(marks),
                "count": len(marks),
            }
        return chart

    def get_overall_staff_performance_chart(self, user: User) -> Dict[str, Any]:
        self._check_admin(user)
        chart: Dict[str, Any] = {}
        for uid, u in self.users.items():
            if u.role == Role.STAFF:
                staff = u
                # get subjects they teach
                subject_ids = staff.subjects
                # get results for those subjects to calculate averages
                subject_marks: Dict[str, List[float]] = {}
                for res in self.results.values():
                    if res.subject_id in subject_ids:
                        subject_marks.setdefault(res.subject_id, []).append(res.marks)
                chart[staff.name] = {
                    "subjects_taught": [self.subjects[s].name for s in subject_ids if s in self.subjects],
                    "student_count": len({res.student_id for res in self.results.values() if res.subject_id in subject_ids}),
                    "per_subject_average": {
                        self.subjects[s].name: sum(marks)/len(marks) for s, marks in subject_marks.items() if s in self.subjects
                    },
                }
        return chart

    def get_course_chart(self, user: User) -> Dict[str, Any]:
        self._check_admin(user)
        chart = {
            "total_courses": len(self.courses),
            "details": {}
        }
        for c in self.courses.values():
            chart["details"][c.name] = {
                "subject_count": len(c.subjects),
                "subjects": [self.subjects[s].name for s in c.subjects if s in self.subjects],
            }
        return chart

    def get_subject_chart(self, user: User) -> Dict[str, Any]:
        self._check_admin(user)
        chart = {
            "total_subjects": len(self.subjects),
            "details": {}
        }
        for subj in self.subjects.values():
            # count enrollments (student_subjects)
            enrollment_count = sum(
                1 for u in self.users.values() if u.role == Role.STUDENT and subj.subject_id in u.subjects
            )
            chart["details"][subj.name] = {
                "course": self.courses[subj.course_id].name if subj.course_id and subj.course_id in self.courses else "None",
                "enrollment": enrollment_count,
            }
        return chart

    def get_leave_chart(self, user: User) -> Dict[str, Any]:
        self._check_admin(user)
        totals = {
            "total": len(self.leaves),
            "pending": sum(1 for l in self.leaves.values() if l.status == LeaveStatus.PENDING),
            "approved": sum(1 for l in self.leaves.values() if l.status == LeaveStatus.APPROVED),
            "rejected": sum(1 for l in self.leaves.values() if l.status == LeaveStatus.REJECTED),
        }
        return totals

    def add_staff(self, user: User, staff_data: Dict[str, Any]) -> Staff:
        self._check_admin(user)
        staff = self.register_staff(
            name=staff_data["name"],
            email=staff_data["email"],
            password=staff_data["password"],
        )
        if "subjects" in staff_data:
            staff.subjects = staff_data["subjects"]
        return staff

    def update_staff(self, user: User, staff_id: str, data: Dict[str, Any]):
        self._check_admin(user)
        if staff_id not in self.users:
            raise ValueError("Staff not found")
        staff = self.users[staff_id]
        if staff.role != Role.STAFF:
            raise ValueError("Not a staff member")
        if "name" in data:
            staff.name = data["name"]
        if "email" in data:
            staff.email = data["email"]
        if "subjects" in data:
            staff.subjects = data["subjects"]
        # add more fields as needed

    def delete_staff(self, user: User, staff_id: str):
        self._check_admin(user)
        if staff_id in self.users and self.users[staff_id].role == Role.STAFF:
            del self.users[staff_id]

    def add_student(self, user: User, student_data: Dict[str, Any]) -> Student:
        self._check_admin(user)
        student = self.register_student(
            name=student_data["name"],
            email=student_data["email"],
            password=student_data["password"],
        )
        if "subjects" in student_data:
            student.subjects = student_data["subjects"]
        return student

    def update_student(self, user: User, student_id: str, data: Dict[str, Any]):
        self._check_admin(user)
        if student_id not in self.users:
            raise ValueError("Student not found")
        student = self.users[student_id]
        if student.role != Role.STUDENT:
            raise ValueError("Not a student")
        if "name" in data:
            student.name = data["name"]
        if "email" in data:
            student.email = data["email"]
        if "subjects" in data:
            student.subjects = data["subjects"]

    def delete_student(self, user: User, student_id: str):
        self._check_admin(user)
        if student_id in self.users and self.users[student_id].role == Role.STUDENT:
            del self.users[student_id]

    def add_course(self, user: User, course_data: Dict[str, Any]) -> Course:
        self._check_admin(user)
        cid = self._generate_id("CRS")
        course = Course(cid, name=course_data["name"], description=course_data.get("description", ""))
        self.courses[cid] = course
        return course

    def update_course(self, user: User, course_id: str, data: Dict[str, Any]):
        self._check_admin(user)
        if course_id not in self.courses:
            raise ValueError("Course not found")
        course = self.courses[course_id]
        if "name" in data:
            course.name = data["name"]
        if "description" in data:
            course.description = data["description"]
        if "subjects" in data:
            course.subjects = data["subjects"]

    def delete_course(self, user: User, course_id: str):
        self._check_admin(user)
        if course_id in self.courses:
            del self.courses[course_id]

    def add_subject(self, user: User, subject_data: Dict[str, Any]) -> Subject:
        self._check_admin(user)
        sid = self._generate_id("SUB")
        subject = Subject(
            sid,
            name=subject_data["name"],
            course_id=subject_data.get("course_id"),
        )
        self.subjects[sid] = subject
        if subject.course_id and subject.course_id in self.courses:
            self.courses[subject.course_id].add_subject(sid)
        return subject

    def update_subject(self, user: User, subject_id: str, data: Dict[str, Any]):
        self._check_admin(user)
        if subject_id not in self.subjects:
            raise ValueError("Subject not found")
        subj = self.subjects[subject_id]
        if "name" in data:
            subj.name = data["name"]
        if "course_id" in data:
            # remove from old course
            if subj.course_id and subj.course_id in self.courses:
                self.courses[subj.course_id].remove_subject(subject_id)
            subj.course_id = data["course_id"]
            if subj.course_id and subj.course_id in self.courses:
                self.courses[subj.course_id].add_subject(subject_id)

    def delete_subject(self, user: User, subject_id: str):
        self._check_admin(user)
        if subject_id in self.subjects:
            subj = self.subjects[subject_id]
            if subj.course_id and subj.course_id in self.courses:
                self.courses[subj.course_id].remove_subject(subject_id)
            del self.subjects[subject_id]

    def add_session(self, user: User, session_data: Dict[str, Any]) -> Session:
        self._check_admin(user)
        sid = self._generate_id("SES")
        session = Session(
            sid,
            name=session_data["name"],
            start_date=session_data["start_date"],
            end_date=session_data["end_date"],
        )
        self.sessions[sid] = session
        return session

    def update_session(self, user: User, session_id: str, data: Dict[str, Any]):
        self._check_admin(user)
        if session_id not in self.sessions:
            raise ValueError("Session not found")
        session = self.sessions[session_id]
        if "name" in data:
            session.name = data["name"]
        if "start_date" in data:
            session.start_date = data["start_date"]
        if "end_date" in data:
            session.end_date = data["end_date"]

    def delete_session(self, user: User, session_id: str):
        self._check_admin(user)
        if session_id in self.sessions:
            del self.sessions[session_id]

    def view_student_attendance(
        self, user: User, student_id: str, subject_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> List[AttendanceRecord]:
        self._check_admin(user)
        records = []
        for att in self.attendances.values():
            if att.student_id != student_id:
                continue
            if subject_id and att.subject_id != subject_id:
                continue
            if session_id and att.session_id != session_id:
                continue
            records.append(att)
        return records

    def review_feedback(self, user: User, feedback_id: str, reply: str):
        self._check_admin(user)
        if feedback_id not in self.feedbacks:
            raise ValueError("Feedback not found")
        self.feedbacks[feedback_id].reply = reply

    def review_leave(self, user: User, leave_id: str, action: str):
        self._check_admin(user)
        if leave_id not in self.leaves:
            raise ValueError("Leave not found")
        if action.lower() == "approve":
            self.leaves[leave_id].status = LeaveStatus.APPROVED
        elif action.lower() == "reject":
            self.leaves[leave_id].status = LeaveStatus.REJECTED
        else:
            raise ValueError("Action must be 'approve' or 'reject'")

    # --------------------- STAFF ACTIONS ---------------------
    def _check_staff(self, user: User):
        if user.role != Role.STAFF:
            raise PermissionError("Only staff members can perform this operation")

    def get_staff_student_performance(self, staff: User) -> Dict[str, Any]:
        self._check_staff(staff)
        # for each subject taught, aggregate student marks
        result: Dict[str, Any] = {}
        for subj_id in staff.subjects:
            if subj_id not in self.subjects:
                continue
            subj_name = self.subjects[subj_id].name
            student_marks: Dict[str, List[float]] = {}
            for res in self.results.values():
                if res.subject_id == subj_id:
                    student_marks.setdefault(res.student_id, []).append(res.marks)
            avg_per_student = {
                sid: sum(marks)/len(marks) for sid, marks in student_marks.items()
            }
            result[subj_name] = avg_per_student
        return result

    def get_staff_subject_attendance_summary(self, staff: User) -> Dict[str, Any]:
        self._check_staff(staff)
        summary: Dict[str, Any] = {}
        for subj_id in staff.subjects:
            if subj_id not in self.subjects:
                continue
            total = 0
            present = 0
            for att in self.attendances.values():
                if att.subject_id == subj_id:
                    total += 1
                    if att.status == AttendanceStatus.PRESENT:
                        present += 1
            subj_name = self.subjects[subj_id].name
            summary[subj_name] = {"total_attendance": total, "present": present, "absent": total - present}
        return summary

    def get_staff_leave_status(self, staff: User) -> List[LeaveApplication]:
        self._check_staff(staff)
        return [l for l in self.leaves.values() if l.user_id == staff.user_id]

    def take_attendance(
        self,
        staff: User,
        student_id: str,
        subject_id: str,
        session_id: str,
        date: date,
        status: AttendanceStatus,
    ) -> AttendanceRecord:
        self._check_staff(staff)
        if subject_id not in staff.subjects:
            raise PermissionError("Staff does not teach this subject")
        if student_id not in self.users or self.users[student_id].role != Role.STUDENT:
            raise ValueError("Invalid student")
        att_id = self._generate_id("ATT")
        record = AttendanceRecord(att_id, student_id, subject_id, session_id, date, status)
        self.attendances[att_id] = record
        return record

    def update_attendance(self, staff: User, attendance_id: str, new_status: AttendanceStatus):
        self._check_staff(staff)
        if attendance_id not in self.attendances:
            raise ValueError("Attendance record not found")
        record = self.attendances[attendance_id]
        if record.subject_id not in staff.subjects:
            raise PermissionError("Staff cannot modify attendance for this subject")
        record.status = new_status

    def add_result(
        self,
        staff: User,
        student_id: str,
        subject_id: str,
        session_id: str,
        marks: float,
    ) -> ResultRecord:
        self._check_staff(staff)
        if subject_id not in staff.subjects:
            raise PermissionError("Staff does not teach this subject")
        if student_id not in self.users or self.users[student_id].role != Role.STUDENT:
            raise ValueError("Invalid student")
        res_id = self._generate_id("RES")
        result = ResultRecord(res_id, student_id, subject_id, session_id, marks)
        self.results[res_id] = result
        return result

    def update_result(self, staff: User, result_id: str, new_marks: float):
        self._check_staff(staff)
        if result_id not in self.results:
            raise ValueError("Result not found")
        result = self.results[result_id]
        if result.subject_id not in staff.subjects:
            raise PermissionError("Staff cannot modify result for this subject")
        result.marks = new_marks

    def apply_leave_staff(self, staff: User, start_date: date, end_date: date, reason: str) -> LeaveApplication:
        self._check_staff(staff)
        leave_id = self._generate_id("LV")
        leave = LeaveApplication(leave_id, staff.user_id, start_date, end_date, reason)
        self.leaves[leave_id] = leave
        return leave

    def send_feedback_staff(self, staff: User, message: str) -> Feedback:
        self._check_staff(staff)
        fb_id = self._generate_id("FB")
        feedback = Feedback(fb_id, staff.user_id, message, date.today())
        self.feedbacks[fb_id] = feedback
        return feedback

    # --------------------- STUDENT ACTIONS ---------------------
    def _check_student(self, user: User):
        if user.role != Role.STUDENT:
            raise PermissionError("Only students can perform this operation")

    def get_student_attendance(self, student: User, subject_id: Optional[str] = None, session_id: Optional[str] = None) -> List[AttendanceRecord]:
        self._check_student(student)
        records = []
        for att in self.attendances.values():
            if att.student_id != student.user_id:
                continue
            if subject_id and att.subject_id != subject_id:
                continue
            if session_id and att.session_id != session_id:
                continue
            records.append(att)
        return records

    def get_student_results(self, student: User, subject_id: Optional[str] = None, session_id: Optional[str] = None) -> List[ResultRecord]:
        self._check_student(student)
        records = []
        for res in self.results.values():
            if res.student_id != student.user_id:
                continue
            if subject_id and res.subject_id != subject_id:
                continue
            if session_id and res.session_id != session_id:
                continue
            records.append(res)
        return records

    def get_student_leave_status(self, student: User) -> List[LeaveApplication]:
        self._check_student(student)
        return [l for l in self.leaves.values() if l.user_id == student.user_id]

    def get_student_performance_chart(self, student: User) -> Dict[str, Any]:
        self._check_student(student)
        chart: Dict[str, Any] = {}
        for subj_id in student.subjects:
            if subj_id not in self.subjects:
                continue
            subj_name = self.subjects[subj_id].name
            marks = [r.marks for r in self.results.values() if r.student_id == student.user_id and r.subject_id == subj_id]
            if marks:
                chart[subj_name] = {"average": sum(marks)/len(marks), "max": max(marks), "min": min(marks)}
            else:
                chart[subj_name] = {"average": 0, "max": 0, "min": 0}
        return chart

    def get_student_attendance_chart(self, student: User) -> Dict[str, Any]:
        self._check_student(student)
        chart: Dict[str, Any] = {}
        for subj_id in student.subjects:
            if subj_id not in self.subjects:
                continue
            subj_name = self.subjects[subj_id].name
            total = 0
            present = 0
            for att in self.attendances.values():
                if att.student_id == student.user_id and att.subject_id == subj_id:
                    total += 1
                    if att.status == AttendanceStatus.PRESENT:
                        present += 1
            chart[subj_name] = {"total_classes": total, "present": present, "absent": total - present, "percentage": (present / total * 100) if total else 0}
        return chart

    def apply_leave_student(self, student: User, start_date: date, end_date: date, reason: str) -> LeaveApplication:
        self._check_student(student)
        leave_id = self._generate_id("LV")
        leave = LeaveApplication(leave_id, student.user_id, start_date, end_date, reason)
        self.leaves[leave_id] = leave
        return leave

    def send_feedback_student(self, student: User, message: str) -> Feedback:
        self._check_student(student)
        fb_id = self._generate_id("FB")
        feedback = Feedback(fb_id, student.user_id, message, date.today())
        self.feedbacks[fb_id] = feedback
        return feedback

    # --------------------- UTILITY ---------------------
    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    # Convenience wrappers for role-based access to avoid passing user every time?
    # We keep them as explicit parameter for clarity.
    # For Staff and Student views, they access these methods with their user object.
    # The methods above already enforce role.

# Example usage (optional main block)
if __name__ == "__main__":
    sm = StudentManagementSystem()
    admin = sm.register_admin("Admin", "admin@school.com", "admin123")
    staff1 = sm.register_staff("John Teacher", "john@school.com", "pass")
    student1 = sm.register_student("Alice", "alice@school.com", "pass")

    # add course and subject
    course = sm.add_course(admin, {"name": "Computer Science"})
    subject = sm.add_subject(admin, {"name": "Python Programming", "course_id": course.course_id})
    session = sm.add_session(admin, {"name": "2024-2025", "start_date": date(2024,9,1), "end_date": date(2025,6,30)})

    # assign subject to staff
    sm.update_staff(admin, staff1.user_id, {"subjects": [subject.subject_id]})
    # enroll student
    sm.update_student(admin, student1.user_id, {"subjects": [subject.subject_id]})

    # staff takes attendance
    att = sm.take_attendance(staff1, student1.user_id, subject.subject_id, session.session_id, date.today(), AttendanceStatus.PRESENT)
    # staff adds result
    res = sm.add_result(staff1, student1.user_id, subject.subject_id, session.session_id, 85.5)

    # student views
    print(sm.get_student_attendance(student1))
    print(sm.get_student_results(student1))
    print(sm.get_student_performance_chart(student1))
    print(sm.get_student_attendance_chart(student1))