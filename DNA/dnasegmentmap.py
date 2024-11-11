#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020  Nick Hall
# Copyright (C) 2020-2024  Gary Griffin
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""
DNA Gramplet
This Gramplet shows a DNA segment map.
"""
#-------------------------------------------------------------------------
#
# Gtk modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import PangoCairo
from gramps.gui.editors import EditPerson
from gramps.gui.editors import EditNote

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.plug import Gramplet
from gramps.gen.display.name import displayer as _nd
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.utils.grampslocale import GrampsLocale
from gramps.gen.config import config
import random
import re
import csv
import os
from gramps.gen.relationship import get_relationship_calculator
_ = glocale.translation.gettext

#------------------------------------------------------------------------
#
# Configuration file
#
#------------------------------------------------------------------------
CONFIG = config.register_manager('DNASegmentMap')
CONFIG.register('map.chromosome-build', 37)
CONFIG.register('map.legend-swatch-offset-y', 0)
CONFIG.register('map.show_associate_id',0)
CONFIG.register('map.maternal-background', (0.996, 0.8, 0.941, 1.0))
CONFIG.register('map.paternal-background', (0.722, 0.808, 0.902, 1.0))
CONFIG.register('map.legend-single-chromosome-y-offset', 0)
CONFIG.register('map.show-centromere',1)
CONFIG.register('map.legend-char-height',12)
CONFIG.register('map.include-citation-notes',0)
CONFIG.register('map.chromosome-x-scale',1.4)
CONFIG.register('map.chromosome-y-scale',1)
CONFIG.register('map.output-visual-segments',0)
CONFIG.register('map.grandparent-view',0)
CONFIG.register('map.output-folder',"")
#
# disabled config options
#
#CONFIG.register('map.association-string',"DNA")
#


CONFIG.init()

draw_single_chromosome = False
current_chromosome = '1'
#
# draw_grandparent_color is a quick and dirty pass at visual phasing to the grandparent. 
# The DNA segment will be painted one of 4 colors, depending on the grandparent found in the path of the tree. 
# The maternal side has 2 color options (maternal grandfather or maternal grandmother).
# The paternal side has 2 color options (paternal grandmother or paternal grandfather).
# first cousins or closer are not displayed. 
# If there is no known path based on the tree, the segment is not displayed.
#
draw_grandparent_color = False


class DNASegmentMap(Gramplet):

    def init(self):
        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()

    def db_changed(self):
        self.connect(self.dbstate.db, 'person-add', self.update)
        self.connect(self.dbstate.db, 'person-delete', self.update)
        self.connect(self.dbstate.db, 'person-update', self.update)
        self.connect(self.dbstate.db, 'family-update', self.update)
        self.connect(self.dbstate.db, 'family-add', self.update)
        self.connect(self.dbstate.db, 'family-delete', self.update)
        self.connect(self.dbstate.db, 'note-add', self.update)
        self.connect(self.dbstate.db, 'note-delete', self.update)
        self.connect(self.dbstate.db, 'note-update', self.update)
        self.connect_signal('Person',self.update)

    def build_gui(self):
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.vbox.set_margin_start(6)
        self.vbox.set_margin_end(6)
        self.vbox.set_margin_top(6)
        self.vbox.set_margin_bottom(6)
        self.vbox.set_spacing(12)
        return self.vbox


    def main(self):
        for widget in self.vbox.get_children():
            self.vbox.remove(widget)
        active_handle = self.get_active('Person')
        if active_handle:
            active = self.dbstate.db.get_person_from_handle(active_handle)
            self.relationship = get_relationship_calculator(glocale)
            random.seed(0.66) # use a fixed arbitrary number so it is concistent on redraw
            segmap = SegmentMap()
            segmap.connect('clicked', self.update)
            segmap.show_assoc_id = segmap._config.get('map.show_associate_id')
#            segmap.set_axis(_('Chr'))
            segmap.dbstate = self.dbstate
            segmap.uistate = self.uistate
            segmap.segments = []
            segmap.gender = active.gender
            segmap.active = active
            segmap.relationship = self.relationship
            include_citation_notes = segmap._config.get('map.include-citation-notes')
            association_string = "DNA"
            segmap.grandparent_depth = segmap._config.get('map.grandparent-view')
#
# Disabled Config
#
#            association_string = segmap._config.get('map.association-string')
            for assoc in active.get_person_ref_list():
                if assoc.get_relation() == association_string:
                    rgb_color = [random.random(),random.random(),random.random()]
                    associate = self.dbstate.db.get_person_from_handle(assoc.ref)
                    data, msg = self.relationship.get_relationship_distance_new(self.dbstate.db,active,associate,False, True, True)
                    if data[0][0] <= 0 : # Unrelated
                        side = 'U'
                    elif data[0][0] == 1: #parent / child
                        if self.dbstate.db.get_person_from_handle(data[0][1]).get_gramps_id() == active.get_gramps_id():
                            side = 'U'
                        else:
                            if self.dbstate.db.get_person_from_handle(data[0][1]).gender == 0:
                                side = 'M'
                            else:
                                side = 'P'
                    elif (len(data) > 1 and data[0][0] == data[1][0] and data[0][2][0] != data[1][2][0]): #shares both parents
                        side = 'U'
                    elif (len(data[0][2]) == 0): # association is descendant of active
                        side = 'U'
                    else:
                        side = data[0][2].upper()
                    # Get Notes attached to Association
                    for handle in assoc.get_note_list():
                        note = self.dbstate.db.get_note_from_handle(handle)
                        for line in note.get().split('\n'):
                            assoc_handle = assoc.ref
                            self.write_chromo(line, side, rgb_color, assoc, note, segmap)
                    # Get Notes attached to Citation which is attached to the Association
                    if include_citation_notes :
                        for citation_handle in assoc.get_citation_list():
                            citation = self.dbstate.db.get_citation_from_handle(citation_handle)
                            for handle in citation.get_note_list():
                                note = self.dbstate.db.get_note_from_handle(handle)
                                for line in note.get().split('\n'):
                                    assoc_handle = assoc.ref
                                    self.write_chromo(line, side, rgb_color, assoc, note, segmap)
            if len(segmap.segments) > 0:
                segmap.show()
                self.vbox.pack_start(segmap, True, True, 0)

    def write_chromo(self, line, side, rgb_color, assoc, note, segmap):

        if "\t" in line:
# Tabs are the field separators. Now determine THOUSEP and RADIXCHAR. Use Field 2 (Stop Pos) to see if there are THOUSEP there. Use Field 3 (SNPs) to see if there is a radixchar
            field = line.split('\t')
            if len(field) > 3:
                if "," in field[2]:
                    line = line.replace(",", "")
                elif "." in field[2]:
                    line = line.replace(".", "")
                if "," in field[3]:
                    line = line.replace(",", ".")
            else:
                associate = segmap.dbstate.db.get_person_from_handle(assoc.ref)
                id_str = _(_nd.display(associate) )
                print("Skipping: ",id_str,line)
            line = line.replace("\t", ",")
# If Tab is not the field separator, then comma is. And point is the radixchar.
        field = line.split(',')
        if len(field) < 4:
            return False
        chromo = field[0].strip()
        start = get_base(field[1])
        stop = get_base(field[2])
        try:
            cms = float(field[3])
        except:
            return False
        try:
            snp = int(field[4])
        except:
            snp = 0
        seg_comment = ''
        updated_side = side
        if len(field) > 5:
            if field[5] in { "M", "U"}: 
                updated_side = field[5].strip()
            elif field[5] in { "P"} :
                updated_side = "F"
            else:
                seg_comment = field[5].strip()
        handle = assoc.ref
        associate = segmap.dbstate.db.get_person_from_handle(assoc.ref)
        id_str = _(_nd.display(associate) )
        if segmap.show_assoc_id : 
                id_str += ' [' + associate.get_gramps_id() + ']'
        segmap.segments.append([chromo, start, stop, updated_side, cms, snp, id_str, rgb_color, associate, handle, note])
#        print(id_str,"|", chromo, "|",start, "|",stop, "|",side)

def get_base(num):
    try:
        return int(num)
    except:
        try:
            return int(float(num) * 1000000)
        except:
            return 0


#-------------------------------------------------------------------------
#
# SegmentMap class
#
#-------------------------------------------------------------------------

class SegmentMap(Gtk.DrawingArea):
    """
    A segment map of DNA data.
    """

    __gsignals__ = {'clicked': (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        Gtk.DrawingArea.__init__(self)

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK )
        self.connect('motion-notify-event', self.on_pointer_motion)
        self.connect('button-press-event', self.on_button_press)
        self.title = ''
        self.axis = ''
        self.grid_lines = True
        self.__rects = None
        self.__active = -1
        self.highlight = None

        self._config = config.get_manager('DNASegmentMap')
        build = self._config.get('map.chromosome-build')
        self.legend_swatch_offset_y = self._config.get('map.legend-swatch-offset-y')
        self.maternal_background = self._config.get('map.maternal-background')
        self.paternal_background = self._config.get('map.paternal-background')
        self.legend_single_chromosome = self._config.get('map.legend-single-chromosome-y-offset')
        self.show_centromere = self._config.get('map.show-centromere')
        self.legend_char_height = self._config.get('map.legend-char-height')
        self.x_scale = self._config.get('map.chromosome-x-scale')
        self.y_scale = self._config.get('map.chromosome-y-scale')
        self.output_segments = self._config.get('map.output-visual-segments')

        self._config.save()
        self.chromosomesThirtySeven = (
            ('1', 249250621),
            ('2', 243199373),
            ('3', 198022430),
            ('4', 191154276),
            ('5', 180915260),
            ('6', 171115067),
            ('7', 159138663),
            ('8', 146364022),
            ('9', 141213431),
            ('10', 135534747),
            ('11', 135006516),
            ('12', 133851895),
            ('13', 115169878),
            ('14', 107349540),
            ('15', 102531392),
            ('16', 90354753),
            ('17', 81195210),
            ('18', 78077248),
            ('19', 59128983),
            ('20', 63025520),
            ('21', 48129895),
            ('22', 51304566),
            ('X', 155270560))

        self.chromosomesThirtyEight = (
            ('1', 248956422),
            ('2', 242193529),
            ('3', 198295559),
            ('4', 190214555),
            ('5', 181538259),
            ('6', 170805979),
            ('7', 159345973),
            ('8', 145138636),
            ('9', 138394717),
            ('10', 133797422),
            ('11', 135086622),
            ('12', 133275309),
            ('13', 114364328),
            ('14', 107043718),
            ('15', 101991189),
            ('16', 90338345),
            ('17', 83257441),
            ('18', 80373285),
            ('19', 58617616),
            ('20', 64444167),
            ('21', 46709983),
            ('22', 50818468),
            ('X', 156040895))

        self.chromosomesThirtySix = (
            ('1', 247249719),
            ('2', 242951149),
            ('3', 199501827),
            ('4', 191273063),
            ('5', 180857866),
            ('6', 170899992),
            ('7', 158821424),
            ('8', 146274826),
            ('9', 140273252),
            ('10', 135374737),
            ('11', 134452384),
            ('12', 132349534),
            ('13', 114142980),
            ('14', 106368585),
            ('15', 100338915),
            ('16', 88827254),
            ('17', 78774742),
            ('18', 76117153),
            ('19', 63811651),
            ('20', 62435964),
            ('21', 46944323),
            ('22', 49691432),
            ('X', 154913754))
        self.centromereThirtySix = (
            ('1', 121236957, 123476957),
            ('2', 91689898, 94689898),
            ('3', 90587544, 93487544),
            ('4', 49354874, 52354874),
            ('5', 46441398, 49441398),
            ('6', 58938125, 61938125),
            ('7', 58058273, 61058273),
            ('8', 43958052, 46958052),
            ('9', 47107499, 50107499),
            ('10', 39244941, 41624941),
            ('11', 51450781, 54450781),
            ('12', 34747961, 36142961),
            ('13', 16000000, 17868000),
            ('14', 15070000, 18070000),
            ('15', 15260000, 18260000),
            ('16', 35143302, 36943302),
            ('17', 22187133, 22287133),
            ('18', 15400898, 16764896),
            ('19', 26923622, 29923622),
            ('20', 26267569, 28033230),
            ('21', 10260000, 13260000),
            ('22', 11330000, 14330000),
            ('X', 58598737, 61598737))
        self.centromereThirtySeven = (
            ('1', 121535434, 124535434),
            ('2', 92326171, 95326171),
            ('3', 90504854, 93504854),
            ('4', 49660117, 52660117),
            ('5', 46405641, 49405641),
            ('6', 58830166, 61830166),
            ('7', 58054331, 61054331),
            ('8', 43838887, 46838887),
            ('9', 47367679, 50367679),
            ('10', 39254935, 42254935),
            ('11', 51644205, 54644205),
            ('12', 34856694, 37856694),
            ('13', 16000000, 19000000),
            ('14', 16000000, 19000000),
            ('15', 17000000, 20000000),
            ('16', 35335801, 38335801),
            ('17', 22263006, 25263006),
            ('18', 15460898, 18460898),
            ('19', 24681782, 27681782),
            ('20', 26369569, 29369569),
            ('21', 11288129, 14288129),
            ('22', 13000000, 16000000),
            ('X', 58632012, 61632012))
        self.centromereThirtyEight = (
            ('1', 121700000, 125100000),
            ('2', 91800000, 96000000),
            ('3', 87800000, 94000000),
            ('4', 48200000, 51800000),
            ('5', 46100000, 51400000),
            ('6', 58500000, 62600000),
            ('7', 58100000, 62100000),
            ('8', 43200000, 47200000),
            ('9', 42200000, 45500000),
            ('10', 38000000, 41600000),
            ('11', 51000000, 55800000),
            ('12', 33200000, 37800000),
            ('13', 16500000, 18900000),
            ('14', 16100000, 18200000),
            ('15', 17500000, 20500000),
            ('16', 35300000, 38400000),
            ('17', 22700000, 27400000),
            ('18', 15400000, 21500000),
            ('19', 24200000, 28100000),
            ('20', 25700000, 30400000),
            ('21', 10900000, 13000000),
            ('22', 13700000, 17400000),
            ('X', 58100000, 63800000))
        if build == 36: 
            self.chromosomes = self.chromosomesThirtySix
            self.centromere = self.centromereThirtySix
        elif build == 38:
            self.chromosomes = self.chromosomesThirtyEight
            self.centromere = self.centromereThirtyEight
        else:
            self.chromosomes = self.chromosomesThirtySeven
            self.centromere = self.centromereThirtySeven
            build = 37
        self.labels = [chromo[0] for chromo in self.chromosomes]
# fixed colormap (partial) to use to MyHeritage color based on grandparent instead of association name
        self.colormap = {
            'U':(1,1,1),
            'M':(0,0,0.5),
            'F':(0.5,0,0),
            'FF':(0, 0, 1),
            'FM':(0, 0.5, 0),
            'MF':(1, 0, 0),
            'MM':(1, 1, 0),
            'FFF':(0,0,139/255),
            'FFM':(173/255,216/255,230/255),
            'FMF':(0,100/255,0),
            'FMM':(144/255,238/255,144/255),
            'MFF':(139/255,0,0),
            'MFM':(240/255,0.5,0.5),
            'MMF':(1,215/255,0),
            'MMM':(1,1,224/255)
        }
        self.grandparent = {
	        'f':"Father",
	        'm':"Mother",
	        "u": "Unknown",
	        'F':"Father",
	        'M':"Mother",
	        "U":"Unknown",
	        'mm':"Maternal Grandmother",
            'mf':"Maternal Grandfather",
            'fm':"Paternal Grandmother",
            'ff':"Paternal Grandfather",
            'mmm':"Maternal Grandmothers Mother",
            'mfm':"Maternal Grandfathers Mother",
            'fmm':"Paternal Grandmothers Mother",
            'ffm':"Paternal Grandfathers Mother",
            'mmf':"Maternal Grandmothers Father",
            'mff':"Maternal Grandfathers Father",
            'fmf':"Paternal Grandmothers Father",
            'fff':"Paternal Grandfathers Father"
        }
    def set_title(self, title):
        """
        Set the main chart title.
        @param title: The main chart title.
        @type title: str
        """
        self.title = title

    def set_axis(self, axis):
        """
        Set the axis title.
        @param title: The axis title.
        @type title: str
        """
        self.axis = axis

    def set_grid_lines(self, grid_lines):
        """
        Specify if grid lines should be displayed.
        @param grid_lines: True if grid lines should be displayed.
        @type grid_lines: bool
        """
        self.grid_lines = grid_lines

    def set_segments(self, segments):
        """
        Set the segment data.
        @param data: A list of segments.
        @type data: list
        """
        self.segments = segments

    def do_draw(self, cr):
        """
        A custom draw method for this widget.
        @param cr: A cairo context.
        @type cr: cairo.Context
        """
        
        global draw_grandparent_color
        
        allocation = self.get_allocation()
        context = self.get_style_context()
        fg_color = context.get_color(context.get_state())
        cr.set_source_rgba(*fg_color)
# Add English Locale to allow grandparent : grandchild DNA to be included
        en_locale = GrampsLocale(lang='en_US.UTF8')
        en_locale.language=['en']
        en_rel_calc = get_relationship_calculator(reinit=True,clocale=en_locale)
        match_grandparent = {
	        "grandfather",
	        "grandmother"
        } 
# If no active person, return
        if not self.active:
            return

# Title
       
        assoc_label_str = _('Chromosome ' )
        if draw_single_chromosome :
            assoc_label_str += current_chromosome
        else:
            assoc_label_str += 'Segment'
            
        assoc_label_str += _(' Map for '+_nd.display(self.active))
# Define grandparents and great grandparents for visual phasing. Trap if user changed tree while in this view
        try: 
            mother, father = self.relationship.get_birth_parents(self.dbstate.db,self.active)
        except :
            return
        grand_handle = {}
        if mother : 
            grand_handle['mm'], grand_handle['mf'] = self.relationship.get_birth_parents(self.dbstate.db,self.dbstate.db.get_person_from_handle(mother))
            if grand_handle['mm'] :
                grand_handle['mmm'], grand_handle['mmf'] = self.relationship.get_birth_parents(self.dbstate.db,self.dbstate.db.get_person_from_handle(grand_handle['mm']))
            else :
                grand_handle['mmm'] = None
                grand_handle['mmf'] = None
            if grand_handle['mf'] :
                grand_handle['mfm'], grand_handle['mff'] = self.relationship.get_birth_parents(self.dbstate.db,self.dbstate.db.get_person_from_handle(grand_handle['mf']))
            else :
                grand_handle['mfm'] = None
                grand_handle['mff'] = None
        else :
            grand_handle['mm'] = None
            grand_handle['mf'] = None
            grand_handle['mfm'] = None
            grand_handle['mff'] = None
            grand_handle['mmm'] = None
            grand_handle['mmf'] = None
        if father : 
            grand_handle['fm'], grand_handle['ff'] = self.relationship.get_birth_parents(self.dbstate.db,self.dbstate.db.get_person_from_handle(father))
            if grand_handle['fm'] :
                grand_handle['fmm'], grand_handle['fmf'] = self.relationship.get_birth_parents(self.dbstate.db,self.dbstate.db.get_person_from_handle(grand_handle['fm']))
            else :
                grand_handle['fmm'] = None
                grand_handle['fmf'] = None
            if grand_handle['ff'] :
                grand_handle['ffm'], grand_handle['fff'] = self.relationship.get_birth_parents(self.dbstate.db,self.dbstate.db.get_person_from_handle(grand_handle['ff']))
            else :
                grand_handle['ffm'] = None
                grand_handle['fff'] = None
        else : 
            grand_handle['fm'] = None
            grand_handle['ff'] = None
            grand_handle['fmm'] = None
            grand_handle['fmf'] = None
            grand_handle['ffm'] = None
            grand_handle['fff'] = None
        for i in 'mm','mf','fm','ff', 'mmm','mmf','mfm','mff','fmm','fmf','ffm','fff' :
            if grand_handle[i] :
                self.grandparent[i.upper()] = _nd.display(self.dbstate.db.get_person_from_handle(grand_handle[i]))
            else :
                self.grandparent[i.upper()] = self.grandparent[i]
        if self.show_assoc_id : 
            assoc_label_str += ' [' + self.active.get_gramps_id() + ']'
        self.set_title(_(assoc_label_str))

        layout = self.create_pango_layout(self.title)
        width, height = layout.get_pixel_size()
        cr.move_to((allocation.width - width) / 2, 0)
        PangoCairo.show_layout(cr, layout)

        offset = height + 5

        chr_height = 12
        spacing = 2
        self.maximum = 250000000
        self.maximum *= self.x_scale
        if draw_single_chromosome :
            for i, label in enumerate (self.chromosomes):
                if label[0] == current_chromosome: self.maximum = label[1] * self.x_scale
# Chromosome labels
        self.__chrrects = []
        label_width = 0
        if not draw_single_chromosome :
            for i, label in enumerate(self.labels):
                layout = self.create_pango_layout(label)
                width, height = layout.get_pixel_size()
                if width > label_width:
                    label_width = width
                offset_x = -(len(label)-2)* 6
                cr.move_to(offset_x, i * 2 * (chr_height + spacing) + offset+7)
                self.__chrrects.append((offset_x, i * 2 * (chr_height + spacing) + offset+7, chr_height, chr_height))
                PangoCairo.show_layout(cr, layout)

            self.set_axis(_('Chr'))
            layout = self.create_pango_layout(self.axis)
            width, height = layout.get_pixel_size()
            if width > label_width:
                label_width = width
            label_width += 5
            cr.move_to((label_width - width) / 2, 0)
            PangoCairo.show_layout(cr, layout)

        chart_width = (allocation.width - label_width) * 0.95

        bottom = len(self.chromosomes) * 2 * (chr_height + spacing) + offset

        # Ticks and grid lines
        if not draw_single_chromosome :
            tick_step, maximum = 50000000 , 250000000 * self.x_scale
            count = 0
            while count <= 250000000:
                # draw tick
                tick_pos = label_width + chart_width * count / self.maximum
                cr.move_to(tick_pos, bottom)
                cr.line_to(tick_pos, bottom + 5)
                cr.stroke()
                # draw grid line
                if self.grid_lines:
                    cr.set_dash([1, 2])
                    cr.move_to(tick_pos, bottom)
                    cr.line_to(tick_pos, (2 * spacing) + offset)
                    cr.stroke()
                    cr.set_dash([])
                count += tick_step

            offset += spacing

        # Chromosomes background
        if not draw_single_chromosome:
            cr.set_line_width(0)
            for i, chromo in enumerate(self.chromosomes):
                if self.show_centromere :
                    centloc = self.centromere[i][2]
                else:
                    centloc = self.centromere[i][1]
# draw paternal
                cr.rectangle(label_width,
                         i * 2 * (chr_height + spacing) + offset,
                         chart_width * self.centromere[i][1] / self.maximum ,
                         chr_height)
                cr.rectangle(label_width+chart_width * centloc / self.maximum,
                         i * 2 * (chr_height + spacing) + offset,
                         chart_width * (chromo[1]-centloc) / self.maximum,
                         chr_height)
                if self.show_centromere:
                    cr.move_to(label_width + chart_width * self.centromere[i][1] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset)
                    cr.line_to(label_width + chart_width * self.centromere[i][1] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[i][1] + (self.centromere[i][2] - self.centromere[i][1])/2) / self.maximum,
                        i * 2 * (chr_height + spacing) + offset + chr_height/2)
                    cr.close_path()
                    cr.move_to(label_width + chart_width * self.centromere[i][2] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset)
                    cr.line_to(label_width + chart_width * self.centromere[i][2] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[i][1] + (self.centromere[i][2] - self.centromere[i][1])/2) / self.maximum,
                        i * 2 * (chr_height + spacing) + offset + chr_height/2)
                    cr.close_path()
                cr.set_source_rgba(self.paternal_background[0], self.paternal_background[1], self.paternal_background[2], self.paternal_background[3])
                cr.fill_preserve()
                cr.set_source_rgba(*fg_color)
                cr.stroke()

# draw Maternal
                cr.rectangle(label_width,
                         i * 2 * (chr_height + spacing) + offset + chr_height,
                         chart_width * self.centromere[i][1] / self.maximum,
                         chr_height)
                cr.rectangle(label_width+chart_width * centloc / self.maximum,
                         i * 2 * (chr_height + spacing) + offset + chr_height,
                         chart_width * (chromo[1]-centloc) / self.maximum,
                         chr_height)
                if self.show_centromere:
                    cr.move_to(label_width + chart_width * self.centromere[i][1] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * self.centromere[i][1] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset + chr_height + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[i][1] + (self.centromere[i][2] - self.centromere[i][1])/2) / self.maximum,
                        i * 2 * (chr_height + spacing) + offset + chr_height + chr_height/2)
                    cr.close_path()
                    cr.move_to(label_width + chart_width * self.centromere[i][2] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * self.centromere[i][2] / self.maximum, 
                        i * 2 * (chr_height + spacing) + offset + chr_height + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[i][1] + (self.centromere[i][2] - self.centromere[i][1])/2) / self.maximum,
                        i * 2 * (chr_height + spacing) + offset + chr_height + chr_height/2)
                    cr.close_path()
                cr.set_source_rgba(self.maternal_background[0], self.maternal_background[1], self.maternal_background[2], self.maternal_background[3])
                cr.fill_preserve()
                cr.set_source_rgba(*fg_color)
                cr.stroke()
        # Grey out paternal X background for males
            if self.gender == 1: 
                cr.rectangle(label_width, 22 * 2 * (chr_height + spacing) + offset, chart_width * chromo[1] / self.maximum, chr_height)
                cr.set_source_rgba(0.8, 0.8, 0.8, 1)
                cr.fill_preserve()
                cr.set_source_rgba(*fg_color)
                cr.stroke()

        # Segments
        cr.set_line_width(1)
        self.__rects = []
        self.__legendrects = []
        self.__associates = []
        self.__notes = []
        self.__assoc_handle = []
        self.__legend_str = []
        self.__rect_count = []

        if draw_single_chromosome:
            legend_offset_y = self.legend_single_chromosome * (chr_height + spacing) + offset
            legend_offset_x = allocation.width * 0.75
        else:
            legend_offset_y = 0 * (chr_height + spacing) + offset
            legend_offset_x = allocation.width * 0.75
#        legend_offset_x = allocation.width * 0.75
        last_name = ''
        legend = _('Legend')
        if draw_grandparent_color and not draw_single_chromosome :
            legend += _(': Grandparent')
        layout = self.create_pango_layout(legend)
        cr.move_to(legend_offset_x, legend_offset_y)
        cr.set_source_rgba(*fg_color)
        PangoCairo.show_layout(cr, layout)
        legend_offset_y += chr_height + 2 * spacing
        legend_chr_height = self.legend_char_height
        chromo_count = -1
        row_num = 0
        legend_count = 0
        if draw_single_chromosome:
          maximum = self.maximum 
          for chromo, start, stop, side, cms, snp, assoc_name, rgb_color, associate, handle, note in self.segments:
            chromo_count += 1
            try:
                this_chromo = self.labels.index(chromo)
            except ValueError:
                continue
            if chromo == current_chromosome:
              if last_name != assoc_name: 
                last_name = assoc_name
                row_num += 1
# Background
                if self.show_centromere :
                    centloc = self.centromere[this_chromo][2]
                else:
                    centloc = self.centromere[this_chromo][1]
# draw paternal
                cr.rectangle(label_width, 
                        row_num * 2 * (chr_height + spacing) + offset, 
                        chart_width * self.centromere[this_chromo][1] / maximum, 
                        chr_height)
                cr.rectangle(label_width + chart_width * centloc / maximum , 
                        row_num * 2 * (chr_height + spacing) + offset, 
                        chart_width * (maximum/ self.x_scale - centloc) / maximum, 
                        chr_height)
                if self.show_centromere:
                    cr.move_to(label_width + chart_width * self.centromere[this_chromo][1] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset)
                    cr.line_to(label_width + chart_width * self.centromere[this_chromo][1] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[this_chromo][1] + (self.centromere[this_chromo][2] - self.centromere[this_chromo][1])/2) / self.maximum,
                        row_num * 2 * (chr_height + spacing) + offset + chr_height/2)
                    cr.close_path()
                    cr.move_to(label_width + chart_width * self.centromere[this_chromo][2] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset)
                    cr.line_to(label_width + chart_width * self.centromere[this_chromo][2] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[this_chromo][1] + (self.centromere[this_chromo][2] - self.centromere[this_chromo][1])/2) / self.maximum,
                        row_num * 2 * (chr_height + spacing) + offset + chr_height/2)
                    cr.close_path()
                cr.set_source_rgba(self.paternal_background[0], self.paternal_background[1], self.paternal_background[2], self.paternal_background[3])
                cr.fill_preserve()
                cr.stroke()
# draw maternal
                cr.rectangle(label_width, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height, 
                        chart_width * self.centromere[this_chromo][1] / maximum, 
                        chr_height)
                cr.rectangle(label_width+ chart_width * centloc / maximum, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height, 
                        chart_width* (maximum/ self.x_scale - centloc) / maximum, 
                        chr_height)
                if self.show_centromere:
                    cr.move_to(label_width + chart_width * self.centromere[this_chromo][1] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * self.centromere[this_chromo][1] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[this_chromo][1] + (self.centromere[this_chromo][2] - self.centromere[this_chromo][1])/2) / self.maximum,
                        row_num * 2 * (chr_height + spacing) + offset + chr_height + chr_height/2)
                    cr.close_path()
                    cr.move_to(label_width + chart_width * self.centromere[this_chromo][2] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height)
                    cr.line_to(label_width + chart_width * self.centromere[this_chromo][2] / self.maximum, 
                        row_num * 2 * (chr_height + spacing) + offset + chr_height + chr_height)
                    cr.line_to(label_width + chart_width * (self.centromere[this_chromo][1] + (self.centromere[this_chromo][2] - self.centromere[this_chromo][1])/2) / self.maximum,
                        row_num * 2 * (chr_height + spacing) + offset + chr_height + chr_height/2)
                    cr.close_path()
                cr.set_source_rgba(self.maternal_background[0], self.maternal_background[1], self.maternal_background[2], self.maternal_background[3])
                cr.fill_preserve()
                cr.stroke()
        # Grey out paternal X background for males
                if (self.gender == 1) and (current_chromosome == 'X'): 
                    cr.rectangle(label_width, row_num * 2 * (chr_height + spacing) + offset, chart_width / self.x_scale, chr_height)
                    cr.set_source_rgba(0.8, 0.8, 0.8, 1)
                    cr.fill_preserve()
                    cr.set_source_rgba(*fg_color)
                    cr.stroke()
# Legend
                cr.rectangle(legend_offset_x - legend_chr_height - 2 * spacing,
                             legend_offset_y + self.legend_swatch_offset_y,
                             legend_chr_height,
                             legend_chr_height)
                cr.set_source_rgba(rgb_color[0], rgb_color[1], rgb_color[2], 1)
                cr.fill_preserve()
                cr.stroke()
                layout = self.create_pango_layout(last_name)
                cr.move_to(legend_offset_x, legend_offset_y)
                self.__legendrects.append((legend_offset_x, legend_offset_y,len(assoc_name) * 6, legend_chr_height))
                self.__associates.append(associate)
                self.__assoc_handle.append(handle)
                self.__legend_str.append(last_name)
                cr.set_source_rgba(*fg_color)
                legend_offset_y += legend_chr_height + 2 * spacing
                PangoCairo.show_layout(cr, layout)
# Segment Info
              chr_offset = row_num * 2 * (chr_height + spacing) + offset
              chr_mult = 1
              if side[0] == 'M':
                chr_offset += chr_height
              if side == 'U':
                chr_mult = 2
              alpha_color = 1 / chr_mult
              if self.highlight == None or self.highlight == assoc_name:
                cr.rectangle(label_width + chart_width * start / maximum,
                             chr_offset,
                             chart_width * (stop-start) / maximum,
                             chr_mult * chr_height)
                self.__rects.append((label_width + chart_width * start / maximum,
                             chr_offset,
                             chart_width * (stop-start) / maximum,
                             chr_mult * chr_height))
                self.__rect_count.append(chromo_count)
                cr.set_source_rgba(rgb_color[0], rgb_color[1], rgb_color[2], alpha_color)
                cr.fill_preserve()
                cr.stroke()
                self.__notes.append(note)
# Legend entry
              if last_name != assoc_name:
                last_name = assoc_name
                print("Single ",legend_count)
                cr.rectangle(legend_offset_x - legend_chr_height - 2 * spacing,
                             legend_offset_y,
                             legend_chr_height,
                             legend_chr_height)
                cr.set_source_rgba(rgb_color[0], rgb_color[1], rgb_color[2], 1/chr_mult)
                cr.fill_preserve()
                cr.stroke()

                layout = self.create_pango_layout(last_name)
                cr.move_to(legend_offset_x, legend_offset_y)
                self.__legendrects.append((legend_offset_x, legend_offset_y,len(assoc_name) * 6, legend_chr_height))
                self.__associates.append(associate)
                self.__assoc_handle.append(handle)
                self.__legend_str.append(last_name)
                cr.set_source_rgba(*fg_color)
                legend_offset_y += legend_chr_height + 2 * spacing
                PangoCairo.show_layout(cr, layout)
        else: # Drawing all chromosome segments
          row_num = 24
          if self.grandparent_depth == 0: draw_grandparent_color = False
#
# open TSV file for writing visual phasing info
#
          if draw_grandparent_color and self.output_segments :
              try:
                  TSVfile = self.active.get_gramps_id() + ".tsv"
                  homedir = self._config.get("map.output-folder")
                  if not homedir :
                      homedir = os.environ.get('HOMEPATH')
                      if not homedir : 
                          homedir = os.environ.get('HOME')
                  dir_fd = os.open(homedir, os.O_RDONLY)
                  def opener(path, flags):
                      return os.open(path, flags, dir_fd=dir_fd)
                  csvfile = open(TSVfile, 'w', newline='',opener=opener)
                  visualphasing = csv.writer(csvfile, delimiter='\t')
                  visualphasing.writerow(['Active Person is ',TSVfile," ",_nd.display(self.active)])
                  visualphasing.writerow(["Chr","Start","Stop","cM","SNP", "Relationship","Name", "Associate"])
                  os.close(dir_fd)
              except :
                  self.output_segments = False
                  print("Cannot open TSV file. Disabling output segments")
          maximum = self.maximum 
          for chromo, start, stop, side, cms, snp, assoc_name, rgb_color, associate, handle, note in self.segments:
            chromo_count += 1
            try:
                i = self.labels.index(chromo)
            except ValueError:
                continue
            chr_offset = i * 2 * (chr_height + spacing) + offset
            chr_mult = 1
            if side[0] == 'M':
                chr_offset += chr_height
            if side == 'U':
                chr_mult = 2
#            alpha_color = 1 / chr_mult
            if self.highlight == None or self.highlight == assoc_name:
                cr.rectangle(label_width + chart_width * start / maximum,
                             chr_offset,
                             chart_width * (stop-start) / maximum,
                             chr_mult * chr_height)
                self.__rects.append((label_width + chart_width * start / maximum,
                             chr_offset,
                             chart_width * (stop-start) / maximum,
                             chr_mult * chr_height))
                self.__rect_count.append(chromo_count)
#
# Reset color here if desired. self.colormap can be used to paint based on common ancestor path
#
                if last_name != assoc_name :
                    local_color = rgb_color
                    alpha_color = 1 / chr_mult
                    if draw_grandparent_color :
                        last_name = assoc_name
                        if len(side) < 2 :
                            sub_side = side[0]
                            alpha_color = 0
                        elif len(side) == 2 :
	#
	#   translate the realtionship in English and compare vs 'grandmother' and 'grandfather'. 
	#
                            rel_string = en_rel_calc.get_one_relationship(self.dbstate.db,self.active,associate)
                            if rel_string in match_grandparent :
	# special case : associate is the grandparent, so include them
                                sub_side = side[0:2]
                            else :
                                sub_side = side[0]
                                alpha_color = 0
	# Limit to grandparents - do not include great grandparents
                        elif len(side) == 3 :
                                sub_side = side[0:2]
                        else :
                                sub_side = side[0:self.grandparent_depth+1]
                        local_color = self.colormap.get(sub_side)
                if draw_grandparent_color and self.output_segments and len(sub_side) > 1 : 
                    visualphasing.writerow([chromo, start, stop, cms, snp,sub_side, self.grandparent.get(sub_side), _nd.display(associate)])
                if not local_color :
                    local_color = [0,0,0]
                cr.set_source_rgba(local_color[0], local_color[1], local_color[2], alpha_color)
                cr.fill_preserve()
                cr.stroke()
                self.__notes.append(note)
# Legend entry
            if (last_name != assoc_name) and (not draw_grandparent_color) :
                legend_count += 1
                last_name = assoc_name
                cr.rectangle(legend_offset_x - legend_chr_height - 2 * spacing,
                             legend_offset_y + self.legend_swatch_offset_y,
                             legend_chr_height,
                             legend_chr_height)
                cr.set_source_rgba(rgb_color[0], rgb_color[1], rgb_color[2], 1/chr_mult)
                cr.fill_preserve()
                cr.stroke()

                layout = self.create_pango_layout(last_name)
                cr.move_to(legend_offset_x, legend_offset_y)
                self.__legendrects.append((legend_offset_x, legend_offset_y,len(assoc_name) * 6, legend_chr_height))
                self.__associates.append(associate)
                self.__assoc_handle.append(handle)
                self.__legend_str.append(last_name)
                cr.set_source_rgba(*fg_color)
                legend_offset_y += legend_chr_height + 2 * spacing
                PangoCairo.show_layout(cr, layout)
          if draw_grandparent_color :
                alpha_color = 1
#
# Limit to grandparent. Do not include great grandparent
#
                ordered_relationship = ["FF","FM","MF","MM"]
                if self.grandparent_depth > 1 : ordered_relationship = ["FF","FM","MF","MM", "FFF","FFM","FMF","FMM","MFF","MFM","MMF","MMM"]
                for i in ordered_relationship :
                    cr.rectangle(legend_offset_x - legend_chr_height - 2 * spacing,
                             legend_offset_y + self.legend_swatch_offset_y,
                             legend_chr_height,
                             legend_chr_height)
                    local_color = self.colormap.get(i)
                    cr.set_source_rgba(local_color[0], local_color[1], local_color[2], alpha_color)
                    cr.fill_preserve()
                    cr.stroke()
                    layout = self.create_pango_layout(self.grandparent.get(i))
                    cr.move_to(legend_offset_x, legend_offset_y)
                    cr.set_source_rgba(*fg_color)
                    legend_offset_y += legend_chr_height + 2 * spacing
                    PangoCairo.show_layout(cr, layout)        
        y_scale = max(1,row_num/20, self.y_scale, legend_count / 30 )  # rescale Y to max of user-specified and number of rows
        self.set_size_request(-1, y_scale * bottom + height + 5)

    def on_pointer_motion(self, _dummy, event):
        """
        Called when the pointer is moved.
        @param _dummy: This widget.  Unused.
        @type _dummy: Gtk.Widget
        @param event: An event.
        @type event: Gdk.Event
        """
        if self.__rects is None:
            return False
        active = -1
        tooltip_text = ''
        # Tooltip for segment map
        for i, rect in enumerate(self.__rects):
            if (event.x > rect[0] and event.x < rect[0] + rect[2] and
                    event.y > rect[1] and event.y < rect[1] + rect[3]):
                active = self.__rect_count[i]
                tooltip_text += _("\n{0}\n{1} cMs".format(self.segments[active][6], self.segments[active][4]))
                if self.segments[active][5] > 0:
                    tooltip_text += _(", ")
                    tooltip_text += glocale.format_string('%d',self.segments[active][5], grouping = True)
                    tooltip_text += _(" SNPs")
                tooltip_text += _(" : Starts at ")
                tooltip_text += glocale.format_string('%d',self.segments[active][1], grouping = True)
                tooltip_text += _(" and ends at ")
                tooltip_text += glocale.format_string('%d',self.segments[active][2], grouping = True)
                rel_strings , common_an = self.relationship.get_all_relationships(self.dbstate.db,self.active,self.segments[active][8])
#                if len(rel_strings) > 0 :
#                    tooltip_text += _("\nRelationship : {0} ".format(rel_strings[0]))
#                if len(common_an) > 0:
                j = 0
                while j < len(rel_strings) :
                    common = common_an[j]
                    rel_string_nn = rel_strings[j]
                    length = len(common)
                    commontext = ""
                    if length == 1:
                        p1 = self.dbstate.db.get_person_from_handle(common[0])
                        if common[0] in [self.segments[active][8].handle, self.active.handle]:
                            name = _nd.display(p1)
                            commontext = " " + _("{0}".format(name))
                        else :
                            name = _nd.display(p1)
                            commontext = " " + _("{0}".format(name))
                    elif length >= 2:
                        p1str = _nd.display(self.dbstate.db.get_person_from_handle(common[0]))
                        p2str = _nd.display(self.dbstate.db.get_person_from_handle(common[1]))
                        commontext = " " + _("%(ancestor1)s and %(ancestor2)s") % {
                                  'ancestor1': p1str,
                                  'ancestor2': p2str
                                  }                            
                    tooltip_text += _("\nRelationship: {0} ".format(rel_string_nn))
                    tooltip_text += _(" Ancestor: {0}".format(commontext))
                    j += 1
                tooltip_text += "\n"
        
        if active == -1:
            for i, rect in enumerate(self.__chrrects):
                if (event.x > rect[0] and event.x < rect[0] + rect[2] and
                    event.y > rect[1] and event.y < rect[1] + rect[3]):
                    tooltip_text = "Click on Chr to view a closeup"
        self.set_tooltip_text(tooltip_text)
        # Tooltip for Legend
        if active == -1:
            activeLegend = -1
            for i, rect in enumerate(self.__legendrects):
                if (event.x > rect[0] and event.x < rect[0] + rect[2] and
                    event.y > rect[1] and event.y < rect[1] + rect[3]):
                    activeLegend = i
            if activeLegend == -1:
                if self.highlight != None:
                    self.set_tooltip_text('')
                    self.highlight = None
#                    self.emit('clicked')
            else:
                if self.highlight == None:
                    self.set_tooltip_text(_('Click to make this person active\nRight-click to edit this person'))
                    self.highlight = self.__legend_str[activeLegend]
#                    self.emit('clicked')
        return False

    def on_button_press(self, _dummy, event):
        """
        Called when a mouse button is clicked.
        @param _dummy: This widget.  Unused.
        @type _dummy: Gtk.Widget
        @param event: An event.
        @type event: Gdk.Event
        """
        global draw_single_chromosome, current_chromosome, draw_grandparent_color
        active = -1
#
#   Traverse legend for pointer if not in visual phasing view
#
        if not draw_grandparent_color :
            for i, rect in enumerate(self.__legendrects):
                if (event.x > rect[0] and event.x < rect[0] + rect[2] and
                        event.y > rect[1] and event.y < rect[1] + rect[3]):
                    active = i
            if active != -1:
        # Primary Button Press
                if (event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS):
                        self.uistate.set_active(self.__assoc_handle[active], 'Person')
        #Secondary Button Press
                if (event.button == 3 and event.type == Gdk.EventType.BUTTON_PRESS):
                    try:
                        EditPerson(self.dbstate, self.uistate, [], self.__associates[active])
                    except:
                        return False
                return
#
#   Traverse painted chromosomes for pointer
#
        for i, rect in enumerate(self.__rects):
            if (event.x > rect[0] and event.x < rect[0] + rect[2] and
                    event.y > rect[1] and event.y < rect[1] + rect[3]):
                active = i
        if active != -1:
        # Secondary Button Press
            if (event.button == 3 and event.type == Gdk.EventType.BUTTON_PRESS):
                try:
                    EditNote(self.dbstate, self.uistate, [], self.__notes[active])
                except:
                    return False
            return
#
#   Traverse chromosome labels for pointer
#
        for i, rect in enumerate(self.__chrrects):
            if (event.x > rect[0] and event.x < rect[0] + rect[2] and
                    event.y > rect[1] and event.y < rect[1] + rect[3]):
                draw_single_chromosome = True
                self.emit('clicked')
                current_chromosome = self.chromosomes[i][0]
                return
#
# Pressed button but didnt hit anything. Assume meant to change back to full view
#
        if draw_single_chromosome :
            draw_single_chromosome = False
        else :
            draw_grandparent_color = not draw_grandparent_color
        self.emit('clicked')
