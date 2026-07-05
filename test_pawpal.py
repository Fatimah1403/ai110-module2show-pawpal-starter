from datetime import date, timedelta

import pytest

from pawpal_system import Task, Pet, Owner, Scheduler, ScheduledTask


def _owner_with_pet(pet: Pet) -> Owner:
    """Build an Owner registered with a single pet (Scheduler needs both)."""
    owner = Owner("Jordan")
    owner.add_pet(pet)
    return owner


def test_find_time_conflicts_flags_overlap():
    a = ScheduledTask(Task("Walk", 30, "high"), start_minute=480)  # 8:00–8:30
    b = ScheduledTask(Task("Feed", 15, "high"), start_minute=490)  # 8:10–8:25
    warnings = Scheduler.find_time_conflicts([("Mochi", a), ("Mochi", b)])
    assert len(warnings) == 1


def test_find_time_conflicts_touching_windows_ok():
    a = ScheduledTask(Task("Walk", 30, "high"), start_minute=480)  # 8:00–8:30
    b = ScheduledTask(Task("Feed", 15, "high"), start_minute=510)  # 8:30–8:45 (touches, no overlap)
    assert Scheduler.find_time_conflicts([("Mochi", a), ("Luna", b)]) == []


def test_detect_conflicts_across_pets():
    owner = Owner("Jordan")
    mochi, luna = Pet("Mochi", "dog", 3), Pet("Luna", "cat", 5)
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Walk", 30, "high", earliest_minute=480))  # 8:00
    luna.add_task(Task("Vet", 20, "high", earliest_minute=485))    # 8:05 → overlaps
    assert len(Scheduler.detect_conflicts_across(owner)) == 1


def test_completing_daily_task_spawns_next_day():
    pet = Pet(name="Mochi", species="dog", age=3)
    today = date(2026, 7, 5)
    walk = Task("Walk", 30, "high", frequency="daily", due_date=today)
    pet.add_task(walk)

    nxt = pet.complete_task(walk, today=today)

    assert walk.completed is True
    assert nxt is not None
    assert nxt.completed is False
    assert nxt.due_date == today + timedelta(days=1)   # tomorrow
    assert len(pet.tasks) == 2


def test_completing_weekly_task_spawns_next_week():
    pet = Pet(name="Luna", species="cat", age=5)
    today = date(2026, 7, 5)
    brush = Task("Brush fur", 15, "medium", frequency="weekly", due_date=today)
    pet.add_task(brush)

    nxt = pet.complete_task(brush, today=today)

    assert nxt.due_date == today + timedelta(weeks=1)   # 7 days out


def test_as_needed_task_does_not_respawn():
    pet = Pet(name="Rex", species="dog", age=2)
    vet = Task("Vet", 60, "low", frequency="as_needed")
    pet.add_task(vet)

    nxt = pet.complete_task(vet)

    assert nxt is None
    assert len(pet.tasks) == 1


def test_mark_done_changes_completed_status():
    task = Task(title="Morning walk", duration_minutes=30, priority="high")
    assert task.completed is False
    task.mark_done()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(Task(title="Feeding", duration_minutes=15, priority="high"))
    assert len(pet.tasks) == 1
    pet.add_task(Task(title="Bath", duration_minutes=45, priority="low"))
    assert len(pet.tasks) == 2


# --- Schedule generation & time-budget fitting -----------------------------

def test_schedule_chains_start_times():
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Walk", 20, "high"))     # placed first (higher priority)
    pet.add_task(Task("Play", 15, "medium"))   # placed second
    owner = _owner_with_pet(pet)
    schedule = Scheduler(owner, pet, available_minutes=120, start_minute=480).generate_schedule()

    assert [st.start_minute for st in schedule] == [480, 500]  # 8:00, then 8:20


def test_task_fits_when_duration_equals_remaining_time():
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Walk", 30, "high"))
    owner = _owner_with_pet(pet)
    schedule = Scheduler(owner, pet, available_minutes=30).generate_schedule()

    assert len(schedule) == 1  # 30 <= 30 boundary fits


def test_oversized_task_is_skipped_but_smaller_one_still_fits():
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Long grooming", 50, "high"))   # too big for a 40-min window
    pet.add_task(Task("Quick feed", 20, "medium"))    # should still be placed
    owner = _owner_with_pet(pet)
    schedule = Scheduler(owner, pet, available_minutes=40).generate_schedule()

    titles = [st.task.title for st in schedule]
    assert titles == ["Quick feed"]  # loop keeps going after the skip


def test_empty_pet_produces_no_schedule():
    pet = Pet("Mochi", "dog", 3)
    owner = _owner_with_pet(pet)
    scheduler = Scheduler(owner, pet)

    assert scheduler.generate_schedule() == []
    assert "No tasks could be scheduled" in scheduler.explain_plan()


