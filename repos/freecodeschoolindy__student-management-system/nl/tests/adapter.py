"""Per-model behavioral drivers for `student-management-system` NL track.

One driver per model, written by reading that model's run0 source:

  claude    StudentManagementSystem with TOKEN-based sessions: register_user ->
            login returns a token, and every read takes that token
            (get_my_profile(token) / get_student_profile(token, profile_id)).
  gpt       StudentManagementSystem addressed by USERNAME rather than token:
            get_private_student_profile(requester_username, student_username);
            waitlist and volunteers are admin-gated methods on the same object.
  deepseek  Django models + two function views. Driven through the ORM (the
            loader bootstraps Django and creates the tables) with a stub
            request; access control is in the view decorators.
  gemini    plain objects: StudentManagementSystem.register_*/login, plus a
            separate AdminDashboard and Waitlist. Profile access control lives
            on Student.get_profile(requester).

Access control is observed as "did a profile come back", so N5 (other user
denied) is False both when the call raises and when it returns nothing.

Return shapes match test_conformance.py's asserts.
"""

STUDENT, ADMIN, OTHER = "stu", "adm", "oth"
PW = "pw12345"


class ClaudeDriver:
    """Token-based sessions. login() returns a DICT {"token", "user", ...}, not
    a bare token, and every read/write is keyed by that token. The waitlist is
    public (self-signup), so add_to_waitlist takes no admin token."""

    def __init__(self, module):
        self.m = module

    def _sys(self):
        s = self.m.StudentManagementSystem()
        s.register_user(STUDENT, "s@e.com", PW, "student")
        s.register_user(OTHER, "o@e.com", PW, "student")
        s.register_user(ADMIN, "a@e.com", PW, "admin")
        return s

    @staticmethod
    def _token(session):
        return session["token"]

    def login_succeeds(self):
        return self._token(self._sys().login(STUDENT, PW)) is not None

    def login_rejects_wrong_password(self):
        try:
            self._sys().login(STUDENT, "wrong")
            return False
        except Exception:
            return True

    def login_rejects_unknown_user(self):
        try:
            self._sys().login("nobody", PW)
            return False
        except Exception:
            return True

    def _profile(self, s):
        tok = self._token(s.login(STUDENT, PW))
        return tok, s.create_student_profile(tok, "F", "L")

    def profile_visible_to_owner(self):
        s = self._sys()
        tok, _p = self._profile(s)
        return s.get_my_profile(tok) is not None

    def profile_visible_to_other(self):
        s = self._sys()
        _tok, p = self._profile(s)
        other = self._token(s.login(OTHER, PW))
        try:
            return s.get_student_profile(other, p["profile_id"]) is not None
        except Exception:
            return False

    def profile_visible_to_admin(self):
        s = self._sys()
        _tok, p = self._profile(s)
        adm = self._token(s.login(ADMIN, PW))
        return s.get_student_profile(adm, p["profile_id"]) is not None

    def waitlist_add_then_listed(self):
        s = self._sys()
        s.add_to_waitlist("Ann", "Lee", "a@e.com")     # public self-signup
        adm = self._token(s.login(ADMIN, PW))
        return len(s.get_waitlist(adm)) == 1

    def volunteer_add_then_listed(self):
        s = self._sys()
        adm = self._token(s.login(ADMIN, PW))
        s.add_volunteer(adm, "Vic", "Tor", "v@e.com")
        return len(s.get_all_volunteers(adm)) == 1

    def role_tokens(self):
        return {"student", "admin", "organizer"}


class GptDriver:
    """Addressed by username; admin-gated collections."""

    def __init__(self, module):
        self.m = module

    def _sys(self):
        s = self.m.StudentManagementSystem()
        s.register_student(STUDENT, PW, "Stu Dent", "s@e.com")
        s.register_student(OTHER, PW, "Oth Er", "o@e.com")
        s.register_admin(ADMIN, PW)
        return s

    def login_succeeds(self):
        return self._sys().login(STUDENT, PW) is not None

    def login_rejects_wrong_password(self):
        try:
            self._sys().login(STUDENT, "wrong")
            return False
        except Exception:
            return True

    def login_rejects_unknown_user(self):
        try:
            self._sys().login("nobody", PW)
            return False
        except Exception:
            return True

    def profile_visible_to_owner(self):
        s = self._sys()
        return s.get_private_student_profile(STUDENT, STUDENT) is not None

    def profile_visible_to_other(self):
        s = self._sys()
        try:
            return s.get_private_student_profile(OTHER, STUDENT) is not None
        except Exception:
            return False

    def profile_visible_to_admin(self):
        s = self._sys()
        return s.get_private_student_profile(ADMIN, STUDENT) is not None

    def waitlist_add_then_listed(self):
        s = self._sys()
        s.add_student_to_waitlist(ADMIN, STUDENT)
        return len(s.get_waitlist(ADMIN)) == 1

    def volunteer_add_then_listed(self):
        s = self._sys()
        s.add_volunteer(ADMIN, "Vic", "mentor")
        return len(s.list_volunteers(ADMIN)) == 1

    def role_tokens(self):
        return {"student", "admin"}


