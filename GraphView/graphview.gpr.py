register(VIEW,
    id    = 'graphview',
    name  = _("Graph View"),
    category = ("Ancestry", _("Charts")),
    description =  _("Dynamic and interactive graph of relations"),
    version = '1.0.141',
    gramps_target_version = "5.2",
    status = STABLE,
    fname = 'graphview.py',
    authors = ["Gary Burton"],
    authors_email = ["gary.burton@zen.co.uk"],
    viewclass = 'GraphView',
    icons = [('gramps-graph', _('Graph View'))],
    stock_icon = 'gramps-graph',
    requires_gi=[('GooCanvas', '2.0,3.0')],
    requires_exe=['dot'],
)
