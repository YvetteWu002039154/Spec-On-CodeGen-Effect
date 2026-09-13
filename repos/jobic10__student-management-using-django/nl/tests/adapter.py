"""Per-model behavioral drivers for `student-management-using-django` NL track.

One driver per model, written by reading that model's run0 source. The four
generations put the same admin/staff/student workflow behind four different
shapes:

  claude    StudentManagementSystem() facade, no actor argument:
            add_course(name), add_staff(...), take_attendance(staff_id, ...),
            student_apply_leave(...), reply_student_feedback(id, reply).
  gpt       StudentManagementSystem() facade where every admin action takes the
            acting admin's id: create_admin(name) first, then
            create_course(admin_id, name), review_leave(admin_id, id, approve).
  deepseek  MODULE-LEVEL globals (users, courses, sessions, attendance_records,
            leave_requests, feedbacks) mutated by Admin/Staff/Student objects.
            The add_* methods return None, so ids are read back from the dicts.
  gemini    Admin/Staff/Student methods all take the StudentManagementSystem as
            their first argument: admin.add_course(system, name).

Statuses are normalised because the generations disagree on vocabulary: a leave
is pending as int 0, "Pending" or LeaveStatus.PENDING; attendance is present as
True, "Present" or a PRESENT enum member. The contract pins the state, not the
spelling.

Return shapes match test_conformance.py's asserts.
"""

COURSE, SUBJECT, MARKS, REPLY = "Physics", "Algebra", 80.0, "thanks"
DATE = "2024-01-01"


def _norm_status(value):
    """Leave state -> 'pending' / 'approved' / 'rejected'."""
    v = getattr(value, "value", value)
    if isinstance(v, bool):
        return "approved" if v else "pending"
    if isinstance(v, int):
        return {0: "pending", 1: "approved", 2: "rejected"}.get(v, str(v))
    return str(v).strip().lower()


def _norm_present(value):
    """Attendance mark -> bool."""
    v = getattr(value, "value", value)
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    return str(v).strip().lower() in ("present", "p", "true", "1")


class ClaudeDriver:
    """One StudentManagementSystem; admin actions take no actor id."""

    def __init__(self, module):
        self.m = module

    def _sys(self):
        return self.m.StudentManagementSystem()

    def _staffed(self, s):
        c = s.add_course(COURSE)
        st = s.add_staff("stf", "pw", "s@e.com", "S", "T", "addr", c.course_id)
        return c, st

    def _enrolled(self, s):
        c, st = self._staffed(s)
        ses = s.add_session(2024, 2025)
        stu = s.add_student("stu", "pw", "u@e.com", "U", "V", "addr",
                            c.course_id, ses.session_id)
        sub = s.add_subject(SUBJECT, c.course_id, st.user_id)
        return st, stu, sub, ses

    def add_course_name(self):
        return self._sys().add_course(COURSE).course_name

    def staff_present(self):
        s = self._sys()
        st = s.add_staff("stf", "pw", "s@e.com", "S", "T", "addr")
        return any(x.user_id == st.user_id for x in s.get_all_staff())

    def student_present(self):
        s = self._sys()
        stu = s.add_student("stu", "pw", "u@e.com", "U", "V", "addr")
        return any(x.user_id == stu.user_id for x in s.get_all_students())

    def add_subject_name(self):
        s = self._sys()
        c, st = self._staffed(s)
        return s.add_subject(SUBJECT, c.course_id, st.user_id).subject_name

    def add_session(self):
        return self._sys().add_session(2024, 2025) is not None

    def attendance_present(self):
        s = self._sys()
        st, stu, sub, ses = self._enrolled(s)
        s.take_attendance(st.user_id, sub.subject_id, ses.session_id, DATE,
                          {stu.user_id: True})
        rows = s.student_view_attendance(stu.user_id)
        return bool(rows) and _norm_present(rows[0]["status"])

    def result_marks(self):
        s = self._sys()
        st, stu, sub, _ses = self._enrolled(s)
        s.add_result(st.user_id, stu.user_id, sub.subject_id, MARKS, 0)
        return float(s.student_view_result(stu.user_id)[0]["total_marks"])

    def leave_pending(self):
        s = self._sys()
        stu = s.add_student("stu", "pw", "u@e.com", "U", "V", "addr")
        lv = s.student_apply_leave(stu.user_id, DATE, "sick")
        return _norm_status(lv.leave_status)

    def leave_approved(self):
        s = self._sys()
        stu = s.add_student("stu", "pw", "u@e.com", "U", "V", "addr")
        lv = s.student_apply_leave(stu.user_id, DATE, "sick")
        s.approve_student_leave(lv.leave_id)
        return _norm_status(lv.leave_status)

    def feedback_reply(self):
        s = self._sys()
        stu = s.add_student("stu", "pw", "u@e.com", "U", "V", "addr")
        fb = s.student_send_feedback(stu.user_id, "hello")
        s.reply_student_feedback(fb.feedback_id, REPLY)
        return fb.feedback_reply


