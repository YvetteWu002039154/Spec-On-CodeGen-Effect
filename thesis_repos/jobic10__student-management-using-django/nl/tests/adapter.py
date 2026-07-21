import datetime
import enum

_TODAY = datetime.date(2024, 1, 15)


# --- small shared normalization helpers -------------------------------------

_INT_STATUS = {0: "pending", 1: "approved", 2: "rejected", -1: "rejected"}


def _status_token(v):
    """Normalize a leave status (int / enum / str) to a lowercase word."""
    if isinstance(v, enum.Enum):
        v = getattr(v, "value", v.name)
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, int):
        return _INT_STATUS.get(v, str(v))
    return str(v).lower()


def _is_present(status):
    """Normalize an attendance status (bool / enum / str) to present=True."""
    if isinstance(status, bool):
        return status
    if isinstance(status, enum.Enum):
        status = getattr(status, "value", status.name)
    return str(status).lower() in ("present", "true", "1")


def _marks_of(obj):
    """Read a marks-like value off a result object / dict."""
    if isinstance(obj, dict):
        for k in ("marks", "exam_marks", "total_marks", "exam"):
            if k in obj:
                return obj[k]
        return None
    for a in ("marks", "exam_marks", "exam", "total_marks"):
        v = getattr(obj, a, None)
        if v is not None:
            return v
    return None


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m
        self.sms = m.StudentManagementSystem()
        self._world = None

    def _build(self):
        if self._world is not None:
            return self._world
        s = self.sms
        course = s.add_course("Mathematics")
        staff = s.add_staff(username="stf1", password="pw123456", email="stf1@x.com",
                            first_name="Sam", last_name="Ng", address="1 St",
                            course_id=course.course_id)
        subject = s.add_subject("Algebra", course.course_id, staff.user_id)
        session = s.add_session(2020, 2024)
        student = s.add_student(username="stu1", password="pw123456", email="stu1@x.com",
                               first_name="Al", last_name="Lee", address="2 St",
                               course_id=course.course_id, session_id=session.session_id)
        self._world = dict(course=course, staff=staff, subject=subject,
                           session=session, student=student)
        return self._world

    def add_course_name(self):
        return self.sms.add_course("Physics").course_name

    def staff_present(self):
        w = self._build()
        return any(u.user_id == w["staff"].user_id for u in self.sms.get_all_staff())

    def student_present(self):
        w = self._build()
        return any(u.user_id == w["student"].user_id for u in self.sms.get_all_students())

    def add_subject_name(self):
        return self._build()["subject"].subject_name

    def add_session(self):
        w = self._build()
        return w["session"] in self.sms.get_all_sessions()

    def attendance_present(self):
        w = self._build()
        self.sms.take_attendance(w["staff"].user_id, w["subject"].subject_id,
                                 w["session"].session_id, _TODAY,
                                 {w["student"].user_id: True})
        recs = self.sms.student_view_attendance(w["student"].user_id)
        return _is_present(recs[0]["status"])

    def result_marks(self):
        w = self._build()
        self.sms.add_result(w["staff"].user_id, w["student"].user_id,
                            w["subject"].subject_id, 80.0, 15.0)
        rows = self.sms.student_view_result(w["student"].user_id)
        return _marks_of(rows[0])

    def leave_pending(self):
        w = self._build()
        leave = self.sms.student_apply_leave(w["student"].user_id, "2024-01-20", "sick")
        return _status_token(leave.leave_status)

    def leave_approved(self):
        w = self._build()
        leave = self.sms.student_apply_leave(w["student"].user_id, "2024-01-21", "sick")
        self.sms.approve_student_leave(leave.leave_id)
        return _status_token(leave.leave_status)

    def feedback_reply(self):
        w = self._build()
        fb = self.sms.student_send_feedback(w["student"].user_id, "great class")
        self.sms.reply_student_feedback(fb.feedback_id, "thanks")
        return fb.feedback_reply


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m
        self.sms = m.StudentManagementSystem()
        self.admin_id = self.sms.create_admin("Root")
        self._world = None

    def _lookup(self, obj_id, attr, class_name):
        for store in vars(self.sms).values():
            if isinstance(store, dict) and obj_id in store:
                obj = store[obj_id]
                if type(obj).__name__ == class_name:
                    return getattr(obj, attr, None)
        return None

    def _find_leave(self, lid):
        for row in self.sms.list_leaves_as_admin(self.admin_id):
            if row.id == lid:
                return row
        return None

    def _build(self):
        if self._world is not None:
            return self._world
        s = self.sms
        cid = s.create_course(self.admin_id, "Mathematics")
        stf = s.create_staff(self.admin_id, "Sam")
        sess = s.create_session(self.admin_id, "2020-2024")
        stud = s.create_student(self.admin_id, "Al", cid, sess)
        subj = s.create_subject(self.admin_id, "Algebra", cid, stf)
        self._world = dict(cid=cid, staff=stf, session=sess, student=stud, subject=subj)
        return self._world

    def add_course_name(self):
        cid = self.sms.create_course(self.admin_id, "Physics")
        return self._lookup(cid, "name", "Course")

    def staff_present(self):
        w = self._build()
        return self._lookup(w["staff"], "name", "Staff") is not None

    def student_present(self):
        w = self._build()
        return self._lookup(w["student"], "name", "Student") is not None

    def add_subject_name(self):
        w = self._build()
        return self._lookup(w["subject"], "name", "Subject")

    def add_session(self):
        w = self._build()
        return self._lookup(w["session"], "name", "Session") is not None

    def attendance_present(self):
        w = self._build()
        self.sms.take_or_update_attendance(w["staff"], w["student"], w["subject"],
                                           _TODAY, self.m.AttendanceStatus.PRESENT)
        recs = self.sms.view_attendance_as_student(w["student"])
        return _is_present(recs[0].status)

    def result_marks(self):
        w = self._build()
        self.sms.add_or_update_result(w["staff"], w["student"], w["subject"], 80.0)
        rows = self.sms.view_result_as_student(w["student"])
        return _marks_of(rows[0])

    def leave_pending(self):
        w = self._build()
        lid = self.sms.apply_leave_as_student(w["student"],
                                              datetime.date(2024, 1, 20),
                                              datetime.date(2024, 1, 22), "sick")
        return _status_token(self._find_leave(lid).status)

    def leave_approved(self):
        w = self._build()
        lid = self.sms.apply_leave_as_student(w["student"],
                                              datetime.date(2024, 1, 23),
                                              datetime.date(2024, 1, 24), "sick")
        self.sms.review_leave(self.admin_id, lid, True)
        return _status_token(self._find_leave(lid).status)

    def feedback_reply(self):
        w = self._build()
        fid = self.sms.send_feedback_as_student(w["student"], "great class")
        self.sms.review_and_reply_feedback(self.admin_id, fid, "thanks")
        for row in self.sms.list_feedback_as_admin(self.admin_id):
            if row.id == fid:
                return row.reply
        return None


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m
        self.admin = m.Admin("ADM", "Root", "root@x.com", "pw")
        m.users[self.admin.uid] = self.admin
        self._n = 0
        self._world = None

    def _uid(self, prefix):
        self._n += 1
        return f"{prefix}_{self._n}"

    def _last_leave(self, uid):
        rows = [l for l in self.m.leave_requests if l.applicant_id == uid]
        return rows[-1]

    def _build(self):
        if self._world is not None:
            return self._world
        m = self.m
        before_c = set(m.courses)
        self.admin.add_course("Mathematics")
        cid = next(iter(set(m.courses) - before_c))
        before_sub = set(m.subjects)
        self.admin.add_subject("Algebra", cid)
        sub_id = next(iter(set(m.subjects) - before_sub))
        before_ses = set(m.sessions)
        self.admin.add_session(cid, sub_id, "2024-01-15", "intro")
        ses_id = next(iter(set(m.sessions) - before_ses))
        staff = m.Staff(self._uid("STF"), "Sam", "sam@x.com", "pw")
        m.users[staff.uid] = staff
        m.staff_list.append(staff.uid)
        student = m.Student(self._uid("STU"), "Al", "al@x.com", "pw")
        m.users[student.uid] = student
        m.student_list.append(student.uid)
        self._world = dict(cid=cid, sub_id=sub_id, ses_id=ses_id,
                           staff=staff, student=student)
        return self._world

    def add_course_name(self):
        before = set(self.m.courses)
        self.admin.add_course("Physics")
        cid = next(iter(set(self.m.courses) - before))
        return self.m.courses[cid].name

    def staff_present(self):
        before = set(self.m.users)
        self.admin.add_staff("Temp", "temp@x.com", "pw")
        return len(set(self.m.users) - before) == 1

    def student_present(self):
        before = set(self.m.users)
        self.admin.add_student("Temp", "tmp2@x.com", "pw")
        return len(set(self.m.users) - before) == 1

    def add_subject_name(self):
        w = self._build()
        return self.m.subjects[w["sub_id"]].name

    def add_session(self):
        return self._build()["ses_id"] in self.m.sessions

    def attendance_present(self):
        w = self._build()
        w["staff"].take_attendance(w["ses_id"], w["student"].uid, True)
        recs = [r for r in self.m.attendance_records
                if r.student_id == w["student"].uid and r.session_id == w["ses_id"]]
        return _is_present(recs[-1].status)

    def result_marks(self):
        w = self._build()
        w["staff"].add_result(w["student"].uid, w["sub_id"], 80.0)
        rows = [r for r in self.m.results
                if r.student_id == w["student"].uid and r.subject_id == w["sub_id"]]
        return _marks_of(rows[-1])

    def leave_pending(self):
        w = self._build()
        w["student"].apply_leave("sick", "2024-01-20", "2024-01-22")
        return _status_token(self._last_leave(w["student"].uid).status)

    def leave_approved(self):
        w = self._build()
        w["student"].apply_leave("sick", "2024-01-23", "2024-01-24")
        row = self._last_leave(w["student"].uid)
        self.admin.approve_leave(row.leave_id)
        return _status_token(row.status)

    def feedback_reply(self):
        w = self._build()
        w["student"].send_feedback("great class")
        fb = [f for f in self.m.feedbacks if f.sender_id == w["student"].uid][-1]
        self.admin.reply_feedback(fb.feedback_id, "thanks")
        return fb.reply


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m
        self.sms = m.StudentManagementSystem()
        self.admin = m.Admin(1, "Root", "root@x.com", "pw")
        self._world = None

    def _build(self):
        if self._world is not None:
            return self._world
        course = self.admin.add_course(self.sms, "Mathematics")
        session = self.admin.add_session(self.sms, 2020, 2024)
        staff = self.admin.add_staff(self.sms, "Sam", "sam@x.com", "pw")
        student = self.admin.add_student(self.sms, "Al", "al@x.com", "pw",
                                         course.course_id, session.session_id)
        subject = self.admin.add_subject(self.sms, "Algebra", course.course_id,
                                         staff.user_id)
        self._world = dict(course=course, session=session, staff=staff,
                           student=student, subject=subject)
        return self._world

    def add_course_name(self):
        return self.admin.add_course(self.sms, "Physics").name

    def staff_present(self):
        w = self._build()
        return w["staff"].user_id in self.sms.users

    def student_present(self):
        w = self._build()
        return w["student"].user_id in self.sms.users

    def add_subject_name(self):
        return self._build()["subject"].name

    def add_session(self):
        return self.admin.add_session(self.sms, 2021, 2025) is not None

    def attendance_present(self):
        w = self._build()
        att = w["staff"].take_attendance(self.sms, w["student"].user_id,
                                         w["subject"].subject_id, "2024-01-15", "Present")
        return _is_present(att.status)

    def result_marks(self):
        w = self._build()
        res = w["staff"].add_result(self.sms, w["student"].user_id,
                                    w["subject"].subject_id, 80.0)
        return _marks_of(res)

    def leave_pending(self):
        w = self._build()
        leave = w["student"].apply_leave(self.sms, "2024-01-20", "sick")
        return _status_token(leave.status)

    def leave_approved(self):
        w = self._build()
        leave = w["student"].apply_leave(self.sms, "2024-01-21", "sick")
        self.admin.review_leave(self.sms, leave.leave_id, "Approved")
        return _status_token(leave.status)

    def feedback_reply(self):
        w = self._build()
        fb = w["student"].send_feedback(self.sms, "great class")
        self.admin.review_feedback(self.sms, fb.feedback_id, "thanks")
        return fb.reply


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
