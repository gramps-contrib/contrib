register(GRAMPLET,
        id="Related Relatives Gramplet",
        name=_("Related Relatives Gramplet"),
        description = _("Gramplet showing relatives in a relation"),
        status = STABLE, # not yet tested with python 3
        fname="RelatedRelativesGramplet.py",
        height=230,
        expand=True,
        gramplet = 'RelatedRelativesGramplet',
        gramplet_title=_("Related Relatives"),
        version = '1.0.28',
        gramps_target_version="5.1",
        help_url = "RelatedRelativesGramplet",
        )
