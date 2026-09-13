import json
import datetime
import uuid
from typing import List, Optional, Dict, Any


class Task:
    """Represents a single task in Planty."""
    def __init__(self, title: str, description: str = "", due_date: Optional[datetime.datetime] = None,
                 priority: int = 1, completed: bool = False, tags: Optional[List[str]] = None,
                 parent: Optional['Task'] = None) -> None:
        if not title:
            raise ValueError("Title cannot be empty")
        if priority not in (1, 2, 3, 4):
            raise ValueError("Priority must be 1, 2, 3, or 4")
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[datetime.datetime] = due_date
        self.priority: int = priority
        self.completed: bool = completed
        self.tags: List[str] = tags if tags is not None else []
        self.subtasks: List['Task'] = []
        self.parent: Optional['Task'] = parent
        self.created_at: datetime.datetime = datetime.datetime.now()

    def add_subtask(self, title: str, **kwargs) -> 'Task':
        """Add a subtask to this task and return it."""
        subtask = Task(title=title, parent=self, **kwargs)
        self.subtasks.append(subtask)
        return subtask

    def remove_subtask(self, task_id: str) -> None:
        """Remove a subtask by its id."""
        self.subtasks = [t for t in self.subtasks if t.id != task_id]

    def mark_complete(self, recursive: bool = False) -> None:
        """Mark this task as completed. If recursive, also complete subtasks."""
        self.completed = True
        if recursive:
            for st in self.subtasks:
                st.mark_complete(recursive=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task to a dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'completed': self.completed,
            'tags': self.tags,
            'subtasks': [st.to_dict() for st in self.subtasks],
            'parent_id': self.parent.id if self.parent else None,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], parent: Optional['Task'] = None) -> 'Task':
        """Deserialize a task from a dictionary. Subtasks are built recursively."""
        due_date = data.get('due_date')
        if due_date:
            due_date = datetime.datetime.fromisoformat(due_date)
        task = cls(
            title=data['title'],
            description=data.get('description', ''),
            due_date=due_date,
            priority=data.get('priority', 1),
            completed=data.get('completed', False),
            tags=data.get('tags', []),
            parent=parent
        )
        # Override id and created_at for consistency during restore
        task.id = data['id']
        task.created_at = datetime.datetime.fromisoformat(data['created_at'])
        # Rebuild subtasks
        for sub_data in data.get('subtasks', []):
            subtask = cls.from_dict(sub_data, parent=task)
            task.subtasks.append(subtask)
        return task

    def __repr__(self) -> str:
        status = "✓" if self.completed else " "
        return f"[{status}] {self.title} (p{self.priority})"


class Project:
    """A project containing tasks."""
    def __init__(self, name: str, description: str = "") -> None:
        if not name:
            raise ValueError("Project name cannot be empty")
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.tasks: List[Task] = []
        self.created_at: datetime.datetime = datetime.datetime.now()

    def add_task(self, title: str, **kwargs) -> Task:
        """Add a task to the project and return it."""
        task = Task(title=title, **kwargs)
        self.tasks.append(task)
        return task

    def remove_task(self, task_id: str) -> None:
        """Remove a task by its id."""
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Recursively find a task by id within this project."""
        for task in self.tasks:
            if task.id == task_id:
                return task
            found = self._find_in_subtasks(task, task_id)
            if found:
                return found
        return None

    def _find_in_subtasks(self, task: Task, task_id: str) -> Optional[Task]:
        if task.id == task_id:
            return task
        for st in task.subtasks:
            found = self._find_in_subtasks(st, task_id)
            if found:
                return found
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize project to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tasks': [t.to_dict() for t in self.tasks],
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Deserialize project from dictionary."""
        project = cls(name=data['name'], description=data.get('description', ''))
        project.id = data['id']
        project.created_at = datetime.datetime.fromisoformat(data['created_at'])
        for task_data in data.get('tasks', []):
            task = Task.from_dict(task_data)
            project.tasks.append(task)
        return project

    def __repr__(self) -> str:
        active = sum(1 for t in self.tasks if not t.completed)
        return f"Project: {self.name} ({active} active tasks)"


