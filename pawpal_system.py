from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
VALID_FREQUENCIES = {"daily", "weekly", "as_needed"}
# How far ahead the next occurrence of a recurring task lands.
FREQUENCY_DELTA = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def minutes_to_clock(minute: int) -> str:
    """Convert minutes-from-midnight into a 12-hour clock string like '8:05 AM'."""
    h, m = divmod(minute % (24 * 60), 60)
    period = "AM" if h < 12 else "PM"
    if h == 0:
        h = 12
    elif h > 12:
        h -= 12
    return f"{h}:{m:02d} {period}"


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str            # "low" | "medium" | "high"
    frequency: str = "daily" # "daily" | "weekly" | "as_needed"
    completed: bool = False
    earliest_minute: Optional[int] = None  # optional time-of-day pin (minutes from midnight)
    due: bool = False                       # for "as_needed" tasks: is it needed right now?
    due_date: Optional[date] = None         # calendar day this task is due

    def __post_init__(self) -> None:
        """Reject invalid priority / frequency values immediately on construction."""
        if self.priority not in PRIORITY_ORDER:
            raise ValueError(f"priority must be one of {list(PRIORITY_ORDER)}")
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {sorted(VALID_FREQUENCIES)}")

    def is_high_priority(self) -> bool:
        """Return True if this task's priority is high."""
        return self.priority == "high"

    def is_pinned(self) -> bool:
        """Return True if this task has a requested start time."""
        return self.earliest_minute is not None

    def is_recurring(self) -> bool:
        """Return True if this task repeats (daily or weekly)."""
        return self.frequency in FREQUENCY_DELTA

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_occurrence(self, today: Optional[date] = None) -> Optional[Task]:
        """Build the next occurrence of a recurring task, or None if it doesn't repeat.

        The new due date is the current due_date plus one interval (a day for
        "daily", a week for "weekly"). If this task has no due_date, we anchor to
        `today` (defaulting to date.today()), so the next date is today + interval.
        The returned Task is a fresh, not-yet-completed copy.
        """
        if not self.is_recurring():
            return None
        anchor = self.due_date or (today or date.today())
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            completed=False,
            earliest_minute=self.earliest_minute,
            due=self.due,
            due_date=anchor + FREQUENCY_DELTA[self.frequency],
        )

    def __str__(self) -> str:
        """Return a compact human-readable summary of the task."""
        status = "✓" if self.completed else "○"
        pin = f" @ {minutes_to_clock(self.earliest_minute)}" if self.is_pinned() else ""
        when = f", due {self.due_date.isoformat()}" if self.due_date else ""
        return f"[{status}] {self.title} ({self.duration_minutes} min, {self.priority}{pin}{when})"


