"""
tests/test_pawpal.py — Unit tests for PawPal+ core logic.

Run with:  python3 -m pytest tests/ -v
"""

import pytest
from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler, DailyPlan, ScheduledTask


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_task():
    """A basic high-priority walk task."""
    return Task(title="Morning walk", duration_minutes=30, priority="high", category="walk")


@pytest.fixture
def pet_with_tasks():
    """A Pet pre-loaded with four tasks of mixed priority."""
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task("Morning walk",  30, "high",   "walk"))
    pet.add_task(Task("Breakfast",     10, "high",   "feeding"))
    pet.add_task(Task("Fetch session", 20, "medium", "enrichment"))
    pet.add_task(Task("Bath time",     40, "low",    "grooming"))
    return pet


@pytest.fixture
def owner():
    """An Owner with 60 minutes available."""
    return Owner(name="Jordan", available_minutes=60)


# ── Task tests ────────────────────────────────────────────────────────────────

def test_mark_complete_changes_status(sample_task):
    """mark_complete() should flip completed from False to True."""
    assert sample_task.completed is False
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_mark_complete_is_idempotent(sample_task):
    """Calling mark_complete() twice should leave the task completed."""
    sample_task.mark_complete()
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_once_task_returns_none_on_complete(sample_task):
    """mark_complete() on a one-time task should return None."""
    result = sample_task.mark_complete()
    assert result is None


def test_daily_recurring_task_creates_next_occurrence():
    """mark_complete() on a daily task should return a new task due tomorrow."""
    today     = str(date.today())
    tomorrow  = str(date.today() + timedelta(days=1))
    task = Task("Medication", 5, "high", "meds", frequency="daily", due_date=today)
    next_t = task.mark_complete()
    assert task.completed is True
    assert next_t is not None
    assert next_t.due_date == tomorrow
    assert next_t.completed is False
    assert next_t.title == "Medication"
    assert next_t.frequency == "daily"


def test_weekly_recurring_task_creates_next_occurrence():
    """mark_complete() on a weekly task should return a task due in 7 days."""
    today      = str(date.today())
    next_week  = str(date.today() + timedelta(weeks=1))
    task = Task("Bath", 30, "low", "grooming", frequency="weekly", due_date=today)
    next_t = task.mark_complete()
    assert next_t is not None
    assert next_t.due_date == next_week


# ── Pet tests ─────────────────────────────────────────────────────────────────

def test_add_task_increases_count():
    """Adding a task should increase the pet's task count by 1."""
    pet = Pet(name="Luna", species="cat", age=5)
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task("Medication", 5, "high", "meds"))
    assert len(pet.get_tasks()) == 1


def test_add_multiple_tasks(pet_with_tasks):
    """Pet should hold all four tasks that were added."""
    assert len(pet_with_tasks.get_tasks()) == 4


def test_remove_task_decreases_count(pet_with_tasks):
    """Removing a task by title should decrease the count by 1."""
    before = len(pet_with_tasks.get_tasks())
    pet_with_tasks.remove_task("Bath time")
    assert len(pet_with_tasks.get_tasks()) == before - 1


def test_remove_task_case_insensitive(pet_with_tasks):
    """remove_task() should match titles regardless of case."""
    pet_with_tasks.remove_task("MORNING WALK")
    titles = [t.title for t in pet_with_tasks.get_tasks()]
    assert "Morning walk" not in titles


# ── Owner tests ───────────────────────────────────────────────────────────────

def test_owner_add_pet(owner):
    """add_pet() should register the pet and make it retrievable."""
    pet = Pet("Mochi", "dog", 3)
    owner.add_pet(pet)
    assert pet in owner.get_pets()


def test_owner_set_availability(owner):
    """set_availability() should update the available_minutes attribute."""
    owner.set_availability(45)
    assert owner.available_minutes == 45


def test_owner_get_all_tasks(owner, pet_with_tasks):
    """get_all_tasks() should return one (pet, task) tuple per task."""
    owner.add_pet(pet_with_tasks)
    pairs = owner.get_all_tasks()
    assert len(pairs) == len(pet_with_tasks.get_tasks())
    for pet, task in pairs:
        assert isinstance(task, Task)


# ── Scheduler: sort & filter ──────────────────────────────────────────────────

