from gi.repository import GObject
from gi.repository import MyPaintGegl

from cellist import CelList


class Cel(object):
    def __init__(self, graph):
        self._gegl_surface = MyPaintGegl.TiledSurface()
        self.surface = self._gegl_surface.interface()
        self.surface_node = graph.create_child("gegl:buffer-source")
        self.surface_node.set_property("buffer", self._gegl_surface.get_buffer())


class XSheet(GObject.GObject):
    __gsignals__ = {
        "frame-changed": (GObject.SignalFlags.RUN_FIRST, None, []),
        "layer-changed": (GObject.SignalFlags.RUN_FIRST, None, []),
    }

    def __init__(self, frames_length=24, layers_length=3):
        GObject.GObject.__init__(self)

        self._frames_length = frames_length
        self.frame_idx = 0
        self.layer_idx = 0
        self.layers = [CelList() for x in range(layers_length)]
        self._play_hid = None

    def get_layers(self):
        return self.layers

    def go_to_frame(self, frame_idx):
        cant_go = (frame_idx < 0 or frame_idx > self.frames_length-1 or
                   frame_idx == self.frame_idx)
        if cant_go:
            return False

        self.frame_idx = frame_idx

        self.emit("frame-changed")
        return True

    def previous_frame(self, loop=False):
        if not loop:
            if self.frame_idx == 0:
                return False
        else:
            if self.frame_idx == 0:
                self.frame_idx = self.frames_length-1
                return True

        self.frame_idx -= 1

        self.emit("frame-changed")
        return True

    def next_frame(self, loop=False):
        if not loop:
            if self.frame_idx == self.frames_length-1:
                return False
        else:
            if self.frame_idx == self.frames_length-1:
                self.frame_idx = 0
                return True

        self.frame_idx += 1

        self.emit("frame-changed")
        return True

    def play(self):
        if self._play_hid is not None:
            return False

        self._play_hid = GObject.timeout_add(42, self.next_frame, True)
        return True

    def stop(self):
        if self._play_hid is None:
            return False

        GObject.source_remove(self._play_hid)
        self._play_hid = None
        return True

    @property
    def is_playing(self):
        return self._play_hid is not None

    def previous_layer(self):
        if self.layer_idx == 0:
            return False

        self.layer_idx -= 1

        self.emit("layer-changed")
        return True

    def next_layer(self):
        if self.layer_idx == self.layers_length-1:
            return False

        self.layer_idx += 1

        self.emit("layer-changed")
        return True

    def get_cel(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.frame_idx

        if layer_idx is None:
            layer_idx = self.layer_idx

        return self.layers[layer_idx][frame_idx]

    def get_cel_relative(self, frame_diff=0, layer_diff=0):
        frame_idx = self.frame_idx + frame_diff
        layer_idx = self.layer_idx + layer_diff
        return self.layers[layer_idx][frame_idx]

    def get_cel_relative_by_cels(self, cel_diff, frame_diff=0, layer_diff=0):
        frame_idx = self.frame_idx + frame_diff
        layer_idx = self.layer_idx + layer_diff
        return self.layers[layer_idx].get_relative(frame_idx, cel_diff)

    def has_cel(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.frame_idx

        if layer_idx is None:
            layer_idx = self.layer_idx

        return not self.layers[layer_idx].is_unset_at(frame_idx)

    def add_cel(self, graph, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.frame_idx

        if layer_idx is None:
            layer_idx = self.layer_idx

        if self.layers[layer_idx].is_unset_at(frame_idx):
            self.layers[layer_idx][frame_idx] = Cel(graph)
            self.emit("frame-changed")

    def clear_cel(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.frame_idx

        if layer_idx is None:
            layer_idx = self.layer_idx

        cel = self.layers[layer_idx][frame_idx]
        if cel is None:
            # FIXME will fail in blanks
            del self.layers[layer_idx][frame_idx]
        else:
            self.layers[layer_idx][frame_idx] = None
        self.emit("frame-changed")

    @property
    def frames_length(self):
        return self._frames_length

    @property
    def layers_length(self):
        return len(self.layers)

    @property
    def frames_separation(self):
        return 6
