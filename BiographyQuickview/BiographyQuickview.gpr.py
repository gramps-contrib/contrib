# ------------------------------------------------------------------------
#
# Register the report
#
# ------------------------------------------------------------------------

register(
    QUICKREPORT,
    id="biographyquickview",
    name=_("Biography"),
    description=_("Display a text biography"),
    version="1.0.16",
    gramps_target_version="6.0",
    status=STABLE,
    fname="BiographyQuickview.py",
    authors=["A Guinane"],
    category=CATEGORY_QR_PERSON,
    runfunc="run",
    help_url="Addon:Biography_Quickview",
)