class GptDriver:
    """Same facade shape, but every admin action names the acting admin, and
    every create_* returns an integer ID rather than an object. This generation
    exposes no public getter for a course/staff/student/subject — the only
    lookups are its own `_require_*` helpers, which return the entity or raise —
    so presence and name are observed through those."""

    def __init__(self, module):
        self.m = module

    def _sys(self):
        s = self.m.StudentManagementSystem()
        return s, s.create_admin("Root")

    def _enrolled(self, s, a):
        cid = s.create_course(a, COURSE)
        sesid = s.create_session(a, "2024/25")
        stfid = s.create_staff(a, "Staffer")
        stuid = s.create_student(a, "Studier", cid, sesid)
        subid = s.create_subject(a, SUBJECT, cid, stfid)
        return cid, sesid, stfid, stuid, subid

    def add_course_name(self):
        s, a = self._sys()
        return s._require_course(s.create_course(a, COURSE)).name

    def staff_present(self):
        s, a = self._sys()
        return s._require_staff(s.create_staff(a, "Staffer")) is not None

    def student_present(self):
        s, a = self._sys()
        cid = s.create_course(a, COURSE)
        sesid = s.create_session(a, "2024/25")
        return s._require_student(s.create_student(a, "Studier", cid, sesid)) is not None

    def add_subject_name(self):
        s, a = self._sys()
        cid = s.create_course(a, COURSE)
        stfid = s.create_staff(a, "Staffer")
        return s._require_subject(s.create_subject(a, SUBJECT, cid, stfid)).name

    def add_session(self):
        s, a = self._sys()
        return s.create_session(a, "2024/25") is not None

    def attendance_present(self):
        s, a = self._sys()
        _c, _ses, stf, stu, sub = self._enrolled(s, a)
        s.take_or_update_attendance(stf, stu, sub, DATE, True)
        rows = s.view_attendance_as_student(stu)
        return bool(rows) and _norm_present(rows[0].status)

    def result_marks(self):
        s, a = self._sys()
        _c, _ses, stf, stu, sub = self._enrolled(s, a)
        s.add_or_update_result(stf, stu, sub, MARKS)
        return float(s.view_result_as_student(stu)[0].marks)

    def leave_pending(self):
        s, a = self._sys()
        _c, _ses, _stf, stu, _sub = self._enrolled(s, a)
        s.apply_leave_as_student(stu, DATE, DATE, "sick")
        return _norm_status(s.list_leaves_as_student(stu)[0].status)

    def leave_approved(self):
        s, a = self._sys()
        _c, _ses, _stf, stu, _sub = self._enrolled(s, a)
        lv = s.apply_leave_as_student(stu, DATE, DATE, "sick")
        s.review_leave(a, getattr(lv, "id", lv), True)
        return _norm_status(s.list_leaves_as_student(stu)[0].status)

    def feedback_reply(self):
        s, a = self._sys()
        _c, _ses, _stf, stu, _sub = self._enrolled(s, a)
        fb = s.send_feedback_as_student(stu, "hello")
        s.review_and_reply_feedback(a, getattr(fb, "id", fb), REPLY)
        return s.list_feedback_as_student(stu)[0].reply


