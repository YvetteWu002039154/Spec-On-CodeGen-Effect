from typing import List, Dict, Optional, Union

class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

class Admin(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email)

class Staff(User):
    def __init__(self, user_id: int, name: str, email: str):
        super().__init__(user_id, name, email)

class Student(User):
    def __init__(self, user_id: int, name: str, email: str, course_id: int, session_id: int):
        super().__init__(user_id, name, email)
        self.course_id = course_id
        self.session_id = session_id

class Course:
    def __init__(self, course_id: int, name: str):
        self.course_id = course_id
        self.name = name

class Subject:
    def __init__(self, subject_id: int, name: str, course_id: int, staff_id: int):
        self.subject_id = subject_id
        self.name = name
        self.course_id = course_id
        self.staff_id = staff_id

class Session:
    def __init__(self, session_id: int, start_year: str, end_year: str):
        self.session_id = session_id
        self.start_year = start_year
        self.end_year = end_year

class Attendance:
    def __init__(self, attendance_id: int, subject_id: int, session_id: int, date: str):
        self.attendance_id = attendance_id
        self.subject_id = subject_id
        self.session_id = session_id
        self.date = date
        self.student_status_map: Dict[int, bool] = {}

class Result:
    def __init__(self, result_id: int, student_id: int, subject_id: int, marks: float):
        self.result_id = result_id
        self.student_id = student_id
        self.subject_id = subject_id
        self.marks = marks

class Leave:
    def __init__(self, leave_id: int, user_id: int, date: str, message: str):
        self.leave_id = leave_id
        self.user_id = user_id
        self.date = date
        self.message = message
        self.status: str = "Pending"

class Feedback:
    def __init__(self, feedback_id: int, user_id: int, message: str):
        self.feedback_id = feedback_id
        self.user_id = user_id
        self.message = message
        self.reply: Optional[str] = None

