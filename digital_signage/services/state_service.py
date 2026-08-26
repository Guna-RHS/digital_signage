"""Affected-display resolution, schedule evaluation, priority/conflict
resolution, fallback, and effective per-display state assembly — Phase C of
the spec, all in one module since these steps compose into a single pipeline.
resolve_affected_displays is the one independent entry point, called from
doctype controllers via record_change.

Two different "what should this display know" functions, on purpose:

- resolve_effective_state: resolves all the way down to one winning
  campaign right now. Backs the desk-only preview_effective_state API —
  useful for a human to see "what's playing right now," not what devices
  sync.
- resolve_sync_state: returns the full *eligible* set (active
  display+assignment+campaign, not narrowed by schedule time or priority).
  This is what api/v1/sync.py actually sends devices — the client spec's
  non-negotiable rule is that the client owns playback timing and resolves
  schedule/priority locally (offline, at every schedule boundary, without a
  round-trip), which is only possible if it receives every eligible
  campaign's full schedule data up front, not a single server-resolved
  winner. See docs/SCHEDULING_AND_PRIORITY.md — this file's priority/tie-break
  algorithm is the specification the *client* must now implement; this
  backend's own copy of it (_active_candidates/_select_winner) exists solely
  to answer the desk preview question, not to gate what devices receive.

Known Milestone 1 simplification: the domain model has no per-Display
timezone field (heartbeat-reported client timezone is a later-milestone
concern), so `timezone_policy` is currently read but both policies resolve
"now" using the site's System Settings timezone when resolve_effective_state
needs a concrete instant. See docs/SCHEDULING_AND_PRIORITY.md.
"""

import frappe
from frappe.utils import get_time, now_datetime

from digital_signage.core.constants import (
	CONTRACT_VERSION,
	MEDIA_LIFECYCLE_ACTIVE,
	RECURRENCE_DATE_RANGE,
	RECURRENCE_SELECTED_DAYS,
	TARGET_TYPE_DISPLAY,
	TARGET_TYPE_DISPLAY_GROUP,
	WEEKDAY_FIELDS,
)
from digital_signage.core.versioning import bump_display_versions, get_server_version

# --- affected-display resolution -------------------------------------------


def resolve_affected_displays(doc):
	"""Given a changed doc, return the concrete set of Display names whose
	effective state may have changed as a result. Single reusable
	implementation per the spec — every doc_events wiring below calls this,
	nothing computes affected displays another way."""
	doctype = doc.doctype

	if doctype == "Display":
		return {doc.name}

	if doctype == "Display Group":
		return _group_member_displays(doc.name)

	if doctype == "Campaign Assignment":
		return _displays_for_assignment_fields(doc.target_type, doc.display, doc.display_group)

	if doctype == "Schedule":
		return _displays_for_assignments(_assignments_for_campaign(doc.campaign)) if doc.campaign else set()

	if doctype == "Campaign":
		return _displays_for_assignments(_assignments_for_campaign(doc.name))

	if doctype == "Playlist":
		displays = set()
		for campaign_name in _campaigns_for_playlist(doc.name):
			displays |= _displays_for_assignments(_assignments_for_campaign(campaign_name))
		return displays

	if doctype == "Media":
		displays = set()
		playlist_names = set(frappe.get_all("Playlist Item", filters={"media": doc.name}, pluck="parent"))
		for playlist_name in playlist_names:
			for campaign_name in _campaigns_for_playlist(playlist_name):
				displays |= _displays_for_assignments(_assignments_for_campaign(campaign_name))
		return displays

	return set()


def record_change(doc, reason=None):
	"""Doctype controllers call this from on_update/after_insert/on_trash."""
	reason = reason or f"{doc.doctype} {doc.name} changed"
	displays = resolve_affected_displays(doc)
	if displays:
		bump_display_versions(displays, reason)


def _group_member_displays(group_name):
	return {r.display for r in frappe.get_all("Display Group Member", filters={"parent": group_name}, fields=["display"])}


def _campaigns_for_playlist(playlist_name):
	return frappe.get_all("Campaign", filters={"playlist": playlist_name}, pluck="name")


