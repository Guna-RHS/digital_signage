# Digital Signage (Frappe app)

Frappe control plane for the RHS digital signage platform: manages displays,
media, playlists, campaigns, schedules, and templated content generation,
and serves the sync API the player app talks to. The player itself (Tauri +
Rust + React) is a separate repository — this app is the source of truth;
the player is an autonomous, offline-capable client that syncs from it.

## Requirements

- A working [Frappe bench](https://docs.frappe.io/framework/user/en/installation)
  (Frappe v15) with a site already created
- Playwright + a headless Chromium, **only if you use the templated content
  generation feature** (Content Template / Generated Content — see below):
  ```bash
  ./env/bin/pip install playwright
  ./env/bin/python -m playwright install --with-deps chromium
  ```
  Run the second command as the **same OS user the bench workers run as**
  (usually `frappe`), not root — Playwright caches the browser under that
  user's home directory, and the worker processes won't find a browser
  installed under a different user's cache.

## Install

```bash
cd ~/frappe-bench   # your bench directory
bench get-app https://github.com/<your-org>/digital_signage.git
bench --site <your-site> install-app digital_signage
bench --site <your-site> migrate
```

This creates all the DocTypes (Display, Media, Playlist, Campaign, Schedule,
Campaign Assignment, Content Template, Generated Content, Device Credential,
Device Pairing Code, Signage State Version) under the **Digital Signage**
desk workspace.

## Usage flow

### 1. Register a display

Desk → Digital Signage → **Displays** → New. Set a `device_identifier`
(this is what the player app is configured with) and mark it Active.

### 2. Add content — the four-step chain

Four things have to exist, in this order, before anything plays on a
screen. **Every step after the first uses the black "Create" button** at
the top of the previous record's form — it opens the next form already
linked to the one you came from, so you never have to hunt down the right
record yourself:

1. **Media** — upload a file directly (**Media** → New → attach, set
   Active once it's gone through Uploaded → Validated → Active), or
   generate it from a template (see **Templated content generation**
   below).
2. **Playlist** — one or more Media, in order. Open it → **Create ▾ →
   Campaign**.
3. **Campaign** — references the Playlist, has a `priority`. This form has
   two extra sections, **Schedules** and **Assignments**, listing whatever
   already exists — and its own **Create ▾** button adds either:
   - **Schedule** — *when* the campaign is eligible (Always, a date range,
     daily, or specific weekdays/times)
   - **Campaign Assignment** — *which* Display or Display Group it applies to

**A Campaign needs at least one active Schedule *and* one active Campaign
Assignment to ever show up anywhere** — either alone is not enough. Forget
one and the campaign just silently never plays, which is confusing to
debug after the fact — so saving a Schedule or Assignment with the other
one missing pops a message telling you exactly that, with a button to
create the missing piece right there.

Higher `priority` (on Campaign) and `assignment_priority` (on the
Assignment) win when multiple campaigns are eligible for a display at the
same time — see `docs/SCHEDULING_AND_PRIORITY.md` for the exact precedence
and tie-break rules.

### 3. Pair a player to this display

Open the Display record → **Generate Pairing Code**. This produces a
one-time code (expires in 15 minutes) — give it, along with this site's
URL and the Display's `device_identifier`, to whoever is setting up the
player app (see that repo's README).

### 4. How changes reach an already-paired display

A paired player is offline-first: it plays from its own last-synced copy
of the content, and only refreshes that copy when it actually syncs.
**You don't need to do anything for that to happen** — any content change
that affects a display (activating/deactivating a Campaign, editing a
Schedule, adding an Assignment, etc.) automatically flags that display, and
its own background check-in (every ~15 seconds) picks the change up on its
own. Expect **20-30 seconds** end to end between saving a change and
seeing it take effect on screen — that's the check-in interval plus the
player actually re-rendering, not a bug.

If you don't want to wait even that long, the Display record has a
**Force Sync** button that nudges it the same way, just triggered by you
instead of the timer.

### 4. Templated content generation

Instead of manually designing an image per event: **Content Template**
defines a reusable HTML/Jinja2 layout (a background image or video, plus
placeholders for a title, subtitle, and any number of people — each with a
name, title, and optional logo). **Generated Content** is one filled-in
instance of a template — pick the template, fill in the values, add one
row per person, and click **Generate**. This renders the template with a
headless browser and creates a real, ready-to-use Media record from the
result — from there it goes into a Playlist exactly like an uploaded file.

A template's **Background Type** is either:
- **Image** — the rendered result is a still image
- **Video** — the background video plays at full opacity; the template's
  still Background Image is layered on top at low opacity (see
  **Background Overlay Opacity**, default 0.3) as a watermark/brand frame,
  and the result is a real video file, not a still frame

## Activating / deactivating — without deleting anything

Everything in this app is designed to be turned off and back on without
ever needing to delete a record:

| To stop... | Uncheck **Is Active** on... | Effect |
|---|---|---|
| One piece of content everywhere | Media | Excluded from every playlist that references it |
| One playlist item without removing it | Playlist Item's **Enabled** checkbox | Skipped during playback, stays in the list |
| A whole campaign | Campaign | Never wins scheduling, regardless of its Schedule |
| A campaign for one display only | Campaign Assignment | That display stops being eligible for it; others are unaffected |
| A schedule window | Schedule | That window is no longer considered active, even if its Campaign is |
| A display entirely | Display | The player stops receiving any content on next sync, but stays paired — no need to unpair it |

To reverse any of the above, just check the box again — nothing needs to be
recreated. There is no separate "deactivate the whole app" switch by
design: turn off what you actually mean to turn off, at the level above,
rather than an all-or-nothing kill switch that could unintentionally take
other displays offline too.

To fully **uninstall** the app (rare — only if removing this feature from
the bench entirely, not for day-to-day pausing):
```bash
bench --site <your-site> uninstall-app digital_signage
```
This is destructive (drops all its tables) — back up first
(`bench --site <your-site> backup --with-files`).

## "Why isn't my content showing?" checklist

Work through these in order — this is the exact sequence that trips people
up:

1. **Does the Campaign have at least one active Schedule?** Open the
   Campaign → check the **Schedules** section isn't empty, and that at
   least one row isn't marked inactive.
2. **Does the Campaign have at least one active Campaign Assignment**
   pointing at the right Display (or a Display Group it belongs to)?
   Check the **Assignments** section the same way.
3. **Is the Campaign itself active?** (`Is Active` checkbox on the
   Campaign form.)
4. **Is the winning Schedule's time window actually covering right now?**
   If it's not `Always`/all-day, check the recurrence type, date range,
   and start/end time.
5. **Has the display actually synced since you made the change?** Open the
   Display record — check `Last Heartbeat` is recent (within the last
   ~15-30s if the player is running) and `Last Sync At`. If it's stale,
   either wait for the next automatic check-in or click **Force Sync**.
6. **Is there a higher-priority campaign winning instead?** If multiple
   campaigns are eligible for the same display at once, only the highest
   `assignment_priority` (then Campaign `priority`) actually plays — see
   `docs/SCHEDULING_AND_PRIORITY.md`.

## Running tests

```bash
bench --site <your-site> run-tests --app digital_signage
```

See `docs/TESTING.md` for more.

## Docs

- `docs/ARCHITECTURE.md` — layered architecture, what's built
- `docs/DOMAIN_MODEL.md` — the DocTypes
- `docs/SCHEDULING_AND_PRIORITY.md` — precedence rules, tie-breaks, worked examples
- `docs/DEVICE_LIFECYCLE.md` — pairing → credential → revoke
- `docs/API_V1.md` — the device-facing API the player calls
- `docs/SYNC_PROTOCOL.md` — the sync envelope contract
- `docs/ASSET_MANAGEMENT.md` — asset manifest + download/verification
- `docs/SECURITY.md` — credential hashing, what's *not* hardened yet
- `docs/CLIENT_INTEGRATION.md` — the full flow a real client follows
- `docs/TESTING.md` — how to run the suite

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/digital_signage
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

## License

mit
