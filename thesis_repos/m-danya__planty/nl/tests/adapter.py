# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def created_task_title(self, title):
        return self.m.Task(title=title).title

    def new_task_is_completed(self):
        return self.m.Task(title="Sample task").is_completed()

    def completed_after_complete(self):
        task = self.m.Task(title="Sample task")
        task.complete()
        return task.is_completed()

    def open_after_reopen(self):
        task = self.m.Task(title="Sample task")
        task.complete()
        task.reopen()
        return task.is_completed()

    def container_count_after_add(self):
        project = self.m.Project(name="Container")
        project.add_task(self.m.Task(title="Grouped task"))
        return len(project.tasks)

    def container_count_after_remove(self):
        project = self.m.Project(name="Container")
        task = self.m.Task(title="Grouped task")
        project.add_task(task)
        project.remove_task(task.id)
        return len(project.tasks)

    def priority_level_count(self):
        return len(list(self.m.Priority))


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def created_task_title(self, title):
        return self.m.Planty().create_task(title).content

    def new_task_is_completed(self):
        app = self.m.Planty()
        task = app.create_task("Sample task")
        return app.get_task(task.id).status == self.m.Status.DONE

    def completed_after_complete(self):
        app = self.m.Planty()
        task = app.create_task("Sample task")
        app.complete_task(task.id)
        return app.get_task(task.id).status == self.m.Status.DONE

    def open_after_reopen(self):
        app = self.m.Planty()
        task = app.create_task("Sample task")
        app.complete_task(task.id)
        app.reopen_task(task.id)
        return app.get_task(task.id).status == self.m.Status.DONE

    def container_count_after_add(self):
        app = self.m.Planty()
        pid = app.create_project("Container").id
        app.create_task("Grouped task", project_id=pid)
        return len(app.list_tasks(project_id=pid))

    def container_count_after_remove(self):
        app = self.m.Planty()
        pid = app.create_project("Container").id
        task = app.create_task("Grouped task", project_id=pid)
        app.delete_task(task.id)
        return len(app.list_tasks(project_id=pid))

    def priority_level_count(self):
        return len(list(self.m.Priority))


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def created_task_title(self, title):
        return self.m.Task(title).title

    def new_task_is_completed(self):
        return self.m.Task("Sample task").is_completed

    def completed_after_complete(self):
        task = self.m.Task("Sample task")
        task.complete()
        return task.is_completed

    def open_after_reopen(self):
        task = self.m.Task("Sample task")
        task.complete()
        task.uncomplete()
        return task.is_completed

    def container_count_after_add(self):
        project = self.m.Project("Container")
        project.add_task(self.m.Task("Grouped task"))
        return len(list(project.get_all_tasks()))

    def container_count_after_remove(self):
        project = self.m.Project("Container")
        task = self.m.Task("Grouped task")
        project.add_task(task)
        project.remove_task(task)
        return len(list(project.get_all_tasks()))

    def priority_level_count(self):
        return len(list(self.m.Priority))


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def created_task_title(self, title):
        return self.m.Task(title).title

    def new_task_is_completed(self):
        return self.m.Task("Sample task").is_completed

    def completed_after_complete(self):
        task = self.m.Task("Sample task")
        task.complete()
        return task.is_completed

    def open_after_reopen(self):
        task = self.m.Task("Sample task")
        task.complete()
        task.uncomplete()
        return task.is_completed

    def container_count_after_add(self):
        project = self.m.Project("Container")
        project.add_task(self.m.Task("Grouped task"))
        return len(project.get_tasks(include_completed=True))

    def container_count_after_remove(self):
        project = self.m.Project("Container")
        task = self.m.Task("Grouped task")
        project.add_task(task)
        project.remove_task(task)
        return len(project.get_tasks(include_completed=True))

    def priority_level_count(self):
        return len(list(self.m.Priority))


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
