from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str            # "low" | "medium" | "high"
    frequency: str = "daily" # "daily" | "weekly" | "as_needed"
    completed: bool = False

    def __post_init__(self) -> None:
        """Reject invalid priority values immediately on construction."""
        if self.priority not in PRIORITY_ORDER:
            raise ValueError(f"priority must be one of {list(PRIORITY_ORDER)}")

    def is_high_priority(self) -> bool:
        """Return True if this task's priority is high."""
        return self.priority == "high"

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def __str__(self) -> str:
        """Return a compact human-readable summary of the task."""
        status = "✓" if self.completed else "○"
        return f"[{status}] {self.title} ({self.duration_minutes} min, {self.priority})"


@dataclass
class ScheduledTask:
    task: Task
    start_minute: int  # minutes from start of day (e.g. 480 = 8:00 AM)

    def start_time_str(self) -> str:
        """Convert start_minute into a 12-hour clock string like '8:05 AM'."""
        h, m = divmod(self.start_minute, 60)
        period = "AM" if h < 12 else "PM"
        if h == 0:
            h = 12
        elif h > 12:
            h -= 12
        return f"{h}:{m:02d} {period}"


@dataclass
class Pet:
    name: str
    species: str
    age: int
    owner: Optional[Owner] = field(default=None, repr=False)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a care task to this pet's task list."""
        self.tasks.append(task)

    def get_needs(self) -> list[Task]:
        """Return only tasks not yet completed."""
        return [t for t in self.tasks if not t.completed]

    def __str__(self) -> str:
        """Return a short display string for the pet."""
        return f"{self.name} ({self.species}, age {self.age})"


class Owner:
    def __init__(self, name: str, email: str = "") -> None:
        self.name = name
        self.email = email
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner and set the back-reference."""
        pet.owner = self
        self.pets.append(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Collect all pending tasks across every pet, paired with their pet."""
        return [
            (pet, task)
            for pet in self.pets
            for task in pet.get_needs()
        ]

    def __str__(self) -> str:
        """Return a short display string for the owner."""
        return f"Owner({self.name}, {len(self.pets)} pet(s))"


class Scheduler:
    def __init__(
        self,
        owner: Owner,
        pet: Pet,
        tasks: list[Task] | None = None,
        available_minutes: int = 480,  # 8 hours default
        start_minute: int = 480,       # 8:00 AM default
    ) -> None:
        self.owner = owner
        self.pet = pet
        self.tasks = tasks or []
        self.available_minutes = available_minutes
        self.start_minute = start_minute

    def _collect_tasks(self) -> list[Task]:
        """Ask the Owner for all pending tasks, then merge any extra tasks passed directly."""
        from_owner = [task for _, task in self.owner.get_all_tasks()]
        seen = {id(t) for t in from_owner}
        extras = [t for t in self.tasks if id(t) not in seen and not t.completed]
        return from_owner + extras

    def generate_schedule(self) -> list[ScheduledTask]:
        """Sort pending tasks by priority (then shortest first), fit within available_minutes."""
        pending = self._collect_tasks()
        sorted_tasks = sorted(
            pending,
            key=lambda t: (PRIORITY_ORDER[t.priority], t.duration_minutes),
        )
        schedule: list[ScheduledTask] = []
        cursor = self.start_minute
        remaining = self.available_minutes
        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                schedule.append(ScheduledTask(task=task, start_minute=cursor))
                cursor += task.duration_minutes
                remaining -= task.duration_minutes
        return schedule

    def explain_plan(self) -> str:
        """Build and return a human-readable daily schedule with time slots and skip count."""
        schedule = self.generate_schedule()
        if not schedule:
            return f"No tasks could be scheduled for {self.pet.name} today."
        lines = [
            f"Daily plan for {self.pet.name} ({self.pet.species})  —  owner: {self.owner.name}",
            f"Available time: {self.available_minutes} min  |  Starting at: {ScheduledTask(Task('', 0, 'low'), self.start_minute).start_time_str()}",
            "",
        ]
        for i, st in enumerate(schedule, 1):
            reason = "high priority" if st.task.is_high_priority() else f"{st.task.priority} priority"
            lines.append(
                f"  {i}. {st.start_time_str()}  →  {st.task.title} "
                f"({st.task.duration_minutes} min, {reason})"
            )
        total_min = sum(st.task.duration_minutes for st in schedule)
        skipped = len(self._collect_tasks()) - len(schedule)
        lines.append(f"\nTotal: {total_min} min across {len(schedule)} task(s).", )
        if skipped:
            lines.append(f"Skipped: {skipped} task(s) that didn't fit in the available time.")
        return "\n".join(lines)