class PlantyManager:
    """Central manager for all projects and tasks."""
    def __init__(self) -> None:
        self.inbox: Project = Project("Inbox")
        self.projects: Dict[str, Project] = {}
        self.tags: set = set()

    def add_project(self, name: str, description: str = "") -> Project:
        """Create a new project and return it."""
        project = Project(name, description)
        self.projects[project.id] = project
        return project

    def remove_project(self, project_id: str) -> None:
        """Delete a project by id. Cannot delete Inbox."""
        if project_id == self.inbox.id:
            raise ValueError("Cannot remove the Inbox project")
        if project_id in self.projects:
            del self.projects[project_id]
        else:
            raise KeyError("Project not found")

    def get_project(self, project_id: str) -> Optional[Project]:
        """Return a project by id, or None."""
        if project_id == self.inbox.id:
            return self.inbox
        return self.projects.get(project_id)

    def add_task_to_inbox(self, title: str, **kwargs) -> Task:
        """Add a task to the GTD inbox."""
        return self.inbox.add_task(title, **kwargs)

    def move_task(self, task_id: str, from_project_id: str, to_project_id: str) -> None:
        """Move a task (and its subtasks) from one project to another."""
        from_project = self.get_project(from_project_id)
        if not from_project:
            raise KeyError("Source project not found")
        to_project = self.get_project(to_project_id)
        if not to_project:
            raise KeyError("Target project not found")

        task = from_project.get_task_by_id(task_id)
        if not task:
            raise KeyError("Task not found in source project")

        # Remove from source
        # If it's a root-level task in the project
        if task in from_project.tasks:
            from_project.tasks.remove(task)
        else:
            # It's a subtask; find and remove it from its parent
            parent_task = task.parent
            if parent_task:
                parent_task.subtasks.remove(task)
            else:
                # Fallback: should not happen
                from_project.tasks = [t for t in from_project.tasks if t.id != task_id]

        # Add to target
        to_project.tasks.append(task)

    def get_all_tasks(self, completed: bool = False) -> List[Task]:
        """Return all tasks (optionally only completed ones) across all projects."""
        all_tasks = []
        all_projects = [self.inbox] + list(self.projects.values())
        for project in all_projects:
            for task in project.tasks:
                if completed or not task.completed:
                    all_tasks.append(task)
                    all_tasks.extend(self._collect_subtasks(task, completed))
        return all_tasks

    def _collect_subtasks(self, task: Task, completed: bool) -> List[Task]:
        results = []
        for st in task.subtasks:
            if completed or not st.completed:
                results.append(st)
            results.extend(self._collect_subtasks(st, completed))
        return results

    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """Find all tasks that have a specific tag."""
        return [t for t in self.get_all_tasks() if tag in t.tags]

    def get_tasks_due_before(self, date: datetime.datetime) -> List[Task]:
        """Get incomplete tasks due before a certain date."""
        return [
            t for t in self.get_all_tasks()
            if t.due_date and t.due_date <= date and not t.completed
        ]

    def save_to_file(self, filename: str) -> None:
        """Persist the entire state to a JSON file."""
        data = {
            'inbox': self.inbox.to_dict(),
            'projects': [p.to_dict() for p in self.projects.values()],
            'tags': list(self.tags)
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_file(cls, filename: str) -> 'PlantyManager':
        """Load state from a JSON file and return a new PlantyManager."""
        manager = cls()
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        manager.inbox = Project.from_dict(data['inbox'])
        for proj_data in data.get('projects', []):
            project = Project.from_dict(proj_data)
            manager.projects[project.id] = project
        manager.tags = set(data.get('tags', []))
        return manager

    def update_tags_set(self) -> None:
        """Refresh the tags set from all existing tasks."""
        all_tags = set()
        for task in self.get_all_tasks(completed=True):  # include completed for tags
            all_tags.update(task.tags)
        self.tags = all_tags


# Optional basic CLI for demonstration
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Planty - Task Management")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add project
    parser_add_project = subparsers.add_parser('add-project', help='Add a new project')
    parser_add_project.add_argument('name', help='Project name')
    parser_add_project.add_argument('--desc', default='', help='Project description')
    parser_add_project.add_argument('--file', default='planty_data.json', help='Data file')
    
    # Add task to project
    parser_add_task = subparsers.add_parser('add-task', help='Add a task to a project')
    parser_add_task.add_argument('project_id', help='Target project id (or "inbox")')
    parser_add_task.add_argument('title', help='Task title')
    parser_add_task.add_argument('--priority', type=int, choices=[1,2,3,4], default=1)
    parser_add_task.add_argument('--due', help='Due date (YYYY-MM-DD)')
    parser_add_task.add_argument('--tags', help='Comma separated tags')
    parser_add_task.add_argument('--file', default='planty_data.json', help='Data file')
    
    # List projects
    parser_list = subparsers.add_parser('list-projects', help='List all projects')
    parser_list.add_argument('--file', default='planty_data.json', help='Data file')
    
    # List tasks
    parser_list_tasks = subparsers.add_parser('list-tasks', help='List tasks in a project')
    parser_list_tasks.add_argument('project_id', nargs='?', default=None, help='Project id (omit for all)')
    parser_list_tasks.add_argument('--completed', action='store_true', help='Include completed')
    parser_list_tasks.add_argument('--file', default='planty_data.json', help='Data file')
    
    args = parser.parse_args()
    
    try:
        manager = PlantyManager.load_from_file(args.file) if args.command else PlantyManager()
    except (FileNotFoundError, json.JSONDecodeError):
        manager = PlantyManager()
    
    if args.command == 'add-project':
        proj = manager.add_project(args.name, args.desc)
        manager.save_to_file(args.file)
        print(f"Project added: {proj.name} ({proj.id})")
    
    elif args.command == 'add-task':
        pid = args.project_id if args.project_id != 'inbox' else manager.inbox.id
        due = datetime.datetime.fromisoformat(args.due) if args.due else None
        tags = [t.strip() for t in args.tags.split(',')] if args.tags else []
        proj = manager.get_project(pid)
        if not proj:
            print(f"Project {pid} not found.")
            return
        task = proj.add_task(args.title, priority=args.priority, due_date=due, tags=tags)
        manager.update_tags_set()
        manager.save_to_file(args.file)
        print(f"Task added: {task.title} ({task.id})")
    
    elif args.command == 'list-projects':
        print("Inbox:", manager.inbox.id, "-", manager.inbox.name)
        for pid, proj in manager.projects.items():
            print(f"Project: {proj.name} ({proj.id})")
    
    elif args.command == 'list-tasks':
        if args.project_id:
            pid = args.project_id if args.project_id != 'inbox' else manager.inbox.id
            proj = manager.get_project(pid)
            if not proj:
                print(f"Project {pid} not found.")
                return
            tasks = proj.tasks
            if not args.completed:
                tasks = [t for t in tasks if not t.completed]
            print(f"Tasks in {proj.name}:")
            _print_tasks(tasks, indent=0)
        else:
            all_tasks = manager.get_all_tasks(completed=args.completed)
            print("All tasks:")
            _print_tasks(all_tasks, indent=0)
    
    else:
        parser.print_help()


def _print_tasks(tasks: List[Task], indent: int = 0) -> None:
    prefix = " " * indent
    for task in tasks:
        due = f" due:{task.due_date.date()}" if task.due_date else ""
        print(f"{prefix}{task}{due}")
        if task.subtasks:
            _print_tasks(task.subtasks, indent + 2)


if __name__ == "__main__":
    main()