#-------------------------
#
# Command Line Merge
#
#-----------------------
register(TOOL,
    id    = 'climerge',
    name  = "Command Line Merge",
    category = TOOL_UTILS,
    status = STABLE,
    fname = 'CliMerge.py',
    toolclass = 'CliMerge',
    optionclass = 'CliMergeOptions',
    tool_modes = [TOOL_MODE_CLI],
    authors = ["M.D. Nauta"],
    authors_email = ["m.d.nauta@hetnet.nl"],
    description  = _("Merge primary objects via the command line."),
    version = '1.0.4',
    gramps_target_version = '3.5',
)
