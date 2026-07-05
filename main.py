from datetime import date

from pawpal_system import Task, Pet, Owner, Scheduler, minutes_to_clock

AVAILABLE_MINUTES = 120
START_MINUTE      = 480   # 8:00 AM

# --- Build the owner ---
jordan = Owner("Jordan", "jordan@example.com")

# --- Create two pets ---
mochi = Pet("Mochi", "dog", 3)
luna  = Pet("Luna",  "cat", 5)

jordan.add_pet(mochi)
jordan.add_pet(luna)

# --- Add tasks OUT OF ORDER on purpose (times are not chronological) ---
mochi.add_task(Task("Evening walk", 30, "medium", earliest_minute=1080))  # 6:00 PM
mochi.add_task(Task("Morning walk", 30, "high",   earliest_minute=480))    # 8:00 AM
mochi.add_task(Task("Feeding",      15, "high",   earliest_minute=720))    # 12:00 PM
mochi.add_task(Task("Play / fetch", 20, "medium"))                         # no pinned time

luna.add_task(Task("Litter box cleaning", 10, "high",   earliest_minute=600))  # 10:00 AM
luna.add_task(Task("Feeding",             10, "high",   earliest_minute=450))  # 7:30 AM
luna.add_task(Task("Brush fur",           15, "medium"))                       # no pinned time

# Mark one task done to show completion filtering.
mochi.tasks[2].mark_done()   # Feeding already handled

# --- Sorting demo: tasks added out of order come back chronologically ---
print("=" * 55)
print("SORTED BY TIME (Scheduler.sort_by_time)")
for pet in jordan.pets:
    scheduler = Scheduler(owner=jordan, pet=pet, sort_by="time")
    print(f"\n{pet.name}:")
    for task in scheduler.sort_by_time():
        when = minutes_to_clock(task.earliest_minute) if task.is_pinned() else "unscheduled"
        print(f"  {when:>12}  →  {task.title} ({task.duration_minutes} min, {task.priority})")

# --- Filtering demo: by pet name and by completion status ---
print("\n" + "=" * 55)
print("FILTER: only Mochi's tasks (Owner.filter_tasks)")
for pet, task in jordan.filter_tasks(pet_name="Mochi"):
    print(f"  {pet.name}: {task}")

print("\nFILTER: completed tasks across all pets")
for pet, task in jordan.filter_tasks(completed=True):
    print(f"  {pet.name}: {task}")

print("\nFILTER: pending tasks for Luna")
for pet, task in jordan.filter_tasks(pet_name="Luna", completed=False):
    print(f"  {pet.name}: {task}")

# --- Auto-recurring demo: completing a recurring task spawns the next one ---
print("\n" + "=" * 55)
print("AUTO-RECURRING (Pet.complete_task)")
today = date(2026, 7, 5)   # fixed date so the demo output is stable
walk = mochi.tasks[1]      # "Morning walk", daily
walk.due_date = today
print(f"  Before: {walk}")
nxt = mochi.complete_task(walk, today=today)
print(f"  Completed → {walk}")
print(f"  Auto-created next occurrence → {nxt}")

# --- Conflict demo: two tasks scheduled at the same time ---
print("\n" + "=" * 55)
print("TIME CONFLICTS (Scheduler.detect_conflicts_across)")
# Same pet: medicine at 8:00 AM overlaps Mochi's morning walk (also 8:00 AM).
mochi.add_task(Task("Give medicine", 15, "high", earliest_minute=480))
# Different pet: Luna's nail trim is also pinned to 8:00 AM — Jordan can't do both.
luna.add_task(Task("Nail trim", 20, "low", earliest_minute=480))

conflicts = Scheduler.detect_conflicts_across(jordan)
if conflicts:
    for w in conflicts:
        print(f"  ⛔ {w}")
else:
    print("  No time conflicts.")

# --- Full schedule per pet ---
print("\n" + "=" * 55)
print("DAILY PLANS")
for pet in jordan.pets:
    print("-" * 55)
    scheduler = Scheduler(
        owner=jordan,
        pet=pet,
        available_minutes=AVAILABLE_MINUTES,
        start_minute=START_MINUTE,
        sort_by="time",
    )
    print(scheduler.explain_plan())
print("=" * 55)
