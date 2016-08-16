#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2012 Nick Hall
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

register(VIEW,
id = 'QuiltView',
name = _('Quilt Chart'),
category = ('Ancestry', _('Charts')),
description =  _('The view shows a quilt chart visualisation of a family tree'),
version = '1.0.1',
gramps_target_version = '5.0',
status = STABLE,
fname = 'QuiltView.py',
authors = ['Nick Hall', 'Serge Noiraud'],
authors_email = ['nick__hall@hotmail.com', 'serge.noiraud@free.fr'],
viewclass = 'QuiltView',
)
