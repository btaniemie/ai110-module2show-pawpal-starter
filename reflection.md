# PawPal+ Project Reflection

## 1. System Design

### Three Core User Actions

1. **Add a pet** — The owner enters basic pet info (name, species, age, any special needs) so the system knows whose care plan it is building.
2. **Add / edit care tasks** — The owner creates tasks (e.g., "morning walk", "medication") with a title, duration in minutes, priority level (low / medium / high), category, and recurrence frequency. They can also remove tasks.
3. **Generate a daily schedule** — The owner clicks "Generate" and the system produces an ordered daily plan that fits within their available time, prioritises high-priority tasks, and explains why each task was included or skipped.

**a. Initial design**

The system is built around six classes:

- **`Owner`** — stores name, daily available minutes, and care preferences. Holds a list of `Pet` objects and exposes `get_all_tasks()` to retrieve every task across all pets.
- **`Pet`** — stores name, species, age, and special needs. Responsible for maintaining a task list with `add_task()` and `remove_task()`.
- **`Task`** *(dataclass)* — a pure data object: title, duration, priority, category, notes, completion flag, recurrence frequency, and due date. `mark_complete()` returns the next occurrence `Task` if recurring, else `None`.
- **`Scheduler`** — the core logic class. Accepts an `Owner` and `Pet`, sorts and filters tasks, greedily fits them into the time budget, detects conflicts, and generates a plain-English explanation.
- **`DailyPlan`** *(dataclass)* — holds the ordered `ScheduledTask` list, total time used, and skipped tasks. `display()` renders a terminal-friendly table; `get_summary()` returns stats.
- **`ScheduledTask`** *(dataclass)* — wraps a `Task` with an assigned `start_time` string and a `reason` explaining the scheduling decision.

**b. Design changes**

Two changes were made after the initial skeleton:

1. **Added `frequency` and `due_date` to `Task`** — The initial design had no notion of recurrence. Once recurring tasks were added to the requirements, it was cleaner to store the frequency on the `Task` itself (rather than a separate `RecurringTask` subclass) so the scheduler didn't need to branch on type. `mark_complete()` was changed from `-> None` to `-> Optional[Task]` to return the pre-populated next occurrence.

2. **Added `sort_by_time`, `filter_tasks`, and `detect_conflicts` to `Scheduler`** — The original scheduler only sorted by priority for *generation*. Displaying the plan chronologically and surfacing overlap warnings were added as separate methods rather than baking them into `generate_schedule()`, keeping each method focused on a single responsibility.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers two constraints:
- **Time budget** — the owner's `available_minutes` is a hard cap; no task is added that would exceed it.
- **Task priority** — tasks are sorted high → medium → low before the greedy pass, so important tasks are never bumped by lower-priority ones.

Duration is used as a secondary sort key (shortest first within the same priority) to maximise the number of tasks that fit. Priority was treated as the dominant constraint because missing a medication is more harmful than skipping a bath.

**b. Tradeoffs**

The scheduler uses **greedy selection by priority + duration** rather than an optimal knapsack solver. This means a large high-priority task can block several smaller medium-priority tasks that would collectively provide more total value. For example, a 50-minute "grooming" (high) could crowd out a 10-minute "feeding" and 15-minute "enrichment" (both medium) when only 60 minutes are available.

This tradeoff is reasonable because pet care tasks are not interchangeable — a medication at high priority genuinely cannot be substituted by two enrichment tasks. The greedy approach also runs in O(n log n) and is easy to explain to users ("we scheduled your most important tasks first"), which matters for trust in an AI-assisted tool.

The conflict detection strategy takes a similar lightweight approach: it checks for exact time-window overlap between any two scheduled tasks and emits a warning rather than crashing or rescheduling. This is intentional — the scheduler itself never produces conflicts, so the detector exists to catch manual edits or future multi-pet scheduling scenarios.

---

## 3. AI Collaboration

**a. How you used AI**

AI was used across four phases:
- **Design brainstorming** — generating the initial Mermaid UML diagram and translating it into Python class skeletons with dataclasses.
- **Implementation scaffolding** — drafting method bodies for `generate_schedule()`, `display()`, and `explain_plan()` from the docstrings and algorithm description.
- **Test generation** — producing pytest fixtures and test functions covering happy paths and edge cases (empty pets, budget-busting tasks, overlapping time windows).
- **UI wiring** — generating the Streamlit `session_state` pattern for persisting the `Owner` object across reruns, and the three-tab layout structure.

The most effective prompts were ones that shared the existing code and asked for a *specific, scoped* addition ("add `detect_conflicts` to `Scheduler` that returns warning strings") rather than open-ended rewrites.

**b. Judgment and verification**

The AI initially generated `mark_complete()` as a `void` method that simply set `self.completed = True`. When recurring task logic was introduced, the AI suggested a separate `RecurringTask` subclass with its own `generate_next()` method. I rejected this because it would have required the scheduler to type-check every task and duplicated most of `Task`'s fields. Instead I kept `Task` flat and changed `mark_complete()` to return `Optional[Task]`, which was verified by running the `test_daily_recurring_task_creates_next_occurrence` test and checking the returned object's `due_date` against `date.today() + timedelta(days=1)`.

---

## 4. Testing and Verification

**a. What you tested**

23 tests covering:
- `mark_complete()` state change, idempotency, one-time return value, daily recurrence (+1 day), weekly recurrence (+7 days)
- `Pet.add_task` / `remove_task` count changes and case-insensitive matching
- `Owner.add_pet`, `set_availability`, `get_all_tasks`
- `Scheduler.sort_tasks` priority ordering, `sort_by_time` chronological ordering
- `filter_tasks` by completion, `filter_by_priority`
- `generate_schedule` date field, time budget enforcement, skipped-task recording
- `detect_conflicts` overlap detection, and confirming zero conflicts in auto-generated plans
- `DailyPlan.get_summary` key presence and value accuracy

These tests mattered because the scheduler's correctness is not visible until a plan is actually generated — a bug in sorting or budget math would silently produce a wrong schedule, so automated checks provide the only reliable guard.

**b. Confidence**

★★★★☆ — All 23 tests pass in 0.05 s. Remaining gaps:
- Tasks added out of chronological order to an existing plan
- Multi-pet conflict detection (owner can only be in one place at once)
- Edge case where `available_minutes` is 0
- Recurrence when `due_date` is left blank (currently falls back to `date.today()`)

---

## 5. Reflection

**a. What went well**

The clean separation between the logic layer (`pawpal_system.py`) and the UI (`app.py`) made it easy to verify every feature in the terminal before touching Streamlit. The CLI demo (`main.py`) acted as a living integration test throughout development.

**b. What you would improve**

The greedy scheduler doesn't account for preferred time-of-day (e.g., walks in the morning, meds in the evening). A next iteration would add a `preferred_time` field to `Task` and a two-pass scheduler: first assign tasks to their preferred windows, then fill remaining gaps greedily.

**c. Key takeaway**

AI is most valuable as a *first-draft* generator and a sounding board, not as a final decision-maker. Every AI suggestion needed to be evaluated against the actual class design — accepting the `RecurringTask` subclass suggestion, for example, would have added unnecessary complexity. The human role is to hold the architecture in mind and decide what fits.
