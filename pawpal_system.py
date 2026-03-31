"""
pawpal_system.py — PawPal+ logic layer.

Contains all backend classes for the pet care scheduling system.
UML (Mermaid) is documented inline below for reference.

classDiagram
    class Owner {
        +str name
        +int available_minutes
        +list~str~ preferences
        +add_pet(pet)
        +get_pets() list
        +set_availability(minutes)
        +get_all_tasks() list
    }
    class Pet {
        +str name
        +str species
        +int age
        +list~str~ special_needs
        +add_task(task)
        +remove_task(title)
        +get_tasks() list
    }
    class Task {
        +str title
        +int duration_minutes
        +str priority
        +str category
        +str notes
        +bool completed
        +mark_complete()
    }
    class ScheduledTask {
        +Task task
        +str start_time
        +str reason
    }
    class DailyPlan {
        +str date
        +list~ScheduledTask~ scheduled_tasks
        +int total_time_used
        +list~Task~ unscheduled_tasks
        +display() str
        +get_summary() dict
    }
    class Scheduler {
        +Owner owner
        +Pet pet
        +generate_schedule(date) DailyPlan
        +explain_plan(plan) str
        +filter_by_priority(priority) list
        +sort_tasks() list
    }
    Owner "1" --> "1..*" Pet : owns
    Pet "1" --> "0..*" Task : has
    Scheduler --> Owner : uses
    Scheduler --> Pet : manages
    Scheduler --> DailyPlan : produces
    DailyPlan --> ScheduledTask : contains
    ScheduledTask --> Task : wraps
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PRIORITIES = ("low", "medium", "high")
VALID_CATEGORIES = ("walk", "feeding", "meds", "grooming", "enrichment", "other")
VALID_FREQUENCIES = ("once", "daily", "weekly")


# ---------------------------------------------------------------------------
# Data objects (dataclasses)
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet care activity with duration, priority, and completion state."""

    title: str
    duration_minutes: int
    priority: str           # "low" | "medium" | "high"
    category: str           # "walk" | "feeding" | "meds" | "grooming" | "enrichment" | "other"
    notes: str = ""
    completed: bool = False
    frequency: str = "once"
    due_date: str = ""

    def mark_complete(self) -> Optional["Task"]:
        """Mark done; return next Task if recurring, else None."""
        self.completed = True
        if self.frequency == "once":
            return None
        from datetime import date, timedelta
        base = date.fromisoformat(self.due_date) if self.due_date else date.today()
        delta = timedelta(days=1) if self.frequency == "daily" else timedelta(weeks=1)
        return Task(self.title, self.duration_minutes, self.priority,
                    self.category, self.notes, False, self.frequency,
                    str(base + delta))


@dataclass
class ScheduledTask:
    """A Task placed into a daily plan with an assigned start time and scheduling reason."""

    task: Task
    start_time: str         # e.g. "08:00"
    reason: str             # plain-English explanation for why this task was scheduled


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------