class StudentManagementSystem:
    def __init__(self):
        self._admins: Dict[int, Admin] = {}
        self._staffs: Dict[int, Staff] = {}
        self._students: Dict[int, Student] = {}
        self._courses: Dict[int, Course] = {}
        self._subjects: Dict[int, Subject] = {}
        self._sessions: Dict[int, Session] = {}
        self._attendances: Dict[int, Attendance] = {}
        self._results: Dict[int, Result] = {}
        self._leaves: Dict[int, Leave] = {}
        self._feedbacks: Dict[int, Feedback] = {}

        self._id_counters: Dict[str, int] = {
            "user": 1,
            "course": 1,
            "subject": 1,
            "session": 1,
            "attendance": 1,
            "result": 1,
            "leave": 1,
            "feedback": 1
        }

    def _generate_id(self, entity_type: str) -> int:
        new_id = self._id_counters[entity_type]
        self._id_counters[entity_type] += 1
        return new_id

    def add_admin(self, name: str, email: str) -> Admin:
        admin_id = self._generate_id("user")
        admin = Admin(admin_id, name, email)
        self._admins[admin_id] = admin
        return admin

    def admin_view_overall_summary(self) -> Dict[str, int]:
        return {
            "total_students": len(self._students),
            "total_staff": len(self._staffs),
            "total_courses": len(self._courses),
            "total_subjects": len(self._subjects),
            "total_leaves": len(self._leaves),
            "total_feedbacks": len(self._feedbacks)
        }

    def admin_add_staff(self, name: str, email: str) -> Staff:
        staff_id = self._generate_id("user")
        staff = Staff(staff_id, name, email)
        self._staffs[staff_id] = staff
        return staff

    def admin_update_staff(self, staff_id: int, name: str, email: str) -> None:
        if staff_id not in self._staffs:
            raise ValueError("Staff not found")
        self._staffs[staff_id].name = name
        self._staffs[staff_id].email = email

    def admin_delete_staff(self, staff_id: int) -> None:
        if staff_id in self._staffs:
            del self._staffs[staff_id]

    def admin_add_student(self, name: str, email: str, course_id: int, session_id: int) -> Student:
        if course_id not in self._courses or session_id not in self._sessions:
            raise ValueError("Invalid course or session ID")
        student_id = self._generate_id("user")
        student = Student(student_id, name, email, course_id, session_id)
        self._students[student_id] = student
        return student

    def admin_update_student(self, student_id: int, name: str, email: str, course_id: int, session_id: int) -> None:
        if student_id not in self._students:
            raise ValueError("Student not found")
        if course_id not in self._courses or session_id not in self._sessions:
            raise ValueError("Invalid course or session ID")
        student = self._students[student_id]
        student.name = name
        student.email = email
        student.course_id = course_id
        student.session_id = session_id

    def admin_delete_student(self, student_id: int) -> None:
        if student_id in self._students:
            del self._students[student_id]

    def admin_add_course(self, name: str) -> Course:
        course_id = self._generate_id("course")
        course = Course(course_id, name)
        self._courses[course_id] = course
        return course

    def admin_update_course(self, course_id: int, name: str) -> None:
        if course_id not in self._courses:
            raise ValueError("Course not found")
        self._courses[course_id].name = name

    def admin_delete_course(self, course_id: int) -> None:
        if course_id in self._courses:
            del self._courses[course_id]

    def admin_add_subject(self, name: str, course_id: int, staff_id: int) -> Subject:
        if course_id not in self._courses or staff_id not in self._staffs:
            raise ValueError("Invalid course or staff ID")
        subject_id = self._generate_id("subject")
        subject = Subject(subject_id, name, course_id, staff_id)
        self._subjects[subject_id] = subject
        return subject

    def admin_update_subject(self, subject_id: int, name: str, course_id: int, staff_id: int) -> None:
        if subject_id not in self._subjects:
            raise ValueError("Subject not found")
        if course_id not in self._courses or staff_id not in self._staffs:
            raise ValueError("Invalid course or staff ID")
        subject = self._subjects[subject_id]
        subject.name = name
        subject.course_id = course_id
        subject.staff_id = staff_id

    def admin_delete_subject(self, subject_id: int) -> None:
        if subject_id in self._subjects:
            del self._subjects[subject_id]

    def admin_add_session(self, start_year: str, end_year: str) -> Session:
        session_id = self._generate_id("session")
        session = Session(session_id, start_year, end_year)
        self._sessions[session_id] = session
        return session

    def admin_update_session(self, session_id: int, start_year: str, end_year: str) -> None:
        if session_id not in self._sessions:
            raise ValueError("Session not found")
        session = self._sessions[session_id]
        session.start_year = start_year
        session.end_year = end_year

    def admin_delete_session(self, session_id: int) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    def admin_view_student_attendance(self, student_id: int) -> List[Dict[str, Union[str, bool]]]:
        if student_id not in self._students:
            raise ValueError("Student not found")
        records = []
        for att in self._attendances.values():
            if student_id in att.student_status_map:
                records.append({
                    "attendance_id": att.attendance_id,
                    "date": att.date,
                    "subject_id": att.subject_id,
                    "status": att.student_status_map[student_id]
                })
        return records

    def admin_review_feedback(self, feedback_id: int, reply: str) -> None:
        if feedback_id not in self._feedbacks:
            raise ValueError("Feedback not found")
        self._feedbacks[feedback_id].reply = reply

    def admin_review_leave(self, leave_id: int, status: str) -> None:
        if leave_id not in self._leaves:
            raise ValueError("Leave not found")
        if status not in ["Approved", "Rejected"]:
            raise ValueError("Status must be 'Approved' or 'Rejected'")
        self._leaves[leave_id].status = status

    def staff_view_summary(self, staff_id: int) -> Dict[str, int]:
        if staff_id not in self._staffs:
            raise ValueError("Staff not found")
        my_subjects = [s for s in self._subjects.values() if s.staff_id == staff_id]
        my_leaves = [l for l in self._leaves.values() if l.user_id == staff_id]
        
        student_ids = set()
        for sub in my_subjects:
            for stu in self._students.values():
                if stu.course_id == sub.course_id:
                    student_ids.add(stu.user_id)
                    
        return {
            "total_my_students": len(student_ids),
            "total_my_subjects": len(my_subjects),
            "total_my_leaves": len(my_leaves)
        }

    def staff_take_attendance(self, staff_id: int, subject_id: int, session_id: int, date: str, student_status_map: Dict[int, bool]) -> Attendance:
        if subject_id not in self._subjects or self._subjects[subject_id].staff_id != staff_id:
            raise ValueError("Unauthorized or Subject not found")
        if session_id not in self._sessions:
            raise ValueError("Session not found")
            
        attendance_id = self._generate_id("attendance")
        attendance = Attendance(attendance_id, subject_id, session_id, date)
        
        for student_id, status in student_status_map.items():
            if student_id not in self._students:
                raise ValueError(f"Student ID {student_id} not found")
            attendance.student_status_map[student_id] = status
            
        self._attendances[attendance_id] = attendance
        return attendance

    def staff_update_attendance(self, staff_id: int, attendance_id: int, student_status_map: Dict[int, bool]) -> None:
        if attendance_id not in self._attendances:
            raise ValueError("Attendance record not found")
        attendance = self._attendances[attendance_id]
        if self._subjects[attendance.subject_id].staff_id != staff_id:
            raise ValueError("Unauthorized to update this attendance")
            
        for student_id, status in student_status_map.items():
            if student_id not in self._students:
                raise ValueError(f"Student ID {student_id} not found")
            attendance.student_status_map[student_id] = status

    def staff_add_result(self, staff_id: int, student_id: int, subject_id: int, marks: float) -> Result:
        if subject_id not in self._subjects or self._subjects[subject_id].staff_id != staff_id:
            raise ValueError("Unauthorized or Subject not found")
        if student_id not in self._students:
            raise ValueError("Student not found")
            
        result_id = self._generate_id("result")
        result = Result(result_id, student_id, subject_id, marks)
        self._results[result_id] = result
        return result

    def staff_update_result(self, staff_id: int, result_id: int, marks: float) -> None:
        if result_id not in self._results:
            raise ValueError("Result not found")
        result = self._results[result_id]
        if self._subjects[result.subject_id].staff_id != staff_id:
            raise ValueError("Unauthorized to update this result")
        result.marks = marks

    def staff_apply_leave(self, staff_id: int, date: str, message: str) -> Leave:
        if staff_id not in self._staffs:
            raise ValueError("Staff not found")
        leave_id = self._generate_id("leave")
        leave = Leave(leave_id, staff_id, date, message)
        self._leaves[leave_id] = leave
        return leave

    def staff_send_feedback(self, staff_id: int, message: str) -> Feedback:
        if staff_id not in self._staffs:
            raise ValueError("Staff not found")
        feedback_id = self._generate_id("feedback")
        feedback = Feedback(feedback_id, staff_id, message)
        self._feedbacks[feedback_id] = feedback
        return feedback

    def student_view_summary(self, student_id: int) -> Dict[str, int]:
        if student_id not in self._students:
            raise ValueError("Student not found")
        student = self._students[student_id]
        my_subjects = [s for s in self._subjects.values() if s.course_id == student.course_id]
        my_leaves = [l for l in self._leaves.values() if l.user_id == student_id]
        
        attendance_count = sum(1 for att in self._attendances.values() if student_id in att.student_status_map)
        
        return {
            "total_my_subjects": len(my_subjects),
            "total_my_leaves": len(my_leaves),
            "total_attendance_records": attendance_count
        }

    def student_view_attendance(self, student_id: int) -> List[Dict[str, Union[str, bool]]]:
        if student_id not in self._students:
            raise ValueError("Student not found")
        records = []
        for att in self._attendances.values():
            if student_id in att.student_status_map:
                records.append({
                    "date": att.date,
                    "subject_id": att.subject_id,
                    "status": att.student_status_map[student_id]
                })
        return records

    def student_view_result(self, student_id: int) -> List[Result]:
        if student_id not in self._students:
            raise ValueError("Student not found")
        return [res for res in self._results.values() if res.student_id == student_id]

    def student_apply_leave(self, student_id: int, date: str, message: str) -> Leave:
        if student_id not in self._students:
            raise ValueError("Student not found")
        leave_id = self._generate_id("leave")
        leave = Leave(leave_id, student_id, date, message)
        self._leaves[leave_id] = leave
        return leave

    def student_send_feedback(self, student_id: int, message: str) -> Feedback:
        if student_id not in self._students:
            raise ValueError("Student not found")
        feedback_id = self._generate_id("feedback")
        feedback = Feedback(feedback_id, student_id, message)
        self._feedbacks[feedback_id] = feedback
        return feedback