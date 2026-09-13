from __future__ import annotations
from typing import List, Dict, Optional, Union, Tuple
from datetime import date, datetime
from enum import Enum
from collections import defaultdict
import statistics


class Role(Enum):
    ADMIN = "Admin"
    STAFF = "Staff"
    STUDENT = "Student"


class LeaveStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class AttendanceStatus(Enum):
    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"


class User:
    def __init__(self, user_id: str, name: str, email: str, role: Role, password: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role
        self.password = password


class Admin(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, Role.ADMIN, password)


class Staff(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, Role.STAFF, password)
        self.subjects_taught: List[str] = []  # subject_ids


class Student(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, Role.STUDENT, password)
        self.course_ids: List[str] = []  # ids of courses enrolled


class Course:
    def __init__(self, course_id: str, name: str, description: str = ""):
        self.course_id = course_id
        self.name = name
        self.description = description
        self.subject_ids: List[str] = []

    def add_subject(self, subject_id: str):
        if subject_id not in self.subject_ids:
            self.subject_ids.append(subject_id)

    def remove_subject(self, subject_id: str):
        if subject_id in self.subject_ids:
            self.subject_ids.remove(subject_id)


class Subject:
    def __init__(self, subject_id: str, name: str, description: str = ""):
        self.subject_id = subject_id
        self.name = name
        self.description = description


class Session:
    def __init__(self, session_id: str, subject_id: str, staff_id: str,
                 date: date, time: str, topic: str = ""):
        self.session_id = session_id
        self.subject_id = subject_id
        self.staff_id = staff_id
        self.date = date
        self.time = time
        self.topic = topic


class Attendance:
    def __init__(self, attendance_id: str, student_id: str, session_id: str,
                 status: AttendanceStatus):
        self.attendance_id = attendance_id
        self.student_id = student_id
        self.session_id = session_id
        self.status = status


class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str,
                 marks: float, exam_type: str = "Exam"):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks
        self.exam_type = exam_type
        # grade based on marks percentage (assuming max 100)
        if marks >= 90:
            self.grade = 'A'
        elif marks >= 80:
            self.grade = 'B'
        elif marks >= 70:
            self.grade = 'C'
        elif marks >= 60:
            self.grade = 'D'
        else:
            self.grade = 'F'


