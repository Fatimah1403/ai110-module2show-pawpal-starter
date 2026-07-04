# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The initial UML included four classes:

- **Owner** — holds the owner's name and email, maintains a list of pets, and exposes `add_pet()` to register a new pet.
- **Pet** — a dataclass storing the pet's name, species, and age. It holds a back-reference to its owner and exposes `get_needs()` to return the default set of care tasks for that pet.
- **Task** — a dataclass representing a single care action with a title, duration in minutes, and a priority level (`"low"` / `"medium"` / `"high"`). Exposes `is_high_priority()` as a convenience check.
- **Scheduler** — the logic engine. Takes an Owner, a Pet, and a list of Tasks, then produces a prioritized daily plan via `generate_schedule()` and a human-readable explanation via `explain_plan()`.

**b. Design changes**

Yes, two changes were made after reviewing the skeleton:

1. **Added `ScheduledTask` dataclass.** The original `generate_schedule()` returned `list[Task]`, but a real schedule needs to know *when* each task starts, not just which tasks to do. `ScheduledTask` wraps a `Task` with a `start_minute` field (minutes from the start of the day), so the output carries both the task data and its time slot.

2. **Added `available_minutes` to `Scheduler` and priority validation to `Task`.** Without a time budget, the scheduler had no way to check whether all tasks actually fit in a day. Adding `available_minutes` (defaulting to 480 = 8 hours) gives the scheduler a constraint to work against. Priority validation (`__post_init__` raising `ValueError` on unknown strings) was added because a raw `str` field silently accepts typos like `"High"`, which would break any priority-ordering logic.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
