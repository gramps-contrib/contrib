#------------------------------------------------------------------------
#
# Register the Gramplet
#
#------------------------------------------------------------------------

register(GRAMPLET,
         id="etree Gramplet",
         name=_("etree Gramplet"),
         description = _("Gramplet for testing etree with Gramps XML"),
         status = STABLE, # not yet tested with python 3
         version = '1.0.3',
         gramps_target_version = "5.1",
         include_in_listing = False,
         height = 400,
         gramplet = "etreeGramplet",
         fname ="etreeGramplet.py",
         gramplet_title =_("etree"),
         )
