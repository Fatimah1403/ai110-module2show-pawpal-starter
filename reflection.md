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

My scheduler works against three constraints. The first is **priority** — every task is `"high"`, `"medium"`, or `"low"`, and the default ordering places high-priority tasks first so the things that matter most for the pet get scheduled before the day fills up. The second is a **time budget** (`available_minutes`): the builder only places a task if it still fits in the remaining time, and anything that overflows is reported as skipped instead of silently dropped. The third is **time-of-day preferences** — a task can be pinned to a specific start time with `earliest_minute` (for example a morning walk or a medication window), and the builder treats that as the earliest the task may begin.

I decided priority mattered most because the whole point of the app is to help a busy owner stay consistent with the *important* care first. Time came second, because a plan that ignores how many minutes the owner actually has isn't realistic. Pinned times came last: they're useful, but only some tasks genuinely need a fixed slot, so I made them optional rather than required. When I added time-based sorting later, I kept priority sorting as the default so those two constraints could be chosen between (`sort_by="priority"` vs `"time"`) instead of one silently overriding the other.

**b. Tradeoffs**

One deliberate tradeoff is in **conflict detection: it only inspects *pinned* tasks** — those given an explicit `earliest_minute` — and it *reports* overlaps as warnings rather than automatically resolving them.

`detect_conflicts_across()` builds each pinned task's intended window (`earliest_minute` → `earliest_minute + duration_minutes`) and flags any two whose windows overlap, within one pet or across pets. This is a genuine overlap check on *durations*, not just exact start-time matches — an 8:00 AM walk and an 8:15 AM feeding still collide. But it makes two intentional simplifications:

1. **Unpinned tasks are ignored by the cross-pet check.** A task with no requested time has no fixed window to compare, so it can't "conflict" until the per-pet scheduler places it. The greedy `_build()` then sequences those tasks back-to-back, so within a single pet they never overlap by construction.
2. **Conflicts are surfaced, not auto-fixed.** When two pets are both booked at 8:00 AM, the scheduler warns the owner instead of silently moving one, because it can't know which pet the owner would rather delay.

**Why it's reasonable here:** the app is a *planning aid* for a human owner, not an autonomous dispatcher. Pinned tasks are exactly the ones with real-world time constraints (a morning walk, a medication window), so those are where a missed conflict actually hurts. Keeping the check pinned-only keeps it lightweight and O(n log n) after sorting, and it never raises — it just returns warning strings — so a conflict degrades into a helpful message rather than a crash. Leaving the final call to the owner respects that they have context (which pet is more flexible today) that the scheduler doesn't.

---

## 3. AI Collaboration

**a. How you used AI**

I used my AI coding assistant across the whole build, but in different ways at each phase. Early on I used it for **design brainstorming** — talking through whether a schedule should return `Task`s or something richer, which is how I landed on adding the `ScheduledTask` wrapper. During implementation I used it mostly for **incremental feature work**: I'd describe one behavior (sorting by time, recurring tasks, conflict detection) and have it draft the method, then I'd read it, adjust, and run the tests. I also leaned on it for **explaining concepts** — for example how `timedelta` handles date math and why sorting `"HH:MM"` strings lexically is a trap — which helped me make better decisions rather than just pasting code.

The features that were most effective for me were: (1) **inline, file-aware edits** — having it read `pawpal_system.py` and make a targeted change I could immediately run beat copy-pasting from a chat window; (2) **running the tests and `main.py` after each change**, so I got real feedback (pass/fail, actual output) instead of guessing; and (3) **asking "how" questions before "do it" questions** — prompts like "what's the cleanest way to sort by time, and how do lambdas work as a sort key" gave me the understanding to judge the code, and turned out to be far more useful than just "write the sort function."

Keeping **separate chat sessions for different phases** helped me stay organized. Each phase (design, core scheduling, recurring tasks, conflict detection, documentation) had its own session with a clear goal, so the context stayed focused and I could reason about one feature at a time without an enormous thread mixing everything together. It also made it easier to go back and see *why* a decision was made in a given phase, because that reasoning lived in that phase's conversation.

**b. Judgment and verification**

