"""Structure-conformance suite for `planty` (m-danya__planty) **UML track**.

One shared test body runs against the 4 UML generations, via the adapter.
Expected structure comes only from CONTRACT.md, derived from the
class diagram `uml/input/classes.puml` (a pyreverse extraction of the `planty`
package) and grounded in the origin `planty/domain/task.py`. The diagram records
three kinds of fact — inheritance links (`--|>`), association links
(`--> : attr`), and the methods under a class — and each test pins one (Un). A
class/attribute a generation omits is a FAILURE, as is a present-but-wrong
link/method; this track does not skip / mark N/A.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

# The five pure-domain entities the diagram draws `--|> Entity` from.
_DOMAIN_ENTITIES = ("Task", "Section", "User", "RecurrenceInfo", "Attachment")

# The completion/archive method set the diagram lists under Task.
_TASK_LIFECYCLE = frozenset({"mark_completed", "toggle_completed", "archive",
                             "unarchive"})
# The membership method set the diagram lists under Section.
_SECTION_MEMBERSHIP = frozenset({"insert_task", "remove_task",
                                 "insert_subsection", "remove_subsection"})


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, [load_gencodemodule(ident, _PATHS[ident])])
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
# Inheritance links (--|>)
# ---------------------------------------------------------------------------
def test_domain_entities_share_common_base(impl):
    # U1: Task/Section/User/RecurrenceInfo/Attachment all --|> a common Entity base.
    # Asserted on convergence (they share a base class), not its literal name.
    assert _guard(lambda: impl.common_ancestor_names(_DOMAIN_ENTITIES))


def test_task_specializes_entity(impl):
    # U2: Task --|> Entity.
    assert _guard(lambda: impl.subclass_link("Task", "Entity")) is True


def test_section_specializes_entity(impl):
    # U3: Section --|> Entity.
    assert _guard(lambda: impl.subclass_link("Section", "Entity")) is True


# ---------------------------------------------------------------------------
# Association links (--> : attr)
# ---------------------------------------------------------------------------
def test_section_tasks_refs_task(impl):
    # U4: Section --> Task (attribute `tasks : list[Task]`).
    assert "Task" in _guard(lambda: impl.attr_refs("Section", "tasks"))


def test_section_subsections_refs_section(impl):
    # U5: Section --> Section (attribute `subsections : list['Section']`).
    assert "Section" in _guard(lambda: impl.attr_refs("Section", "subsections"))


def test_task_attachments_refs_attachment(impl):
    # U6: Task --> Attachment (attribute `attachments : Optional[list['Attachment']]`).
    assert "Attachment" in _guard(lambda: impl.attr_refs("Task", "attachments"))


def test_task_recurrence_refs_recurrence_info(impl):
    # U7: Task --> RecurrenceInfo (attribute `recurrence : Optional[RecurrenceInfo]`).
    assert "RecurrenceInfo" in _guard(lambda: impl.attr_refs("Task", "recurrence"))


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_task_lifecycle_methods(impl):
    # U8: Task carries the completion/archive set
    #     mark_completed / toggle_completed / archive / unarchive.
    assert _TASK_LIFECYCLE <= _guard(lambda: impl.methods("Task"))


def test_task_attachment_methods(impl):
    # U9: Task carries add_attachment and remove_attachment.
    assert {"add_attachment", "remove_attachment"} <= _guard(lambda: impl.methods("Task"))


def test_section_membership_methods(impl):
    # U10: Section carries the task/subsection membership set
    #      insert_task / remove_task / insert_subsection / remove_subsection.
    assert _SECTION_MEMBERSHIP <= _guard(lambda: impl.methods("Section"))
