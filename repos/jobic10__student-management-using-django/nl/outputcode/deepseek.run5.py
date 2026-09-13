from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
import uuid

class Person:
    def __init__(self, name: str, email: str) -> None:
        self.id: str = str(uuid.uuid4())
        self.name = name
        self.email = email

class Student(Person):
    def __init__(self, name: str, email: str) -> None:
        super().__init__(name, email)
        self.courses: List[str] = []  # course ids
        self.subjects: List[str] = []  # subject ids

class Staff(Person):
    def __init__(self, name: str, email: str, role: str = "Teacher") -> None:
        super().__init__(name, email)
        self.role = role
        self.subjects_taught: List[str] = []  # subject ids

class Admin(Person):
    def __init__(self, name: str, email: str) -> None:
        super().__init__(name, email)

class Course:
    def __init__(self, name: str) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.subjects: List[str] = []  # subject ids

class Subject:
    def __init__(self, name: str, course_id: str, staff_id: Optional[str] = None) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.course_id = course_id
        self.teacher_id = staff_id  # who teaches this subject

class Session:
    def __init__(self, name: str, start_year: int, end_year: int) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.start_year = start_year
        self.end_year = end_year

class Attendance:
    def __init__(self, student_id: str, subject_id: str, session_id: str, att_date: date, status: str) -> None:
        self.id = str(uuid.uuid4())
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.date = att_date
        self.status = status  # present, absent

class Result:
    def __init__(self, student_id: str, subject_id: str, session_id: str, marks: float) -> None:
        self.id = str(uuid.uuid4())
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.marks = marks
        self.grade = self._calculate_grade(marks)

    def _calculate_grade(self, marks: float) -> str:
        if marks >= 90:
            return 'A'
        elif marks >= 80:
            return 'B'
        elif marks >= 70:
            return 'C'
        elif marks >= 60:
            return 'D'
        else:
            return 'F'

class Leave:
    def __init__(self, applicant_id: str, applicant_type: str, start_date: date, end_date: date, reason: str) -> None:
        self.id = str(uuid.uuid4())
        self.applicant_id = applicant_id
        self.applicant_type = applicant_type  # "student" or "staff"
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = "pending"  # pending, approved, rejected
        self.reviewed_by = None  # admin id

class Feedback:
    def __init__(self, sender_id: str, sender_type: str, message: str) -> None:
        self.id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.sender_type = sender_type  # "student" or "staff"
        self.message = message
        self.reply = ""
        self.status = "unreviewed"  # unreviewed, replied

