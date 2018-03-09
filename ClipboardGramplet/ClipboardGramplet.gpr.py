#------------------------------------------------------------------------
#
# Register the Gramplet
#
#------------------------------------------------------------------------

register(GRAMPLET,
         id="Clipboard Gramplet",
         name=_("Collections Clipboard Gramplet"),
         description = _("Gramplet for grouping items"),
         status = STABLE,
         version = '1.0.31',
         gramps_target_version = "5.0",
         height=200,
         gramplet = "ClipboardGramplet",
         fname="ClipboardGramplet.py",
         gramplet_title=_("Clipboard"),
         )

