# encoding:utf-8
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020 Christian Schulze
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
import traceback
import os
import sys
import html

from gi.repository import Gtk, GdkPixbuf
from gramps.gen.const import USER_PLUGINS
from gramps.gen.config import logging
from gramps.gen.config import config
from gramps.gen.plug.utils import Zipfile

import importlib

##########################################
# Zipfile_bugfix and ModuleProvider cannot be moved to another file,
# because the gpr is evaluated with exec before writing the files
# when installing the addons.


class Zipfile_bugfix(Zipfile):
    """
    Zipfile workaround. This class doesn't work with zip files in the
    recent release.
    pr-1068: replace file() -> open()
    """
    def extractall(self, path, members=None):
        """
        Extract all of the files in the zip into path.
        """
        import os
        names = self.zip_obj.namelist()
        for name in self.get_paths(names):
            fullname = os.path.join(path, name)
            if not os.path.exists(fullname):
                os.mkdir(fullname)
        for name in self.get_files(names):
            fullname = os.path.join(path, name)
            outfile = open(fullname, 'wb') # !!!!!
            outfile.write(self.zip_obj.read(name))
            outfile.close()


class ModuleProvider:
    """
    ModuleProvider
    ==============

    This class is used to load modules, and if necessary download them first.
    """
    def __init__(self, plugin_name, uistate):
        """
        Args:
            plugin_name (str): name of the plugin where this class is used
            uistate (): uistate for dialog
        """
        self.plugin_name = plugin_name
        self.uistate = uistate

    def check_for(self, module_name, module_version):
        """
        Check if a module is available.

        Args:
            module_name (str): module name
            module_version (str): module version

        Returns:
            Module: loaded module or None
        """
        import importlib
        import sys
        import os
        from gramps.gen.const import USER_PLUGINS
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, '__version__'):
                if module.__version__ != module_version:
                    raise ImportError()
        except Exception as e:
            pass
        else:
            return module

        try:
            filename = os.path.join(
                USER_PLUGINS,
                self.plugin_name,
                module_name + '-' + module_version,
                module_name,
                '__init__.py')
            if os.path.isfile(filename):
                spec = importlib.util.spec_from_file_location(
                    module_name, filename)
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
            else:
                raise FileNotFoundError(filename)
        except Exception as e:
            pass
        else:
            return module
        return None

    def request(self, module_name, module_version, source_link):
        """
        Request a module. Either it is available, or it will be downloaded
        and loaded.

        Args:
            module_name (str): module name
            module_version (str): module version
            source_link (str): http address of the wheel

        Returns:
            Module: the loaded module
        """
        import os
        import logging
        from gramps.gen.const import USER_PLUGINS
        module = self.check_for(module_name, module_version)
        if module:
            return module

        # Users often refuse to download the modules. However, the modules
        # are required, so the user can only choose between installing the
        # requirements or uninstall the plugin. If this warning would be
        # deactivated but the requirements are not available, then an
        # ImportError Exception will be caused. So deactivating this warning
        # will cause another one.
        message = (
            _("Failed to load the required module {module_name} "
            "version {module_version}.")
            + _("\n\nIt is not possible to use {self.plugin_name} "
            "without this module. You can either uninstall this plugin, "
            "or download the module.")).format(**locals())
        logging.warning(self.plugin_name + ': ' + message)
        if self.uistate:
            from gramps.gui.dialog import QuestionDialog2
            ok_cancel = QuestionDialog2(
                _(self.plugin_name + ' Plugin'),
                _(message),
                _("Download module"),
                _("_Cancel"),
                parent=self.uistate.window)
            prompt = ok_cancel.run()
            if prompt == False:
                #cancel
                logging.info(self.plugin_name + ': ' +
                             _('The user chose to ignore the warning once.'))
                return None
            elif prompt == True:
                logging.info(self.plugin_name + ': ' +
                             _('The user chose to install the module.'))
                output_path = os.path.join(USER_PLUGINS, self.plugin_name)
                self.load_addon_file(source_link, output_path=output_path,
                                     callback=print)
                module = self.check_for(module_name, module_version)
                return module
        return None

    def load_addon_file(self, path, output_path, callback=None):
        """
        Load an module from a particular path (from URL or file system) and
        extract to output_path.
        """
        from urllib.request import urlopen
        from gramps.gen.plug.utils import urlopen_maybe_no_check_cert
        from io import StringIO, BytesIO
        global Zipfile_bugfix
        import tarfile
        import os

        download_with_curl = os.name != 'nt'

        if download_with_curl:
            output_filepath = os.path.join(output_path, os.path.basename(path))
            import subprocess
            try:
                exitCode = subprocess.Popen(
                    ['curl', '-L', path, '--output', output_filepath]).wait()
                if exitCode != 0:
                    raise RuntimeError("curl call failed")
            except Exception:
                if callback:
                    callback(_("Unable to open '%s' with curl") % path)
                return False
            path = output_filepath
        if not download_with_curl and (
            path.startswith("http://") or
            path.startswith("https://") or
            path.startswith("ftp://")):
            try:
                fp = urlopen_maybe_no_check_cert(path)
            except RuntimeWarning:
                if callback:
                    callback(_("Unable to open '%s'") % path)
                return False
        else:
            try:
                fp = open(path,'rb')
            except RuntimeWarning:
                if callback:
                    callback(_("Unable to open '%s'") % path)
                if download_with_curl:
                    os.remove(path)
                return False
        try:
            content = fp.read()
            buffer = BytesIO(content)
        except RuntimeWarning:
            if callback:
                callback(_("Error in reading '%s'") % path)
            if download_with_curl:
                os.remove(path)
            return False
        fp.close()
        if download_with_curl:
            os.remove(path)
        # file_obj is either Zipfile or TarFile
        if path.endswith(".zip") or path.endswith(".ZIP"):
            file_obj = Zipfile_bugfix(buffer)
        elif path.endswith(".tar.gz") or path.endswith(".tgz"):
            try:
                file_obj = tarfile.open(None, fileobj=buffer)
            except RuntimeWarning:
                if callback:
                    callback(_("Error: cannot open '%s'") % path)
                return False
        else:
            if callback:
                callback(_("Error: unknown file type: '%s'") % path)
            return False

        try:
            file_obj.extractall(output_path)
        except OSError:
            if callback:
                callback("OSError installing '%s', skipped!" % path)
            file_obj.close()
            return False
        file_obj.close()

        return True

    def cleanup_old_versions(self):
        raise NotImplementedError()