def test_scheduler_sort_tasks_high_first(owner, pet_with_tasks):
    """sort_tasks() should place high-priority tasks before medium and low."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    priorities = [t.priority for t in scheduler.sort_tasks()]
    seen_non_high = False
    for p in priorities:
        if p != "high":
            seen_non_high = True
        if seen_non_high:
            assert p != "high"


def test_sort_by_time_returns_chronological_order(owner):
    """sort_by_time() should order ScheduledTasks by start_time string."""
    pet = Pet("T", "dog", 1)
    scheduler = Scheduler(owner=owner, pet=pet)
    plan = DailyPlan(date="2026-03-31")
    plan.scheduled_tasks = [
        ScheduledTask(Task("C", 10, "low",    "other"),   "10:30", ""),
        ScheduledTask(Task("A", 10, "high",   "walk"),    "08:00", ""),
        ScheduledTask(Task("B", 10, "medium", "feeding"), "09:15", ""),
    ]
    times = [s.start_time for s in scheduler.sort_by_time(plan)]
    assert times == ["08:00", "09:15", "10:30"]


def test_filter_tasks_by_completion(owner, pet_with_tasks):
    """filter_tasks() should split tasks correctly by completed status."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    pet_with_tasks.get_tasks()[0].mark_complete()   # complete first task
    done    = scheduler.filter_tasks(completed=True)
    pending = scheduler.filter_tasks(completed=False)
    assert len(done) == 1
    assert len(pending) == 3


def test_filter_by_priority(owner, pet_with_tasks):
    """filter_by_priority('high') should return only high-priority tasks."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    high = scheduler.filter_by_priority("high")
    assert all(t.priority == "high" for t in high)
    assert len(high) == 2


# ── Scheduler: schedule generation ───────────────────────────────────────────

def test_scheduler_generates_plan(owner, pet_with_tasks):
    """generate_schedule() should return a DailyPlan with the correct date."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    plan = scheduler.generate_schedule(date="2026-03-31")
    assert isinstance(plan, DailyPlan)
    assert plan.date == "2026-03-31"


def test_scheduler_respects_time_budget(owner, pet_with_tasks):
    """Total time used must not exceed available minutes."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    plan = scheduler.generate_schedule()
    assert plan.total_time_used <= owner.available_minutes


def test_scheduler_skips_tasks_that_dont_fit():
    """Tasks exceeding the remaining budget should appear in unscheduled_tasks."""
    owner = Owner(name="Alex", available_minutes=10)
    pet   = Pet("Buddy", "dog", 2)
    pet.add_task(Task("Long walk", 60, "high", "walk"))
    plan  = Scheduler(owner=owner, pet=pet).generate_schedule()
    assert len(plan.unscheduled_tasks) == 1
    assert plan.scheduled_tasks == []


# ── Scheduler: conflict detection ─────────────────────────────────────────────

def test_detect_conflicts_flags_overlapping_tasks(owner):
    """detect_conflicts() should flag two tasks whose windows overlap."""
    pet = Pet("T", "dog", 1)
    scheduler = Scheduler(owner=owner, pet=pet)
    plan = DailyPlan(date="2026-03-31")
    plan.scheduled_tasks = [
        ScheduledTask(Task("Walk", 30, "high", "walk"),    "09:00", ""),
        ScheduledTask(Task("Bath", 20, "low",  "grooming"), "09:15", ""),  # overlaps
    ]
    conflicts = scheduler.detect_conflicts(plan)
    assert len(conflicts) == 1
    assert "Walk" in conflicts[0] and "Bath" in conflicts[0]


def test_no_conflicts_in_sequential_plan(owner, pet_with_tasks):
    """A plan built by generate_schedule() should never contain conflicts."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    plan = scheduler.generate_schedule()
    assert scheduler.detect_conflicts(plan) == []


# ── DailyPlan ─────────────────────────────────────────────────────────────────

def test_daily_plan_get_summary(owner, pet_with_tasks):
    """get_summary() should return a dict with the correct keys and values."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    plan = scheduler.generate_schedule()
    summary = plan.get_summary()
    assert set(summary) == {"total_tasks", "time_used", "tasks_skipped"}
    assert summary["total_tasks"] == len(plan.scheduled_tasks)
    assert summary["time_used"]   == plan.total_time_used


def test_explain_plan_is_non_empty_string(owner, pet_with_tasks):
    """explain_plan() should return a non-empty string."""
    scheduler = Scheduler(owner=owner, pet=pet_with_tasks)
    plan = scheduler.generate_schedule()
    assert isinstance(scheduler.explain_plan(plan), str)
    assert len(scheduler.explain_plan(plan)) > 0
