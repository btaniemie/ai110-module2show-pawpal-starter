# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the CLI demo

```bash
python3 main.py
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

---

## Features

### Core

- **Owner & Pet profiles** — store name, species, age, special needs, and daily time budget
- **Task management** — add tasks with title, duration, priority (high/medium/low), category, and notes
- **Greedy scheduler** — fits the most important tasks into the owner's available time each day; high-priority tasks always scheduled first, with shortest-duration tiebreaking to maximise task count

### Smarter Scheduling

- **Priority-first sorting** — `Scheduler.sort_tasks()` orders tasks high → medium → low, then by duration ascending so more tasks fit in the budget
- **Chronological display** — `Scheduler.sort_by_time()` sorts a generated `DailyPlan` by start time for a clean timeline view
- **Completion filtering** — `Scheduler.filter_tasks(completed=True/False)` lets you see only done or pending tasks
- **Recurring tasks** — tasks can be marked `"daily"` or `"weekly"`; calling `mark_complete()` automatically returns a new `Task` instance due the next day or week
- **Conflict detection** — `Scheduler.detect_conflicts()` checks every pair of `ScheduledTask` windows for overlap and returns plain-English warnings; conflicts are surfaced as `st.warning` banners in the UI
- **Plan explanation** — `Scheduler.explain_plan()` generates a natural-language summary of what was scheduled, why, and what was skipped

---

## Testing PawPal+

### Run tests

```bash
python3 -m pytest tests/ -v
```

### What the test suite covers

| Area | Tests |
|---|---|
| Task completion | `mark_complete()` flips status; idempotent; one-time returns `None` |
| Recurring tasks | Daily task returns next-day occurrence; weekly returns +7 days |
| Pet task management | Add increases count; remove by title (case-insensitive) |
| Owner wiring | `add_pet`, `set_availability`, `get_all_tasks` |
| Scheduler sorting | High priority first; `sort_by_time` chronological order |
| Scheduler filtering | By priority; by completion status |
| Schedule generation | Returns `DailyPlan`; respects time budget; skips tasks that don't fit |
| Conflict detection | Flags overlapping windows; clean sequential plans have zero conflicts |
| Plan output | `get_summary` keys/values; `explain_plan` is non-empty string |

**Confidence level: ★★★★☆** — all 23 tests pass; edge cases covered include zero-task pets, single-task budgets, and back-to-back time conflicts. Next iteration would add tests for tasks added out of order and multi-pet conflict detection across owners.
