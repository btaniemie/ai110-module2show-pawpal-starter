"""
main.py — CLI demo for PawPal+.

Run with:  python3 main.py
"""

from datetime import date as D
from pawpal_system import Owner, Pet, Task, Scheduler, DailyPlan, ScheduledTask


def main() -> None:
    # ── Owner ─────────────────────────────────────────────────────────────────
    owner = Owner(name="Jordan", available_minutes=90, preferences=["morning walks"])

    # ── Pets ──────────────────────────────────────────────────────────────────
    mochi = Pet(name="Mochi", species="dog", age=3)
    luna  = Pet(name="Luna",  species="cat", age=5, special_needs=["daily meds"])
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # ── Tasks for Mochi ───────────────────────────────────────────────────────
    mochi.add_task(Task("Morning walk",  30, "high",   "walk",        frequency="daily",  due_date=str(D.today())))
    mochi.add_task(Task("Breakfast",     10, "high",   "feeding",     frequency="daily",  due_date=str(D.today())))
    mochi.add_task(Task("Fetch session", 20, "medium", "enrichment"))
    mochi.add_task(Task("Bath time",     40, "low",    "grooming",    notes="Oatmeal shampoo"))

    # ── Tasks for Luna ────────────────────────────────────────────────────────
    luna.add_task(Task("Medication",     5,  "high",   "meds",        frequency="daily",  due_date=str(D.today())))
    luna.add_task(Task("Dinner",         10, "high",   "feeding",     frequency="daily",  due_date=str(D.today())))
    luna.add_task(Task("Laser pointer",  15, "medium", "enrichment"))

    # ── Generate schedules ────────────────────────────────────────────────────
    print("\n>>> Scheduling for Mochi...\n")
    scheduler_mochi = Scheduler(owner=owner, pet=mochi)
    plan_mochi = scheduler_mochi.generate_schedule()
    print(plan_mochi.display())
    print()
    print(scheduler_mochi.explain_plan(plan_mochi))

    print("\n>>> Scheduling for Luna...\n")
    scheduler_luna = Scheduler(owner=owner, pet=luna)
    plan_luna = scheduler_luna.generate_schedule()
    print(plan_luna.display())

    # ── Sort by time ──────────────────────────────────────────────────────────
    print("\n>>> Mochi's plan sorted by time:")
    for s in scheduler_mochi.sort_by_time(plan_mochi):
        print(f"  {s.start_time}  {s.task.title}")

    # ── Filter pending tasks ──────────────────────────────────────────────────
    pending = scheduler_mochi.filter_tasks(completed=False)
    print(f"\n>>> Pending tasks for Mochi: {[t.title for t in pending]}")

    # ── Mark a task complete (recurring) ──────────────────────────────────────
    print("\n>>> Marking 'Morning walk' complete (daily recurring)...")
    for st_task in plan_mochi.scheduled_tasks:
        if st_task.task.title == "Morning walk":
            next_task = st_task.task.mark_complete()
            if next_task:
                mochi.add_task(next_task)
                print(f"    Next occurrence added: '{next_task.title}' due {next_task.due_date}")
            break

    done = scheduler_mochi.filter_tasks(completed=True)
    print(f">>> Completed tasks for Mochi: {[t.title for t in done]}")

    # ── Conflict detection demo ───────────────────────────────────────────────
    print("\n>>> Conflict detection demo (manually overlapping tasks):")
    conflict_plan = DailyPlan(date=str(D.today()))
    conflict_plan.scheduled_tasks = [
        ScheduledTask(Task("Walk", 30, "high", "walk"),    "09:00", "demo"),
        ScheduledTask(Task("Bath", 20, "low",  "grooming"), "09:15", "demo"),  # overlaps!
    ]
    conflicts = scheduler_mochi.detect_conflicts(conflict_plan)
    if conflicts:
        for w in conflicts:
            print(f"  WARNING: {w}")
    else:
        print("  No conflicts.")

    print("\n>>> No conflicts in auto-generated plan:")
    auto_conflicts = scheduler_mochi.detect_conflicts(plan_mochi)
    print(f"  {len(auto_conflicts)} conflict(s) found.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n>>> Plan summaries:")
    print(f"  Mochi : {plan_mochi.get_summary()}")
    print(f"  Luna  : {plan_luna.get_summary()}")


if __name__ == "__main__":
    main()
