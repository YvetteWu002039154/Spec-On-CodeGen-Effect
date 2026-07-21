import enum

# --- small shared observation helpers ---------------------------------------

def _enum_tokens(enum_cls):
    """Member names and values of an enum, lowercased."""
    tokens = set()
    for member in enum_cls:
        tokens.add(str(member.name).lower())
        tokens.add(str(member.value).lower())
    return tokens


def _role_token(obj):
    """Best-effort lowercased role token from a principal handle/login object."""
    if isinstance(obj, dict):
        return str(obj.get("role")).lower()
    r = getattr(obj, "role", None)
    if isinstance(r, enum.Enum):
        return str(getattr(r, "value", r.name)).lower()
    return str(r).lower()


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def login_succeeds(self):
        sys = self.m.StudentManagementSystem()
        sys.register_user("stu", "stu@example.com", "Passw0rd123", role="student")
        return sys.login("stu", "Passw0rd123") is not None

    def login_rejects_wrong_password(self):
        sys = self.m.StudentManagementSystem()
        sys.register_user("stu", "stu@example.com", "Passw0rd123", role="student")
        try:
            sys.login("stu", "wrong-password")
        except Exception:
            return True
        return False

    def login_rejects_unknown_user(self):
        sys = self.m.StudentManagementSystem()
        try:
            sys.login("ghost", "whatever")
        except Exception:
            return True
        return False

    def profile_visible_to_owner(self):
        sys = self.m.StudentManagementSystem()
        sys.register_user("stu", "stu@example.com", "Passw0rd123", role="student")
        token = sys.login("stu", "Passw0rd123")["token"]
        pid = sys.create_student_profile(token, "First", "Last")["profile_id"]
        return sys.get_student_profile(token, pid) is not None

    def profile_visible_to_other(self):
        sys = self.m.StudentManagementSystem()
        sys.register_user("stu", "stu@example.com", "Passw0rd123", role="student")
        sys.register_user("oth", "oth@example.com", "Passw0rd123", role="student")
        token = sys.login("stu", "Passw0rd123")["token"]
        pid = sys.create_student_profile(token, "First", "Last")["profile_id"]
        other_token = sys.login("oth", "Passw0rd123")["token"]
        try:
            return sys.get_student_profile(other_token, pid) is not None
        except Exception:
            return False

    def profile_visible_to_admin(self):
        sys = self.m.StudentManagementSystem()
        sys.register_user("stu", "stu@example.com", "Passw0rd123", role="student")
        token = sys.login("stu", "Passw0rd123")["token"]
        pid = sys.create_student_profile(token, "First", "Last")["profile_id"]
        admin_token = sys.login("admin", "admin123")["token"]
        return sys.get_student_profile(admin_token, pid) is not None

    def waitlist_add_then_listed(self):
        sys = self.m.StudentManagementSystem()
        email = "wait@example.com"
        sys.add_to_waitlist("Wait", "Lister", email)
        admin_token = sys.login("admin", "admin123")["token"]
        return any(email == e["email"] for e in sys.get_waitlist(admin_token))

    def volunteer_add_then_listed(self):
        sys = self.m.StudentManagementSystem()
        admin_token = sys.login("admin", "admin123")["token"]
        email = "vol@example.com"
        sys.add_volunteer(admin_token, "Vol", "Unteer", email)
        return any(email == v["email"] for v in sys.get_all_volunteers(admin_token))

    def role_tokens(self):
        sys = self.m.StudentManagementSystem()
        s = sys.register_user("stu", "stu@example.com", "Passw0rd123", role="student")
        a = sys.register_user("adm", "adm@example.com", "Passw0rd123", role="admin")
        return {_role_token(s), _role_token(a)}


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def login_succeeds(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123", "First Last", "stu@example.com")
        return sys.login("stu", "Passw0rd123") is not None

    def login_rejects_wrong_password(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123", "First Last", "stu@example.com")
        try:
            sys.login("stu", "wrong-password")
        except Exception:
            return True
        return False

    def login_rejects_unknown_user(self):
        sys = self.m.StudentManagementSystem()
        try:
            sys.login("ghost", "whatever")
        except Exception:
            return True
        return False

    def profile_visible_to_owner(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123", "First Last", "stu@example.com")
        return sys.get_private_student_profile("stu", "stu") is not None

    def profile_visible_to_other(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123", "First Last", "stu@example.com")
        sys.register_student("oth", "Passw0rd123", "Other User", "oth@example.com")
        try:
            return sys.get_private_student_profile("oth", "stu") is not None
        except Exception:
            return False

    def profile_visible_to_admin(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123", "First Last", "stu@example.com")
        sys.register_admin("adm", "Passw0rd123")
        return sys.get_private_student_profile("adm", "stu") is not None

    def waitlist_add_then_listed(self):
        waitlist = self.m.Waitlist()
        waitlist.add_student("stu")
        return "stu" in waitlist.list_students()

    def volunteer_add_then_listed(self):
        vm = self.m.VolunteerManagement()
        vm.add_volunteer("Vol Unteer", "mentor")
        return any(v.name == "Vol Unteer" for v in vm.list_volunteers())

    def role_tokens(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123", "First Last", "stu@example.com")
        sys.register_admin("adm", "Passw0rd123")
        return {_role_token(sys.login("stu", "Passw0rd123")),
                _role_token(sys.login("adm", "Passw0rd123"))}


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def login_succeeds(self):
        user = self.m.User(username="stu", role="student")
        user.set_password("Passw0rd123")
        return user.check_password("Passw0rd123")

    def login_rejects_wrong_password(self):
        user = self.m.User(username="stu", role="student")
        user.set_password("Passw0rd123")
        return user.check_password("wrong-password") is False

    def login_rejects_unknown_user(self):
        return self.m.User.objects.get(username="ghost") is None

    def profile_visible_to_owner(self):
        return self.m.StudentProfile.objects.get(user__username="stu") is not None

    def profile_visible_to_other(self):
        return self.m.StudentProfile.objects.get(user__username="stu") is not None

    def profile_visible_to_admin(self):
        return self.m.StudentProfile.objects.get(user__username="stu") is not None

    def waitlist_add_then_listed(self):
        self.m.WaitlistEntry.objects.create(name="Wait", email="wait@example.com")
        return self.m.WaitlistEntry.objects.filter(email="wait@example.com").exists()

    def volunteer_add_then_listed(self):
        self.m.Volunteer.objects.create(skills="python", availability="weekends")
        return self.m.Volunteer.objects.count() >= 1

    def role_tokens(self):
        return {c[0] for c in self.m.User.ROLE_CHOICES}


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def login_succeeds(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123")
        return sys.login("stu", "Passw0rd123") is not None

    def login_rejects_wrong_password(self):
        sys = self.m.StudentManagementSystem()
        sys.register_student("stu", "Passw0rd123")
        try:
            sys.login("stu", "wrong-password")
        except Exception:
            return True
        return False

    def login_rejects_unknown_user(self):
        sys = self.m.StudentManagementSystem()
        try:
            sys.login("ghost", "whatever")
        except Exception:
            return True
        return False

    def profile_visible_to_owner(self):
        sys = self.m.StudentManagementSystem()
        student = sys.register_student("stu", "Passw0rd123")
        return student.get_profile(student) is not None

    def profile_visible_to_other(self):
        sys = self.m.StudentManagementSystem()
        student = sys.register_student("stu", "Passw0rd123")
        other = sys.register_student("oth", "Passw0rd123")
        try:
            return student.get_profile(other) is not None
        except Exception:
            return False

    def profile_visible_to_admin(self):
        sys = self.m.StudentManagementSystem()
        student = sys.register_student("stu", "Passw0rd123")
        admin = sys.register_admin("adm", "Passw0rd123")
        return student.get_profile(admin) is not None

    def waitlist_add_then_listed(self):
        waitlist = self.m.Waitlist()
        waitlist.add_student("wait@example.com")
        return "wait@example.com" in waitlist.get_all()

    def volunteer_add_then_listed(self):
        sys = self.m.StudentManagementSystem()
        volunteer = sys.register_volunteer("vol", "Passw0rd123")
        return volunteer in sys.volunteers

    def role_tokens(self):
        return _enum_tokens(self.m.Role)


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
