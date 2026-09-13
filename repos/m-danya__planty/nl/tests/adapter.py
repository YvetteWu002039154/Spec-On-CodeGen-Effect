"""Per-model behavioral drivers for `planty` NL track.

One driver per model, written by reading that model's run0 source. Nothing is
searched: each names the concrete classes, methods and completion flag its
generation actually uses.

The four run0 generations split into two shapes:

  claude    plain objects. Task(title).complete()/.reopen(); done is
            `task.status is TaskStatus.DONE`. Container is Project.add_task /
            .remove_task(task_id) / .get_all_tasks().
  gpt       a facade with integer ids. Planty().create_task(content),
            .complete_task(id)/.reopen_task(id); done is `task.status is
            Status.DONE`. Container is create_project + list_tasks(project_id=).
  deepseek  plain objects; Task.is_completed is a @property, and get_all_tasks()
            yields an iterator.
            Container is Project.add_task/.remove_task taking the TASK object.
  gemini    plain objects, boolean attribute: task.is_completed. Container is
            Project.add_task/.remove_task; get_tasks() hides completed ones by
            default, so the count is read with include_completed=True.

Return shapes match test_conformance.py's asserts.
"""

TITLE = "Write thesis"


class _Base:
    def __init__(self, module):
        self.m = module

    # N7 — the scale's level count, not its vocabulary (P1..P4 vs LOW..URGENT)
    def priority_level_count(self):
        return len(list(self.m.Priority))


class ClaudeDriver(_Base):
    """Task/Project objects; completion is a TaskStatus enum on the task."""

    def _task(self):
        return self.m.Task(TITLE)

    def created_task_title(self, title):
        return self.m.Task(title).title

    def new_task_is_completed(self):
        return self._task().status is self.m.TaskStatus.DONE

    def completed_after_complete(self):
        t = self._task()
        t.complete()
        return t.status is self.m.TaskStatus.DONE

    def open_after_reopen(self):
        t = self._task()
        t.complete()
        t.reopen()
        return t.status is self.m.TaskStatus.DONE

    def container_count_after_add(self):
        p = self.m.Project("Inbox")
        p.add_task(self._task())
        return len(p.get_all_tasks())

    def container_count_after_remove(self):
        p = self.m.Project("Inbox")
        t = self._task()
        p.add_task(t)
        p.remove_task(t.id)          # keyed by id, not the object
        return len(p.get_all_tasks())


class GptDriver(_Base):
    """A Planty facade over integer ids; tasks are looked up, not held."""

    def _app(self):
        return self.m.Planty()

    def created_task_title(self, title):
        return self._app().create_task(title).content     # 'content', not 'title'

    def new_task_is_completed(self):
        app = self._app()
        return app.create_task(TITLE).status is self.m.Status.DONE

    def completed_after_complete(self):
        app = self._app()
        t = app.create_task(TITLE)
        return app.complete_task(t.id).status is self.m.Status.DONE

    def open_after_reopen(self):
        app = self._app()
        t = app.create_task(TITLE)
        app.complete_task(t.id)
        return app.reopen_task(t.id).status is self.m.Status.DONE

    def container_count_after_add(self):
        app = self._app()
        p = app.create_project("Work")
        app.create_task(TITLE, project_id=p.id)
        return len(app.list_tasks(project_id=p.id))

    def container_count_after_remove(self):
        app = self._app()
        p = app.create_project("Work")
        t = app.create_task(TITLE, project_id=p.id)
        app.delete_task(t.id)
        return len(app.list_tasks(project_id=p.id))


class DeepseekDriver(_Base):
    """Plain objects. `is_completed` is a @property, not a method, and
    Project.get_all_tasks() yields an iterator rather than a list. Container
    removal takes the task OBJECT."""

    def created_task_title(self, title):
        return self.m.Task(title).title

    def new_task_is_completed(self):
        return self.m.Task(TITLE).is_completed

    def completed_after_complete(self):
        t = self.m.Task(TITLE)
        t.complete()
        return t.is_completed

    def open_after_reopen(self):
        t = self.m.Task(TITLE)
        t.complete()
        t.uncomplete()
        return t.is_completed

    def container_count_after_add(self):
        p = self.m.Project("Inbox")
        p.add_task(self.m.Task(TITLE))
        return len(list(p.get_all_tasks()))

    def container_count_after_remove(self):
        p = self.m.Project("Inbox")
        t = self.m.Task(TITLE)
        p.add_task(t)
        p.remove_task(t)
        return len(list(p.get_all_tasks()))


class GeminiDriver(_Base):
    """Plain objects; completion is a bool attribute. Project.get_tasks() hides
    completed tasks unless include_completed=True, so the count asks for all."""

    def created_task_title(self, title):
        return self.m.Task(title).title

    def new_task_is_completed(self):
        return self.m.Task(TITLE).is_completed

    def completed_after_complete(self):
        t = self.m.Task(TITLE)
        t.complete()
        return t.is_completed

    def open_after_reopen(self):
        t = self.m.Task(TITLE)
        t.complete()
        t.uncomplete()
        return t.is_completed

    def container_count_after_add(self):
        p = self.m.Project("Inbox")
        p.add_task(self.m.Task(TITLE))
        return len(p.get_tasks(include_completed=True))

    def container_count_after_remove(self):
        p = self.m.Project("Inbox")
        t = self.m.Task(TITLE)
        p.add_task(t)
        p.remove_task(t)
        return len(p.get_tasks(include_completed=True))


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