def _assignments_for_campaign(campaign_name):
	return frappe.get_all("Campaign Assignment", filters={"campaign": campaign_name}, pluck="name")


def _displays_for_assignments(assignment_names):
	displays = set()
	if not assignment_names:
		return displays
	rows = frappe.get_all(
		"Campaign Assignment",
		filters={"name": ["in", list(assignment_names)]},
		fields=["target_type", "display", "display_group"],
	)
	for row in rows:
		displays |= _displays_for_assignment_fields(row.target_type, row.display, row.display_group)
	return displays


def _displays_for_assignment_fields(target_type, display, display_group):
	if target_type == TARGET_TYPE_DISPLAY and display:
		return {display}
	if target_type == TARGET_TYPE_DISPLAY_GROUP and display_group:
		return _group_member_displays(display_group)
	return set()


# --- schedule evaluation ----------------------------------------------------


def evaluate_schedule(schedule, at_datetime):
	"""Is `schedule` active at `at_datetime`? Pure function of the schedule
	doc + a datetime — no DB access, easy to unit test directly."""
	if not schedule.is_active:
		return False

	at_date = at_datetime.date()
	at_time = at_datetime.time()

	if schedule.recurrence_type == RECURRENCE_DATE_RANGE:
		if not (schedule.start_date and schedule.end_date):
			return False
		if not (schedule.start_date <= at_date <= schedule.end_date):
			return False
	else:
		if schedule.start_date and at_date < schedule.start_date:
			return False
		if schedule.end_date and at_date > schedule.end_date:
			return False

	if schedule.recurrence_type == RECURRENCE_SELECTED_DAYS:
		weekday_field = WEEKDAY_FIELDS[at_date.weekday()]
		if not schedule.get(weekday_field):
			return False

	if not schedule.all_day:
		start_t = get_time(schedule.start_time)
		end_t = get_time(schedule.end_time)
		if not (start_t <= at_time <= end_t):
			return False

	return True


# --- priority / conflict resolution + effective state assembly -------------


def resolve_effective_state(display_name, at_datetime=None):
	"""Desk-only preview (api/internal.preview_effective_state): gather
	candidate (assignment, campaign) pairs, filter to active + in-schedule,
	pick the single deterministic winner right now. This is NOT what
	devices sync — see resolve_sync_state for that, and the module
	docstring for why the two exist separately."""
	display = frappe.get_doc("Display", display_name)
	at_datetime = at_datetime or now_datetime()

	candidates = _active_candidates(display, at_datetime) if display.is_active else []
	winner = _select_winner(candidates)

	envelope = {
		"contract_version": CONTRACT_VERSION,
		"device_id": display.device_identifier,
		"server_version": get_server_version(display.name),
		"generated_at": now_datetime(),
		"display": _display_summary(display),
		"groups": _group_summaries_for(display.name),
		"media": [],
		"playlists": [],
		"campaigns": [],
		"schedules": [],
		"assignments": [],
		"fallback": _fallback_summary(),
	}

	if winner:
		campaign = winner["campaign"]
		playlist = frappe.get_doc("Playlist", campaign.playlist)
		envelope["campaigns"] = [_campaign_summary(campaign)]
		envelope["playlists"] = [_playlist_summary(playlist)]
		envelope["media"] = _media_summaries_for(playlist)
		envelope["assignments"] = [_assignment_summary(winner["assignment"])]
		envelope["schedules"] = [_schedule_summary(s) for s in winner["matched_schedules"]]
	else:
		fallback_playlist = _fallback_playlist()
		if fallback_playlist:
			envelope["playlists"] = [_playlist_summary(fallback_playlist)]
			envelope["media"] = _media_summaries_for(fallback_playlist)

	return envelope


