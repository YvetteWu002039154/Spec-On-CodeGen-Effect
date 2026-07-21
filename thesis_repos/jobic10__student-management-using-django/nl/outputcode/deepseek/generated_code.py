from typing import List, Dict, Optional, Union, Any
import enum
import datetime


# ---------- Enums ----------
class Role(enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"


class LeaveStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------- Data Classes / Simple Structures ----------
class Person:
    def __init__(self, uid: str, name: str, email: str, password: str, role: Role):
        self.uid = uid
        self.name = name
        self.email = email
        self.password = password
        self.role = role

    def check_password(self, password: str) -> bool:
        return self.password == password


class Course:
    def __init__(self, course_id: str, name: str, description: str = ""):
        self.course_id = course_id
        self.name = name
        self.description = description


class Subject:
    def __init__(self, subject_id: str, name: str, course_id: str, description: str = ""):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.description = description


class Session:
    def __init__(self, session_id: str, course_id: str, subject_id: str, date: str, topic: str = ""):
        self.session_id = session_id
        self.course_id = course_id
        self.subject_id = subject_id
        self.date = date
        self.topic = topic


class AttendanceRecord:
    def __init__(self, record_id: str, session_id: str, student_id: str, status: bool = False):
        self.record_id = record_id
        self.session_id = session_id
        self.student_id = student_id
        self.status = status  # True = present, False = absent


class Result:
    def __init__(self, result_id: str, student_id: str, subject_id: str, marks: float, max_marks: float = 100.0):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks
        self.max_marks = max_marks


class LeaveRequest:
    def __init__(self, leave_id: str, applicant_id: str, reason: str, from_date: str, to_date: str,
                 status: LeaveStatus = LeaveStatus.PENDING, reply: str = ""):
        self.leave_id = leave_id
        self.applicant_id = applicant_id
        self.reason = reason
        self.from_date = from_date
        self.to_date = to_date
        self.status = status
        self.reply = reply


class Feedback:
    def __init__(self, feedback_id: str, sender_id: str, message: str, reply: str = ""):
        self.feedback_id = feedback_id
        self.sender_id = sender_id
        self.message = message
        self.reply = reply


# ---------- Global Storage (in-memory) ----------
users: Dict[str, Person] = {}  # uid -> Person
staff_list: List[str] = []  # uids with role STAFF
student_list: List[str] = []  # uids with role STUDENT
courses: Dict[str, Course] = {}
subjects: Dict[str, Subject] = {}
sessions: Dict[str, Session] = {}
attendance_records: List[AttendanceRecord] = []
results: List[Result] = []
leave_requests: List[LeaveRequest] = []
feedbacks: List[Feedback] = []


# ---------- Utility ----------
def generate_id(prefix: str) -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


# ---------- Admin Class ----------
class Admin(Person):
    def __init__(self, uid: str, name: str, email: str, password: str):
        super().__init__(uid, name, email, password, Role.ADMIN)

    # Staff management
    def add_staff(self, name: str, email: str, password: str) -> None:
        sid = generate_id("STF")
        user = Person(sid, name, email, password, Role.STAFF)
        users[sid] = user
        staff_list.append(sid)
        print(f"Staff added with ID: {sid}")

    def update_staff(self, staff_id: str, name: str = None, email: str = None, password: str = None) -> bool:
        if staff_id not in users or users[staff_id].role != Role.STAFF:
            print("Staff not found.")
            return False
        staff = users[staff_id]
        if name:
            staff.name = name
        if email:
            staff.email = email
        if password:
            staff.password = password
        print("Staff updated.")
        return True

    def delete_staff(self, staff_id: str) -> bool:
        if staff_id not in users or users[staff_id].role != Role.STAFF:
            print("Staff not found.")
            return False
        del users[staff_id]
        staff_list.remove(staff_id)
        print("Staff deleted.")
        return True

    # Student management
    def add_student(self, name: str, email: str, password: str) -> None:
        sid = generate_id("STU")
        user = Person(sid, name, email, password, Role.STUDENT)
        users[sid] = user
        student_list.append(sid)
        print(f"Student added with ID: {sid}")

    def update_student(self, student_id: str, name: str = None, email: str = None, password: str = None) -> bool:
        if student_id not in users or users[student_id].role != Role.STUDENT:
            print("Student not found.")
            return False
        student = users[student_id]
        if name:
            student.name = name
        if email:
            student.email = email
        if password:
            student.password = password
        print("Student updated.")
        return True

    def delete_student(self, student_id: str) -> bool:
        if student_id not in users or users[student_id].role != Role.STUDENT:
            print("Student not found.")
            return False
        del users[student_id]
        student_list.remove(student_id)
        print("Student deleted.")
        return True

    # Course management
    def add_course(self, name: str, description: str = "") -> None:
        cid = generate_id("CRS")
        course = Course(cid, name, description)
        courses[cid] = course
        print(f"Course added with ID: {cid}")

    def update_course(self, course_id: str, name: str = None, description: str = None) -> bool:
        if course_id not in courses:
            print("Course not found.")
            return False
        course = courses[course_id]
        if name:
            course.name = name
        if description is not None:
            course.description = description
        print("Course updated.")
        return True

    def delete_course(self, course_id: str) -> bool:
        if course_id not in courses:
            print("Course not found.")
            return False
        del courses[course_id]
        # delete related subjects, sessions?
        # keep simple: just remove references
        print("Course deleted.")
        return True

    # Subject management
    def add_subject(self, name: str, course_id: str, description: str = "") -> None:
        if course_id not in courses:
            print("Course not found.")
            return
        sid = generate_id("SUB")
        subject = Subject(sid, name, course_id, description)
        subjects[sid] = subject
        print(f"Subject added with ID: {sid}")

    def update_subject(self, subject_id: str, name: str = None, course_id: str = None, description: str = None) -> bool:
        if subject_id not in subjects:
            print("Subject not found.")
            return False
        subject = subjects[subject_id]
        if name:
            subject.name = name
        if course_id:
            if course_id not in courses:
                print("New course not found.")
                return False
            subject.course_id = course_id
        if description is not None:
            subject.description = description
        print("Subject updated.")
        return True

    def delete_subject(self, subject_id: str) -> bool:
        if subject_id not in subjects:
            print("Subject not found.")
            return False
        del subjects[subject_id]
        print("Subject deleted.")
        return True

    # Session management
    def add_session(self, course_id: str, subject_id: str, date: str, topic: str = "") -> None:
        if course_id not in courses or subject_id not in subjects:
            print("Invalid course or subject.")
            return
        sid = generate_id("SES")
        session = Session(sid, course_id, subject_id, date, topic)
        sessions[sid] = session
        print(f"Session added with ID: {sid}")

    def update_session(self, session_id: str, course_id: str = None, subject_id: str = None,
                       date: str = None, topic: str = None) -> bool:
        if session_id not in sessions:
            print("Session not found.")
            return False
        sess = sessions[session_id]
        if course_id:
            if course_id not in courses:
                print("Course not found.")
                return False
            sess.course_id = course_id
        if subject_id:
            if subject_id not in subjects:
                print("Subject not found.")
                return False
            sess.subject_id = subject_id
        if date:
            sess.date = date
        if topic is not None:
            sess.topic = topic
        print("Session updated.")
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id not in sessions:
            print("Session not found.")
            return False
        del sessions[session_id]
        print("Session deleted.")
        return True

    # View student attendance (for any student)
    def view_student_attendance(self, student_id: str) -> None:
        if student_id not in users or users[student_id].role != Role.STUDENT:
            print("Student not found.")
            return
        print(f"Attendance records for {users[student_id].name}:")
        for rec in attendance_records:
            if rec.student_id == student_id:
                session = sessions.get(rec.session_id)
                if session:
                    print(f"  Session: {session.date} - {session.topic} -> {'Present' if rec.status else 'Absent'}")
        if not any(rec.student_id == student_id for rec in attendance_records):
            print("No records.")

    # Review feedback
    def view_feedbacks(self) -> None:
        if not feedbacks:
            print("No feedbacks.")
            return
        for fb in feedbacks:
            sender = users.get(fb.sender_id)
            sender_name = sender.name if sender else "Unknown"
            print(f"Feedback {fb.feedback_id} from {sender_name}: {fb.message}")
            if fb.reply:
                print(f"  Reply: {fb.reply}")

    def reply_feedback(self, feedback_id: str, reply: str) -> bool:
        for fb in feedbacks:
            if fb.feedback_id == feedback_id:
                fb.reply = reply
                print("Reply sent.")
                return True
        print("Feedback not found.")
        return False

    # Review leave
    def view_leave_requests(self) -> None:
        if not leave_requests:
            print("No leave requests.")
            return
        for lr in leave_requests:
            applicant = users.get(lr.applicant_id)
            app_name = applicant.name if applicant else "Unknown"
            print(f"Leave {lr.leave_id} by {app_name}: {lr.from_date} to {lr.to_date} - {lr.reason} [{lr.status.value}]")
            if lr.reply:
                print(f"  Reply: {lr.reply}")

    def approve_leave(self, leave_id: str) -> bool:
        for lr in leave_requests:
            if lr.leave_id == leave_id:
                lr.status = LeaveStatus.APPROVED
                lr.reply = "Approved"
                print("Leave approved.")
                return True
        print("Leave request not found.")
        return False

    def reject_leave(self, leave_id: str, reason: str = "") -> bool:
        for lr in leave_requests:
            if lr.leave_id == leave_id:
                lr.status = LeaveStatus.REJECTED
                lr.reply = reason or "Rejected"
                print("Leave rejected.")
                return True
        print("Leave request not found.")
        return False

    # Summary charts
    def show_summary(self) -> None:
        print("\n=== Overall Summary ===")
        print(f"Total Staff: {len(staff_list)}")
        print(f"Total Students: {len(student_list)}")
        print(f"Total Courses: {len(courses)}")
        print(f"Total Subjects: {len(subjects)}")
        print(f"Total Sessions: {len(sessions)}")
        total_leaves = len(leave_requests)
        pending_leaves = sum(1 for lr in leave_requests if lr.status == LeaveStatus.PENDING)
        approved_leaves = sum(1 for lr in leave_requests if lr.status == LeaveStatus.APPROVED)
        print(f"Leave: {total_leaves} total, {pending_leaves} pending, {approved_leaves} approved")
        if results:
            avg_mark = sum(r.marks for r in results) / len(results)
            print(f"Average result across all students: {avg_mark:.2f}")
        else:
            print("No result data.")


# ---------- Staff Class ----------
class Staff(Person):
    def __init__(self, uid: str, name: str, email: str, password: str):
        super().__init__(uid, name, email, password, Role.STAFF)

    # Attendance
    def take_attendance(self, session_id: str, student_id: str, status: bool) -> None:
        # Check if student exists
        if student_id not in users or users[student_id].role != Role.STUDENT:
            print("Invalid student ID.")
            return
        if session_id not in sessions:
            print("Session not found.")
            return
        # Check if record already exists; update or create new
        for rec in attendance_records:
            if rec.session_id == session_id and rec.student_id == student_id:
                rec.status = status
                print("Attendance updated.")
                return
        rec_id = generate_id("ATT")
        record = AttendanceRecord(rec_id, session_id, student_id, status)
        attendance_records.append(record)
        print("Attendance recorded.")

    def update_attendance(self, session_id: str, student_id: str, status: bool) -> None:
        self.take_attendance(session_id, student_id, status)  # same logic

    # Results
    def add_result(self, student_id: str, subject_id: str, marks: float, max_marks: float = 100.0) -> None:
        if student_id not in users or users[student_id].role != Role.STUDENT:
            print("Invalid student ID.")
            return
        if subject_id not in subjects:
            print("Subject not found.")
            return
        # check if result exists
        for r in results:
            if r.student_id == student_id and r.subject_id == subject_id:
                r.marks = marks
                r.max_marks = max_marks
                print("Result updated.")
                return
        rid = generate_id("RES")
        result = Result(rid, student_id, subject_id, marks, max_marks)
        results.append(result)
        print("Result added.")

    def update_result(self, student_id: str, subject_id: str, marks: float, max_marks: float = 100.0) -> None:
        self.add_result(student_id, subject_id, marks, max_marks)  # same logic

    # Leave
    def apply_leave(self, reason: str, from_date: str, to_date: str) -> None:
        lid = generate_id("LEA")
        leave = LeaveRequest(lid, self.uid, reason, from_date, to_date)
        leave_requests.append(leave)
        print(f"Leave request submitted, ID: {lid}")

    # Feedback
    def send_feedback(self, message: str) -> None:
        fid = generate_id("FDB")
        fb = Feedback(fid, self.uid, message)
        feedbacks.append(fb)
        print(f"Feedback sent, ID: {fid}")

    # Summary charts for staff
    def show_my_summary(self) -> None:
        print(f"\n=== Summary for Staff: {self.name} ===")
        # Count my students (could be those I teach via subjects they are enrolled? We'll just show total students)
        print(f"Total Students in system: {len(student_list)}")
        # Count my subjects (for simplicity, all subjects, but ideally assigned staff-subject mapping not implemented)
        print(f"Total Subjects: {len(subjects)}")
        my_leaves = [lr for lr in leave_requests if lr.applicant_id == self.uid]
        print(f"My Leave Requests: {len(my_leaves)}")
        for lr in my_leaves:
            print(f"  {lr.leave_id}: {lr.from_date} to {lr.to_date} - {lr.status.value}")
        my_feedbacks = [fb for fb in feedbacks if fb.sender_id == self.uid]
        print(f"My Feedbacks: {len(my_feedbacks)}")
        # Attendances recorded by me: we don't track who recorded, so omit.
        print("---")


# ---------- Student Class ----------
class Student(Person):
    def __init__(self, uid: str, name: str, email: str, password: str):
        super().__init__(uid, name, email, password, Role.STUDENT)

    def view_attendance(self) -> None:
        print(f"\nAttendance for {self.name}:")
        my_records = [rec for rec in attendance_records if rec.student_id == self.uid]
        if not my_records:
            print("No attendance records.")
            return
        for rec in my_records:
            session = sessions.get(rec.session_id)
            if session:
                print(f"  Session: {session.date} - {session.topic} -> {'Present' if rec.status else 'Absent'}")

    def view_result(self) -> None:
        print(f"\nResults for {self.name}:")
        my_results = [r for r in results if r.student_id == self.uid]
        if not my_results:
            print("No results.")
            return
        for r in my_results:
            subject = subjects.get(r.subject_id)
            subj_name = subject.name if subject else r.subject_id
            print(f"  {subj_name}: {r.marks}/{r.max_marks}")

    def apply_leave(self, reason: str, from_date: str, to_date: str) -> None:
        lid = generate_id("LEA")
        leave = LeaveRequest(lid, self.uid, reason, from_date, to_date)
        leave_requests.append(leave)
        print(f"Leave request submitted, ID: {lid}")

    def send_feedback(self, message: str) -> None:
        fid = generate_id("FDB")
        fb = Feedback(fid, self.uid, message)
        feedbacks.append(fb)
        print(f"Feedback sent, ID: {fid}")

    def show_my_summary(self) -> None:
        print(f"\n=== Summary for Student: {self.name} ===")
        print(f"My Subjects: {len(subjects)} (all)")  # simplified
        my_attendance = [rec for rec in attendance_records if rec.student_id == self.uid]
        print(f"Attendance records: {len(my_attendance)}")
        present = sum(1 for rec in my_attendance if rec.status)
        if my_attendance:
            print(f"  Present: {present} out of {len(my_attendance)}")
        my_results_list = [r for r in results if r.student_id == self.uid]
        print(f"Results entries: {len(my_results_list)}")
        my_leaves = [lr for lr in leave_requests if lr.applicant_id == self.uid]
        print(f"My Leave Requests: {len(my_leaves)}")
        for lr in my_leaves:
            print(f"  {lr.leave_id}: {lr.from_date} to {lr.to_date} - {lr.status.value}")
        my_feedbacks = [fb for fb in feedbacks if fb.sender_id == self.uid]
        print(f"My Feedbacks: {len(my_feedbacks)}")
        print("---")


# ---------- Preload some data for demo ----------
def initialize_demo_data():
    # Create admin
    admin = Admin("ADM001", "Admin User", "admin@example.com", "admin123")
    users[admin.uid] = admin
    # Create staff
    s1 = Staff("STF001", "John Smith", "john@example.com", "staff123")
    users[s1.uid] = s1
    staff_list.append(s1.uid)
    s2 = Staff("STF002", "Sarah Connor", "sarah@example.com", "staff123")
    users[s2.uid] = s2
    staff_list.append(s2.uid)
    # Create students
    st1 = Student("STU001", "Alice Johnson", "alice@example.com", "student123")
    users[st1.uid] = st1
    student_list.append(st1.uid)
    st2 = Student("STU002", "Bob Williams", "bob@example.com", "student123")
    users[st2.uid] = st2
    student_list.append(st2.uid)
    # Course
    c1 = Course("CRS001", "Computer Science", "CS course")
    courses[c1.course_id] = c1
    # Subjects
    sub1 = Subject("SUB001", "Python Programming", "CRS001", "Learn Python")
    sub2 = Subject("SUB002", "Data Structures", "CRS001", "DSA")
    subjects[sub1.subject_id] = sub1
    subjects[sub2.subject_id] = sub2
    # Sessions
    sess1 = Session("SES001", "CRS001", "SUB001", "2025-04-01", "Introduction")
    sess2 = Session("SES002", "CRS001", "SUB001", "2025-04-03", "Variables")
    sessions[sess1.session_id] = sess1
    sessions[sess2.session_id] = sess2
    # Attendance
    att1 = AttendanceRecord("ATT001", "SES001", "STU001", True)
    att2 = AttendanceRecord("ATT002", "SES001", "STU002", False)
    att3 = AttendanceRecord("ATT003", "SES002", "STU001", True)
    attendance_records.extend([att1, att2, att3])
    # Results
    res1 = Result("RES001", "STU001", "SUB001", 85)
    res2 = Result("RES002", "STU002", "SUB001", 78)
    results.extend([res1, res2])
    # Leave
    lr1 = LeaveRequest("LEA001", "STU001", "Sick", "2025-04-10", "2025-04-12", LeaveStatus.PENDING)
    lr2 = LeaveRequest("LEA002", "STF001", "Family function", "2025-04-15", "2025-04-16", LeaveStatus.PENDING)
    leave_requests.extend([lr1, lr2])
    # Feedback
    fb1 = Feedback("FDB001", "STU001", "Need more practice sessions.")
    fb2 = Feedback("FDB002", "STF001", "Request lab equipment.")
    feedbacks.extend([fb1, fb2])


# ---------- Main Menu System ----------
def main():
    initialize_demo_data()
    print("===== Student Management System =====")
    while True:
        print("\nLogin")
        user_id = input("User ID: ").strip()
        password = input("Password: ").strip()
        user = users.get(user_id)
        if user and user.check_password(password):
            if user.role == Role.ADMIN:
                admin_menu(user)
            elif user.role == Role.STAFF:
                staff_menu(user)
            elif user.role == Role.STUDENT:
                student_menu(user)
        else:
            print("Invalid credentials. Try again.")


def admin_menu(admin: Admin):
    while True:
        print("\n--- Admin Menu ---")
        print("1. Manage Staff")
        print("2. Manage Students")
        print("3. Manage Courses")
        print("4. Manage Subjects")
        print("5. Manage Sessions")
        print("6. View Student Attendance")
        print("7. Review & Reply Feedback")
        print("8. Review Leave Requests")
        print("9. Overall Summary Charts")
        print("0. Logout")
        choice = input("Choice: ").strip()
        if choice == "1":
            admin_manage_staff(admin)
        elif choice == "2":
            admin_manage_students(admin)
        elif choice == "3":
            admin_manage_courses(admin)
        elif choice == "4":
            admin_manage_subjects(admin)
        elif choice == "5":
            admin_manage_sessions(admin)
        elif choice == "6":
            sid = input("Student ID: ").strip()
            admin.view_student_attendance(sid)
        elif choice == "7":
            review_feedback(admin)
        elif choice == "8":
            review_leave(admin)
        elif choice == "9":
            admin.show_summary()
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


def admin_manage_staff(admin: Admin):
    while True:
        print("\n--- Manage Staff ---")
        print("1. Add Staff")
        print("2. Update Staff")
        print("3. Delete Staff")
        print("4. List Staff")
        print("0. Back")
        c = input("Choice: ").strip()
        if c == "1":
            n = input("Name: ").strip()
            e = input("Email: ").strip()
            p = input("Password: ").strip()
            admin.add_staff(n, e, p)
        elif c == "2":
            sid = input("Staff ID: ").strip()
            n = input("New Name (leave blank): ").strip() or None
            e = input("New Email (leave blank): ").strip() or None
            p = input("New Password (leave blank): ").strip() or None
            admin.update_staff(sid, n, e, p)
        elif c == "3":
            sid = input("Staff ID: ").strip()
            admin.delete_staff(sid)
        elif c == "4":
            print("Staff List:")
            for sid in staff_list:
                s = users[sid]
                print(f"  {s.uid}: {s.name} ({s.email})")
        elif c == "0":
            break


def admin_manage_students(admin: Admin):
    while True:
        print("\n--- Manage Students ---")
        print("1. Add Student")
        print("2. Update Student")
        print("3. Delete Student")
        print("4. List Students")
        print("0. Back")
        c = input("Choice: ").strip()
        if c == "1":
            n = input("Name: ").strip()
            e = input("Email: ").strip()
            p = input("Password: ").strip()
            admin.add_student(n, e, p)
        elif c == "2":
            sid = input("Student ID: ").strip()
            n = input("New Name (leave blank): ").strip() or None
            e = input("New Email (leave blank): ").strip() or None
            p = input("New Password (leave blank): ").strip() or None
            admin.update_student(sid, n, e, p)
        elif c == "3":
            sid = input("Student ID: ").strip()
            admin.delete_student(sid)
        elif c == "4":
            print("Student List:")
            for sid in student_list:
                s = users[sid]
                print(f"  {s.uid}: {s.name} ({s.email})")
        elif c == "0":
            break


def admin_manage_courses(admin: Admin):
    while True:
        print("\n--- Manage Courses ---")
        print("1. Add Course")
        print("2. Update Course")
        print("3. Delete Course")
        print("4. List Courses")
        print("0. Back")
        c = input("Choice: ").strip()
        if c == "1":
            n = input("Name: ").strip()
            d = input("Description: ").strip()
            admin.add_course(n, d)
        elif c == "2":
            cid = input("Course ID: ").strip()
            n = input("New Name (leave blank): ").strip() or None
            d = input("New Description (leave blank): ").strip()
            if d == "":
                d = None
            admin.update_course(cid, n, d)
        elif c == "3":
            cid = input("Course ID: ").strip()
            admin.delete_course(cid)
        elif c == "4":
            print("Course List:")
            for cid, c in courses.items():
                print(f"  {cid}: {c.name} - {c.description}")
        elif c == "0":
            break


def admin_manage_subjects(admin: Admin):
    while True:
        print("\n--- Manage Subjects ---")
        print("1. Add Subject")
        print("2. Update Subject")
        print("3. Delete Subject")
        print("4. List Subjects")
        print("0. Back")
        c = input("Choice: ").strip()
        if c == "1":
            n = input("Name: ").strip()
            cid = input("Course ID: ").strip()
            d = input("Description: ").strip()
            admin.add_subject(n, cid, d)
        elif c == "2":
            sid = input("Subject ID: ").strip()
            n = input("New Name (leave blank): ").strip() or None
            cid = input("New Course ID (leave blank): ").strip() or None
            d = input("New Description (leave blank): ").strip()
            if d == "":
                d = None
            admin.update_subject(sid, n, cid, d)
        elif c == "3":
            sid = input("Subject ID: ").strip()
            admin.delete_subject(sid)
        elif c == "4":
            print("Subject List:")
            for sid, s in subjects.items():
                print(f"  {sid}: {s.name} (Course: {s.course_id}) - {s.description}")
        elif c == "0":
            break


def admin_manage_sessions(admin: Admin):
    while True:
        print("\n--- Manage Sessions ---")
        print("1. Add Session")
        print("2. Update Session")
        print("3. Delete Session")
        print("4. List Sessions")
        print("0. Back")
        c = input("Choice: ").strip()
        if c == "1":
            cid = input("Course ID: ").strip()
            sid = input("Subject ID: ").strip()
            date = input("Date (YYYY-MM-DD): ").strip()
            topic = input("Topic: ").strip()
            admin.add_session(cid, sid, date, topic)
        elif c == "2":
            sessid = input("Session ID: ").strip()
            cid = input("New Course ID (leave blank): ").strip() or None
            sid = input("New Subject ID (leave blank): ").strip() or None
            date = input("New Date (leave blank): ").strip() or None
            topic = input("New Topic (leave blank): ").strip()
            if topic == "":
                topic = None
            admin.update_session(sessid, cid, sid, date, topic)
        elif c == "3":
            sessid = input("Session ID: ").strip()
            admin.delete_session(sessid)
        elif c == "4":
            print("Session List:")
            for sid, s in sessions.items():
                print(f"  {sid}: {s.date} - {s.topic} (Course: {s.course_id}, Subject: {s.subject_id})")
        elif c == "0":
            break


def review_feedback(admin: Admin):
    while True:
        admin.view_feedbacks()
        print("\n1. Reply to Feedback")
        print("0. Back")
        c = input("Choice: ").strip()
        if c == "1":
            fid = input("Feedback ID: ").strip()
            reply = input("Reply: ").strip()
            admin.reply_feedback(fid, reply)
        elif c == "0":
            break


def review_leave(admin: Admin):
    while True:
        admin.view_leave_requests()
        print("\n1. Approve Leave")
        print("2. Reject Leave")
        print("0. Back")
        c = input("Choice: ").strip()
        if c == "1":
            lid = input("Leave ID: ").strip()
            admin.approve_leave(lid)
        elif c == "2":
            lid = input("Leave ID: ").strip()
            reason = input("Rejection reason (optional): ").strip()
            admin.reject_leave(lid, reason)
        elif c == "0":
            break


def staff_menu(staff: Staff):
    while True:
        print("\n--- Staff Menu ---")
        print("1. Take/Update Attendance")
        print("2. Add/Update Result")
        print("3. Apply for Leave")
        print("4. Send Feedback to HOD")
        print("5. View My Summary Charts")
        print("0. Logout")
        choice = input("Choice: ").strip()
        if choice == "1":
            sess = input("Session ID: ").strip()
            stu = input("Student ID: ").strip()
            status = input("Status (present/absent): ").strip().lower()
            staff.take_attendance(sess, stu, status == "present")
        elif choice == "2":
            stu = input("Student ID: ").strip()
            sub = input("Subject ID: ").strip()
            marks = float(input("Marks: ").strip())
            max_marks = float(input("Max Marks (default 100): ").strip() or "100")
            staff.add_result(stu, sub, marks, max_marks)
        elif choice == "3":
            reason = input("Reason: ").strip()
            from_d = input("From date (YYYY-MM-DD): ").strip()
            to_d = input("To date (YYYY-MM-DD): ").strip()
            staff.apply_leave(reason, from_d, to_d)
        elif choice == "4":
            msg = input("Message: ").strip()
            staff.send_feedback(msg)
        elif choice == "5":
            staff.show_my_summary()
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


def student_menu(student: Student):
    while True:
        print("\n--- Student Menu ---")
        print("1. View Attendance")
        print("2. View Result")
        print("3. Apply for Leave")
        print("4. Send Feedback to HOD")
        print("5. View My Summary Charts")
        print("0. Logout")
        choice = input("Choice: ").strip()
        if choice == "1":
            student.view_attendance()
        elif choice == "2":
            student.view_result()
        elif choice == "3":
            reason = input("Reason: ").strip()
            from_d = input("From date (YYYY-MM-DD): ").strip()
            to_d = input("To date (YYYY-MM-DD): ").strip()
            student.apply_leave(reason, from_d, to_d)
        elif choice == "4":
            msg = input("Message: ").strip()
            student.send_feedback(msg)
        elif choice == "5":
            student.show_my_summary()
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()