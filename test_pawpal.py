from datetime import date, timedelta

from pawpal_system import Task, Pet, Owner, Scheduler, ScheduledTask


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