def resolve_sync_state(display_name):
	"""What a device actually syncs (sync_service.build_sync_response): the
	FULL set of eligible campaigns/schedules/assignments/playlists/media for
	this display — active display+assignment+campaign, but deliberately
	*not* narrowed by current schedule time or by priority. Per the client
	spec's non-negotiable rule ("the client owns playback timing and
	evaluates its synchronized schedule locally") and section 22's worked
	example (three overlapping-priority campaigns switching through a single
	day), the client needs every schedule's full recurrence data to evaluate
	boundaries offline — a server-resolved single winner can't support that
	without re-syncing on every boundary. Contrast with resolve_effective_state,
	which still resolves to one winner for the desk preview."""
	display = frappe.get_doc("Display", display_name)

	envelope = {
		"contract_version": CONTRACT_VERSION,
		"device_id": display.device_identifier,
		"server_version": get_server_version(display.name),
		"generated_at": now_datetime(),
		"display": _display_summary(display),
		"groups": _group_summaries_for(display.name),
		"media": [],
		"playlists": [],
		"campaigns": [],
		"schedules": [],
		"assignments": [],
		"fallback": _fallback_summary(),
	}

	playlists_by_name = {}

	if display.is_active:
		campaigns_by_name = {}
		assignments = []
		schedules = []
		for candidate in _eligible_candidates(display):
			assignment, campaign = candidate["assignment"], candidate["campaign"]
			assignments.append(_assignment_summary(assignment))
			if campaign.name not in campaigns_by_name:
				campaigns_by_name[campaign.name] = campaign
				playlist = frappe.get_doc("Playlist", campaign.playlist)
				if playlist.is_active:
					playlists_by_name[playlist.name] = playlist
			for schedule_name in frappe.get_all(
				"Schedule", filters={"campaign": campaign.name, "is_active": 1}, pluck="name"
			):
				schedules.append(frappe.get_doc("Schedule", schedule_name))

		envelope["campaigns"] = [_campaign_summary(c) for c in campaigns_by_name.values()]
		envelope["schedules"] = [_schedule_summary(s) for s in schedules]
		envelope["assignments"] = assignments

	# Fallback media must be locally available offline too, whether or not
	# any campaign is currently eligible.
	fallback_playlist = _fallback_playlist()
	if fallback_playlist:
		playlists_by_name.setdefault(fallback_playlist.name, fallback_playlist)

	envelope["playlists"] = [_playlist_summary(p) for p in playlists_by_name.values()]

	media_names = set()
	for playlist in playlists_by_name.values():
		media_names.update(item.media for item in playlist.items if item.enabled)
	envelope["media"] = _media_summaries_for_names(media_names)

	return envelope


def _eligible_candidates(display):
	"""Active assignment + active campaign, direct to this display or via an
	active group it belongs to. No schedule-time or priority filtering —
	callers decide what to do with that (resolve_effective_state narrows
	further for its single-winner preview; resolve_sync_state uses the set
	as-is)."""
	group_names = frappe.get_all(
		"Display Group Member",
		filters={"display": display.name},
		pluck="parent",
	)
	active_group_names = (
		frappe.get_all("Display Group", filters={"name": ["in", group_names], "is_active": 1}, pluck="name")
		if group_names
		else []
	)

	assignment_names = set(
		frappe.get_all(
			"Campaign Assignment",
			filters={"target_type": TARGET_TYPE_DISPLAY, "display": display.name, "is_active": 1},
			pluck="name",
		)
	)
	if active_group_names:
		assignment_names |= set(
			frappe.get_all(
				"Campaign Assignment",
				filters={
					"target_type": TARGET_TYPE_DISPLAY_GROUP,
					"display_group": ["in", active_group_names],
					"is_active": 1,
				},
				pluck="name",
			)
		)

	candidates = []
	for assignment_name in assignment_names:
		assignment = frappe.get_doc("Campaign Assignment", assignment_name)
		campaign = frappe.get_doc("Campaign", assignment.campaign)
		if not campaign.is_active:
			continue
		candidates.append({"assignment": assignment, "campaign": campaign})
	return candidates


