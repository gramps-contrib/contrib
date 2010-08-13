sidebar_list = [("RelationshipView", _("Relationship Split View")), 
                ("EventView", _("Event Split View")), 
                ("FamilyView", _("Family Split View")),
                ("FanChartView", _("Fan Chart Split View")),
                ("GeoView", _("Geo Split View")),
                ("HtmlView", _("Html Split View")),
                ("MediaView", _("Media Split View")),
                ("NoteView", _("Note Split View")),
                ("PedigreeView", _("Pedigree Split View")),
                ("PersonListView", _("Person List Split View")),
                ("PersonTreeView", _("Person Tree Split View")),
                ("PlaceListView", _("Place List Split View")),
                ("PlaceTreeView", _("Place Tree Split View")),
                ("RepositoryView", _("Repository Split View")),
                ("SourceView", _("Source Split View")), 
                 ]

for name, trans in sidebar_list:
    register(VIEW, 
             id    = '%sSidebar' % name,
             name  = trans, 
             category = ("Splitviews", _("Splitviews")),
             description =  _("%s with a Gramplet Pane") % trans,
             version = '1.1.2',
             gramps_target_version = '3.3',
             status = STABLE,
             fname = 'sidebarviews.py',
             authors = [u"Doug Blank"],
             authors_email = ["doug.blank@gmail.com"],
             viewclass = '%sSidebar' % name,
      )