class SchoolSystem:
    def __init__(self) -> None:
        self.students: Dict[str, Student] = {}
        self.staff_members: Dict[str, Staff] = {}
        self.admins: Dict[str, Admin] = {}
        self.courses: Dict[str, Course] = {}
        self.subjects: Dict[str, Subject] = {}
        self.sessions: Dict[str, Session] = {}
        self.attendances: Dict[str, Attendance] = {}
        self.results: Dict[str, Result] = {}
        self.leaves: Dict[str, Leave] = {}
        self.feedbacks: Dict[str, Feedback] = {}

    # ---------- Admin methods ----------
    def add_staff(self, name: str, email: str, role: str = "Teacher") -> Staff:
        staff = Staff(name, email, role)
        self.staff_members[staff.id] = staff
        return staff

    def update_staff(self, staff_id: str, name: Optional[str] = None, email: Optional[str] = None, role: Optional[str] = None) -> bool:
        staff = self.staff_members.get(staff_id)
        if not staff:
            return False
        if name:
            staff.name = name
        if email:
            staff.email = email
        if role:
            staff.role = role
        return True

    def delete_staff(self, staff_id: str) -> bool:
        if staff_id in self.staff_members:
            del self.staff_members[staff_id]
            return True
        return False

    def add_student(self, name: str, email: str) -> Student:
        student = Student(name, email)
        self.students[student.id] = student
        return student

    def update_student(self, student_id: str, name: Optional[str] = None, email: Optional[str] = None) -> bool:
        student = self.students.get(student_id)
        if not student:
            return False
        if name:
            student.name = name
        if email:
            student.email = email
        return True

    def delete_student(self, student_id: str) -> bool:
        if student_id in self.students:
            del self.students[student_id]
            return True
        return False

    def add_course(self, name: str) -> Course:
        course = Course(name)
        self.courses[course.id] = course
        return course

    def update_course(self, course_id: str, name: str) -> bool:
        course = self.courses.get(course_id)
        if not course:
            return False
        course.name = name
        return True

    def delete_course(self, course_id: str) -> bool:
        if course_id in self.courses:
            del self.courses[course_id]
            # Optionally remove subject references, but for simplicity not required.
            return True
        return False

    def add_subject(self, name: str, course_id: str, staff_id: Optional[str] = None) -> Subject:
        subject = Subject(name, course_id, staff_id)
        self.subjects[subject.id] = subject
        if course_id in self.courses:
            self.courses[course_id].subjects.append(subject.id)
        if staff_id and staff_id in self.staff_members:
            self.staff_members[staff_id].subjects_taught.append(subject.id)
        return subject

    def update_subject(self, subject_id: str, name: Optional[str] = None, course_id: Optional[str] = None, staff_id: Optional[str] = None) -> bool:
        subj = self.subjects.get(subject_id)
        if not subj:
            return False
        if name:
            subj.name = name
        if course_id:
            subj.course_id = course_id
        if staff_id is not None:
            if subj.teacher_id:
                old_staff = self.staff_members.get(subj.teacher_id)
                if old_staff and subject_id in old_staff.subjects_taught:
                    old_staff.subjects_taught.remove(subject_id)
            subj.teacher_id = staff_id
            if staff_id and staff_id in self.staff_members:
                self.staff_members[staff_id].subjects_taught.append(subject_id)
        return True

    def delete_subject(self, subject_id: str) -> bool:
        subj = self.subjects.pop(subject_id, None)
        if not subj:
            return False
        # Clean up references
        course = self.courses.get(subj.course_id)
        if course and subject_id in course.subjects:
            course.subjects.remove(subject_id)
        if subj.teacher_id:
            staff = self.staff_members.get(subj.teacher_id)
            if staff and subject_id in staff.subjects_taught:
                staff.subjects_taught.remove(subject_id)
        return True

    def add_session(self, name: str, start_year: int, end_year: int) -> Session:
        session = Session(name, start_year, end_year)
        self.sessions[session.id] = session
        return session

    def update_session(self, session_id: str, name: Optional[str] = None, start_year: Optional[int] = None, end_year: Optional[int] = None) -> bool:
        sess = self.sessions.get(session_id)
        if not sess:
            return False
        if name:
            sess.name = name
        if start_year:
            sess.start_year = start_year
        if end_year:
            sess.end_year = end_year
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def view_student_attendance(self, student_id: str) -> List[Dict[str, Any]]:
        records = []
        for att in self.attendances.values():
            if att.student_id == student_id:
                records.append({
                    'attendance_id': att.id,
                    'date': att.date,
                    'subject_id': att.subject_id,
                    'status': att.status
                })
        return records

    def review_feedback(self, feedback_id: str, reply: str, admin_id: str) -> bool:
        fb = self.feedbacks.get(feedback_id)
        if not fb or fb.status != "unreviewed":
            return False
        fb.reply = reply
        fb.status = "replied"
        # Admin who reviewed? Not required but we could store.
        return True

    def approve_leave(self, leave_id: str, admin_id: str) -> bool:
        leave = self.leaves.get(leave_id)
        if not leave or leave.status != "pending":
            return False
        leave.status = "approved"
        leave.reviewed_by = admin_id
        return True

    def reject_leave(self, leave_id: str, admin_id: str) -> bool:
        leave = self.leaves.get(leave_id)
        if not leave or leave.status != "pending":
            return False
        leave.status = "rejected"
        leave.reviewed_by = admin_id
        return True

    def get_overall_summary(self) -> Dict[str, Any]:
        # Performance charts data
        total_students = len(self.students)
        total_staff = len(self.staff_members)
        total_courses = len(self.courses)
        total_subjects = len(self.subjects)
        total_sessions = len(self.sessions)

        # Results summary
        avg_marks = 0.0
        if self.results:
            avg_marks = sum(r.marks for r in self.results.values()) / len(self.results)
        # Attendance summary
        total_attendance = len(self.attendances)
        present_count = sum(1 for a in self.attendances.values() if a.status == "present")
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0

        # Leave status counts
        leave_stats = {"pending": 0, "approved": 0, "rejected": 0}
        for l in self.leaves.values():
            leave_stats[l.status] += 1

        return {
            "total_students": total_students,
            "total_staff": total_staff,
            "total_courses": total_courses,
            "total_subjects": total_subjects,
            "total_sessions": total_sessions,
            "average_marks": round(avg_marks, 2),
            "attendance_rate": round(attendance_rate, 2),
            "leave_stats": leave_stats
        }

    # ---------- Staff methods ----------
    def take_attendance(self, staff_id: str, student_id: str, subject_id: str, session_id: str, att_date: date, status: str) -> Optional[Attendance]:
        # Check staff teaches this subject
        staff = self.staff_members.get(staff_id)
        if not staff or subject_id not in staff.subjects_taught:
            return None
        if student_id not in self.students:
            return None
        if subject_id not in self.subjects:
            return None
        if session_id not in self.sessions:
            return None
        att = Attendance(student_id, subject_id, session_id, att_date, status)
        self.attendances[att.id] = att
        return att

    def update_attendance(self, attendance_id: str, staff_id: str, new_status: str) -> bool:
        att = self.attendances.get(attendance_id)
        if not att:
            return False
        # Ensure this staff teaches the subject
        staff = self.staff_members.get(staff_id)
        if not staff or att.subject_id not in staff.subjects_taught:
            return False
        att.status = new_status
        return True

    def add_result(self, staff_id: str, student_id: str, subject_id: str, session_id: str, marks: float) -> Optional[Result]:
        staff = self.staff_members.get(staff_id)
        if not staff or subject_id not in staff.subjects_taught:
            return None
        if student_id not in self.students:
            return None
        if subject_id not in self.subjects:
            return None
        if session_id not in self.sessions:
            return None
        res = Result(student_id, subject_id, session_id, marks)
        self.results[res.id] = res
        return res

    def update_result(self, result_id: str, staff_id: str, new_marks: float) -> bool:
        res = self.results.get(result_id)
        if not res:
            return False
        staff = self.staff_members.get(staff_id)
        if not staff or res.subject_id not in staff.subjects_taught:
            return False
        res.marks = new_marks
        res.grade = res._calculate_grade(new_marks)
        return True

    def apply_leave_staff(self, staff_id: str, start_date: date, end_date: date, reason: str) -> Optional[Leave]:
        if staff_id not in self.staff_members:
            return None
        leave = Leave(staff_id, "staff", start_date, end_date, reason)
        self.leaves[leave.id] = leave
        return leave

    def send_feedback_staff(self, staff_id: str, message: str) -> Optional[Feedback]:
        if staff_id not in self.staff_members:
            return None
        fb = Feedback(staff_id, "staff", message)
        self.feedbacks[fb.id] = fb
        return fb

    def get_my_students_performance(self, staff_id: str) -> List[Dict[str, Any]]:
        staff = self.staff_members.get(staff_id)
        if not staff:
            return []
        students_data = {}
        for res in self.results.values():
            if res.subject_id in staff.subjects_taught:
                student = self.students.get(res.student_id)
                if student:
                    sid = student.id
                    if sid not in students_data:
                        students_data[sid] = {'name': student.name, 'subjects': {}}
                    students_data[sid]['subjects'][res.subject_id] = {
                        'marks': res.marks,
                        'grade': res.grade,
                        'session_id': res.session_id
                    }
        return [{'student_id': sid, 'name': info['name'], 'subjects': info['subjects']} for sid, info in students_data.items()]

    def get_my_subjects_summary(self, staff_id: str) -> List[Dict[str, Any]]:
        staff = self.staff_members.get(staff_id)
        if not staff:
            return []
        summary = []
        for subj_id in staff.subjects_taught:
            subj = self.subjects.get(subj_id)
            if not subj:
                continue
            results = [r for r in self.results.values() if r.subject_id == subj_id]
            avg = sum(r.marks for r in results) / len(results) if results else 0
            summary.append({
                'subject_id': subj.id,
                'name': subj.name,
                'average_marks': round(avg, 2),
                'total_results': len(results)
            })
        return summary

    def get_leave_status_staff(self, staff_id: str) -> List[Dict[str, Any]]:
        return [{'leave_id': l.id, 'start': l.start_date, 'end': l.end_date, 'reason': l.reason, 'status': l.status}
                for l in self.leaves.values() if l.applicant_id == staff_id and l.applicant_type == "staff"]

    # ---------- Student methods ----------
    def view_attendance(self, student_id: str) -> Optional[List[Dict[str, Any]]]:
        if student_id not in self.students:
            return None
        return self.view_student_attendance(student_id)

    def view_result(self, student_id: str) -> Optional[List[Dict[str, Any]]]:
        if student_id not in self.students:
            return None
        results = [r for r in self.results.values() if r.student_id == student_id]
        return [{'result_id': r.id, 'subject_id': r.subject_id, 'marks': r.marks, 'grade': r.grade, 'session_id': r.session_id} for r in results]

    def apply_leave_student(self, student_id: str, start_date: date, end_date: date, reason: str) -> Optional[Leave]:
        if student_id not in self.students:
            return None
        leave = Leave(student_id, "student", start_date, end_date, reason)
        self.leaves[leave.id] = leave
        return leave

    def send_feedback_student(self, student_id: str, message: str) -> Optional[Feedback]:
        if student_id not in self.students:
            return None
        fb = Feedback(student_id, "student", message)
        self.feedbacks[fb.id] = fb
        return fb

    def get_student_attendance_summary(self, student_id: str) -> Optional[Dict[str, Any]]:
        if student_id not in self.students:
            return None
        records = self.view_attendance(student_id)
        if records is None:
            return None
        total = len(records)
        present = sum(1 for r in records if r['status'] == 'present')
        rate = (present / total * 100) if total > 0 else 0
        return {'total_attendance': total, 'present': present, 'attendance_rate': round(rate, 2)}

    def get_student_result_summary(self, student_id: str) -> Optional[Dict[str, Any]]:
        if student_id not in self.students:
            return None
        results = self.view_result(student_id)
        if results is None:
            return None
        total_marks = sum(r['marks'] for r in results)
        num = len(results)
        avg = total_marks / num if num > 0 else 0
        return {'total_results': num, 'average_marks': round(avg, 2)}

    def get_student_leave_status(self, student_id: str) -> Optional[List[Dict[str, Any]]]:
        if student_id not in self.students:
            return None
        return [{'leave_id': l.id, 'start': l.start_date, 'end': l.end_date, 'reason': l.reason, 'status': l.status}
                for l in self.leaves.values() if l.applicant_id == student_id and l.applicant_type == "student"]