class Pet:
    """Represents a pet and the list of care tasks associated with it."""

    def __init__(
        self,
        name: str,
        species: str,
        age: int,
        special_needs: Optional[list[str]] = None,
    ) -> None:
        self.name = name
        self.species = species
        self.age = age
        self.special_needs: list[str] = special_needs or []
        self._tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Append a care task to this pet's task list."""
        self._tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove the first task whose title matches (case-insensitive)."""
        self._tasks = [t for t in self._tasks if t.title.lower() != title.lower()]

    def get_tasks(self) -> list[Task]:
        """Return a copy of all tasks assigned to this pet."""
        return list(self._tasks)

    def __repr__(self) -> str:
        return f"Pet(name={self.name!r}, species={self.species!r}, age={self.age})"


class Owner:
    """Represents the pet owner, their daily time budget, and their pets."""

    def __init__(
        self,
        name: str,
        available_minutes: int = 120,
        preferences: Optional[list[str]] = None,
    ) -> None:
        self.name = name
        self.available_minutes = available_minutes   # total daily minutes for pet care
        self.preferences: list[str] = preferences or []
        self._pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self._pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets owned."""
        return list(self._pets)

    def set_availability(self, minutes: int) -> None:
        """Update the owner's daily available minutes for pet care."""
        self.available_minutes = minutes

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return every (pet, task) pair across all owned pets."""
        return [(pet, task) for pet in self._pets for task in pet.get_tasks()]

    def __repr__(self) -> str:
        return f"Owner(name={self.name!r}, available_minutes={self.available_minutes})"


# ---------------------------------------------------------------------------
# Plan / output objects
# ---------------------------------------------------------------------------

@dataclass
class DailyPlan:
    """The scheduler's output: an ordered list of scheduled tasks plus skipped ones."""

    date: str
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    total_time_used: int = 0                              # minutes
    unscheduled_tasks: list[Task] = field(default_factory=list)

    def display(self) -> str:
        """Return a formatted, human-readable schedule string for terminal output."""
        lines: list[str] = []
        lines.append(f"{'=' * 52}")
        lines.append(f"  PawPal+ Daily Schedule — {self.date}")
        lines.append(f"{'=' * 52}")

        if not self.scheduled_tasks:
            lines.append("  No tasks scheduled.")
        else:
            for st in self.scheduled_tasks:
                t = st.task
                status = "[done]" if t.completed else "[ ]"
                lines.append(
                    f"  {status} {st.start_time}  {t.title:<28}"
                    f" {t.duration_minutes:>3} min  [{t.priority}]"
                )
                if st.reason:
                    lines.append(f"           -> {st.reason}")

        lines.append(f"{'-' * 52}")
        lines.append(f"  Total time used : {self.total_time_used} min")

        if self.unscheduled_tasks:
            lines.append(f"  Skipped ({len(self.unscheduled_tasks)})      : "
                         + ", ".join(t.title for t in self.unscheduled_tasks))

        lines.append(f"{'=' * 52}")
        return "\n".join(lines)

    def get_summary(self) -> dict:
        """Return a dict with total_tasks, time_used, and tasks_skipped counts."""
        return {
            "total_tasks": len(self.scheduled_tasks),
            "time_used": self.total_time_used,
            "tasks_skipped": len(self.unscheduled_tasks),
        }


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Core scheduling logic.

    Retrieves tasks from the Owner's pets, sorts them by priority and duration,
    then greedily fits them into the owner's daily time budget to produce a DailyPlan.
    """

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
    DEFAULT_START_HOUR = 8   # schedules begin at 08:00

    def __init__(self, owner: Owner, pet: Pet) -> None:
        self.owner = owner
        self.pet = pet

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _minutes_to_time(self, total_minutes: int) -> str:
        """Convert an offset in minutes from DEFAULT_START_HOUR into an HH:MM string."""
        hour = self.DEFAULT_START_HOUR + total_minutes // 60
        minute = total_minutes % 60
        return f"{hour:02d}:{minute:02d}"

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert an 'HH:MM' string to total minutes from midnight."""
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sort_tasks(self) -> list[Task]:
        """Sort pet tasks by priority (high first), then by duration (shortest first)."""
        return sorted(
            self.pet.get_tasks(),
            key=lambda t: (self.PRIORITY_ORDER.get(t.priority, 99), t.duration_minutes),
        )

    def filter_by_priority(self, priority: str) -> list[Task]:
        """Return only the pet's tasks that match the given priority level."""
        return [t for t in self.pet.get_tasks() if t.priority == priority]

    def generate_schedule(self, date: str = "") -> DailyPlan:
        """
        Build a DailyPlan using a greedy algorithm.

        Sorts tasks (high priority first, shortest-first tiebreaker), then adds
        each task to the plan while the remaining time budget allows it.
        Tasks that do not fit are recorded in DailyPlan.unscheduled_tasks.
        """
        from datetime import date as _date

        if not date:
            date = str(_date.today())

        plan = DailyPlan(date=date)
        remaining = self.owner.available_minutes
        elapsed = 0   # minutes since DEFAULT_START_HOUR

        for task in self.sort_tasks():
            if task.duration_minutes <= remaining:
                start = self._minutes_to_time(elapsed)
                reason = (
                    f"Priority '{task.priority}' task fits within remaining "
                    f"{remaining} min budget."
                )
                plan.scheduled_tasks.append(ScheduledTask(task, start, reason))
                elapsed += task.duration_minutes
                remaining -= task.duration_minutes
                plan.total_time_used += task.duration_minutes
            else:
                plan.unscheduled_tasks.append(task)

        return plan

    def explain_plan(self, plan: DailyPlan) -> str:
        """Return a plain-English explanation of why the plan was built the way it was."""
        lines: list[str] = []
        lines.append(
            f"For {self.pet.name} on {plan.date}, {len(plan.scheduled_tasks)} task(s) "
            f"were scheduled using {plan.total_time_used} of "
            f"{self.owner.available_minutes} available minutes."
        )

        if plan.scheduled_tasks:
            lines.append("Scheduled tasks (in order):")
            for st in plan.scheduled_tasks:
                lines.append(
                    f"  • {st.start_time} — {st.task.title} "
                    f"({st.task.duration_minutes} min, {st.task.priority} priority)"
                )

        if plan.unscheduled_tasks:
            names = ", ".join(t.title for t in plan.unscheduled_tasks)
            lines.append(
                f"Skipped due to insufficient time: {names}. "
                "Consider increasing available minutes or removing lower-priority tasks."
            )
        else:
            lines.append("All tasks fit within the available time budget.")

        return "\n".join(lines)

    def sort_by_time(self, plan: DailyPlan) -> list[ScheduledTask]:
        """Sort ScheduledTasks in the plan chronologically by start time."""
        return sorted(plan.scheduled_tasks, key=lambda s: self._time_to_minutes(s.start_time))

    def filter_tasks(self, completed: Optional[bool] = None) -> list[Task]:
        """Return pet tasks filtered by completion status; None returns all."""
        tasks = self.pet.get_tasks()
        if completed is None:
            return tasks
        return [t for t in tasks if t.completed == completed]

    def detect_conflicts(self, plan: DailyPlan) -> list[str]:
        """Return warning strings for any ScheduledTasks whose time windows overlap."""
        warnings: list[str] = []
        items = plan.scheduled_tasks
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                sa = self._time_to_minutes(a.start_time)
                sb = self._time_to_minutes(b.start_time)
                if sa < sb + b.task.duration_minutes and sb < sa + a.task.duration_minutes:
                    warnings.append(
                        f"'{a.task.title}' ({a.start_time}, {a.task.duration_minutes} min)"
                        f" overlaps '{b.task.title}' ({b.start_time}, {b.task.duration_minutes} min)"
                    )
        return warnings
