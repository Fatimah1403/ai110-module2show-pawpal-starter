import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

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

# ---------------------------------------------------------------------------
# Step 3 — Add tasks to a pet  (calls Pet.add_task)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Step 3 — Add Tasks")

pet_names      = [p.name for p in owner.pets]
selected_name  = st.selectbox("Add task to", pet_names)
selected_pet   = next(p for p in owner.pets if p.name == selected_name)

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    task = Task(title=task_title, duration_minutes=int(duration), priority=priority)
    selected_pet.add_task(task)         # Pet.add_task() appends to the pet's task list
    st.success(f"Added '{task_title}' to {selected_name}.")

# Show all tasks grouped by pet
for pet in owner.pets:
    if pet.tasks:
        st.markdown(f"**{pet.name}'s tasks:**")
        st.table([
            {"task": t.title, "duration (min)": t.duration_minutes, "priority": t.priority}
            for t in pet.tasks
        ])

# ---------------------------------------------------------------------------
# Step 4 — Generate schedule  (calls Scheduler.explain_plan)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Step 4 — Generate Schedule")

schedule_for      = st.selectbox("Schedule for", pet_names, key="sched_pet")
available_minutes = st.slider("Available time (minutes)", 30, 480, 120, step=15)

if st.button("Generate schedule"):
    target_pet = next(p for p in owner.pets if p.name == schedule_for)
    if not target_pet.tasks:
        st.warning(f"{schedule_for} has no tasks yet — add some in Step 3.")
    else:
        scheduler = Scheduler(
            owner=owner,
            pet=target_pet,
            available_minutes=available_minutes,
        )
        st.text(scheduler.explain_plan())
