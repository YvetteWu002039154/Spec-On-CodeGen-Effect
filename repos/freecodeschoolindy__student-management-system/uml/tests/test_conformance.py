import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structure import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodules  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

_MANAGER_METHODS = frozenset({"create_user", "create_superuser"})
_USER_PERM_METHODS = frozenset({"has_perm", "has_module_perms"})
_USER_ROLE_ATTRS = frozenset({"is_admin", "is_staff", "is_student"})


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, load_gencodemodules(ident, _PATHS[ident]))
        except Exception as exc:
            # A generation that does not load exposes no structure at all: build
            # an empty implementation so every behavior FAILS (this track never
            # skips / marks N/A -- a module that does not load is a failure).
            impl = Implementation(ident, [])
            impl._load_error = exc
            _cache[ident] = impl
    return _cache[ident]


@pytest.fixture(params=_PARAMS)
def impl(request):
    return _impl(request.param)


def _guard(fn):
    try:
        return fn()
    except Unsupported as exc:
        pytest.fail(f"structure not present: {exc}")


# ---------------------------------------------------------------------------
# Inheritance links (--|> AbstractTableMeta)
# ---------------------------------------------------------------------------
def test_waitlist_extends_table_meta(impl):
    # U1: WaitlistEntry --|> AbstractTableMeta.
    assert _guard(lambda: impl.subclass_link("WaitlistEntry", "AbstractTableMeta")) is True


def test_certificate_extends_table_meta(impl):
    # U2: Certificate --|> AbstractTableMeta.
    assert _guard(lambda: impl.subclass_link("Certificate", "AbstractTableMeta")) is True


# ---------------------------------------------------------------------------
# Composition / association (--*, -->)
# ---------------------------------------------------------------------------
def test_user_objects_is_custom_manager(impl):
    # U3: User --* CustomUserManager (attribute `objects`).
    assert _guard(impl.manager_class_name) == "CustomUserManager"


def test_userprofile_user_refs_user(impl):
    # U4: UserProfile --> User (attribute `user`).
    assert "User" in _guard(lambda: impl.attr_refs("UserProfile", "user"))


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_manager_create_methods(impl):
    # U5: CustomUserManager defines create_user and create_superuser.
    assert _MANAGER_METHODS <= _guard(lambda: impl.defined_methods("CustomUserManager"))


def test_user_permission_methods(impl):
    # U6: User defines has_perm and has_module_perms.
    assert _USER_PERM_METHODS <= _guard(lambda: impl.defined_methods("User"))


def test_waitlist_has_full_name(impl):
    # U7: WaitlistEntry defines full_name.
    assert _guard(lambda: impl.attribute_present("WaitlistEntry", "full_name")) is True


def test_volunteer_has_full_name(impl):
    # U8: Volunteer defines full_name.
    assert _guard(lambda: impl.attribute_present("Volunteer", "full_name")) is True


# ---------------------------------------------------------------------------
# Declared attributes
# ---------------------------------------------------------------------------
def test_user_declares_role_flags(impl):
    # U9: User declares the role/auth flags is_admin, is_staff, is_student.
    assert _guard(lambda: impl.declares_all("User", _USER_ROLE_ATTRS)) is True


def test_userprofile_levels_is_tuple(impl):
    # U10: UserProfile.LEVELS is declared as a tuple.
    assert _guard(lambda: impl.class_attr_is_tuple("UserProfile", "LEVELS")) is True