# ----- Example usage (can be removed if only classes needed) -----
if __name__ == "__main__":
    system = SchoolSystem()
    admin = Admin("Admin Name", "admin@school.com")
    system.admins[admin.id] = admin

    # Admin adds staff, student, course, subject, session
    staff = system.add_staff("John Staff", "john@school.com")
    student = system.add_student("Alice Student", "alice@school.com")
    course = system.add_course("Computer Science")
    session = system.add_session("2024-2025", 2024, 2025)
    subject = system.add_subject("Python Programming", course.id, staff.id)

    # Enroll student in the course/subject
    student.subjects.append(subject.id)
    student.courses.append(course.id)
    staff.subjects_taught = [subject.id]

    # Staff takes attendance
    system.take_attendance(staff.id, student.id, subject.id, session.id, date.today(), "present")
    # Staff adds result
    system.add_result(staff.id, student.id, subject.id, session.id, 85.5)

    # Student views
    print("Student Attendance Summary:", system.get_student_attendance_summary(student.id))
    print("Student Result Summary:", system.get_student_result_summary(student.id))

    # Student applies leave, sends feedback
    leave = system.apply_leave_student(student.id, date.today(), date.today(), "Sick")
    fb = system.send_feedback_student(student.id, "Great course!")
    print("Leaves:", system.get_student_leave_status(student.id))
    print("Feedbacks:", [(f.id, f.message, f.status) for f in system.feedbacks.values()])

    # Admin reviews
    system.review_feedback(fb.id, "Thank you!", admin.id)
    system.approve_leave(leave.id, admin.id)
    print("After review:", fb.status, fb.reply, leave.status)

    # Overall summary
    print("Overall Summary:", system.get_overall_summary())