# --- Sorting ----------------------------------------------------------------

def test_sort_by_time_orders_pinned_and_puts_unpinned_last():
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Evening", 20, "low", earliest_minute=600))
    pet.add_task(Task("Anytime", 20, "low"))               # unpinned
    pet.add_task(Task("Morning", 20, "high", earliest_minute=480))
    owner = _owner_with_pet(pet)

    ordered = Scheduler(owner, pet, sort_by="time").sort_by_time()

    assert [t.title for t in ordered] == ["Morning", "Evening", "Anytime"]


# --- Filtering --------------------------------------------------------------

def test_filter_tasks_by_pet_name_is_case_insensitive():
    mochi, luna = Pet("Mochi", "dog", 3), Pet("Luna", "cat", 5)
    owner = Owner("Jordan")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(Task("Walk", 20, "high"))
    luna.add_task(Task("Feed", 10, "high"))

    assert len(owner.filter_tasks(pet_name="mochi")) == 1   # lowercase still matches
    assert owner.filter_tasks(pet_name="Ghost") == []       # no such pet


def test_filter_tasks_by_completion_status():
    pet = Pet("Mochi", "dog", 3)
    done = Task("Walk", 20, "high")
    pet.add_task(done)
    pet.add_task(Task("Feed", 10, "high"))
    done.mark_done()
    owner = _owner_with_pet(pet)

    assert len(owner.filter_tasks(completed=True)) == 1
    assert len(owner.filter_tasks(completed=False)) == 1
    assert len(owner.filter_tasks()) == 2                   # None = all


# --- Conflict detection: exact same start time ------------------------------

def test_two_tasks_at_exact_same_time_conflict():
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Walk", 30, "high", earliest_minute=480))
    pet.add_task(Task("Medicine", 15, "high", earliest_minute=480))  # same start
    owner = _owner_with_pet(pet)

    assert len(Scheduler.detect_conflicts_across(owner)) == 1


# --- Recurring: calendar rollover -------------------------------------------

def test_daily_task_rolls_over_year_boundary():
    pet = Pet("Mochi", "dog", 3)
    walk = Task("Walk", 30, "high", frequency="daily", due_date=date(2026, 12, 31))
    pet.add_task(walk)

    nxt = pet.complete_task(walk)

    assert nxt.due_date == date(2027, 1, 1)  # timedelta handles the rollover


# --- Validation guards ------------------------------------------------------

def test_invalid_priority_rejected():
    with pytest.raises(ValueError):
        Task("Walk", 30, "High")   # wrong case / unknown priority


def test_invalid_frequency_rejected():
    with pytest.raises(ValueError):
        Task("Walk", 30, "high", frequency="monthly")


# ===========================================================================
# Rubric core behaviours: sorting correctness, recurrence, conflict detection
# ===========================================================================

def test_sorting_returns_tasks_in_chronological_order():
    """Sorting Correctness — tasks come back ordered by their start time."""
    pet = Pet("Mochi", "dog", 3)
    # Added deliberately out of chronological order.
    pet.add_task(Task("Noon feed", 15, "medium", earliest_minute=720))  # 12:00 PM
    pet.add_task(Task("Morning walk", 30, "high", earliest_minute=480))  #  8:00 AM
    pet.add_task(Task("Evening play", 20, "low", earliest_minute=1080))  #  6:00 PM
    owner = _owner_with_pet(pet)

    ordered = Scheduler(owner, pet, sort_by="time").sort_by_time()

    times = [t.earliest_minute for t in ordered]
    assert times == sorted(times)                       # strictly chronological
    assert times == [480, 720, 1080]


def test_completing_daily_task_creates_task_for_next_day():
    """Recurrence Logic — finishing a daily task spawns one for the following day."""
    pet = Pet("Mochi", "dog", 3)
    today = date(2026, 7, 5)
    walk = Task("Walk", 30, "high", frequency="daily", due_date=today)
    pet.add_task(walk)

    followup = pet.complete_task(walk, today=today)

    assert walk.completed is True                        # original is done
    assert followup is not None                          # a new task was created
    assert followup.completed is False                   # and it's still pending
    assert followup.due_date == date(2026, 7, 6)         # exactly one day later
    assert followup in pet.tasks                         # added to the pet's list


def test_scheduler_flags_duplicate_times():
    """Conflict Detection — two tasks at the same start time are flagged."""
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Walk", 30, "high", earliest_minute=480))       # 8:00 AM
    pet.add_task(Task("Give meds", 15, "high", earliest_minute=480))  # 8:00 AM (duplicate)
    owner = _owner_with_pet(pet)

    conflicts = Scheduler.detect_conflicts_across(owner)

    assert len(conflicts) == 1
    assert "conflict" in conflicts[0].lower()
