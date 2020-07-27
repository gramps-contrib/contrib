#------------------------------------------------------------------------
#
# Register the Addon
#
#------------------------------------------------------------------------

register(GENERAL,
         category="WebConnect",
         id="US Web Connect Pack",
         name=_("US Web Connect Pack"),
         description = _("Collection of Web sites for the US (requires libwebconnect)"),
         status = STABLE, # not yet tested with python 3
         version = '1.0.41',
         gramps_target_version = "5.1",
         fname="USWebPack.py",
         load_on_reg = True,
         depends_on = ["libwebconnect"]
         )
