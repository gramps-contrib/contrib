# File: Birthdays.gpr.py
register(GRAMPLET,
	id='Birthdays',
	name=_("Birthdays Gramplet"),
	description = _("a gramplet that displays the birthdays of the living people"),
	status = STABLE, # not yet tested with python 3
	version = '1.0.34',
	fname="BirthdaysGramplet.py",
	height = 200,
	gramplet = 'BirthdaysGramplet',
	gramps_target_version = "5.1",
	gramplet_title = _("Birthdays Gramplet"),
	help_url = "BirthdaysGramplet",
	)