class LeaveRequest:
    def __init__(self, leave_id: str, user_id: str, start_date: date,
                 end_date: date, reason: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = LeaveStatus.PENDING
        self.reviewed_by: Optional[str] = None  # admin user_id


class Feedback:
    def __init__(self, feedback_id: str, user_id: str, message: str,
                 timestamp: datetime = None):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self.reply: Optional[str] = None
        self.replied_by: Optional[str] = None


class System:
    def __init__(self):
        # collections
        self.users: Dict[str, User] = {}
        self.staff: Dict[str, Staff] = {}
        self.students: Dict[str, Student] = {}
        self.admins: Dict[str, Admin] = {}
        self.courses: Dict[str, Course] = {}
        self.subjects: Dict[str, Subject] = {}
        self.sessions: Dict[str, Session] = {}
        self.attendances: Dict[str, Attendance] = {}
        self.results: Dict[str, Result] = {}
        self.leave_requests: Dict[str, LeaveRequest] = {}
        self.feedbacks: Dict[str, Feedback] = {}

        self.current_user: Optional[User] = None

        # counters for generating IDs
        self._id_counters = defaultdict(int)

    def _generate_id(self, prefix: str) -> str:
        self._id_counters[prefix] += 1
        return f"{prefix}{self._id_counters[prefix]}"

    # -------------------------- Authentication --------------------------
    def login(self, user_id: str, password: str) -> Optional[User]:
        user = self.users.get(user_id)
        if user and user.password == password:
            self.current_user = user
            return user
        return None

    def logout(self):
        self.current_user = None

    # -------------------------- Admin User Management --------------------------
    def add_admin(self, name: str, email: str, password: str) -> Admin:
        admin_id = self._generate_id("A")
        admin = Admin(admin_id, name, email, password)
        self.users[admin_id] = admin
        self.admins[admin_id] = admin
        return admin

    def add_staff(self, name: str, email: str, password: str) -> Staff:
        staff_id = self._generate_id("S")
        staff = Staff(staff_id, name, email, password)
        self.users[staff_id] = staff
        self.staff[staff_id] = staff
        return staff

    def add_student(self, name: str, email: str, password: str) -> Student:
        student_id = self._generate_id("ST")
        student = Student(student_id, name, email, password)
        self.users[student_id] = student
        self.students[student_id] = student
        return student

    def update_user(self, user_id: str, name: str = None, email: str = None, password: str = None) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if password is not None:
            user.password = password
        return True

    def delete_user(self, user_id: str) -> bool:
        user = self.users.pop(user_id, None)
        if not user:
            return False
        if user.role == Role.ADMIN:
            self.admins.pop(user_id, None)
        elif user.role == Role.STAFF:
            self.staff.pop(user_id, None)
        elif user.role == Role.STUDENT:
            self.students.pop(user_id, None)
        # Remove associated data? Could cascade but spec not explicit. Keep it simple.
        return True

    # -------------------------- Course Management --------------------------
    def add_course(self, name: str, description: str = "") -> Course:
        course_id = self._generate_id("C")
        course = Course(course_id, name, description)
        self.courses[course_id] = course
        return course

    def update_course(self, course_id: str, name: str = None, description: str = None) -> bool:
        course = self.courses.get(course_id)
        if not course:
            return False
        if name is not None:
            course.name = name
        if description is not None:
            course.description = description
        return True

    def delete_course(self, course_id: str) -> bool:
        if course_id in self.courses:
            del self.courses[course_id]
            # Also remove references from students? Not implemented.
            return True
        return False

    # -------------------------- Subject Management --------------------------
    def add_subject(self, name: str, description: str = "") -> Subject:
        subject_id = self._generate_id("SUB")
        subject = Subject(subject_id, name, description)
        self.subjects[subject_id] = subject
        return subject

    def update_subject(self, subject_id: str, name: str = None, description: str = None) -> bool:
        subject = self.subjects.get(subject_id)
        if not subject:
            return False
        if name is not None:
            subject.name = name
        if description is not None:
            subject.description = description
        return True

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id in self.subjects:
            del self.subjects[subject_id]
            return True
        return False

    def assign_subject_to_course(self, course_id: str, subject_id: str) -> bool:
        course = self.courses.get(course_id)
        subject = self.subjects.get(subject_id)
        if course and subject:
            course.add_subject(subject_id)
            return True
        return False

    def unassign_subject_from_course(self, course_id: str, subject_id: str) -> bool:
        course = self.courses.get(course_id)
        if course:
            course.remove_subject(subject_id)
            return True
        return False

    def assign_subject_to_staff(self, staff_id: str, subject_id: str) -> bool:
        staff = self.staff.get(staff_id)
        subject = self.subjects.get(subject_id)
        if staff and subject and subject_id not in staff.subjects_taught:
            staff.subjects_taught.append(subject_id)
            return True
        return False

    def enroll_student_in_course(self, student_id: str, course_id: str) -> bool:
        student = self.students.get(student_id)
        course = self.courses.get(course_id)
        if student and course and course_id not in student.course_ids:
            student.course_ids.append(course_id)
            return True
        return False

    # -------------------------- Session Management --------------------------
    def add_session(self, subject_id: str, staff_id: str, date: date,
                    time: str, topic: str = "") -> Optional[Session]:
        if subject_id not in self.subjects or staff_id not in self.staff:
            return None
        # optional: verify staff teaches this subject
        staff = self.staff[staff_id]
        if subject_id not in staff.subjects_taught:
            return None
        session_id = self._generate_id("SES")
        session = Session(session_id, subject_id, staff_id, date, time, topic)
        self.sessions[session_id] = session
        return session

    def update_session(self, session_id: str, date: date = None,
                       time: str = None, topic: str = None) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        if date is not None:
            session.date = date
        if time is not None:
            session.time = time
        if topic is not None:
            session.topic = topic
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    # -------------------------- Attendance --------------------------
    def take_attendance(self, session_id: str, student_id: str,
                        status: AttendanceStatus) -> Optional[Attendance]:
        if session_id not in self.sessions or student_id not in self.students:
            return None
        # ensure student is enrolled in a course that includes the session's subject
        session = self.sessions[session_id]
        student = self.students[student_id]
        # get all subjects of student's courses
        student_subjects = set()
        for cid in student.course_ids:
            course = self.courses.get(cid)
            if course:
                student_subjects.update(course.subject_ids)
        if session.subject_id not in student_subjects:
            return None
        attendance_id = self._generate_id("ATT")
        attendance = Attendance(attendance_id, student_id, session_id, status)
        self.attendances[attendance_id] = attendance
        return attendance

    def update_attendance(self, attendance_id: str, new_status: AttendanceStatus) -> bool:
        attendance = self.attendances.get(attendance_id)
        if attendance:
            attendance.status = new_status
            return True
        return False

    # -------------------------- Results --------------------------
    def add_result(self, student_id: str, subject_id: str,
                   marks: float, exam_type: str = "Exam") -> Optional[Result]:
        if student_id not in self.students or subject_id not in self.subjects:
            return None
        result_id = self._generate_id("RES")
        result = Result(result_id, student_id, subject_id, marks, exam_type)
        self.results[result_id] = result
        return result

    def update_result(self, result_id: str, marks: float = None) -> bool:
        result = self.results.get(result_id)
        if not result:
            return False
        if marks is not None:
            result.marks = marks
            # recalc grade
            if marks >= 90:
                result.grade = 'A'
            elif marks >= 80:
                result.grade = 'B'
            elif marks >= 70:
                result.grade = 'C'
            elif marks >= 60:
                result.grade = 'D'
            else:
                result.grade = 'F'
        return True

    # -------------------------- Leave Management --------------------------
    def apply_leave(self, user_id: str, start_date: date,
                    end_date: date, reason: str) -> Optional[LeaveRequest]:
        if user_id not in self.users:
            return None
        # basic overlap check (optional)
        leave_id = self._generate_id("LEV")
        leave = LeaveRequest(leave_id, user_id, start_date, end_date, reason)
        self.leave_requests[leave_id] = leave
        return leave

    def review_leave(self, leave_id: str, admin: Admin,
                     status: LeaveStatus) -> bool:
        leave = self.leave_requests.get(leave_id)
        if not leave or admin.role != Role.ADMIN:
            return False
        leave.status = status
        leave.reviewed_by = admin.user_id
        return True

    # -------------------------- Feedback --------------------------
    def send_feedback(self, user_id: str, message: str) -> Optional[Feedback]:
        if user_id not in self.users:
            return None
        feedback_id = self._generate_id("FB")
        feedback = Feedback(feedback_id, user_id, message)
        self.feedbacks[feedback_id] = feedback
        return feedback

    def reply_feedback(self, feedback_id: str, admin: Admin,
                       reply: str) -> bool:
        if admin.role != Role.ADMIN:
            return False
        feedback = self.feedbacks.get(feedback_id)
        if not feedback:
            return False
        feedback.reply = reply
        feedback.replied_by = admin.user_id
        return True

    # -------------------------- Summary Charts (Stats) --------------------------
    def _get_user_name(self, user_id: str) -> str:
        user = self.users.get(user_id)
        return user.name if user else "Unknown"

    def _get_student_subjects(self, student_id: str) -> List[str]:
        student = self.students.get(student_id)
        if not student:
            return []
        subjects = set()
        for cid in student.course_ids:
            course = self.courses.get(cid)
            if course:
                subjects.update(course.subject_ids)
        return list(subjects)

    def _get_subject_enrolled_students(self, subject_id: str) -> List[str]:
        students = []
        for st_id, student in self.students.items():
            student_subjects = self._get_student_subjects(st_id)
            if subject_id in student_subjects:
                students.append(st_id)
        return students

    def get_admin_summary(self) -> Dict:
        summary = {}
        summary['total_students'] = len(self.students)
        summary['total_staff'] = len(self.staff)
        summary['total_courses'] = len(self.courses)
        summary['total_subjects'] = len(self.subjects)
        summary['total_sessions'] = len(self.sessions)

        # Attendance stats overall
        att_counts = {s: 0 for s in AttendanceStatus}
        for att in self.attendances.values():
            att_counts[att.status] += 1
        total_att = sum(att_counts.values())
        attendance_pct = {}
        for status, count in att_counts.items():
            attendance_pct[status.value] = f"{(count/total_att)*100:.1f}%" if total_att else "0%"
        summary['attendance_summary'] = attendance_pct

        # Result distribution (grades)
        grade_counts = defaultdict(int)
        for res in self.results.values():
            grade_counts[res.grade] += 1
        summary['result_distribution'] = dict(grade_counts)

        # Leave summary
        leave_status_counts = {ls: 0 for ls in LeaveStatus}
        for leave in self.leave_requests.values():
            leave_status_counts[leave.status] += 1
        summary['leave_summary'] = {ls.value: count for ls, count in leave_status_counts.items()}

        # Feedback summary
        replied = sum(1 for fb in self.feedbacks.values() if fb.reply is not None)
        total_fb = len(self.feedbacks)
        summary['feedback_summary'] = {
            'total': total_fb,
            'replied': replied,
            'unreplied': total_fb - replied
        }
        return summary

    def get_staff_summary(self, staff_id: str) -> Optional[Dict]:
        staff = self.staff.get(staff_id)
        if not staff:
            return None
        summary = {}

        # Subjects taught
        summary['subjects_taught'] = [self.subjects[sid].name for sid in staff.subjects_taught if sid in self.subjects]

        # Students under staff (enrolled in subjects taught by staff)
        my_students = set()
        for sid in staff.subjects_taught:
            my_students.update(self._get_subject_enrolled_students(sid))
        summary['total_my_students'] = len(my_students)

        # Attendance statistics for staff's sessions
        staff_sessions = [s for s in self.sessions.values() if s.staff_id == staff_id]
        attendances = []
        for ses in staff_sessions:
            attendances.extend([att for att in self.attendances.values() if att.session_id == ses.session_id])
        att_counts = {s: 0 for s in AttendanceStatus}
        for att in attendances:
            att_counts[att.status] += 1
        total_att = sum(att_counts.values())
        att_pct = {}
        for status, count in att_counts.items():
            att_pct[status.value] = f"{(count/total_att)*100:.1f}%" if total_att else "0%"
        summary['attendance_summary'] = att_pct

        # Results for staff's subjects (only those that belong to his subjects)
        staff_subjects = set(staff.subjects_taught)
        results = [res for res in self.results.values() if res.subject_id in staff_subjects]
        grade_counts = defaultdict(int)
        for res in results:
            grade_counts[res.grade] += 1
        summary['result_distribution'] = dict(grade_counts)

        # Leave status for this staff
        my_leaves = [lv for lv in self.leave_requests.values() if lv.user_id == staff_id]
        leave_status = {ls: 0 for ls in LeaveStatus}
        for lv in my_leaves:
            leave_status[lv.status] += 1
        summary['my_leave_summary'] = {ls.value: count for ls, count in leave_status.items()}

        return summary

    def get_student_summary(self, student_id: str) -> Optional[Dict]:
        student = self.students.get(student_id)
        if not student:
            return None
        summary = {}

        # Enrolled courses
        summary['courses'] = [self.courses[cid].name for cid in student.course_ids if cid in self.courses]

        # Subjects
        my_subjects = self._get_student_subjects(student_id)
        summary['subjects'] = [self.subjects[sid].name for sid in my_subjects if sid in self.subjects]

        # Attendance
        student_att = [att for att in self.attendances.values() if att.student_id == student_id]
        if student_att:
            present = sum(1 for att in student_att if att.status == AttendanceStatus.PRESENT)
            absent = sum(1 for att in student_att if att.status == AttendanceStatus.ABSENT)
            late = sum(1 for att in student_att if att.status == AttendanceStatus.LATE)
            total = len(student_att)
            summary['attendance'] = {
                'Present': f"{(present/total)*100:.1f}%",
                'Absent': f"{(absent/total)*100:.1f}%",
                'Late': f"{(late/total)*100:.1f}%"
            }
        else:
            summary['attendance'] = "No attendance records."

        # Results
        student_results = [res for res in self.results.values() if res.student_id == student_id]
        if student_results:
            res_by_subject = defaultdict(list)
            for res in student_results:
                res_by_subject[res.subject_id].append(res.marks)
            results_summary = {}
            for sid, marks_list in res_by_subject.items():
                sub_name = self.subjects[sid].name if sid in self.subjects else "Unknown"
                avg = statistics.mean(marks_list)
                results_summary[sub_name] = f"Avg: {avg:.1f}, Grade: {self._marks_to_grade(avg)}"
            summary['results'] = results_summary
        else:
            summary['results'] = "No results."

        # Leave status
        my_leaves = [lv for lv in self.leave_requests.values() if lv.user_id == student_id]
        leave_status = {ls: 0 for ls in LeaveStatus}
        for lv in my_leaves:
            leave_status[lv.status] += 1
        summary['my_leave_summary'] = {ls.value: count for ls, count in leave_status.items()}

        return summary

    def _marks_to_grade(self, marks: float) -> str:
        if marks >= 90: return 'A'
        elif marks >= 80: return 'B'
        elif marks >= 70: return 'C'
        elif marks >= 60: return 'D'
        else: return 'F'

    # ---------- Staff-specific operations (can be called after verifying role) ----------
    def staff_take_attendance(self, staff_id: str, session_id: str,
                              student_id: str, status: AttendanceStatus) -> Optional[Attendance]:
        # ensure the staff is assigned to that session's subject
        session = self.sessions.get(session_id)
        if not session or session.staff_id != staff_id:
            return None
        return self.take_attendance(session_id, student_id, status)

    def staff_add_result(self, staff_id: str, student_id: str,
                         subject_id: str, marks: float, exam_type: str = "Exam") -> Optional[Result]:
        # staff must teach the subject
        staff = self.staff.get(staff_id)
        if not staff or subject_id not in staff.subjects_taught:
            return None
        return self.add_result(student_id, subject_id, marks, exam_type)

    def print_summary(self, summary: Dict):
        """Simple console print of summary."""
        for key, value in summary.items():
            print(f"\n{key}:")
            if isinstance(value, dict):
                for k, v in value.items():
                    print(f"  {k}: {v}")
            elif isinstance(value, list):
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"  {value}")


# -------------------------- Example usage (not part of requirements but for completeness) --------------------------
if __name__ == "__main__":
    # This block would be executed only when run directly, not in import.
    pass