The clearest moment I didn't accept a suggestion as-is was during the conflict-detection phase. My demo was printing three conflict warnings at 8:00 AM and the assistant offered to "clean it up" by moving the conflict demo above the auto-recurring step, claiming that would reduce it to a single warning. I paused and asked it to confirm before changing anything — and when it actually traced through the code, it turned out the reorder wouldn't change the count at all, because the morning walk is pinned to 8:00 whether or not it's been completed. So I kept the demo where it was. The output was correct all along; the "cleanup" was based on a wrong assumption. I also turned down an offered refactor of `_conflicts_from()` once I understood it was already O(n) and the change was purely cosmetic.

The main way I verified suggestions was by **running things**: `python -m pytest` after every change, and `python main.py` to see the real output. I wrote tests specifically for the risky parts (the `None`-vs-`int` sort, the exact-time conflict, the daily/weekly rollover) so I wasn't taking the AI's word that they worked. When a suggestion touched design rather than a single line, I asked it to explain the tradeoff first and only accepted it if the reasoning held up.

The biggest thing I learned about being the **"lead architect"** is that the AI is very good at producing plausible code quickly, but *I* have to own the design and the definition of "correct." It will confidently propose changes that sound reasonable and are subtly wrong (like the reorder above), so my job was to keep the mental model of how the system fits together, insist on verification, and say no when a suggestion added complexity without adding value. Working fast with a powerful tool made that discipline *more* important, not less.

---

## 4. Testing and Verification

**a. What you tested**

I ended up with 22 tests in `test_pawpal.py` covering every scheduling behavior. For the core algorithms I tested: sorting returns tasks in chronological order (and un-pinned tasks sort last instead of crashing); completing a daily task creates a new task for the next day (and weekly adds seven days, and `as_needed` doesn't repeat); and the scheduler flags two tasks booked at the same time, both within one pet and across pets. I also tested the schedule builder itself — start times chaining correctly, a task fitting when its duration exactly equals the remaining time, and an oversized task being skipped while a smaller one still fits — plus filtering by pet name and status, and validation rejecting bad `priority`/`frequency` values.

These tests were important because they target the places most likely to break silently. The sorting test protects against a `None`-vs-`int` comparison crash that a naive sort key would hit. The recurrence test includes a year-boundary rollover (Dec 31 → Jan 1), which is exactly the case I'd get wrong if I did the date math by hand instead of trusting `timedelta`. And the fit-boundary test locks in the `<=` comparison so a future change can't quietly start dropping tasks that should fit.

**b. Confidence**

I'm fairly confident — about a 4 out of 5. All 22 tests pass, and they cover the core behaviors plus the edge cases I considered highest-risk (empty pet, exact-time conflict, calendar rollover, fit boundary, invalid input). What holds me back from a 5 is that the tests are behavior-focused rather than exhaustive, and the Streamlit UI in `app.py` has no automated tests — I verified it by launching it and clicking through, not with a test suite.

If I had more time, the edge cases I'd test next are: recurring tasks interacting with the daily fit/skip logic over several simulated days (does the list grow in a way that stays sensible?); overlapping *pinned* tasks where the second one gets pushed so far it no longer fits; and time math around midnight, since `minutes_to_clock` wraps with a modulo and I'd want to confirm nothing schedules past the end of the day in a confusing way.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with how the scheduling logic grew from a simple priority sort into something that handles time budgets, pinned times, recurrence, and conflicts — without turning into a mess. Splitting responsibilities helped a lot: `Task.next_occurrence()` just computes the next task and `Pet.complete_task()` owns adding it to the list, and the conflict detector is a pure function that returns warnings and never raises. Keeping each piece small and testable meant I could add features one at a time and trust the earlier ones still worked because the tests kept passing.

**b. What you would improve**

If I had another iteration, I'd unify the two conflict paths. Right now `detect_conflicts()` reports delays and non-fits for a single pet's built plan, while `detect_conflicts_across()` checks pinned-task overlaps for the whole household — they answer related questions in different ways, and a user could reasonably expect one "here's everything wrong with today" view. I'd also give recurring tasks a real notion of "due today" so completing one doesn't just append the next occurrence immediately; instead the plan would show only what's actually due on the selected day. And I'd add automated tests for the Streamlit UI so it isn't the one untested layer.

**c. Key takeaway**

The most important thing I learned is that with a powerful AI assistant, my real job is being the architect and the verifier, not the typist. The AI could generate a working method in seconds, but it couldn't decide what "correct" meant for this app, and it occasionally proposed confident changes that were subtly wrong. Holding the overall design in my head, insisting on running the tests and the app after every change, and being willing to reject a suggestion that added complexity without value is what kept the system clean. Speed from the tool made that judgment more valuable, not less.
