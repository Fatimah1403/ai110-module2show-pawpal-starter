from pawpal_system import Task, Pet, Owner, Scheduler

# --- Build the owner ---
jordan = Owner("Jordan", "jordan@example.com")

# --- Create two pets ---
mochi = Pet("Mochi", "dog", 3)
luna  = Pet("Luna",  "cat", 5)

jordan.add_pet(mochi)
jordan.add_pet(luna)

# --- Add tasks to Mochi (dog) ---
mochi.add_task(Task("Morning walk",       30, "high",   frequency="daily"))
mochi.add_task(Task("Feeding",            15, "high",   frequency="daily"))
mochi.add_task(Task("Play / fetch",       20, "medium", frequency="daily"))
mochi.add_task(Task("Bath",               45, "low",    frequency="weekly"))

# --- Add tasks to Luna (cat) ---
luna.add_task(Task("Feeding",             10, "high",   frequency="daily"))
luna.add_task(Task("Litter box cleaning", 10, "high",   frequency="daily"))
luna.add_task(Task("Brush fur",           15, "medium", frequency="weekly"))
luna.add_task(Task("Vet check-up",        60, "low",    frequency="as_needed"))

# --- Run the scheduler for Mochi ---
print("=" * 55)
mochi_scheduler = Scheduler(
    owner=jordan,
    pet=mochi,
    available_minutes=120,
    start_minute=480,   # 8:00 AM
)
print(mochi_scheduler.explain_plan())

print()
print("=" * 55)

# --- Run the scheduler for Luna ---
luna_scheduler = Scheduler(
    owner=jordan,
    pet=luna,
    available_minutes=60,
    start_minute=510,   # 8:30 AM
)
print(luna_scheduler.explain_plan())
print("=" * 55)
