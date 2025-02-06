# ------------------------------------------------------------------------
#
# Register the Addon
#
# ------------------------------------------------------------------------

register(
    GENERAL,
    category="WebConnect",
    id="US Web Connect Pack",
    name=_("US Web Connect Pack"),
    description=_("Collection of Web sites for the US (requires libwebconnect)"),
    status=STABLE,  # not yet tested with python 3
    version="1.0.50",
    gramps_target_version="6.0",
    fname="USWebPack.py",
    load_on_reg=True,
    depends_on=["libwebconnect"],
    help_url="Addon:Web_Connect_Pack#Available_Web_connect_Packs",
)
