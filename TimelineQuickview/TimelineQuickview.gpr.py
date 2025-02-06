# ------------------------------------------------------------------------
#
# Register the report
#
# ------------------------------------------------------------------------

register(
    QUICKREPORT,
    id="timelinequickview",
    name=_("Timeline"),
    description=_("Display a person's events on a timeline"),
    version="1.0.34",
    gramps_target_version="6.0",
    status=STABLE,
    fname="TimelineQuickview.py",
    authors=["Douglas Blank"],
    authors_email=["doug.blank@gmail.com"],
    category=CATEGORY_QR_PERSON,
    runfunc="run",
    help_url="Addon:Timeline_Quickview",
)
