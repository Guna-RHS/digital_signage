"""App install lifecycle hooks (see hooks.py's after_install)."""

from digital_signage.setup import seed_welcome_template


def after_install():
	"""Seeds the 'Welcome' / 'Welcome (Video)' Content Templates on a fresh
	install, so a new site has a working templated-content example out of
	the box instead of requiring the manual
	`bench execute digital_signage.setup.seed_welcome_template.run` step.
	seed_welcome_template.run() is itself idempotent (checks
	frappe.db.exists first), so this is safe even if it's ever invoked more
	than once for the same site."""
	seed_welcome_template.run()