##########################################


life_line_chart_version_required = (1, 7, 5)
life_line_chart_version_required_str = '.'.join(
    [str(i) for i in life_line_chart_version_required])
some_import_error = False

try:
    _uistate = locals().get('uistate')

    if _uistate:  # don't bother with any of this unless GUI
        mp=ModuleProvider('LifeLineChartView', _uistate)
        if sys.version_info.major==3 and sys.version_info.minor>5:
            svgwrite = mp.request(
                'svgwrite',
                '1.4',
                'https://pypi.python.org/packages/source/s/'
                'svgwrite/svgwrite-1.4.zip'
            )
        else:
            svgwrite = True
        life_line_chart = mp.request(
            'life_line_chart',
            life_line_chart_version_required_str,
            'https://pypi.python.org/packages/source/l/'
            'life_line_chart/life_line_chart-' +
            life_line_chart_version_required_str + '.tar.gz'
        )

        fname = os.path.join(USER_PLUGINS, 'LifeLineChartView')
        icons = Gtk.IconTheme().get_default()
        icons.append_search_path(fname)
        some_import_error = life_line_chart is None or svgwrite is None

except Exception as e:
    some_import_error = True
    import_error_message = traceback.format_exc()
    logging.log(logging.ERROR, 'Failed to load LifeLineChartView plugin.\n' +
                import_error_message)


if locals().get('uistate') is None or locals().get('uistate'):
    # Right after the download the plugin is loaded without uistate
    # If the gui is available, then the error message is shown anyway
    # so here we can import to avoid additional messages.
    register(VIEW,
             id='lifelinechartancestorview',
             name=_("Life Line Ancestor Chart"),
             category=("Ancestry", _("Charts")),
             description=_("Persons and their relation in a time based chart"),
             version = '1.3.17',
             gramps_target_version="5.1",
             status=STABLE,
             fname='lifelinechartview.py',
             authors=["Christian Schulze"],
             authors_email=["c.w.schulze@gmail.com"],
             viewclass='LifeLineChartAncestorView',
             stock_icon='gramps-lifelineancestorchart-bw',
             )
    register(VIEW,
             id='lifelinechartdescendantview',
             name=_("Life Line Descendant Chart"),
             category=("Ancestry", _("Charts")),
             description=_("Persons and their relation in a time based chart"),
             version = '1.3.17',
             gramps_target_version="5.1",
             status=STABLE,
             fname='lifelinechartview.py',
             authors=["Christian Schulze"],
             authors_email=["c.w.schulze@gmail.com"],
             viewclass='LifeLineChartDescendantView',
             stock_icon='gramps-lifelinedescendantchart-bw',
             )

# prevent the view from starting if there is a problem; we still need to
# register to support plugin manager 'installed' and addon updates correctly
if locals().get('uistate'):
    from gramps.gui.pluginmanager import GuiPluginManager
    pmgr = GuiPluginManager.get_instance()
    if some_import_error:
        pmgr.hide_plugin('lifelinechartancestorview')
        pmgr.hide_plugin('lifelinechartdescendantview')
    elif 'lifelinechartancestorview' in pmgr.get_hidden_plugin_ids():
        pmgr.unhide_plugin('lifelinechartancestorview')
        pmgr.unhide_plugin('lifelinechartdescendantview')