class DeepseekDriver:
    """Django models + two function views, driven through the ORM.

    The loader already bootstraps Django and creates this module's tables, so
    the models ARE drivable — an earlier version of this driver wrongly assumed
    they were not and hardcoded failures.

    Access control lives in the view decorators, not in a service object:
      student_profile_view  @login_required           -> own profile
      student_detail_view   @user_passes_test(staff or role == 'organizer')
    The views end in render(), which raises because no templates exist in this
    single-file generation. That raise is the signal that the permission gate
    was PASSED; a denied request instead returns a redirect/forbidden response
    without reaching render(). So "visible" == "reached the renderer"."""

    def __init__(self, module):
        self.m = module

    def _fresh(self):
        for cls in (self.m.StudentProfile, self.m.Volunteer,
                    self.m.WaitlistEntry, self.m.User):
            cls.objects.all().delete()

    def _user(self, username, role="student", staff=False):
        u = self.m.User.objects.create(username=username, role=role, is_staff=staff)
        u.set_password(PW)
        u.save()
        return u

    @staticmethod
    def _request(user):
        return type("Req", (), {"user": user, "method": "GET",
                                "path": "/", "GET": {}, "POST": {},
                                "META": {}, "session": {}})()

    def _reaches_render(self, view, user, *args):
        try:
            resp = view(self._request(user), *args)
        except Exception:
            return True                      # got past the gate, died in render()
        return getattr(resp, "status_code", 200) not in (301, 302, 403)

    def login_succeeds(self):
        self._fresh()
        self._user(STUDENT)
        return self.m.User.objects.get(username=STUDENT).check_password(PW) is True

    def login_rejects_wrong_password(self):
        self._fresh()
        self._user(STUDENT)
        return self.m.User.objects.get(username=STUDENT).check_password("wrong") is False

    def login_rejects_unknown_user(self):
        self._fresh()
        return not self.m.User.objects.filter(username="nobody").exists()

    def _seed_profile(self):
        self._fresh()
        owner = self._user(STUDENT)
        self.m.StudentProfile.objects.create(user=owner, full_name="F L",
                                             email="s@e.com")
        return owner

    def profile_visible_to_owner(self):
        owner = self._seed_profile()
        return self._reaches_render(self.m.student_profile_view, owner)

    def profile_visible_to_other(self):
        owner = self._seed_profile()
        other = self._user(OTHER)
        return self._reaches_render(self.m.student_detail_view, other, owner.id)

    def profile_visible_to_admin(self):
        owner = self._seed_profile()
        admin = self._user(ADMIN, role="organizer", staff=True)
        return self._reaches_render(self.m.student_detail_view, admin, owner.id)

    def waitlist_add_then_listed(self):
        self._fresh()
        self.m.WaitlistEntry.objects.create(name="Ann", email="a@e.com")
        return self.m.WaitlistEntry.objects.count() == 1

    def volunteer_add_then_listed(self):
        self._fresh()
        u = self._user("vic", role="volunteer")
        self.m.Volunteer.objects.create(user=u, skills="mentoring",
                                        availability="weekends")
        return self.m.Volunteer.objects.count() == 1

    def role_tokens(self):
        return {str(c[0]).lower() for c in self.m.User.ROLE_CHOICES}


class GeminiDriver:
    """Plain objects; the dashboard and waitlist are separate collaborators."""

    def __init__(self, module):
        self.m = module

    def _sys(self):
        s = self.m.StudentManagementSystem()
        s.register_student(STUDENT, PW)
        s.register_student(OTHER, PW)
        s.register_admin(ADMIN, PW)
        return s

    def login_succeeds(self):
        return self._sys().login(STUDENT, PW) is not None

    def login_rejects_wrong_password(self):
        try:
            return self._sys().login(STUDENT, "wrong") is None
        except Exception:
            return True

    def login_rejects_unknown_user(self):
        try:
            return self._sys().login("nobody", PW) is None
        except Exception:
            return True

    def _pair(self):
        s = self._sys()
        return s, s.login(STUDENT, PW), s.login(OTHER, PW), s.login(ADMIN, PW)

    def profile_visible_to_owner(self):
        _s, stu, _oth, _adm = self._pair()
        return stu.get_profile(stu) is not None

    def profile_visible_to_other(self):
        _s, stu, oth, _adm = self._pair()
        try:
            return stu.get_profile(oth) is not None
        except Exception:
            return False

    def profile_visible_to_admin(self):
        _s, stu, _oth, adm = self._pair()
        try:
            return stu.get_profile(adm) is not None
        except Exception:
            return False

    def waitlist_add_then_listed(self):
        w = self.m.Waitlist()
        w.add_student("Ann")
        return len(w.get_all()) == 1

    def volunteer_add_then_listed(self):
        s = self._sys()
        s.register_volunteer("Vic", PW)
        adm = s.login(ADMIN, PW)
        return len(self.m.AdminDashboard(s).view_all_volunteers(adm)) == 1

    def role_tokens(self):
        return {str(r.value).lower() for r in self.m.Role}


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
