# Scheduling and Priority

## Who resolves this: the client, not this backend

For a given `(display, timestamp)`, there is exactly one deterministic
answer — but as of the client-player integration work, **the client resolves
it, not this backend.** `GET sync.get` (`api/v1/sync.py`, backed by
`state_service.resolve_sync_state`) sends every currently-*eligible*
campaign (active display/assignment/campaign) with its full schedule data,
un-narrowed by current time or priority. The rules below are the algorithm
the **Rust client's scheduler** implements against that data, offline, so it
can switch between campaigns at schedule boundaries throughout a day without
a round-trip to this server (see the worked example lower in this doc — it
only works if the client has every campaign's full schedule up front).

This backend keeps its own copy of the same algorithm
(`state_service.resolve_effective_state` — `_active_candidates`,
`_select_winner`, `evaluate_schedule`) purely to answer "what's playing on
this display right now" for the desk-only `preview_effective_state` admin
method (`api/internal.py`). That copy is real, tested
(`test_priority_resolution.py`, `test_schedule_evaluation.py`), and kept in
sync with the rules below — but it is not what governs device playback.
Devices never call it.

## Pipeline

1. **Filter to active only.** Display must be active, or nothing is
   considered at all (goes straight to fallback). Campaign must be active.
   Campaign Assignment must be active. Display Group (if going through one)
   must be active.
2. **Apply date/time/recurrence filters** — `evaluate_schedule`. A campaign
   with zero Schedules, or zero *matching* Schedules at the given time, is
   never a candidate — a Schedule is what gates "is this campaign live right
   now"; there's no such thing as an always-on Campaign without at least one
   Schedule saying so (an `Always`-recurrence Schedule is how you express
   that explicitly).
3. **Rank remaining candidates**, in order:
   1. **Specificity**: a direct `Display` assignment always beats a
      `Display Group` assignment for the same display, regardless of
      priority. (This is deliberately checked *before* priority — a
      lower-priority direct assignment still wins over a higher-priority
      group assignment.)
   2. **`assignment_priority`** (higher wins) — this is the field on
      **Campaign Assignment**, not `Campaign.priority`, because it's the
      assignment (a specific campaign→display/group binding) that's in
      conflict, not the campaign in the abstract. `Campaign.priority` is
      exposed in the envelope and reserved for a future ranking use, but is
      not part of Milestone 1's winner selection.
   3. **Campaign `revision`** (higher/newer wins) — the final tie-break
      before falling back to identity. `revision` increments on every save
      of that Campaign (see `DOMAIN_MODEL.md`).
   4. **Campaign name**, ascending — a completely arbitrary but *stable*
      last resort so two identical-priority, identical-revision candidates
      still resolve the same way every time, never by database/query order.
4. **If nothing survives filtering**, use the fallback (below).

## Fallback

Exactly one explicit fallback: `Digital Signage Settings.default_playlist`.
If it's set and that playlist is active, its media becomes the envelope's
`playlists`/`media`. If it's unset, or set to a now-inactive playlist, the
envelope is blank (`playlists: []`, `media: []`) — never an undefined state.
The `fallback` key in the envelope always reports the *configured* default,
even when a real campaign won — it's descriptive metadata, not a signal that
fallback was actually used.

## Worked example: direct beats group despite lower priority

- Display `D1` is a member of Display Group `G1`.
- Campaign `A` (priority 1) is assigned directly to `D1` with
  `assignment_priority = 1`.
- Campaign `B` (priority 1) is assigned to `G1` with `assignment_priority = 100`.
- Both have `Always` schedules and are active.

`D1` shows Campaign `A`. Specificity is checked before priority — `100 > 1`
never gets compared, because the direct/group split already decided it.

## Worked example: tie-break chain

- Two Campaigns, `C1` and `C2`, both assigned directly to the same Display
  with equal `assignment_priority`.
- If `C1.revision > C2.revision` (e.g. `C1` was edited more recently), `C1`
  wins.
- If revisions are also equal, whichever campaign's `name` sorts first
  alphabetically wins (e.g. `CAMP-00001` beats `CAMP-00002`) — consistently,
  every time `resolve_effective_state` runs, not just once.

## Schedule evaluation

`evaluate_schedule(schedule, at_datetime)` is a pure function — no DB access,
easy to reason about and unit test directly:

- `Always`: matches any date (unless `start_date`/`end_date` are also set, in
  which case they still bound it — Always/Daily/Selected Days can optionally
  be date-bounded).
- `Date Range`: requires both `start_date` and `end_date`; matches iff
  `start_date <= at_date <= end_date`.
- `Daily`: like Always but conceptually "every day" — day-of-week is
  ignored either way once you're not on Selected Days.
- `Selected Days`: matches only if the weekday of `at_date` has its
  corresponding `monday`..`sunday` checkbox set.
- Time window: only applied when `all_day` is unchecked (see below); when
  applied, matches iff `start_time <= at_time <= end_time`. No overnight
  wraparound (`end_time < start_time` is rejected at save time).

### The `all_day` field, and why it exists

Frappe's own `frappe.model.create_new.set_dynamic_default_values` defaults
**every** `Time`-fieldtype field with no explicit value to `nowtime()` on
insert — this is framework behavior, not a bug in this app, and it means
`start_time`/`end_time` being `None` can never be relied on to mean "no time
restriction." A Schedule saved via the desk with those fields left blank
would silently get near-current-time values instead of staying empty.

`all_day` (Check, default checked) is the actual source of truth for "does
this schedule have a time restriction at all." `start_time`/`end_time` are
only read by `evaluate_schedule` and validated by `schedule_service.py` when
`all_day` is unchecked. This was caught during Milestone 1 by
`test_schedule_evaluation.py` failing (`Always` recurrence unexpectedly not
matching), not discovered later against real data — see
`digital_signage/digital_signage/doctype/schedule/schedule.json`'s `all_day`
field description for the same note in-code.

## Timezone policy — known Milestone 1 limitation

`timezone_policy` (`Display Local` / `Business Timezone`) is stored and
validated as required, but the domain model has **no per-display timezone
field yet** — a display's physical timezone is something Milestone 2's
heartbeat would report, not something known today. Both policy values
currently resolve "now" using the site's System Settings timezone
(`frappe.utils.now_datetime()`'s default behavior) — there is, today, no
behavioral difference between the two policies. This is intentional and
documented rather than silently wrong: `resolve_effective_state`'s caller can
always pass an explicit `at_datetime` (already in whatever frame is correct)
to sidestep this entirely, which is exactly what the test suite does. Once
Milestone 2 captures a display's real timezone via heartbeat, `Display Local`
should switch to using it.
