# ------------------------------------------------------------------------
#
# Register the Addon
#
# ------------------------------------------------------------------------

register(
    GENERAL,
    category="WebConnect",
    id="RU Web Connect Pack",
    name=_("RU Web Connect Pack"),
    description=_("Collection of Web sites for the RU (requires libwebconnect)"),
    status=STABLE,
    version="1.0.6",
    gramps_target_version="6.0",
    fname="RUWebPack.py",
    load_on_reg=True,
    depends_on=["libwebconnect"],
    help_url="Addon:Web_Connect_Pack#Available_Web_connect_Packs",
)
