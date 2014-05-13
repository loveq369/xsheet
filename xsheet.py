import os
import json

from gi.repository import GObject
from gi.repository import MyPaintGegl
from gi.repository import Gegl

from framelist import FrameList


class Cel(object):
    def __init__(self):
        graph = Gegl.Node()
        self.gegl_surface = MyPaintGegl.TiledSurface()
        self.surface = self.gegl_surface.interface()
        self.surface_node = graph.create_child("gegl:buffer-source")
        self.surface_node.set_property("buffer", self.gegl_surface.get_buffer())

    def save_png(self, path_png):
        graph = Gegl.Node()
        save = graph.create_child("gegl:png-save")
        save.set_property('path', path_png)
        self.surface_node.connect_to("output", save, "input")
        save.process()

    def load_png(self, path_png):
        cel_buffer = self.gegl_surface.get_buffer()
        graph = Gegl.Node()
        load = graph.create_child("gegl:load")
        load.set_property('path', path_png)
        translate = graph.create_child("gegl:translate")
        translate.set_property('x', cel_buffer.props.x)
        translate.set_property('y', cel_buffer.props.y)
        write = graph.create_child("gegl:write-buffer")
        write.set_property('buffer', cel_buffer)
        load.connect_to("output", translate, "input")
        translate.connect_to("output", write, "input")
        write.process()
        self.surface_node.process()

    def extent_to_data(self):
        rect = self.gegl_surface.get_buffer().get_extent()
        return [rect.x, rect.y, rect.width, rect.height]

    def extent_from_data(self, data):
        rect = Gegl.Rectangle()
        rect.x = data[0]
        rect.y = data[1]
        rect.width = data[2]
        rect.height = data[3]

        cel_buffer = self.gegl_surface.get_buffer()
        cel_buffer.set_extent(rect)


class XSheet(GObject.GObject):
    __gsignals__ = {
        "frame-changed": (GObject.SignalFlags.RUN_FIRST, None, []),
        "layer-changed": (GObject.SignalFlags.RUN_FIRST, None, []),
    }

    def __init__(self, frames_length=24, layers_length=3):
        GObject.GObject.__init__(self)

        self._frames_length = frames_length
        self.current_frame = 0
        self.layer_idx = 0
        self.layers = [FrameList() for x in range(layers_length)]
        self._play_hid = None

    def get_layers(self):
        return self.layers

    def go_to_frame(self, frame_idx):
        cant_go = (frame_idx < 0 or frame_idx > self.frames_length-1 or
                   frame_idx == self.current_frame)
        if cant_go:
            return False

        self.current_frame = frame_idx

        self.emit("frame-changed")
        return True

    def previous_frame(self, loop=False):
        if not loop:
            if self.current_frame == 0:
                return False
        else:
            if self.current_frame == 0:
                self.current_frame = self.frames_length-1
                return True

        self.current_frame -= 1

        self.emit("frame-changed")
        return True

    def next_frame(self, loop=False):
        if not loop:
            if self.current_frame == self.frames_length-1:
                return False
        else:
            if self.current_frame == self.frames_length-1:
                self.current_frame = 0
                return True

        self.current_frame += 1

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
            frame_idx = self.current_frame

        if layer_idx is None:
            layer_idx = self.layer_idx

        return self.layers[layer_idx][frame_idx]

    def get_cel_relative(self, frame_diff=0, layer_diff=0):
        frame_idx = self.current_frame + frame_diff
        layer_idx = self.layer_idx + layer_diff
        return self.layers[layer_idx][frame_idx]

    def get_cel_relative_by_cels(self, steps, frame_diff=0, layer_diff=0):
        frame_idx = self.current_frame + frame_diff
        layer_idx = self.layer_idx + layer_diff
        return self.layers[layer_idx].get_relative(frame_idx, steps)

    def has_cel(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.current_frame

        if layer_idx is None:
            layer_idx = self.layer_idx

        return self.layers[layer_idx].has_cel_at(frame_idx)

    def add_cel(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.current_frame

        if layer_idx is None:
            layer_idx = self.layer_idx

        if not self.layers[layer_idx].has_cel_at(frame_idx):
            self.layers[layer_idx][frame_idx] = Cel()
            self.emit("frame-changed")

    def remove_clear(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.current_frame

        if layer_idx is None:
            layer_idx = self.layer_idx

        self.layers[layer_idx].remove_clear(frame_idx)
        self.emit("frame-changed")

    def save(self):
        dirname = 'out'
        filename = 'test'

        if not os.path.exists(dirname):
            os.mkdir(dirname)

        cel = self.get_cel()
        if cel is None:
            return

        path_png = os.path.join('out', filename + '.png')
        cel.save_png(path_png)

        path_data = os.path.join('out', filename + '.json')
        data = cel.extent_to_data()
        with open(path_data, 'w') as datafile:
            json.dump(data, datafile)

    def load(self):
        dirname = 'out'
        filename = 'test'

        if not os.path.exists(dirname):
            return

        frame_idx = self.current_frame
        layer_idx = self.layer_idx

        cel = Cel()
        self.layers[layer_idx][frame_idx] = cel

        path_data = os.path.join('out', filename + '.json')
        with open(path_data, 'r') as datafile:
            data = json.load(datafile)
            cel.extent_from_data(data)

        path_png = os.path.join('out', filename + '.png')
        cel.load_png(path_png)

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
