import datetime

from frappe.tests.utils import FrappeTestCase

from digital_signage.services.state_service import evaluate_schedule
from digital_signage.tests.factories import make_campaign, make_media, make_playlist, make_schedule


class TestScheduleEvaluation(FrappeTestCase):
	def setUp(self):
		media = make_media(media_type="Video")
		playlist = make_playlist(items=[{"media": media.name, "sort_order": 1, "enabled": 1}])
		self.campaign = make_campaign(playlist.name)

	def test_always_recurrence_matches_any_time(self):
		schedule = make_schedule(self.campaign.name, recurrence_type="Always")
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2026, 1, 1, 3, 0)))
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2030, 6, 15, 23, 59)))

	def test_inactive_schedule_never_matches(self):
		schedule = make_schedule(self.campaign.name, recurrence_type="Always", is_active=0)
		self.assertFalse(evaluate_schedule(schedule, datetime.datetime(2026, 1, 1, 3, 0)))

	def test_date_range_window(self):
		schedule = make_schedule(
			self.campaign.name,
			recurrence_type="Date Range",
			start_date=datetime.date(2026, 3, 1),
			end_date=datetime.date(2026, 3, 10),
		)
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2026, 3, 5, 12, 0)))
		self.assertFalse(evaluate_schedule(schedule, datetime.datetime(2026, 2, 28, 12, 0)))
		self.assertFalse(evaluate_schedule(schedule, datetime.datetime(2026, 3, 11, 0, 0)))

	def test_time_window(self):
		schedule = make_schedule(
			self.campaign.name,
			recurrence_type="Always",
			start_time=datetime.time(9, 0),
			end_time=datetime.time(17, 0),
		)
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2026, 1, 1, 12, 0)))
		self.assertFalse(evaluate_schedule(schedule, datetime.datetime(2026, 1, 1, 8, 0)))
		self.assertFalse(evaluate_schedule(schedule, datetime.datetime(2026, 1, 1, 18, 0)))

	def test_daily_recurrence_ignores_day_of_week(self):
		schedule = make_schedule(
			self.campaign.name,
			recurrence_type="Daily",
			start_time=datetime.time(8, 0),
			end_time=datetime.time(10, 0),
		)
		# 2026-01-05 is a Monday, 2026-01-10 is a Saturday — both should match.
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2026, 1, 5, 9, 0)))
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2026, 1, 10, 9, 0)))

	def test_selected_days_recurrence(self):
		schedule = make_schedule(self.campaign.name, recurrence_type="Selected Days", monday=1, friday=1)
		# 2026-01-05 = Monday, 2026-01-06 = Tuesday, 2026-01-09 = Friday
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2026, 1, 5, 12, 0)))
		self.assertFalse(evaluate_schedule(schedule, datetime.datetime(2026, 1, 6, 12, 0)))
		self.assertTrue(evaluate_schedule(schedule, datetime.datetime(2026, 1, 9, 12, 0)))

	def test_overlapping_schedules_each_evaluated_independently(self):
		morning = make_schedule(
			self.campaign.name, recurrence_type="Always", start_time=datetime.time(6, 0), end_time=datetime.time(12, 0)
		)
		afternoon = make_schedule(
			self.campaign.name, recurrence_type="Always", start_time=datetime.time(10, 0), end_time=datetime.time(18, 0)
		)
		overlap_time = datetime.datetime(2026, 1, 1, 11, 0)
		self.assertTrue(evaluate_schedule(morning, overlap_time))
		self.assertTrue(evaluate_schedule(afternoon, overlap_time))
