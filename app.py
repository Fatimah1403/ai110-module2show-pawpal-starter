from datetime import date, time

import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, minutes_to_clock

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# Include every recurrence in generated plans (as_needed tasks are flagged due on creation).
ALL_FREQUENCIES = {"daily", "weekly", "as_needed"}


def to_minutes(t: time) -> int:
    """Convert a datetime.time into minutes from midnight."""
    return t.hour * 60 + t.minute


# ---------------------------------------------------------------------------
# Session-state vault — one Owner object persists for the whole session
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None

# ---------------------------------------------------------------------------
# Step 1 — Owner setup
# ---------------------------------------------------------------------------
st.subheader("Step 1 — Owner")
owner_name = st.text_input("Your name", value="Jordan")

if st.button("Set owner"):
    st.session_state.owner = Owner(name=owner_name)
    st.success(f"Owner set: {owner_name}")

if st.session_state.owner is None:
    st.info("Enter your name above and click **Set owner** to get started.")
    st.stop()                           # nothing below renders until owner exists

owner: Owner = st.session_state.owner  # convenient alias

# ---------------------------------------------------------------------------
# Step 2 — Add pets  (calls Owner.add_pet)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Step 2 — Add a Pet")

col1, col2 = st.columns(2)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    new_pet = Pet(name=pet_name, species=species, age=0)
    owner.add_pet(new_pet)              # Owner.add_pet() registers the pet and sets the back-reference
    st.success(f"Added {pet_name} the {species}!")

if owner.pets:
    st.write("Registered pets:")
    for p in owner.pets:
        st.markdown(f"- **{p.name}** ({p.species})")
else:
    st.info("No pets yet — add one above.")
    st.stop()                           # task/schedule sections need at least one pet

pet_names = [p.name for p in owner.pets]

# ---------------------------------------------------------------------------
# Step 3 — Add tasks to a pet  (calls Pet.add_task)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Step 3 — Add Tasks")

selected_name = st.selectbox("Add task to", pet_names)
selected_pet  = next(p for p in owner.pets if p.name == selected_name)

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

col4, col5 = st.columns(2)
with col4:
    frequency = st.selectbox("Repeats", ["daily", "weekly", "as_needed"])
with col5:
    pin_it = st.checkbox("Pin to a specific start time")
    pinned_minute = to_minutes(st.time_input("Start time", value=time(8, 0))) if pin_it else None

if st.button("Add task"):
    task = Task(
        title=task_title,
        duration_minutes=int(duration),
        priority=priority,
        frequency=frequency,
        earliest_minute=pinned_minute,
        due=(frequency == "as_needed"),   # so one-off tasks still schedule
        due_date=date.today(),
    )
    selected_pet.add_task(task)
    st.success(f"Added '{task_title}' to {selected_name}.")

# ---------------------------------------------------------------------------
# Manage tasks — complete (auto-respawns recurring) + filtered table
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Your Tasks")

# --- Mark a task complete (Pet.complete_task → auto-schedules the next one) ---
pending = owner.filter_tasks(completed=False)
if pending:
    labels = [f"{p.name}: {t.title}" for p, t in pending]
    pick = st.selectbox(
        "Mark a task complete",
        range(len(pending)),
        format_func=lambda i: labels[i],
        key="complete_pick",
    )
    if st.button("✓ Mark complete"):
        pet_obj, task_obj = pending[pick]
        nxt = pet_obj.complete_task(task_obj)   # respawns next occurrence if recurring
        if nxt is not None:
            st.success(
                f"Completed '{task_obj.title}'. "
                f"Next **{nxt.frequency}** occurrence auto-scheduled for {nxt.due_date.isoformat()}."
            )
        else:
            st.success(f"Completed '{task_obj.title}'. (One-off task — not repeated.)")

# --- Filter controls (Owner.filter_tasks by pet name / completion status) ---
fcol1, fcol2 = st.columns(2)
with fcol1:
    filter_pet = st.selectbox("Filter by pet", ["All"] + pet_names, key="filter_pet")
with fcol2:
    filter_status = st.selectbox("Filter by status", ["All", "Pending", "Done"], key="filter_status")

status_arg = {"All": None, "Pending": False, "Done": True}[filter_status]
pet_arg = None if filter_pet == "All" else filter_pet

rows = [
    {
        "": "✓" if t.completed else "○",
        "pet": p.name,
        "task": t.title,
        "duration": f"{t.duration_minutes} min",
        "priority": t.priority,
        "repeats": t.frequency,
        "pinned": minutes_to_clock(t.earliest_minute) if t.is_pinned() else "—",
    }
    for p, t in owner.filter_tasks(pet_name=pet_arg, completed=status_arg)
]
if rows:
    st.table(rows)
else:
    st.info("No tasks match this filter yet.")

# ---------------------------------------------------------------------------
# Step 4 — Generate schedule  (Scheduler.generate_schedule + conflict checks)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Step 4 — Generate Schedule")

schedule_for      = st.selectbox("Schedule for", pet_names, key="sched_pet")
available_minutes = st.slider("Available time (minutes)", 30, 480, 120, step=15)
sort_by           = st.radio("Order tasks by", ["time", "priority"], horizontal=True)

if st.button("Generate schedule"):
    target_pet = next(p for p in owner.pets if p.name == schedule_for)
    scheduler = Scheduler(
        owner=owner,
        pet=target_pet,
        available_minutes=available_minutes,
        sort_by=sort_by,
        include_frequencies=ALL_FREQUENCIES,
    )
    schedule = scheduler.generate_schedule()

    if not schedule:
        st.warning(f"No tasks could be scheduled for {schedule_for} today — add some in Step 3.")
    else:
        st.markdown(f"#### 📅 {target_pet.name}'s plan")
        st.table([
            {
                "start": item.start_time_str(),
                "task": item.task.title,
                "duration": f"{item.task.duration_minutes} min",
                "priority": item.task.priority,
            }
            for item in schedule
        ])
        total = sum(item.task.duration_minutes for item in schedule)
        st.caption(f"Total: {total} min across {len(schedule)} task(s), sorted by {sort_by}.")

    # This pet's own conflicts: delayed pins + tasks that didn't fit.
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        st.markdown("**⚠️ Scheduling notes**")
        for c in conflicts:
            st.warning(c)
    elif schedule:
        st.success("Everything fit with no conflicts 🎉")

    # Household conflicts: same clock time across pets (owner can't be two places).
    household = Scheduler.detect_conflicts_across(owner)
    if household:
        st.markdown("**🏠 Household time conflicts** — you're double-booked:")
        for c in household:
            st.warning(c)
