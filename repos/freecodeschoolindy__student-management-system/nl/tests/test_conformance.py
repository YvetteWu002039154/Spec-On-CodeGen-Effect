import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402


class _UnloadableModule:
    def __init__(self, exc):
        self._exc = exc

    def __getattr__(self, name):
        raise AttributeError(f"module did not load: {self._exc!r}")


def _load(ident, path):
    try:
        return load_gencodemodule(ident, path)
    except Exception as exc:
        return _UnloadableModule(exc)


_DRIVERS = {
    ident: build_driver(ident.split("/")[-1], _load(ident, path))
    for ident, path in gencode_paths()
}


@pytest.fixture(params=sorted(_DRIVERS))
def driver(request):
    return _DRIVERS[request.param]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def test_login_succeeds(driver):
    assert driver.login_succeeds() is True


def test_login_rejects_wrong_password(driver):
    assert driver.login_rejects_wrong_password() is True


def test_login_rejects_unknown_user(driver):
    assert driver.login_rejects_unknown_user() is True


# ---------------------------------------------------------------------------
# Private student profile
# ---------------------------------------------------------------------------
def test_profile_visible_to_owner(driver):
    assert driver.profile_visible_to_owner() is True


def test_profile_denied_to_other_user(driver):
    assert driver.profile_visible_to_other() is False


def test_profile_visible_to_admin(driver):
    assert driver.profile_visible_to_admin() is True


# ---------------------------------------------------------------------------
# Waitlist
# ---------------------------------------------------------------------------
def test_waitlist_add_then_listed(driver):
    assert driver.waitlist_add_then_listed() is True


# ---------------------------------------------------------------------------
# Volunteer management
# ---------------------------------------------------------------------------
def test_volunteer_add_then_listed(driver):
    assert driver.volunteer_add_then_listed() is True


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
def test_role_vocabulary(driver):
    assert {"student", "admin"} <= driver.role_tokens()


# ---------------------------------------------------------------------------
# Dependency usage — the description names django; does the generation
# import and use it, or hand-roll a substitute? Static (AST) check — see
# loader.dependency_used and CONTRACT.md § "Dependency usage".
# ---------------------------------------------------------------------------
_PATHS = dict(gencode_paths())


@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


# One test per named dependency rather than a @parametrize: parametrize ids
# append "-<dep>" inside the brackets, which breaks the canonical
# test_xxx[nl/<model>] id shape the step3 scorer parses.
def _assert_dependency_used(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, "
        f"so a hand-rolled substitute does not use the dependency"
    )


def test_uses_named_dependency_django(ident):
    _assert_dependency_used(ident, "django")