@dataclass
class ScheduledTask:
    task: Task
    start_minute: int  # minutes from start of day (e.g. 480 = 8:00 AM)

    @property
    def end_minute(self) -> int:
        """Minute at which this task finishes."""
        return self.start_minute + self.task.duration_minutes

    def start_time_str(self) -> str:
        """Convert start_minute into a 12-hour clock string like '8:05 AM'."""
        return minutes_to_clock(self.start_minute)


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

    def complete_task(self, task: Task, today: Optional[date] = None) -> Optional[Task]:
        """Mark a task done and auto-schedule its next occurrence if it recurs.

        Returns the newly created follow-up Task (already added to this pet), or
        None for one-off / as_needed tasks that don't repeat.
        """
        task.mark_done()
        nxt = task.next_occurrence(today=today)
        if nxt is not None:
            self.add_task(nxt)
        return nxt

    def get_tasks(self, completed: Optional[bool] = None) -> list[Task]:
        """Return this pet's tasks, optionally filtered by completion status.

        completed=None  -> all tasks
        completed=False -> only pending tasks
        completed=True  -> only finished tasks
        """
        if completed is None:
            return list(self.tasks)
        return [t for t in self.tasks if t.completed == completed]

    def get_needs(self) -> list[Task]:
        """Return only tasks not yet completed."""
        return self.get_tasks(completed=False)

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

    def get_tasks(
        self,
        pet: Optional[Pet] = None,
        completed: Optional[bool] = None,
    ) -> list[tuple[Pet, Task]]:
        """Collect (pet, task) pairs across pets, filtered by pet and/or status.

        pet=None       -> every pet; pass a Pet to restrict to one.
        completed=None  -> all tasks; True/False filters by completion status.
        """
        pets = [pet] if pet is not None else self.pets
        return [
            (p, task)
            for p in pets
            for task in p.get_tasks(completed=completed)
        ]

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Collect all pending tasks across every pet, paired with their pet."""
        return self.get_tasks(completed=False)

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[tuple[Pet, Task]]:
        """Filter (pet, task) pairs by pet name and/or completion status.

        pet_name=None  -> every pet; pass a name (case-insensitive) to restrict.
        completed=None -> all tasks; True/False filters by completion status.
        """
        result: list[tuple[Pet, Task]] = []
        for pet in self.pets:
            if pet_name is not None and pet.name.lower() != pet_name.lower():
                continue
            for task in pet.get_tasks(completed=completed):
                result.append((pet, task))
        return result

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
        sort_by: str = "priority",     # "priority" | "time"
        include_frequencies: set[str] | None = None,
    ) -> None:
        if sort_by not in ("priority", "time"):
            raise ValueError('sort_by must be "priority" or "time"')
        self.owner = owner
        self.pet = pet
        self.tasks = tasks or []
        self.available_minutes = available_minutes
        self.start_minute = start_minute
        self.sort_by = sort_by
        # Which recurrences count toward *today's* plan. "as_needed" is excluded
        # unless the caller opts in AND the task is flagged due.
        self.include_frequencies = include_frequencies or {"daily", "weekly"}

    def _is_due(self, task: Task) -> bool:
        """Decide whether a recurring task belongs in today's plan."""
        if task.completed:
            return False
        if task.frequency not in self.include_frequencies:
            return False
        if task.frequency == "as_needed" and not task.due:
            return False
        return True

    def _collect_tasks(self) -> list[Task]:
        """Gather this pet's pending, currently-due tasks, plus any due extras."""
        from_pet = self.pet.get_needs()           # only THIS pet's tasks (bug fix)
        seen = {id(t) for t in from_pet}
        extras = [t for t in self.tasks if id(t) not in seen]
        pool = from_pet + extras
        return [t for t in pool if self._is_due(t)]

    def _sort_key(self, task: Task):
        """Ordering key for the fill loop, controlled by self.sort_by."""
        rank = PRIORITY_ORDER[task.priority]
        pin = task.earliest_minute
        if self.sort_by == "time":
            # Pinned tasks first, in chronological order; then unpinned by priority.
            if pin is not None:
                return (0, pin, rank, task.duration_minutes)
            return (1, 0, rank, task.duration_minutes)
        # Default: priority first, then earlier pins, then shortest.
        return (rank, pin if pin is not None else 24 * 60, task.duration_minutes)

    def _build(self) -> tuple[list[ScheduledTask], list[Task]]:
        """Greedily place due tasks in the available window.

        Returns (scheduled, skipped). A task's earliest_minute pins the soonest
        time it may start; anything that overflows the window is skipped.
        """
        ordered = sorted(self._collect_tasks(), key=self._sort_key)
        schedule: list[ScheduledTask] = []
        skipped: list[Task] = []
        cursor = self.start_minute
        end_window = self.start_minute + self.available_minutes
        for task in ordered:
            start = cursor
            if task.earliest_minute is not None:
                start = max(cursor, task.earliest_minute)
            if start + task.duration_minutes <= end_window:
                schedule.append(ScheduledTask(task=task, start_minute=start))
                cursor = start + task.duration_minutes
            else:
                skipped.append(task)
        return schedule, skipped

    def sort_by_time(self) -> list[Task]:
        """Return this pet's due tasks ordered by their requested start time.

        earliest_minute is an int (minutes from midnight), so a simple lambda
        key sorts chronologically. Unpinned tasks (None) fall back to the end
        of the day so they sort last instead of crashing on None vs int.
        """
        return sorted(
            self._collect_tasks(),
            key=lambda t: t.earliest_minute if t.earliest_minute is not None else 24 * 60,
        )

    def generate_schedule(self) -> list[ScheduledTask]:
        """Return the placed tasks for the day (see _build for the rules)."""
        return self._build()[0]

    @staticmethod
    def _conflicts_from(
        schedule: list[ScheduledTask], skipped: list[Task]
    ) -> list[str]:
        """Turn a built schedule into human-readable conflict warnings."""
        conflicts: list[str] = []
        for st in schedule:
            pin = st.task.earliest_minute
            if pin is not None and st.start_minute > pin:
                conflicts.append(
                    f"'{st.task.title}' wanted {minutes_to_clock(pin)} "
                    f"but starts at {st.start_time_str()} "
                    f"(delayed {st.start_minute - pin} min)."
                )
        for t in skipped:
            if t.earliest_minute is not None:
                conflicts.append(
                    f"'{t.title}' (pinned to {minutes_to_clock(t.earliest_minute)}, "
                    f"{t.duration_minutes} min) doesn't fit in the available window."
                )
            else:
                conflicts.append(
                    f"'{t.title}' ({t.duration_minutes} min) didn't fit and was skipped."
                )
        return conflicts

    def detect_conflicts(self) -> list[str]:
        """Report delayed pins and tasks that couldn't fit in the window."""
        schedule, skipped = self._build()
        return self._conflicts_from(schedule, skipped)

    @staticmethod
    def find_time_conflicts(
        labeled_schedule: list[tuple[str, ScheduledTask]]
    ) -> list[str]:
        """Return a warning for every pair of tasks whose time windows overlap.

        labeled_schedule: (label, ScheduledTask) pairs — label is usually a pet
        name, so the same list can hold tasks from one pet or many.

        Lightweight & safe: pure comparison, never raises, returns [] when clear.
        Sorting by start time lets us stop early — once a later task starts at or
        after the current one ends, nothing further can overlap it.
        """
        items = sorted(labeled_schedule, key=lambda pair: pair[1].start_minute)
        warnings: list[str] = []
        for i, (label_a, a) in enumerate(items):
            for label_b, b in items[i + 1:]:
                if b.start_minute >= a.end_minute:
                    break  # sorted by start → no later task can overlap `a`
                warnings.append(
                    f"Time conflict: '{label_a}: {a.task.title}' "
                    f"({a.start_time_str()}–{minutes_to_clock(a.end_minute)}) overlaps "
                    f"'{label_b}: {b.task.title}' "
                    f"({b.start_time_str()}–{minutes_to_clock(b.end_minute)})."
                )
        return warnings

    @classmethod
    def detect_conflicts_across(
        cls, owner: Owner, pet: Optional[Pet] = None
    ) -> list[str]:
        """Warn when pinned tasks collide in time, within one pet or across pets.

        Uses each pending, pinned task's requested slot (earliest_minute +
        duration). Pass a pet to check just that pet; omit it to check the whole
        household (so 'Mochi at 8:00' vs 'Luna at 8:00' surfaces). Never raises.
        """
        pets = [pet] if pet is not None else owner.pets
        labeled: list[tuple[str, ScheduledTask]] = []
        for p in pets:
            for task in p.get_needs():
                if task.is_pinned():
                    labeled.append(
                        (p.name, ScheduledTask(task=task, start_minute=task.earliest_minute))
                    )
        return cls.find_time_conflicts(labeled)

    def explain_plan(self) -> str:
        """Build and return a human-readable daily schedule with conflicts."""
        schedule, skipped = self._build()
        if not schedule:
            return f"No tasks could be scheduled for {self.pet.name} today."
        lines = [
            f"Daily plan for {self.pet.name} ({self.pet.species})  —  owner: {self.owner.name}",
            f"Available time: {self.available_minutes} min  |  "
            f"Starting at: {minutes_to_clock(self.start_minute)}  |  Sorted by: {self.sort_by}",
            "",
        ]
        for i, st in enumerate(schedule, 1):
            reason = "high priority" if st.task.is_high_priority() else f"{st.task.priority} priority"
            lines.append(
                f"  {i}. {st.start_time_str()}  →  {st.task.title} "
                f"({st.task.duration_minutes} min, {reason})"
            )
        total_min = sum(st.task.duration_minutes for st in schedule)
        lines.append(f"\nTotal: {total_min} min across {len(schedule)} task(s).")
        if skipped:
            lines.append(f"Skipped: {len(skipped)} task(s) that didn't fit in the available time.")
        conflicts = self._conflicts_from(schedule, skipped)
        if conflicts:
            lines.append("\nConflicts:")
            lines.extend(f"  ⚠ {c}" for c in conflicts)
        return "\n".join(lines)
