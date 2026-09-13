from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
import statistics

# -------- Enums --------
class LeaveStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AttendanceStatus(Enum):
    PRESENT = "present"
    ABSENT = "absent"

class Role(Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

# -------- Data Classes --------
@dataclass
class Course:
    id: int
    name: str
    code: str
    description: str = ""

@dataclass
class Subject:
    id: int
    name: str
    course_id: int
    teacher_id: Optional[int] = None

@dataclass
class Session:
    id: int
    year: int
    term: str
    is_active: bool = True

@dataclass
class Attendance:
    id: int
    student_id: int
    subject_id: int
    session_id: int
    date: date
    status: AttendanceStatus

@dataclass
class Result:
    id: int
    student_id: int
    subject_id: int
    session_id: int
    marks: float
    grade: str = ""

@dataclass
class Leave:
    id: int
    applicant_id: int
    applicant_role: Role
    reason: str
    start_date: date
    end_date: date
    status: LeaveStatus = LeaveStatus.PENDING

@dataclass
class Feedback:
    id: int
    sender_id: int
    sender_role: Role
    message: str
    reply: str = ""
    is_replied: bool = False

# -------- Person Base --------
class Person(ABC):
    def __init__(self, id: int, username: str, password: str, fullname: str, email: str = ""):
        self.id = id
        self.username = username
        self.password = password
        self.fullname = fullname
        self.email = email

    @abstractmethod
    def get_role(self) -> Role:
        pass

    def check_password(self, pw: str) -> bool:
        return self.password == pw

class Admin(Person):
    def get_role(self) -> Role:
        return Role.ADMIN

class Teacher(Person):
    def get_role(self) -> Role:
        return Role.TEACHER

class Student(Person):
    def __init__(self, id: int, username: str, password: str, fullname: str, course_id: int, email: str = ""):
        super().__init__(id, username, password, fullname, email)
        self.course_id = course_id

    def get_role(self) -> Role:
        return Role.STUDENT

# -------- Core System --------
class StudentManagementSystem:
    def __init__(self):
        self.admins: List[Admin] = []
        self.teachers: List[Teacher] = []
        self.students: List[Student] = []
        self.courses: List[Course] = []
        self.subjects: List[Subject] = []
        self.sessions: List[Session] = []
        self.attendances: List[Attendance] = []
        self.results: List[Result] = []
        self.leaves: List[Leave] = []
        self.feedbacks: List[Feedback] = []

        self._next_ids = {
            'person': 1, 'course': 1, 'subject': 1, 'session': 1,
            'attendance': 1, 'result': 1, 'leave': 1, 'feedback': 1
        }

    # ----- ID generators -----
    def _next_person_id(self) -> int:
        i = self._next_ids['person']
        self._next_ids['person'] += 1
        return i

    def _next_course_id(self) -> int:
        i = self._next_ids['course']
        self._next_ids['course'] += 1
        return i

    def _next_subject_id(self) -> int:
        i = self._next_ids['subject']
        self._next_ids['subject'] += 1
        return i

    def _next_session_id(self) -> int:
        i = self._next_ids['session']
        self._next_ids['session'] += 1
        return i

    def _next_attendance_id(self) -> int:
        i = self._next_ids['attendance']
        self._next_ids['attendance'] += 1
        return i

    def _next_result_id(self) -> int:
        i = self._next_ids['result']
        self._next_ids['result'] += 1
        return i

    def _next_leave_id(self) -> int:
        i = self._next_ids['leave']
        self._next_ids['leave'] += 1
        return i

    def _next_feedback_id(self) -> int:
        i = self._next_ids['feedback']
        self._next_ids['feedback'] += 1
        return i

    # ----- Authentication -----
    def login(self, username: str, password: str) -> Optional[Person]:
        for lst in [self.admins, self.teachers, self.students]:
            for p in lst:
                if p.username == username and p.password == password:
                    return p
        return None

    # ----- Admin features -----
    # 1. Summary Charts
    def get_admin_student_performance_chart(self) -> str:
        """Overall student performance summary per subject"""
        if not self.results:
            return "No result data available."
        lines = ["==== Student Performance Chart ===="]
        subjects: Dict[int, str] = {s.id: s.name for s in self.subjects}
        for subj_id, subj_name in subjects.items():
            marks = [r.marks for r in self.results if r.subject_id == subj_id]
            if not marks:
                continue
            avg = statistics.mean(marks)
            high = max(marks)
            low = min(marks)
            bar = '#' * int(avg // 5)
            lines.append(f"{subj_name}: Avg={avg:.1f}% [High={high}% Low={low}%] {bar}")
        return "\n".join(lines)

    def get_admin_staff_performance_chart(self) -> str:
        """Average of all results of students taught by each teacher"""
        if not self.teachers:
            return "No teachers found."
        lines = ["==== Staff Performance Chart ===="]
        for t in self.teachers:
            taught_subjects = [s.id for s in self.subjects if s.teacher_id == t.id]
            if not taught_subjects:
                lines.append(f"{t.fullname}: No subjects assigned.")
                continue
            marks = [r.marks for r in self.results if r.subject_id in taught_subjects]
            if not marks:
                lines.append(f"{t.fullname}: No results yet.")
                continue
            avg = statistics.mean(marks)
            lines.append(f"{t.fullname}: Average Student Mark {avg:.1f}%")
        return "\n".join(lines)

    def get_admin_courses_chart(self) -> str:
        """Enrollment count per course"""
        lines = ["==== Courses Chart ===="]
        for c in self.courses:
            count = sum(1 for s in self.students if s.course_id == c.id)
            lines.append(f"{c.name} ({c.code}): {count} students")
        return "\n".join(lines)

    def get_admin_subjects_chart(self) -> str:
        """Subjects per course and teacher"""
        lines = ["==== Subjects Chart ===="]
        for subj in self.subjects:
            teacher_name = "Unassigned"
            if subj.teacher_id:
                t = next((t for t in self.teachers if t.id == subj.teacher_id), None)
                teacher_name = t.fullname if t else "Unknown"
            course_name = "N/A"
            if subj.course_id:
                c = next((c for c in self.courses if c.id == subj.course_id), None)
                course_name = c.name if c else "Unknown"
            lines.append(f"Subject: {subj.name} | Course: {course_name} | Teacher: {teacher_name}")
        return "\n".join(lines)

    def get_admin_leave_chart(self) -> str:
        """Leave summary by status"""
        total = len(self.leaves)
        pending = sum(1 for l in self.leaves if l.status == LeaveStatus.PENDING)
        approved = sum(1 for l in self.leaves if l.status == LeaveStatus.APPROVED)
        rejected = sum(1 for l in self.leaves if l.status == LeaveStatus.REJECTED)
        return f"Leaves: Total={total} | Pending={pending} | Approved={approved} | Rejected={rejected}"

    def view_student_attendance_admin(self, student_id: int) -> List[Attendance]:
        return [a for a in self.attendances if a.student_id == student_id]

    # 2. Manage Staff
    def add_staff(self, username: str, password: str, fullname: str, email: str = "") -> Teacher:
        new_id = self._next_person_id()
        t = Teacher(new_id, username, password, fullname, email)
        self.teachers.append(t)
        return t

    def update_staff(self, staff_id: int, **kwargs) -> bool:
        t = next((t for t in self.teachers if t.id == staff_id), None)
        if not t:
            return False
        for key, val in kwargs.items():
            if hasattr(t, key):
                setattr(t, key, val)
        return True

    def delete_staff(self, staff_id: int) -> bool:
        t = next((t for t in self.teachers if t.id == staff_id), None)
        if not t:
            return False
        self.teachers.remove(t)
        # Reassign subjects taught by this staff to None
        for subj in self.subjects:
            if subj.teacher_id == staff_id:
                subj.teacher_id = None
        return True

    # 3. Manage Students
    def add_student(self, username: str, password: str, fullname: str, course_id: int, email: str = "") -> Student:
        new_id = self._next_person_id()
        s = Student(new_id, username, password, fullname, course_id, email)
        self.students.append(s)
        return s

    def update_student(self, student_id: int, **kwargs) -> bool:
        s = next((s for s in self.students if s.id == student_id), None)
        if not s:
            return False
        for key, val in kwargs.items():
            if hasattr(s, key):
                setattr(s, key, val)
        return True

    def delete_student(self, student_id: int) -> bool:
        s = next((s for s in self.students if s.id == student_id), None)
        if not s:
            return False
        self.students.remove(s)
        # Remove related attendances, results, leaves
        self.attendances = [a for a in self.attendances if a.student_id != student_id]
        self.results = [r for r in self.results if r.student_id != student_id]
        self.leaves = [l for l in self.leaves if not (l.applicant_id == student_id and l.applicant_role == Role.STUDENT)]
        self.feedbacks = [f for f in self.feedbacks if not (f.sender_id == student_id and f.sender_role == Role.STUDENT)]
        return True

    # 4. Manage Course
    def add_course(self, name: str, code: str, description: str = "") -> Course:
        cid = self._next_course_id()
        c = Course(cid, name, code, description)
        self.courses.append(c)
        return c

    def update_course(self, course_id: int, **kwargs) -> bool:
        c = next((c for c in self.courses if c.id == course_id), None)
        if not c:
            return False
        for key, val in kwargs.items():
            if hasattr(c, key):
                setattr(c, key, val)
        return True

    def delete_course(self, course_id: int) -> bool:
        c = next((c for c in self.courses if c.id == course_id), None)
        if not c:
            return False
        # cannot delete if students enrolled? spec doesn't forbid, just delete.
        self.courses.remove(c)
        self.students = [s for s in self.students if s.course_id != course_id]
        self.subjects = [s for s in self.subjects if s.course_id != course_id]
        return True

    # 5. Manage Subjects
    def add_subject(self, name: str, course_id: int, teacher_id: Optional[int] = None) -> Subject:
        sid = self._next_subject_id()
        subj = Subject(sid, name, course_id, teacher_id)
        self.subjects.append(subj)
        return subj

    def update_subject(self, subject_id: int, **kwargs) -> bool:
        subj = next((s for s in self.subjects if s.id == subject_id), None)
        if not subj:
            return False
        for key, val in kwargs.items():
            if hasattr(subj, key):
                setattr(subj, key, val)
        return True

    def delete_subject(self, subject_id: int) -> bool:
        subj = next((s for s in self.subjects if s.id == subject_id), None)
        if not subj:
            return False
        self.subjects.remove(subj)
        # Clean related data
        self.attendances = [a for a in self.attendances if a.subject_id != subject_id]
        self.results = [r for r in self.results if r.subject_id != subject_id]
        return True

    # 6. Manage Sessions
    def add_session(self, year: int, term: str, is_active: bool = True) -> Session:
        sid = self._next_session_id()
        s = Session(sid, year, term, is_active)
        self.sessions.append(s)
        return s

    def update_session(self, session_id: int, **kwargs) -> bool:
        s = next((s for s in self.sessions if s.id == session_id), None)
        if not s:
            return False
        for key, val in kwargs.items():
            if hasattr(s, key):
                setattr(s, key, val)
        return True

    def delete_session(self, session_id: int) -> bool:
        s = next((s for s in self.sessions if s.id == session_id), None)
        if not s:
            return False
        self.sessions.remove(s)
        self.attendances = [a for a in self.attendances if a.session_id != session_id]
        self.results = [r for r in self.results if r.session_id != session_id]
        return True

    # 7. Review Feedback
    def get_pending_feedbacks(self) -> List[Feedback]:
        return [f for f in self.feedbacks if not f.is_replied]

    def reply_feedback(self, feedback_id: int, reply: str) -> bool:
        f = next((f for f in self.feedbacks if f.id == feedback_id), None)
        if not f:
            return False
        f.reply = reply
        f.is_replied = True
        return True

    # 8. Review Leave (Approve/Reject)
    def review_leave(self, leave_id: int, decision: LeaveStatus) -> bool:
        lv = next((l for l in self.leaves if l.id == leave_id), None)
        if not lv:
            return False
        if lv.status != LeaveStatus.PENDING:
            return False
        lv.status = decision
        return True

    # ----- Staff features -----
    def get_teacher_subjects(self, teacher_id: int) -> List[Subject]:
        return [s for s in self.subjects if s.teacher_id == teacher_id]

    def get_teacher_students(self, teacher_id: int) -> List[Student]:
        subj_ids = [s.id for s in self.get_teacher_subjects(teacher_id)]
        students_set = set()
        for subj_id in subj_ids:
            for att in self.attendances:
                if att.subject_id == subj_id:
                    students_set.add(att.student_id)
        # Also students from results maybe
        for res in self.results:
            if res.subject_id in subj_ids:
                students_set.add(res.student_id)
        return [st for st in self.students if st.id in students_set]

    def get_teacher_attendances(self, teacher_id: int) -> List[Attendance]:
        subj_ids = [s.id for s in self.get_teacher_subjects(teacher_id)]
        return [a for a in self.attendances if a.subject_id in subj_ids]

    def get_teacher_results(self, teacher_id: int) -> List[Result]:
        subj_ids = [s.id for s in self.get_teacher_subjects(teacher_id)]
        return [r for r in self.results if r.subject_id in subj_ids]

    def get_teacher_leaves(self, teacher_id: int) -> List[Leave]:
        return [l for l in self.leaves if l.applicant_id == teacher_id and l.applicant_role == Role.TEACHER]

    # Staff: Take/Update Attendance
    def record_attendance(self, student_id: int, subject_id: int, session_id: int, date: date, status: AttendanceStatus) -> Optional[Attendance]:
        # Validate student is in same course as subject's course? Not strictly required, but we ensure subject exists.
        subj = next((s for s in self.subjects if s.id == subject_id), None)
        if not subj:
            return None
        aid = self._next_attendance_id()
        a = Attendance(aid, student_id, subject_id, session_id, date, status)
        self.attendances.append(a)
        return a

    def update_attendance(self, attendance_id: int, status: AttendanceStatus) -> bool:
        a = next((a for a in self.attendances if a.id == attendance_id), None)
        if not a:
            return False
        a.status = status
        return True

    # Staff: Add/Update Result
    def add_result(self, student_id: int, subject_id: int, session_id: int, marks: float, grade: str = "") -> Optional[Result]:
        if not (0 <= marks <= 100):
            return None
        rid = self._next_result_id()
        r = Result(rid, student_id, subject_id, session_id, marks, grade)
        self.results.append(r)
        return r

    def update_result(self, result_id: int, marks: float, grade: str = "") -> bool:
        r = next((r for r in self.results if r.id == result_id), None)
        if not r:
            return False
        if not (0 <= marks <= 100):
            return False
        r.marks = marks
        if grade:
            r.grade = grade
        return True

    # Staff: Apply Leave
    def apply_leave_staff(self, teacher_id: int, reason: str, start_date: date, end_date: date) -> Leave:
        lid = self._next_leave_id()
        lv = Leave(lid, teacher_id, Role.TEACHER, reason, start_date, end_date)
        self.leaves.append(lv)
        return lv

    # Staff: Send Feedback
    def send_feedback_staff(self, teacher_id: int, message: str) -> Feedback:
        fid = self._next_feedback_id()
        fb = Feedback(fid, teacher_id, Role.TEACHER, message)
        self.feedbacks.append(fb)
        return fb

    # ----- Student features -----
    def get_student_attendances(self, student_id: int) -> List[Attendance]:
        return [a for a in self.attendances if a.student_id == student_id]

    def get_student_results(self, student_id: int) -> List[Result]:
        return [r for r in self.results if r.student_id == student_id]

    def get_student_leaves(self, student_id: int) -> List[Leave]:
        return [l for l in self.leaves if l.applicant_id == student_id and l.applicant_role == Role.STUDENT]

    def apply_leave_student(self, student_id: int, reason: str, start_date: date, end_date: date) -> Leave:
        lid = self._next_leave_id()
        lv = Leave(lid, student_id, Role.STUDENT, reason, start_date, end_date)
        self.leaves.append(lv)
        return lv

    def send_feedback_student(self, student_id: int, message: str) -> Feedback:
        fid = self._next_feedback_id()
        fb = Feedback(fid, student_id, Role.STUDENT, message)
        self.feedbacks.append(fb)
        return fb

    # Summary for staff/students
    def get_teacher_summary_chart(self, teacher_id: int) -> str:
        students = self.get_teacher_students(teacher_id)
        leaves = self.get_teacher_leaves(teacher_id)
        subjects = self.get_teacher_subjects(teacher_id)
        lines = ["==== Teacher Dashboard ===="]
        lines.append(f"Taught subjects: {', '.join(s.name for s in subjects)}")
        lines.append(f"Number of students: {len(students)}")
        # Attendance summary
        atts = self.get_teacher_attendances(teacher_id)
        if atts:
            present = sum(1 for a in atts if a.status == AttendanceStatus.PRESENT)
            lines.append(f"Overall attendance: Present {present}/{len(atts)}")
        # Result summary
        res = self.get_teacher_results(teacher_id)
        if res:
            avg = statistics.mean(r.marks for r in res)
            lines.append(f"Average student mark: {avg:.1f}%")
        pending_leaves = sum(1 for l in leaves if l.status == LeaveStatus.PENDING)
        approved_leaves = sum(1 for l in leaves if l.status == LeaveStatus.APPROVED)
        lines.append(f"Leaves: Pending={pending_leaves}, Approved={approved_leaves}")
        return "\n".join(lines)

    def get_student_summary_chart(self, student_id: int) -> str:
        attendances = self.get_student_attendances(student_id)
        results = self.get_student_results(student_id)
        leaves = self.get_student_leaves(student_id)
        lines = ["==== Student Dashboard ===="]
        # Attendance per subject
        subj_att: Dict[int, list] = {}
        for a in attendances:
            subj_att.setdefault(a.subject_id, []).append(a)
        for subj_id, atts in subj_att.items():
            subj = next((s for s in self.subjects if s.id == subj_id), None)
            name = subj.name if subj else "Unknown"
            present = sum(1 for a in atts if a.status == AttendanceStatus.PRESENT)
            total = len(atts)
            lines.append(f"{name}: Attendance {present}/{total} ({100*present/total:.1f}%)")
        # Results
        for r in results:
            subj = next((s for s in self.subjects if s.id == r.subject_id), None)
            name = subj.name if subj else "Unknown"
            lines.append(f"{name}: Marks {r.marks}%")
        # Leaves
        for l in leaves:
            lines.append(f"Leave {l.reason} ({l.status.value}): {l.start_date} to {l.end_date}")
        return "\n".join(lines)

# -------- CLI Menus --------
def admin_menu(system: StudentManagementSystem, admin: Admin):
    while True:
        print("\n**** Admin Menu ****")
        print("1. Summary Charts")
        print("2. Manage Staff")
        print("3. Manage Students")
        print("4. Manage Courses")
        print("5. Manage Subjects")
        print("6. Manage Sessions")
        print("7. View Student Attendance")
        print("8. Review Feedback")
        print("9. Review Leave")
        print("0. Logout")
        choice = input("Select: ").strip()
        if choice == '1':
            print(system.get_admin_student_performance_chart())
            print(system.get_admin_staff_performance_chart())
            print(system.get_admin_courses_chart())
            print(system.get_admin_subjects_chart())
            print(system.get_admin_leave_chart())
        elif choice == '2':
            manage_staff_menu(system)
        elif choice == '3':
            manage_student_menu(system)
        elif choice == '4':
            manage_course_menu(system)
        elif choice == '5':
            manage_subject_menu(system)
        elif choice == '6':
            manage_session_menu(system)
        elif choice == '7':
            sid = input("Enter student ID: ").strip()
            if sid.isdigit():
                atts = system.view_student_attendance_admin(int(sid))
                for a in atts:
                    print(f"{a.date} Subject {a.subject_id} Status {a.status.value}")
                if not atts:
                    print("No attendance recorded.")
        elif choice == '8':
            pends = system.get_pending_feedbacks()
            if not pends:
                print("No pending feedbacks.")
                continue
            for f in pends:
                print(f"ID {f.id} From {f.sender_role.value} {f.sender_id}: {f.message}")
            fid = input("Enter feedback ID to reply (or 0 to skip): ").strip()
            if fid.isdigit() and int(fid) != 0:
                reply = input("Reply: ")
                if system.reply_feedback(int(fid), reply):
                    print("Replied.")
                else:
                    print("Invalid feedback ID.")
        elif choice == '9':
            pending_leaves = [l for l in system.leaves if l.status == LeaveStatus.PENDING]
            if not pending_leaves:
                print("No pending leaves.")
                continue
            for lv in pending_leaves:
                print(f"ID {lv.id} {lv.applicant_role.value} {lv.applicant_id}: {lv.reason} ({lv.start_date} to {lv.end_date})")
            lid = input("Enter leave ID to review: ").strip()
            decision = input("Approve (A) / Reject (R): ").strip().upper()
            if lid.isdigit():
                if decision == 'A':
                    if system.review_leave(int(lid), LeaveStatus.APPROVED):
                        print("Approved.")
                elif decision == 'R':
                    if system.review_leave(int(lid), LeaveStatus.REJECTED):
                        print("Rejected.")
                else:
                    print("Invalid decision.")
            else:
                print("Invalid ID.")
        elif choice == '0':
            break
        else:
            print("Invalid choice.")

def manage_staff_menu(system: StudentManagementSystem):
    while True:
        print("\n--- Manage Staff ---")
        print("1. Add Staff")
        print("2. Update Staff")
        print("3. Delete Staff")
        print("4. List Staff")
        print("0. Back")
        ch = input("Select: ").strip()
        if ch == '1':
            u = input("Username: ")
            p = input("Password: ")
            n = input("Full name: ")
            e = input("Email: ")
            t = system.add_staff(u, p, n, e)
            print(f"Staff added with ID {t.id}")
        elif ch == '2':
            sid = input("Staff ID: ").strip()
            if not sid.isdigit():
                print("Invalid ID")
                continue
            sid = int(sid)
            print("Enter fields to update (leave blank to skip):")
            kwargs = {}
            u = input("Username: ").strip()
            if u: kwargs['username'] = u
            p = input("Password: ").strip()
            if p: kwargs['password'] = p
            n = input("Fullname: ").strip()
            if n: kwargs['fullname'] = n
            e = input("Email: ").strip()
            if e: kwargs['email'] = e
            if kwargs:
                if system.update_staff(sid, **kwargs):
                    print("Updated.")
                else:
                    print("Staff not found.")
        elif ch == '3':
            sid = input("Staff ID to delete: ").strip()
            if sid.isdigit() and system.delete_staff(int(sid)):
                print("Deleted.")
            else:
                print("Delete failed.")
        elif ch == '4':
            for t in system.teachers:
                print(f"ID {t.id}: {t.fullname} ({t.username})")
        elif ch == '0':
            break
        else:
            print("Invalid choice.")

def manage_student_menu(system: StudentManagementSystem):
    while True:
        print("\n--- Manage Students ---")
        print("1. Add Student")
        print("2. Update Student")
        print("3. Delete Student")
        print("4. List Students")
        print("0. Back")
        ch = input("Select: ").strip()
        if ch == '1':
            u = input("Username: ")
            p = input("Password: ")
            n = input("Full name: ")
            cid = input("Course ID: ").strip()
            if not cid.isdigit():
                print("Invalid course ID")
                continue
            e = input("Email: ")
            s = system.add_student(u, p, n, int(cid), e)
            print(f"Student added with ID {s.id}")
        elif ch == '2':
            sid = input("Student ID: ").strip()
            if not sid.isdigit():
                print("Invalid")
                continue
            sid = int(sid)
            kwargs = {}
            u = input("Username (blank skip): ").strip()
            if u: kwargs['username'] = u
            p = input("Password: ").strip()
            if p: kwargs['password'] = p
            n = input("Fullname: ").strip()
            if n: kwargs['fullname'] = n
            cid = input("Course ID: ").strip()
            if cid.isdigit(): kwargs['course_id'] = int(cid)
            e = input("Email: ").strip()
            if e: kwargs['email'] = e
            if kwargs:
                if system.update_student(sid, **kwargs):
                    print("Updated.")
                else:
                    print("Student not found.")
        elif ch == '3':
            sid = input("Student ID to delete: ").strip()
            if sid.isdigit() and system.delete_student(int(sid)):
                print("Deleted.")
            else:
                print("Failed.")
        elif ch == '4':
            for s in system.students:
                course_name = "N/A"
                c = next((c for c in system.courses if c.id == s.course_id), None)
                if c: course_name = c.name
                print(f"ID {s.id}: {s.fullname} ({s.username}) Course: {course_name}")
        elif ch == '0':
            break
        else:
            print("Invalid.")

def manage_course_menu(system: StudentManagementSystem):
    while True:
        print("\n--- Manage Courses ---")
        print("1. Add Course")
        print("2. Update Course")
        print("3. Delete Course")
        print("4. List Courses")
        print("0. Back")
        ch = input("Select: ").strip()
        if ch == '1':
            name = input("Name: ")
            code = input("Code: ")
            desc = input("Description: ")
            c = system.add_course(name, code, desc)
            print(f"Course added ID {c.id}")
        elif ch == '2':
            cid = input("Course ID: ").strip()
            if not cid.isdigit():
                print("Invalid")
                continue
            cid = int(cid)
            kwargs = {}
            name = input("Name (blank skip): ").strip()
            if name: kwargs['name'] = name
            code = input("Code: ").strip()
            if code: kwargs['code'] = code
            desc = input("Description: ").strip()
            if desc: kwargs['description'] = desc
            if system.update_course(cid, **kwargs):
                print("Updated.")
            else:
                print("Not found.")
        elif ch == '3':
            cid = input("Course ID to delete: ").strip()
            if cid.isdigit() and system.delete_course(int(cid)):
                print("Deleted.")
            else:
                print("Failed.")
        elif ch == '4':
            for c in system.courses:
                print(f"ID {c.id}: {c.name} ({c.code})")
        elif ch == '0':
            break

def manage_subject_menu(system: StudentManagementSystem):
    while True:
        print("\n--- Manage Subjects ---")
        print("1. Add Subject")
        print("2. Update Subject")
        print("3. Delete Subject")
        print("4. List Subjects")
        print("0. Back")
        ch = input("Select: ").strip()
        if ch == '1':
            name = input("Name: ")
            cid = input("Course ID: ").strip()
            if not cid.isdigit():
                print("Invalid")
                continue
            tid = input("Teacher ID (optional): ").strip()
            teacher_id = int(tid) if tid.isdigit() else None
            s = system.add_subject(name, int(cid), teacher_id)
            print(f"Subject added ID {s.id}")
        elif ch == '2':
            sid = input("Subject ID: ").strip()
            if not sid.isdigit(): continue
            sid = int(sid)
            kwargs = {}
            name = input("Name: ").strip()
            if name: kwargs['name'] = name
            cid = input("Course ID: ").strip()
            if cid.isdigit(): kwargs['course_id'] = int(cid)
            tid = input("Teacher ID (blank to keep): ").strip()
            if tid.isdigit(): kwargs['teacher_id'] = int(tid)
            if system.update_subject(sid, **kwargs):
                print("Updated.")
            else:
                print("Not found.")
        elif ch == '3':
            sid = input("Subject ID to delete: ").strip()
            if sid.isdigit() and system.delete_subject(int(sid)):
                print("Deleted.")
            else:
                print("Failed.")
        elif ch == '4':
            for s in system.subjects:
                t = next((t for t in system.teachers if t.id == s.teacher_id), None)
                teacher_name = t.fullname if t else "None"
                c = next((c for c in system.courses if c.id == s.course_id), None)
                course_name = c.name if c else "None"
                print(f"ID {s.id}: {s.name} (Course:{course_name}, Teacher:{teacher_name})")
        elif ch == '0':
            break

def manage_session_menu(system: StudentManagementSystem):
    while True:
        print("\n--- Manage Sessions ---")
        print("1. Add Session")
        print("2. Update Session")
        print("3. Delete Session")
        print("4. List Sessions")
        print("0. Back")
        ch = input("Select: ").strip()
        if ch == '1':
            year = input("Year: ").strip()
            term = input("Term: ")
            active = input("Active (y/n): ").strip().lower()
            is_active = active == 'y'
            if year.isdigit():
                s = system.add_session(int(year), term, is_active)
                print(f"Session added ID {s.id}")
            else:
                print("Invalid year")
        elif ch == '2':
            sid = input("Session ID: ").strip()
            if not sid.isdigit(): continue
            sid = int(sid)
            kwargs = {}
            year = input("Year (blank skip): ").strip()
            if year.isdigit(): kwargs['year'] = int(year)
            term = input("Term: ").strip()
            if term: kwargs['term'] = term
            act = input("Active (y/n): ").strip().lower()
            if act: kwargs['is_active'] = act == 'y'
            if system.update_session(sid, **kwargs):
                print("Updated.")
            else:
                print("Not found.")
        elif ch == '3':
            sid = input("Session ID to delete: ").strip()
            if sid.isdigit() and system.delete_session(int(sid)):
                print("Deleted.")
            else:
                print("Failed.")
        elif ch == '4':
            for s in system.sessions:
                print(f"ID {s.id}: Year {s.year} Term {s.term} Active {s.is_active}")
        elif ch == '0':
            break

def teacher_menu(system: StudentManagementSystem, teacher: Teacher):
    while True:
        print("\n**** Teacher Menu ****")
        print("1. Summary Charts")
        print("2. Take/Update Attendance")
        print("3. Add/Update Result")
        print("4. Apply for Leave")
        print("5. Send Feedback")
        print("0. Logout")
        choice = input("Select: ").strip()
        if choice == '1':
            print(system.get_teacher_summary_chart(teacher.id))
        elif choice == '2':
            print("1. New Attendance")
            print("2. Update Attendance")
            sub = input("Choose: ").strip()
            if sub == '1':
                sid = input("Student ID: ").strip()
                subj_id = input("Subject ID: ").strip()
                sess_id = input("Session ID: ").strip()
                date_str = input("Date (YYYY-MM-DD): ").strip()
                status = input("Status (present/absent): ").strip().lower()
                if not all([sid.isdigit(), subj_id.isdigit(), sess_id.isdigit()]):
                    print("Invalid")
                    continue
                try:
                    d = datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    print("Invalid date")
                    continue
                att_status = AttendanceStatus.PRESENT if status == 'present' else AttendanceStatus.ABSENT
                a = system.record_attendance(int(sid), int(subj_id), int(sess_id), d, att_status)
                if a:
                    print(f"Attendance recorded ID {a.id}")
                else:
                    print("Failed (invalid subject?)")
            elif sub == '2':
                aid = input("Attendance ID: ").strip()
                status = input("New status (present/absent): ").strip().lower()
                att_status = AttendanceStatus.PRESENT if status == 'present' else AttendanceStatus.ABSENT
                if aid.isdigit() and system.update_attendance(int(aid), att_status):
                    print("Updated.")
                else:
                    print("Failed.")
        elif choice == '3':
            print("1. Add Result")
            print("2. Update Result")
            sub = input("Choose: ").strip()
            if sub == '1':
                sid = input("Student ID: ").strip()
                subj_id = input("Subject ID: ").strip()
                sess_id = input("Session ID: ").strip()
                marks = input("Marks (0-100): ").strip()
                grade = input("Grade (optional): ").strip()
                try:
                    marks_f = float(marks)
                    if not (0 <= marks_f <= 100):
                        raise ValueError
                except:
                    print("Invalid marks")
                    continue
                r = system.add_result(int(sid), int(subj_id), int(sess_id), marks_f, grade)
                if r:
                    print(f"Result added ID {r.id}")
                else:
                    print("Failed.")
            elif sub == '2':
                rid = input("Result ID: ").strip()
                marks = input("New marks: ").strip()
                grade = input("New grade (optional): ").strip()
                try:
                    marks_f = float(marks)
                except:
                    print("Invalid marks")
                    continue
                if rid.isdigit() and system.update_result(int(rid), marks_f, grade):
                    print("Updated.")
                else:
                    print("Failed.")
        elif choice == '4':
            reason = input("Reason: ")
            start = input("Start date (YYYY-MM-DD): ").strip()
            end = input("End date (YYYY-MM-DD): ").strip()
            try:
                sd = datetime.strptime(start, "%Y-%m-%d").date()
                ed = datetime.strptime(end, "%Y-%m-%d").date()
            except:
                print("Invalid dates")
                continue
            lv = system.apply_leave_staff(teacher.id, reason, sd, ed)
            print(f"Leave applied ID {lv.id} (status: pending)")
        elif choice == '5':
            msg = input("Feedback message: ")
            fb = system.send_feedback_staff(teacher.id, msg)
            print(f"Feedback sent ID {fb.id}")
        elif choice == '0':
            break

def student_menu(system: StudentManagementSystem, student: Student):
    while True:
        print("\n**** Student Menu ****")
        print("1. Summary Charts")
        print("2. View Attendance")
        print("3. View Results")
        print("4. Apply for Leave")
        print("5. Send Feedback")
        print("0. Logout")
        choice = input("Select: ").strip()
        if choice == '1':
            print(system.get_student_summary_chart(student.id))
        elif choice == '2':
            atts = system.get_student_attendances(student.id)
            if not atts:
                print("No attendance records.")
                continue
            for a in atts:
                subj = next((s for s in system.subjects if s.id == a.subject_id), None)
                subj_name = subj.name if subj else "Unknown"
                print(f"Date: {a.date} | Subject: {subj_name} | Status: {a.status.value}")
        elif choice == '3':
            results = system.get_student_results(student.id)
            if not results:
                print("No results.")
                continue
            for r in results:
                subj = next((s for s in system.subjects if s.id == r.subject_id), None)
                subj_name = subj.name if subj else "Unknown"
                print(f"Subject: {subj_name} | Marks: {r.marks}% | Grade: {r.grade}")
        elif choice == '4':
            reason = input("Reason: ")
            start = input("Start date (YYYY-MM-DD): ").strip()
            end = input("End date (YYYY-MM-DD): ").strip()
            try:
                sd = datetime.strptime(start, "%Y-%m-%d").date()
                ed = datetime.strptime(end, "%Y-%m-%d").date()
            except:
                print("Invalid dates")
                continue
            lv = system.apply_leave_student(student.id, reason, sd, ed)
            print(f"Leave applied ID {lv.id} (status: pending)")
        elif choice == '5':
            msg = input("Feedback message: ")
            fb = system.send_feedback_student(student.id, msg)
            print(f"Feedback sent ID {fb.id}")
        elif choice == '0':
            break

def preload_data(system: StudentManagementSystem):
    # Create admin
    system.admins.append(Admin(1, "admin", "admin123", "Admin User"))

    # Courses
    c1 = system.add_course("Computer Science", "CS101")
    c2 = system.add_course("Mathematics", "MATH101")
    # Teachers
    t1 = system.add_staff("teacher1", "teacher1", "Alice Smith")
    t2 = system.add_staff("teacher2", "teacher2", "Bob Jones")
    # Students
    s1 = system.add_student("student1", "student1", "Charlie Brown", c1.id)
    s2 = system.add_student("student2", "student2", "Dana White", c1.id)
    s3 = system.add_student("student3", "student3", "Eve Black", c2.id)

    # Subjects
    sub1 = system.add_subject("Algorithms", c1.id, t1.id)
    sub2 = system.add_subject("Data Structures", c1.id, t1.id)
    sub3 = system.add_subject("Calculus", c2.id, t2.id)
    # Session
    ses = system.add_session(2023, "Fall", True)

    # Some attendance
    system.record_attendance(s1.id, sub1.id, ses.id, date(2023,10,1), AttendanceStatus.PRESENT)
    system.record_attendance(s1.id, sub1.id, ses.id, date(2023,10,2), AttendanceStatus.PRESENT)
    system.record_attendance(s2.id, sub1.id, ses.id, date(2023,10,1), AttendanceStatus.ABSENT)
    system.record_attendance(s3.id, sub3.id, ses.id, date(2023,10,1), AttendanceStatus.PRESENT)

    # Results
    system.add_result(s1.id, sub1.id, ses.id, 85, "B+")
    system.add_result(s2.id, sub1.id, ses.id, 60, "C")
    system.add_result(s1.id, sub2.id, ses.id, 92, "A")
    system.add_result(s3.id, sub3.id, ses.id, 78, "B")

    # Leaves
    system.apply_leave_student(s1.id, "Sick", date(2023,11,1), date(2023,11,2))
    system.apply_leave_staff(t1.id, "Family event", date(2023,11,5), date(2023,11,6))

    # Feedback
    system.send_feedback_student(s1.id, "Need more lab sessions.")
    system.send_feedback_staff(t2.id, "Requesting new equipment.")

def main():
    system = StudentManagementSystem()
    preload_data(system)

    print("==== Student Management System ====")
    while True:
        username = input("Username (or 'quit'): ").strip()
        if username.lower() == 'quit':
            break
        password = input("Password: ").strip()
        user = system.login(username, password)
        if not user:
            print("Invalid credentials.")
            continue
        print(f"Welcome {user.fullname} ({user.get_role().value})")
        if isinstance(user, Admin):
            admin_menu(system, user)
        elif isinstance(user, Teacher):
            teacher_menu(system, user)
        elif isinstance(user, Student):
            student_menu(system, user)
        else:
            print("Unknown role.")

if __name__ == "__main__":
    main()