# -------------------------
#
# Command Line Merge
#
# -----------------------
register(
    TOOL,
    id="climerge",
    name=_("Command Line Merge"),
    category=TOOL_UTILS,
    status=STABLE,
    audience=DEVELOPER,
    fname="CliMerge.py",
    toolclass="CliMerge",
    optionclass="CliMergeOptions",
    tool_modes=[TOOL_MODE_CLI],
    authors=["M.D. Nauta"],
    authors_email=["m.d.nauta@hetnet.nl"],
    description=_("Merge primary objects via the command line."),
    version="1.0.39",
    gramps_target_version="6.0",
    help_url="https://github.com/gramps-project/addons-source/blob/maintenance/gramps60/CliMerge",
)