def _active_candidates(display, at_datetime):
	"""resolve_effective_state's narrowing of _eligible_candidates: only
	candidates with at least one currently-matching schedule, each carrying
	the deterministic sort_key used to pick a single winner."""
	candidates = []
	for candidate in _eligible_candidates(display):
		assignment, campaign = candidate["assignment"], candidate["campaign"]

		schedules = frappe.get_all("Schedule", filters={"campaign": campaign.name, "is_active": 1}, pluck="name")
		matched_schedules = []
		for schedule_name in schedules:
			schedule = frappe.get_doc("Schedule", schedule_name)
			if evaluate_schedule(schedule, at_datetime):
				matched_schedules.append(schedule)
		if not matched_schedules:
			continue

		specificity_rank = 0 if assignment.target_type == TARGET_TYPE_DISPLAY else 1
		candidates.append(
			{
				"assignment": assignment,
				"campaign": campaign,
				"matched_schedules": matched_schedules,
				"sort_key": (
					specificity_rank,
					-(assignment.assignment_priority or 0),
					-(campaign.revision or 0),
					campaign.name,
				),
			}
		)
	return candidates


def _select_winner(candidates):
	if not candidates:
		return None
	return min(candidates, key=lambda c: c["sort_key"])


# --- envelope summaries ------------------------------------------------------


def _display_summary(display):
	return {
		"name": display.name,
		"display_name": display.display_name,
		"is_active": display.is_active,
		"registration_status": display.registration_status,
	}


def _group_summaries_for(display_name):
	group_names = frappe.get_all("Display Group Member", filters={"display": display_name}, pluck="parent")
	if not group_names:
		return []
	return frappe.get_all(
		"Display Group",
		filters={"name": ["in", group_names], "is_active": 1},
		fields=["name", "group_name"],
	)


def _campaign_summary(campaign):
	return {
		"name": campaign.name,
		"title": campaign.title,
		"playlist": campaign.playlist,
		"priority": campaign.priority,
		"interrupt_policy": campaign.interrupt_policy,
		"revision": campaign.revision,
	}


def _playlist_summary(playlist):
	items = sorted((i for i in playlist.items if i.enabled), key=lambda i: i.sort_order)
	return {
		"name": playlist.name,
		"title": playlist.title,
		"revision": playlist.revision,
		"items": [
			{
				"media": i.media,
				"sort_order": i.sort_order,
				"image_duration_seconds": i.image_duration_seconds,
			}
			for i in items
		],
	}


def _media_summaries_for(playlist):
	return _media_summaries_for_names(item.media for item in playlist.items if item.enabled)


def _media_summaries_for_names(media_names):
	media_names = list(media_names)
	if not media_names:
		return []
	return frappe.get_all(
		"Media",
		filters={"name": ["in", media_names], "is_active": 1, "lifecycle_status": MEDIA_LIFECYCLE_ACTIVE},
		fields=["name", "title", "media_type", "file", "mime_type", "file_size", "sha256", "asset_version"],
	)


def _assignment_summary(assignment):
	return {
		"name": assignment.name,
		"campaign": assignment.campaign,
		"target_type": assignment.target_type,
		"display": assignment.display,
		"display_group": assignment.display_group,
		"assignment_priority": assignment.assignment_priority,
	}


def _schedule_summary(schedule):
	return {
		"name": schedule.name,
		"campaign": schedule.campaign,
		"recurrence_type": schedule.recurrence_type,
		"timezone_policy": schedule.timezone_policy,
		"all_day": schedule.all_day,
		"start_date": schedule.start_date,
		"end_date": schedule.end_date,
		"start_time": schedule.start_time,
		"end_time": schedule.end_time,
		"monday": schedule.monday,
		"tuesday": schedule.tuesday,
		"wednesday": schedule.wednesday,
		"thursday": schedule.thursday,
		"friday": schedule.friday,
		"saturday": schedule.saturday,
		"sunday": schedule.sunday,
	}


def _fallback_playlist():
	default_playlist = frappe.db.get_single_value("Digital Signage Settings", "default_playlist")
	if not default_playlist:
		return None
	playlist = frappe.get_doc("Playlist", default_playlist)
	return playlist if playlist.is_active else None


def _fallback_summary():
	return {"default_playlist": frappe.db.get_single_value("Digital Signage Settings", "default_playlist")}
