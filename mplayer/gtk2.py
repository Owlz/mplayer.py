# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011  Darwin M. Bautista <djclue917@gmail.com>
#
# This file is part of PyMPlayer.
#
# PyMPlayer is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyMPlayer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyMPlayer.  If not, see <http://www.gnu.org/licenses/>.

from subprocess import PIPE
from functools import partial

import gtk
import gobject

from mplayer.core import Player
from mplayer import misc


__all__ = ['GPlayer', 'GtkPlayerView']


class GPlayer(Player):
    """Player subclass with GTK/GObject integration."""

    def __init__(self, args=(), stdout=PIPE, stderr=None, autospawn=True):
        super(GPlayer, self).__init__(args, autospawn=False)
        self._stdout = _StdoutWrapper(handle=stdout)
        self._stderr = _StderrWrapper(handle=stderr)
        if autospawn:
            self.spawn()


class GtkPlayerView(gtk.Socket):

    __gsignals__ = {
        'complete': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    def __init__(self):
        super(GtkPlayerView, self).__init__()
        self._mplayer = GPlayer(['-idx', '-fs', '-osdlevel', '0',
            '-really-quiet', '-msglevel', 'global=6', '-fixed-vo'], autospawn=False)
        self._mplayer.stdout.connect(self._handle_data)
        self.connect('destroy', self._on_destroy)
        self.connect('hierarchy-changed', self._on_hierarchy_changed)

    def __getattr__(self, name):
        # Don't expose some properties
        if name in ['args', 'spawn', 'quit']:
            # Raise an AttributeError
            return self.__getattribute__(name)
        try:
            attr = getattr(self._mplayer, name)
        except AttributeError:
            # Raise an AttributeError
            return self.__getattribute__(name)
        else:
            return attr

    def _on_hierarchy_changed(self, *args):
        if self.parent is not None:
            self._mplayer.args += ['-wid', self.get_id()]
            self._mplayer.spawn()
        else:
            self._on_destroy()

    def _on_destroy(self, *args):
        self._mplayer.quit()

    def _handle_data(self, data):
        if data.startswith('EOF code'):
            self.emit('complete')


class _StderrWrapper(misc._StderrWrapper):

    def __init__(self, **kwargs):
        super(_StderrWrapper, self).__init__(**kwargs)
        self._tag = None

    def _attach(self, fobj):
        super(_StderrWrapper, self)._attach(fobj)
        self._tag = gobject.io_add_watch(self._file.fileno(),
            gobject.IO_IN | gobject.IO_PRI, self._process_output)

    def _detach(self):
        gobject.source_remove(self._tag)
        super(_StderrWrapper, self)._detach()


class _StdoutWrapper(_StderrWrapper, misc._StdoutWrapper):
    pass


# Register PyGTK type
gobject.type_register(GtkPlayerView)


if __name__ == '__main__':
    import sys

    w = gtk.Window()
    w.set_size_request(640, 480)
    w.set_title('GtkPlayer')
    w.connect('destroy', gtk.main_quit)
    p = GtkPlayerView()
    p.connect('complete', gtk.main_quit)
    w.add(p)
    w.show_all()
    p.loadfile(sys.argv[1])
    gtk.main()
