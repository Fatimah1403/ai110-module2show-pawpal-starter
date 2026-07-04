from pawpal_system import Task, Pet


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