class DeepseekDriver:
    """State lives in MODULE-LEVEL dicts/lists; add_* return None, so ids are
    read back out of the globals the call just mutated."""

    def __init__(self, module):
        self.m = module

    def _reset(self):
        for name in ("users", "staff_list", "student_list", "courses", "subjects",
                     "sessions", "attendance_records", "results",
                     "leave_requests", "feedbacks"):
            store = getattr(self.m, name, None)
            if isinstance(store, dict):
                store.clear()
            elif isinstance(store, list):
                del store[:]
        return self.m.Admin("ADM1", "Root", "a@e.com", "pw")

    def _last(self, store):
        s = getattr(self.m, store)
        return list(s.values())[-1] if isinstance(s, dict) else s[-1]

    def add_course_name(self):
        self._reset().add_course(COURSE)
        return self._last("courses").name

    def staff_present(self):
        a = self._reset()
        a.add_staff("Staffer", "s@e.com", "pw")
        return any(u.role == self.m.Role.STAFF for u in self.m.users.values())

    def student_present(self):
        a = self._reset()
        a.add_student("Studier", "u@e.com", "pw")
        return any(u.role == self.m.Role.STUDENT for u in self.m.users.values())

    def add_subject_name(self):
        a = self._reset()
        a.add_course(COURSE)
        a.add_subject(SUBJECT, self._last("courses").course_id)
        return self._last("subjects").name

    def add_session(self):
        a = self._reset()
        a.add_course(COURSE)
        a.add_subject(SUBJECT, self._last("courses").course_id)
        a.add_session(self._last("courses").course_id,
                      self._last("subjects").subject_id, DATE)
        return len(self.m.sessions) == 1

    def _cast(self, a):
        """users[] stores plain Person objects, which have no staff/student
        behaviour, so the actors are rebuilt as Staff/Student on the ids the
        admin just registered."""
        a.add_staff("Staffer", "s@e.com", "pw")
        staff_id = self.m.staff_list[-1]
        a.add_student("Studier", "u@e.com", "pw")
        stu_id = self.m.student_list[-1]
        return (self.m.Staff(staff_id, "Staffer", "s@e.com", "pw"),
                self.m.Student(stu_id, "Studier", "u@e.com", "pw"))

    def attendance_present(self):
        a = self._reset()
        staff, stu = self._cast(a)
        a.add_course(COURSE)
        a.add_subject(SUBJECT, self._last("courses").course_id)
        a.add_session(self._last("courses").course_id,
                      self._last("subjects").subject_id, DATE)
        staff.take_attendance(self._last("sessions").session_id, stu.uid, True)
        return bool(self.m.attendance_records) and \
            _norm_present(self.m.attendance_records[-1].status)

    def result_marks(self):
        a = self._reset()
        staff, stu = self._cast(a)
        a.add_course(COURSE)
        a.add_subject(SUBJECT, self._last("courses").course_id)
        staff.add_result(stu.uid, self._last("subjects").subject_id, MARKS)
        return float(self.m.results[-1].marks)

    def leave_pending(self):
        a = self._reset()
        _staff, stu = self._cast(a)
        stu.apply_leave("sick", DATE, DATE)
        return _norm_status(self.m.leave_requests[-1].status)

    def leave_approved(self):
        a = self._reset()
        _staff, stu = self._cast(a)
        stu.apply_leave("sick", DATE, DATE)
        a.approve_leave(self.m.leave_requests[-1].leave_id)
        return _norm_status(self.m.leave_requests[-1].status)

    def feedback_reply(self):
        a = self._reset()
        _staff, stu = self._cast(a)
        stu.send_feedback("hello")
        a.reply_feedback(self.m.feedbacks[-1].feedback_id, REPLY)
        return self.m.feedbacks[-1].reply


class GeminiDriver:
    """Actors are objects, but every operation is passed the system."""

    def __init__(self, module):
        self.m = module

    def _sys(self):
        s = self.m.StudentManagementSystem()
        return s, self.m.Admin("ADM1", "Root", "a@e.com", "pw")

    def add_course_name(self):
        s, a = self._sys()
        return a.add_course(s, COURSE).name

    def staff_present(self):
        s, a = self._sys()
        st = a.add_staff(s, "Staffer", "s@e.com", "pw")
        return st is not None and st.user_id in s.users

    def student_present(self):
        s, a = self._sys()
        c = a.add_course(s, COURSE)
        ses = a.add_session(s, 2024, 2025)
        stu = a.add_student(s, "Studier", "u@e.com", "pw", c.course_id, ses.session_id)
        return stu is not None and stu.user_id in s.users

    def add_subject_name(self):
        s, a = self._sys()
        c = a.add_course(s, COURSE)
        st = a.add_staff(s, "Staffer", "s@e.com", "pw")
        return a.add_subject(s, SUBJECT, c.course_id, st.user_id).name

    def add_session(self):
        s, a = self._sys()
        return a.add_session(s, 2024, 2025) is not None

    def _cast(self, s, a):
        c = a.add_course(s, COURSE)
        ses = a.add_session(s, 2024, 2025)
        st = a.add_staff(s, "Staffer", "s@e.com", "pw")
        stu = a.add_student(s, "Studier", "u@e.com", "pw", c.course_id, ses.session_id)
        sub = a.add_subject(s, SUBJECT, c.course_id, st.user_id)
        return st, stu, sub

    def attendance_present(self):
        s, a = self._sys()
        st, stu, sub = self._cast(s, a)
        st.take_attendance(s, stu.user_id, sub.subject_id, DATE, "Present")
        rows = stu.view_attendance(s)
        return bool(rows) and _norm_present(rows[0].status)

    def result_marks(self):
        s, a = self._sys()
        st, stu, sub = self._cast(s, a)
        st.add_result(s, stu.user_id, sub.subject_id, MARKS)
        return float(stu.view_result(s)[0].marks)

    def leave_pending(self):
        s, a = self._sys()
        _st, stu, _sub = self._cast(s, a)
        return _norm_status(stu.apply_leave(s, DATE, "sick").status)

    def leave_approved(self):
        s, a = self._sys()
        _st, stu, _sub = self._cast(s, a)
        lv = stu.apply_leave(s, DATE, "sick")
        a.review_leave(s, lv.leave_id, "Approved")
        return _norm_status(lv.status)

    def feedback_reply(self):
        s, a = self._sys()
        _st, stu, _sub = self._cast(s, a)
        fb = stu.send_feedback(s, "hello")
        a.review_feedback(s, fb.feedback_id, REPLY)
        return fb.reply


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
