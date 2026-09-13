from __future__ import annotations
import datetime
from typing import List, Optional, Dict

class User:
    def __init__(self, user_id: str, name: str, email: str, password: str, role: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password = password
        self.role = role  # admin, staff, student

class Admin(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, 'admin')

class Staff(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, 'staff')
        self.assigned_subjects: List[str] = []  # subject_ids

class Student(User):
    def __init__(self, user_id: str, name: str, email: str, password: str):
        super().__init__(user_id, name, email, password, 'student')
        self.enrolled_courses: List[str] = []  # course_ids

class Course:
    def __init__(self, course_id: str, name: str, description: str = ""):
        self.course_id = course_id
        self.name = name
        self.description = description

class Subject:
    def __init__(self, subject_id: str, name: str, course_id: str):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id

class Session:
    def __init__(self, session_id: str, name: str, start_date: datetime.date, end_date: datetime.date):
        self.session_id = session_id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date

class Attendance:
    def __init__(self, attendance_id: str, session_id: str, subject_id: str, student_id: str,
                 date: datetime.date, status: str):
        self.attendance_id = attendance_id
        self.session_id = session_id
        self.subject_id = subject_id
        self.student_id = student_id
        self.date = date
        self.status = status  # present, absent, late

class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str, session_id: str, marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.marks = marks

class LeaveApplication:
    def __init__(self, leave_id: str, applicant_id: str, applicant_role: str,
                 start_date: datetime.date, end_date: datetime.date, reason: str, status: str = 'pending'):
        self.leave_id = leave_id
        self.applicant_id = applicant_id
        self.applicant_role = applicant_role
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.status = status  # pending, approved, rejected

class Feedback:
    def __init__(self, feedback_id: str, sender_id: str, sender_role: str, message: str, reply: str = None):
        self.feedback_id = feedback_id
        self.sender_id = sender_id
        self.sender_role = sender_role
        self.message = message
        self.reply = reply

class StudentManagementSystem:
    def __init__(self):
        self.users: List[User] = []
        self.courses: List[Course] = []
        self.subjects: List[Subject] = []
        self.sessions: List[Session] = []
        self.attendances: List[Attendance] = []
        self.results: List[Result] = []
        self.leave_applications: List[LeaveApplication] = []
        self.feedbacks: List[Feedback] = []
        self._next_id = 1

    def _generate_id(self, prefix: str) -> str:
        new_id = f"{prefix}{self._next_id:04d}"
        self._next_id += 1
        return new_id

    # Authentication
    def authenticate(self, user_id: str, password: str) -> Optional[User]:
        for user in self.users:
            if user.user_id == user_id and user.password == password:
                return user
        return None

    # Admin - Manage Staff
    def add_staff(self, name: str, email: str, password: str) -> Staff:
        user_id = self._generate_id("STAFF")
        staff = Staff(user_id, name, email, password)
        self.users.append(staff)
        return staff

    def update_staff(self, user_id: str, name: str = None, email: str = None, password: str = None) -> bool:
        staff = self._find_user(user_id, 'staff')
        if not staff:
            return False
        if name: staff.name = name
        if email: staff.email = email
        if password: staff.password = password
        return True

    def delete_staff(self, user_id: str) -> bool:
        staff = self._find_user(user_id, 'staff')
        if staff:
            self.users.remove(staff)
            return True
        return False

    # Admin - Manage Students
    def add_student(self, name: str, email: str, password: str) -> Student:
        user_id = self._generate_id("STU")
        student = Student(user_id, name, email, password)
        self.users.append(student)
        return student

    def update_student(self, user_id: str, name: str = None, email: str = None, password: str = None) -> bool:
        student = self._find_user(user_id, 'student')
        if not student:
            return False
        if name: student.name = name
        if email: student.email = email
        if password: student.password = password
        return True

    def delete_student(self, user_id: str) -> bool:
        student = self._find_user(user_id, 'student')
        if student:
            self.users.remove(student)
            return True
        return False

    # Admin - Manage Courses
    def add_course(self, name: str, description: str = "") -> Course:
        course_id = self._generate_id("COURSE")
        course = Course(course_id, name, description)
        self.courses.append(course)
        return course

    def update_course(self, course_id: str, name: str = None, description: str = None) -> bool:
        course = self._find_course(course_id)
        if not course:
            return False
        if name: course.name = name
        if description: course.description = description
        return True

    def delete_course(self, course_id: str) -> bool:
        course = self._find_course(course_id)
        if course:
            self.courses.remove(course)
            return True
        return False

    # Admin - Manage Subjects
    def add_subject(self, name: str, course_id: str) -> Optional[Subject]:
        if not self._find_course(course_id):
            return None
        subject_id = self._generate_id("SUBJ")
        subject = Subject(subject_id, name, course_id)
        self.subjects.append(subject)
        return subject

    def update_subject(self, subject_id: str, name: str = None, course_id: str = None) -> bool:
        subject = self._find_subject(subject_id)
        if not subject:
            return False
        if name: subject.name = name
        if course_id and self._find_course(course_id): subject.course_id = course_id
        return True

    def delete_subject(self, subject_id: str) -> bool:
        subject = self._find_subject(subject_id)
        if subject:
            self.subjects.remove(subject)
            return True
        return False

    # Admin - Manage Sessions
    def add_session(self, name: str, start_date: datetime.date, end_date: datetime.date) -> Session:
        session_id = self._generate_id("SESS")
        session = Session(session_id, name, start_date, end_date)
        self.sessions.append(session)
        return session

    def update_session(self, session_id: str, name: str = None, start_date: datetime.date = None,
                       end_date: datetime.date = None) -> bool:
        session = self._find_session(session_id)
        if not session:
            return False
        if name: session.name = name
        if start_date: session.start_date = start_date
        if end_date: session.end_date = end_date
        return True

    def delete_session(self, session_id: str) -> bool:
        session = self._find_session(session_id)
        if session:
            self.sessions.remove(session)
            return True
        return False

    # Attendance
    def add_attendance(self, session_id: str, subject_id: str, student_id: str,
                       date: datetime.date, status: str) -> Optional[Attendance]:
        if not (self._find_session(session_id) and self._find_subject(subject_id) and self._find_student(student_id)):
            return None
        attendance_id = self._generate_id("ATT")
        att = Attendance(attendance_id, session_id, subject_id, student_id, date, status)
        self.attendances.append(att)
        return att

    def get_student_attendance(self, student_id: str, session_id: str = None) -> List[Attendance]:
        return [a for a in self.attendances if a.student_id == student_id and (session_id is None or a.session_id == session_id)]

    def get_subject_attendance(self, subject_id: str, session_id: str = None) -> List[Attendance]:
        return [a for a in self.attendances if a.subject_id == subject_id and (session_id is None or a.session_id == session_id)]

    # Results
    def add_result(self, student_id: str, subject_id: str, session_id: str, marks: float) -> Optional[Result]:
        if not (self._find_student(student_id) and self._find_subject(subject_id) and self._find_session(session_id)):
            return None
        result_id = self._generate_id("RES")
        result = Result(result_id, student_id, subject_id, session_id, marks)
        self.results.append(result)
        return result

    def get_student_results(self, student_id: str, session_id: str = None) -> List[Result]:
        return [r for r in self.results if r.student_id == student_id and (session_id is None or r.session_id == session_id)]

    # Leave
    def apply_leave(self, applicant_id: str, applicant_role: str, start_date: datetime.date,
                    end_date: datetime.date, reason: str) -> LeaveApplication:
        leave_id = self._generate_id("LEAVE")
        leave = LeaveApplication(leave_id, applicant_id, applicant_role, start_date, end_date, reason)
        self.leave_applications.append(leave)
        return leave

    def review_leave(self, leave_id: str, action: str) -> bool:
        leave = self._find_leave(leave_id)
        if leave and action in ('approve', 'reject'):
            leave.status = 'approved' if action == 'approve' else 'rejected'
            return True
        return False

    # Feedback
    def send_feedback(self, sender_id: str, sender_role: str, message: str) -> Feedback:
        feedback_id = self._generate_id("FB")
        fb = Feedback(feedback_id, sender_id, sender_role, message)
        self.feedbacks.append(fb)
        return fb

    def reply_feedback(self, feedback_id: str, reply: str) -> bool:
        fb = self._find_feedback(feedback_id)
        if fb:
            fb.reply = reply
            return True
        return False

    # Charts / Summary
    def admin_summary(self):
        total_staff = len([u for u in self.users if u.role == 'staff'])
        total_students = len([u for u in self.users if u.role == 'student'])
        total_courses = len(self.courses)
        total_subjects = len(self.subjects)
        total_sessions = len(self.sessions)
        pending_leaves = len([l for l in self.leave_applications if l.status == 'pending'])
        pending_feedbacks = len([f for f in self.feedbacks if f.reply is None])
        print("\n--- Summary Charts (Admin) ---")
        print(f"Staff: {total_staff}")
        print(f"Students: {total_students}")
        print(f"Courses: {total_courses}")
        print(f"Subjects: {total_subjects}")
        print(f"Sessions: {total_sessions}")
        print(f"Pending Leaves: {pending_leaves}")
        print(f"Unanswered Feedbacks: {pending_feedbacks}")
        # Additional: average result per subject? Simple.
        if self.results and self.subjects:
            print("\nAverage marks per subject:")
            subject_marks: Dict[str, List[float]] = {}
            for r in self.results:
                subject_marks.setdefault(r.subject_id, []).append(r.marks)
            for sub in self.subjects:
                marks = subject_marks.get(sub.subject_id, [])
                avg = sum(marks)/len(marks) if marks else 0
                print(f"  {sub.name}: {avg:.2f} (from {len(marks)} results)")
        # Attendance summary
        print("\nAverage attendance % per student:")
        student_att: Dict[str, List[str]] = {}
        for a in self.attendances:
            student_att.setdefault(a.student_id, []).append(a.status)
        for u in [u for u in self.users if u.role == 'student']:
            statuses = student_att.get(u.user_id, [])
            present = sum(1 for s in statuses if s == 'present')
            total = len(statuses)
            percent = (present/total)*100 if total else 0
            print(f"  {u.name}: {percent:.1f}% present ({present}/{total})")

    def staff_summary(self, staff_id: str):
        staff_subjects = [s for s in self.subjects if s.subject_id in [u.assigned_subjects for u in self.users if u.user_id == staff_id][0] if isinstance(self._find_user(staff_id, 'staff'), Staff)]
        assigned = self._find_user(staff_id, 'staff')
        if not assigned or not isinstance(assigned, Staff):
            print("Staff not found.")
            return
        print("\n--- Summary Charts (Staff) ---")
        print(f"Subjects assigned: {len(assigned.assigned_subjects)}")
        for sub_id in assigned.assigned_subjects:
            sub = self._find_subject(sub_id)
            if sub:
                print(f"  {sub.name}")
        # Leaves of this staff
        leaves = [l for l in self.leave_applications if l.applicant_id == staff_id]
        print(f"Leave applications: {len(leaves)} ({len([l for l in leaves if l.status=='approved'])} approved)")
        # Students in assigned subjects (via results, attendance)
        # could show avg results
        print("\nStudents results in your subjects:")
        for sub_id in assigned.assigned_subjects:
            sub_results = [r for r in self.results if r.subject_id == sub_id]
            if sub_results:
                avg = sum(r.marks for r in sub_results)/len(sub_results)
                print(f"  {self._find_subject(sub_id).name}: average {avg:.2f}")
            else:
                print(f"  {self._find_subject(sub_id).name}: no results yet")

    def student_summary(self, student_id: str):
        student = self._find_user(student_id, 'student')
        if not student:
            print("Student not found.")
            return
        print("\n--- Summary Charts (Student) ---")
        # Attendance
        atts = self.get_student_attendance(student_id)
        present = sum(1 for a in atts if a.status == 'present')
        total = len(atts)
        percent = (present/total)*100 if total else 0
        print(f"Attendance: {present}/{total} ({percent:.1f}% present)")
        # Results
        results = self.get_student_results(student_id)
        if results:
            avg = sum(r.marks for r in results)/len(results)
            print(f"Average marks across subjects: {avg:.2f}")
        # Leaves
        leaves = [l for l in self.leave_applications if l.applicant_id == student_id]
        print(f"Leave applications: {len(leaves)} ({len([l for l in leaves if l.status=='approved'])} approved)")

    # Helper find methods
    def _find_user(self, user_id: str, role: str = None) -> Optional[User]:
        for u in self.users:
            if u.user_id == user_id:
                if role is None or u.role == role:
                    return u
        return None

    def _find_course(self, course_id: str) -> Optional[Course]:
        for c in self.courses:
            if c.course_id == course_id:
                return c
        return None

    def _find_subject(self, subject_id: str) -> Optional[Subject]:
        for s in self.subjects:
            if s.subject_id == subject_id:
                return s
        return None

    def _find_session(self, session_id: str) -> Optional[Session]:
        for s in self.sessions:
            if s.session_id == session_id:
                return s
        return None

    def _find_student(self, student_id: str) -> Optional[Student]:
        u = self._find_user(student_id, 'student')
        return u if isinstance(u, Student) else None

    def _find_staff(self, staff_id: str) -> Optional[Staff]:
        u = self._find_user(staff_id, 'staff')
        return u if isinstance(u, Staff) else None

    def _find_leave(self, leave_id: str) -> Optional[LeaveApplication]:
        for l in self.leave_applications:
            if l.leave_id == leave_id:
                return l
        return None

    def _find_feedback(self, feedback_id: str) -> Optional[Feedback]:
        for f in self.feedbacks:
            if f.feedback_id == feedback_id:
                return f
        return None


def main():
    sms = StudentManagementSystem()
    # Add sample data
    admin = Admin("ADMIN001", "Administrator", "admin@school.com", "admin123")
    sms.users.append(admin)
    # sample courses, subjects, sessions
    course = sms.add_course("Computer Science", "CS program")
    math_course = sms.add_course("Mathematics", "Math program")
    sub1 = sms.add_subject("Python Programming", course.course_id)
    sub2 = sms.add_subject("Data Structures", course.course_id)
    sub3 = sms.add_subject("Calculus", math_course.course_id)
    session = sms.add_session("2023-2024", datetime.date(2023, 9, 1), datetime.date(2024, 6, 30))
    # staff
    staff1 = sms.add_staff("Dr. Smith", "smith@school.com", "staff123")
    staff1.assigned_subjects.extend([sub1.subject_id, sub2.subject_id])
    staff2 = sms.add_staff("Prof. Johnson", "johnson@school.com", "staff456")
    staff2.assigned_subjects.append(sub3.subject_id)
    # students
    stu1 = sms.add_student("Alice", "alice@school.com", "stu123")
    stu1.enrolled_courses.append(course.course_id)
    stu2 = sms.add_student("Bob", "bob@school.com", "stu456")
    stu2.enrolled_courses.extend([course.course_id, math_course.course_id])
    # attendance
    sms.add_attendance(session.session_id, sub1.subject_id, stu1.user_id, datetime.date(2023, 9, 10), "present")
    sms.add_attendance(session.session_id, sub1.subject_id, stu1.user_id, datetime.date(2023, 9, 11), "absent")
    sms.add_attendance(session.session_id, sub2.subject_id, stu1.user_id, datetime.date(2023, 9, 12), "present")
    sms.add_attendance(session.session_id, sub1.subject_id, stu2.user_id, datetime.date(2023, 9, 10), "present")
    # results
    sms.add_result(stu1.user_id, sub1.subject_id, session.session_id, 85.5)
    sms.add_result(stu1.user_id, sub2.subject_id, session.session_id, 78.0)
    sms.add_result(stu2.user_id, sub1.subject_id, session.session_id, 91.2)
    # leaves
    sms.apply_leave(stu1.user_id, "student", datetime.date(2023, 10, 1), datetime.date(2023, 10, 3), "Medical")
    sms.apply_leave(staff1.user_id, "staff", datetime.date(2023, 10, 5), datetime.date(2023, 10, 6), "Personal")
    # feedback
    sms.send_feedback(stu2.user_id, "student", "Please extend lab hours.")
    sms.send_feedback(staff2.user_id, "staff", "Need new projector.")

    print("=== Student Management System ===")
    while True:
        print("\n1. Login")
        print("2. Exit")
        choice = input("Choose: ").strip()
        if choice == '2':
            break
        elif choice == '1':
            uid = input("User ID: ").strip()
            pwd = input("Password: ").strip()
            user = sms.authenticate(uid, pwd)
            if not user:
                print("Invalid credentials.")
                continue
            if user.role == 'admin':
                admin_menu(sms, user)
            elif user.role == 'staff':
                staff_menu(sms, user)
            else:
                student_menu(sms, user)
        else:
            print("Invalid option.")

def admin_menu(sms: StudentManagementSystem, admin: Admin):
    while True:
        print("\n--- Admin Menu ---")
        print("1. View Summary Charts")
        print("2. Manage Staff")
        print("3. Manage Students")
        print("4. Manage Courses")
        print("5. Manage Subjects")
        print("6. Manage Sessions")
        print("7. View Student Attendance")
        print("8. Review Feedback")
        print("9. Review Leave")
        print("0. Logout")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            sms.admin_summary()
        elif opt == '2':
            manage_staff_menu(sms)
        elif opt == '3':
            manage_students_menu(sms)
        elif opt == '4':
            manage_courses_menu(sms)
        elif opt == '5':
            manage_subjects_menu(sms)
        elif opt == '6':
            manage_sessions_menu(sms)
        elif opt == '7':
            view_student_attendance_menu(sms)
        elif opt == '8':
            review_feedback_menu(sms)
        elif opt == '9':
            review_leave_menu(sms)
        else:
            print("Invalid option.")

def manage_staff_menu(sms: StudentManagementSystem):
    while True:
        print("\n--- Manage Staff ---")
        print("1. Add Staff")
        print("2. Update Staff")
        print("3. Delete Staff")
        print("4. List Staff")
        print("0. Back")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            name = input("Name: ")
            email = input("Email: ")
            pwd = input("Password: ")
            staff = sms.add_staff(name, email, pwd)
            print(f"Staff added with ID {staff.user_id}")
        elif opt == '2':
            uid = input("Staff ID: ")
            name = input("New name (leave blank): ")
            email = input("New email (leave blank): ")
            pwd = input("New password (leave blank): ")
            if sms.update_staff(uid, name or None, email or None, pwd or None):
                print("Updated.")
            else:
                print("Staff not found.")
        elif opt == '3':
            uid = input("Staff ID to delete: ")
            if sms.delete_staff(uid):
                print("Deleted.")
            else:
                print("Not found.")
        elif opt == '4':
            staff_list = [u for u in sms.users if u.role == 'staff']
            for s in staff_list:
                print(f"ID: {s.user_id}, Name: {s.name}, Email: {s.email}")
        else:
            print("Invalid.")

def manage_students_menu(sms: StudentManagementSystem):
    while True:
        print("\n--- Manage Students ---")
        print("1. Add Student")
        print("2. Update Student")
        print("3. Delete Student")
        print("4. List Students")
        print("0. Back")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            name = input("Name: ")
            email = input("Email: ")
            pwd = input("Password: ")
            student = sms.add_student(name, email, pwd)
            print(f"Student added with ID {student.user_id}")
        elif opt == '2':
            uid = input("Student ID: ")
            name = input("New name (leave blank): ")
            email = input("New email (leave blank): ")
            pwd = input("New password (leave blank): ")
            if sms.update_student(uid, name or None, email or None, pwd or None):
                print("Updated.")
            else:
                print("Student not found.")
        elif opt == '3':
            uid = input("Student ID to delete: ")
            if sms.delete_student(uid):
                print("Deleted.")
            else:
                print("Not found.")
        elif opt == '4':
            stud_list = [u for u in sms.users if u.role == 'student']
            for s in stud_list:
                print(f"ID: {s.user_id}, Name: {s.name}, Email: {s.email}")
        else:
            print("Invalid.")

def manage_courses_menu(sms: StudentManagementSystem):
    while True:
        print("\n--- Manage Courses ---")
        print("1. Add Course")
        print("2. Update Course")
        print("3. Delete Course")
        print("4. List Courses")
        print("0. Back")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            name = input("Course name: ")
            desc = input("Description: ")
            course = sms.add_course(name, desc)
            print(f"Course added with ID {course.course_id}")
        elif opt == '2':
            cid = input("Course ID: ")
            name = input("New name (blank): ")
            desc = input("New description (blank): ")
            if sms.update_course(cid, name or None, desc or None):
                print("Updated.")
            else:
                print("Course not found.")
        elif opt == '3':
            cid = input("Course ID to delete: ")
            if sms.delete_course(cid):
                print("Deleted.")
            else:
                print("Not found.")
        elif opt == '4':
            for c in sms.courses:
                print(f"ID: {c.course_id}, Name: {c.name}, Desc: {c.description}")
        else:
            print("Invalid.")

def manage_subjects_menu(sms: StudentManagementSystem):
    while True:
        print("\n--- Manage Subjects ---")
        print("1. Add Subject")
        print("2. Update Subject")
        print("3. Delete Subject")
        print("4. List Subjects")
        print("0. Back")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            name = input("Subject name: ")
            cid = input("Course ID: ")
            sub = sms.add_subject(name, cid)
            if sub:
                print(f"Subject added with ID {sub.subject_id}")
            else:
                print("Invalid course ID.")
        elif opt == '2':
            sid = input("Subject ID: ")
            name = input("New name (blank): ")
            cid = input("New course ID (blank): ")
            if sms.update_subject(sid, name or None, cid or None):
                print("Updated.")
            else:
                print("Subject not found.")
        elif opt == '3':
            sid = input("Subject ID to delete: ")
            if sms.delete_subject(sid):
                print("Deleted.")
            else:
                print("Not found.")
        elif opt == '4':
            for s in sms.subjects:
                print(f"ID: {s.subject_id}, Name: {s.name}, Course: {s.course_id}")
        else:
            print("Invalid.")

def manage_sessions_menu(sms: StudentManagementSystem):
    while True:
        print("\n--- Manage Sessions ---")
        print("1. Add Session")
        print("2. Update Session")
        print("3. Delete Session")
        print("4. List Sessions")
        print("0. Back")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            name = input("Session name: ")
            start = input("Start date (YYYY-MM-DD): ")
            end = input("End date (YYYY-MM-DD): ")
            try:
                sd = datetime.datetime.strptime(start, "%Y-%m-%d").date()
                ed = datetime.datetime.strptime(end, "%Y-%m-%d").date()
                sess = sms.add_session(name, sd, ed)
                print(f"Session added with ID {sess.session_id}")
            except:
                print("Invalid date format.")
        elif opt == '2':
            sid = input("Session ID: ")
            name = input("New name (blank): ")
            start = input("New start (YYYY-MM-DD) (blank): ")
            end = input("New end (YYYY-MM-DD) (blank): ")
            sd = None
            ed = None
            if start:
                try: sd = datetime.datetime.strptime(start, "%Y-%m-%d").date()
                except: print("Invalid date"); continue
            if end:
                try: ed = datetime.datetime.strptime(end, "%Y-%m-%d").date()
                except: print("Invalid date"); continue
            if sms.update_session(sid, name or None, sd, ed):
                print("Updated.")
            else:
                print("Session not found.")
        elif opt == '3':
            sid = input("Session ID: ")
            if sms.delete_session(sid):
                print("Deleted.")
            else:
                print("Not found.")
        elif opt == '4':
            for s in sms.sessions:
                print(f"ID: {s.session_id}, Name: {s.name}, {s.start_date} to {s.end_date}")
        else:
            print("Invalid.")

def view_student_attendance_menu(sms: StudentManagementSystem):
    sid = input("Enter student ID: ")
    session_id = input("Session ID (leave blank for all): ").strip() or None
    atts = sms.get_student_attendance(sid, session_id)
    if not atts:
        print("No attendance records.")
        return
    for a in atts:
        print(f"Date: {a.date}, Subject: {a.subject_id}, Status: {a.status}, Session: {a.session_id}")

def review_feedback_menu(sms: StudentManagementSystem):
    fbs = sms.feedbacks
    if not fbs:
        print("No feedbacks.")
        return
    for i, fb in enumerate(fbs):
        print(f"{i+1}. [{fb.feedback_id}] From: {fb.sender_id} ({fb.sender_role}) - {fb.message} | Reply: {fb.reply or 'none'}")
    try:
        idx = int(input("Enter number to reply (0 to back): ")) - 1
        if idx < 0:
            return
        fb = fbs[idx]
        reply = input("Reply: ")
        sms.reply_feedback(fb.feedback_id, reply)
        print("Reply sent.")
    except:
        print("Invalid selection.")

def review_leave_menu(sms: StudentManagementSystem):
    leaves = sms.leave_applications
    if not leaves:
        print("No leave applications.")
        return
    for i, l in enumerate(leaves):
        print(f"{i+1}. [{l.leave_id}] {l.applicant_id} ({l.applicant_role}) {l.start_date} to {l.end_date} Reason: {l.reason} Status: {l.status}")
    try:
        idx = int(input("Enter number to review (0 to back): ")) - 1
        if idx < 0:
            return
        leave = leaves[idx]
        action = input("Action (approve/reject): ").strip().lower()
        if action in ['approve', 'reject']:
            sms.review_leave(leave.leave_id, action)
            print(f"Leave {action}d.")
        else:
            print("Invalid action.")
    except:
        print("Invalid selection.")

def staff_menu(sms: StudentManagementSystem, staff: Staff):
    while True:
        print("\n--- Staff Menu ---")
        print("1. View Summary Charts")
        print("2. Take/Update Student Attendance")
        print("3. Add/Update Result")
        print("4. Apply for Leave")
        print("5. Send Feedback")
        print("0. Logout")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            sms.staff_summary(staff.user_id)
        elif opt == '2':
            take_update_attendance(sms, staff)
        elif opt == '3':
            add_update_result(sms, staff)
        elif opt == '4':
            apply_leave_menu(sms, staff.user_id, 'staff')
        elif opt == '5':
            send_feedback_menu(sms, staff.user_id, 'staff')
        else:
            print("Invalid option.")

def take_update_attendance(sms: StudentManagementSystem, staff: Staff):
    print("\n--- Take/Update Attendance ---")
    print("Assigned subjects:")
    for sub_id in staff.assigned_subjects:
        sub = sms._find_subject(sub_id)
        if sub:
            print(sub.subject_id, sub.name)
    sub_id = input("Subject ID: ")
    if sub_id not in staff.assigned_subjects:
        print("Not your subject.")
        return
    session_id = input("Session ID: ")
    student_id = input("Student ID: ")
    date_str = input("Date (YYYY-MM-DD): ")
    try:
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        print("Invalid date.")
        return
    status = input("Status (present/absent/late): ").strip().lower()
    if status not in ('present', 'absent', 'late'):
        print("Invalid status.")
        return
    # Check if attendance exists for same student, subject, date, session; update or add
    existing = [a for a in sms.attendances if a.student_id == student_id and a.subject_id == sub_id and
                a.session_id == session_id and a.date == date]
    if existing:
        existing[0].status = status
        print("Updated.")
    else:
        att = sms.add_attendance(session_id, sub_id, student_id, date, status)
        if att:
            print("Attendance recorded.")
        else:
            print("Failed (check IDs).")

def add_update_result(sms: StudentManagementSystem, staff: Staff):
    print("\n--- Add/Update Result ---")
    for sub_id in staff.assigned_subjects:
        sub = sms._find_subject(sub_id)
        if sub:
            print(sub.subject_id, sub.name)
    sub_id = input("Subject ID: ")
    if sub_id not in staff.assigned_subjects:
        print("Not your subject.")
        return
    student_id = input("Student ID: ")
    session_id = input("Session ID: ")
    marks = float(input("Marks: "))
    # Check if result exists; update or add
    existing = [r for r in sms.results if r.student_id == student_id and r.subject_id == sub_id and r.session_id == session_id]
    if existing:
        existing[0].marks = marks
        print("Result updated.")
    else:
        res = sms.add_result(student_id, sub_id, session_id, marks)
        if res:
            print("Result added.")
        else:
            print("Failed (check IDs).")

def apply_leave_menu(sms, user_id, role):
    start_str = input("Start date (YYYY-MM-DD): ")
    end_str = input("End date (YYYY-MM-DD): ")
    reason = input("Reason: ")
    try:
        sd = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        ed = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
    except:
        print("Invalid date.")
        return
    leave = sms.apply_leave(user_id, role, sd, ed, reason)
    print(f"Leave applied, ID {leave.leave_id}")

def send_feedback_menu(sms, user_id, role):
    msg = input("Message: ")
    fb = sms.send_feedback(user_id, role, msg)
    print(f"Feedback sent, ID {fb.feedback_id}")

def student_menu(sms: StudentManagementSystem, student: Student):
    while True:
        print("\n--- Student Menu ---")
        print("1. View Summary Charts")
        print("2. View Attendance")
        print("3. View Result")
        print("4. Apply for Leave")
        print("5. Send Feedback")
        print("0. Logout")
        opt = input("Choose: ").strip()
        if opt == '0':
            break
        elif opt == '1':
            sms.student_summary(student.user_id)
        elif opt == '2':
            view_student_attendance_menu(sms)
        elif opt == '3':
            view_student_result(sms, student.user_id)
        elif opt == '4':
            apply_leave_menu(sms, student.user_id, 'student')
        elif opt == '5':
            send_feedback_menu(sms, student.user_id, 'student')
        else:
            print("Invalid option.")

def view_student_result(sms, student_id):
    session_id = input("Session ID (leave blank for all): ").strip() or None
    results = sms.get_student_results(student_id, session_id)
    if not results:
        print("No results.")
        return
    for r in results:
        sub = sms._find_subject(r.subject_id)
        print(f"Subject: {sub.name if sub else r.subject_id}, Session: {r.session_id}, Marks: {r.marks}")

if __name__ == "__main__":
    main()