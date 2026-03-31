import streamlit as st
from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler, DailyPlan, ScheduledTask

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ── Session state init ────────────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None
if "plans" not in st.session_state:
    st.session_state.plans = {}  # pet_name -> DailyPlan

# ── Sidebar: Owner setup ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("Owner Setup")
    owner_name = st.text_input("Your name", value="Jordan")
    avail = st.number_input("Minutes available today", 10, 480, 120, step=10)
    if st.button("Save Owner", type="primary"):
        st.session_state.owner = Owner(name=owner_name, available_minutes=avail)
        st.session_state.plans = {}
    if st.session_state.owner:
        o = st.session_state.owner
        st.success(f"{o.name} · {o.available_minutes} min/day")

st.title("🐾 PawPal+")
st.caption("Smart daily care planning for your pets.")

if st.session_state.owner is None:
    st.info("Set up your owner profile in the sidebar to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_pets, tab_tasks, tab_schedule = st.tabs(
    ["🐾 My Pets", "📋 Add Tasks", "📅 Daily Schedule"]
)

# ── TAB 1: My Pets ────────────────────────────────────────────────────────────
with tab_pets:
    st.subheader("Add a New Pet")
    c1, c2, c3 = st.columns(3)
    new_pet_name = c1.text_input("Pet name")
    new_species  = c2.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    new_age      = c3.number_input("Age (years)", 0, 30, 2)
    new_special  = st.text_input("Special needs (comma-separated, optional)")

    if st.button("Add Pet", type="primary"):
        if not new_pet_name.strip():
            st.error("Please enter a pet name.")
        elif new_pet_name.lower() in [p.name.lower() for p in owner.get_pets()]:
            st.warning(f"'{new_pet_name}' already exists.")
        else:
            needs = [s.strip() for s in new_special.split(",") if s.strip()]
            owner.add_pet(Pet(name=new_pet_name, species=new_species,
                              age=new_age, special_needs=needs))
            st.success(f"Added {new_pet_name} the {new_species}!")

    pets = owner.get_pets()
    if pets:
        st.subheader("Your Pets")
        for pet in pets:
            needs_str = ", ".join(pet.special_needs) or "none"
            done  = sum(1 for t in pet.get_tasks() if t.completed)
            total = len(pet.get_tasks())
            st.markdown(
                f"**{pet.name}** — {pet.species}, {pet.age} yr  |  "
                f"{done}/{total} tasks done  |  needs: {needs_str}"
            )
    else:
        st.info("No pets yet. Add one above!")

# ── TAB 2: Add Tasks ──────────────────────────────────────────────────────────
with tab_tasks:
    pets = owner.get_pets()
    if not pets:
        st.info("Add a pet first in the 'My Pets' tab.")
    else:
        st.subheader("Add a Task")
        sel_pet_name = st.selectbox("Select pet", [p.name for p in pets], key="tp")
        sel_pet = next(p for p in pets if p.name == sel_pet_name)

        c1, c2 = st.columns(2)
        with c1:
            task_title    = st.text_input("Task title", value="Morning walk")
            task_duration = st.number_input("Duration (minutes)", 1, 240, 20)
            task_priority = st.selectbox("Priority", ["high", "medium", "low"])
        with c2:
            task_category  = st.selectbox(
                "Category", ["walk", "feeding", "meds", "grooming", "enrichment", "other"]
            )
            task_frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
            task_due       = st.text_input("Due date (YYYY-MM-DD)", value=str(date.today()))
            task_notes     = st.text_area("Notes (optional)", height=68)

        if st.button("Add Task", type="primary"):
            if not task_title.strip():
                st.error("Task title cannot be empty.")
            else:
                sel_pet.add_task(Task(
                    title=task_title,
                    duration_minutes=int(task_duration),
                    priority=task_priority,
                    category=task_category,
                    notes=task_notes,
                    frequency=task_frequency,
                    due_date=task_due,
                ))
                st.success(f"Added '{task_title}' to {sel_pet.name}!")

        tasks = sel_pet.get_tasks()
        if tasks:
            st.subheader(f"Tasks for {sel_pet.name}")
            st.table([{
                "Title": t.title,
                "Min": t.duration_minutes,
                "Priority": t.priority,
                "Category": t.category,
                "Frequency": t.frequency,
                "Done": "✓" if t.completed else "",
            } for t in tasks])

# ── TAB 3: Daily Schedule ─────────────────────────────────────────────────────
with tab_schedule:
    pets = owner.get_pets()
    if not pets:
        st.info("Add pets and tasks first.")
    else:
        c1, c2 = st.columns([3, 1])
        sched_name = c1.selectbox("Schedule for", [p.name for p in pets], key="sp")
        c2.write("")
        c2.write("")
        generate = c2.button("Generate", type="primary")

        sched_pet = next(p for p in pets if p.name == sched_name)
        scheduler = Scheduler(owner=owner, pet=sched_pet)

        if generate:
            plan = scheduler.generate_schedule(date=str(date.today()))
            st.session_state.plans[sched_name] = plan

        if sched_name in st.session_state.plans:
            plan: DailyPlan = st.session_state.plans[sched_name]

            if not sched_pet.get_tasks():
                st.warning(f"{sched_pet.name} has no tasks. Add some in 'Add Tasks'.")
            else:
                # Conflict warnings
                for msg in scheduler.detect_conflicts(plan):
                    st.warning(f"⚠️ Conflict detected: {msg}")

                # Summary metrics
                s = plan.get_summary()
                m1, m2, m3 = st.columns(3)
                m1.metric("Tasks Scheduled", s["total_tasks"])
                m2.metric("Time Used (min)", s["time_used"])
                m3.metric("Tasks Skipped", s["tasks_skipped"])

                # Chronologically sorted schedule table
                if plan.scheduled_tasks:
                    st.subheader("Today's Plan")
                    st.table([{
                        "Time": st_t.start_time,
                        "Task": st_t.task.title,
                        "Duration": f"{st_t.task.duration_minutes} min",
                        "Priority": st_t.task.priority,
                        "Frequency": st_t.task.frequency,
                        "Status": "✓ Done" if st_t.task.completed else "Pending",
                    } for st_t in scheduler.sort_by_time(plan)])

                    # Mark complete
                    pending = [s.task.title for s in plan.scheduled_tasks
                               if not s.task.completed]
                    if pending:
                        st.subheader("Mark Complete")
                        to_done = st.selectbox("Select task", pending)
                        if st.button("Mark as done ✓"):
                            for s_task in plan.scheduled_tasks:
                                if s_task.task.title == to_done:
                                    next_t = s_task.task.mark_complete()
                                    if next_t:
                                        sched_pet.add_task(next_t)
                                        st.success(
                                            f"Done! Next '{next_t.title}' "
                                            f"scheduled for {next_t.due_date}."
                                        )
                                    else:
                                        st.success(f"'{to_done}' marked complete!")
                                    break
                            st.rerun()
                    else:
                        st.success("All tasks complete for today! 🎉")

                # Skipped tasks
                if plan.unscheduled_tasks:
                    with st.expander(f"Skipped tasks ({len(plan.unscheduled_tasks)})"):
                        for t in plan.unscheduled_tasks:
                            st.markdown(
                                f"- **{t.title}** ({t.duration_minutes} min, {t.priority})"
                            )

                # Plan explanation
                with st.expander("Why this plan?"):
                    st.text(scheduler.explain_plan(plan))
