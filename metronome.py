import os

from gi.repository import Gst


class Metronome(object):
    def __init__(self, xsheet):
        Gst.init([])
        self._xsheet = xsheet
        self._frame_changed_hid = None

        self._player = Gst.ElementFactory.make("playbin", "tick")
        fakesink = Gst.ElementFactory.make("fakesink", "fake")
        self._player.props.video_sink = fakesink
        self._player.get_bus().add_signal_watch()

        directory = os.path.dirname(os.path.abspath(__file__))
        self._soft_tick_sound_path = os.path.join(
            directory, 'data', 'sounds', 'soft_tick.wav')
        self._strong_tick_sound_path = os.path.join(
            directory, 'data', 'sounds', 'strong_tick.wav')

    def is_on(self):
        return self._frame_changed_hid is not None

    def activate(self):
        if self._frame_changed_hid is not None:
            return False

        self._frame_changed_hid = self._xsheet.connect('frame-changed',
                                                       self._xsheet_changed_cb)
        return True

    def deactivate(self):
        if self._frame_changed_hid is None:
            return False

        self._xsheet.disconnect(self._frame_changed_hid)
        self._frame_changed_hid = None
        return True

    def _tick(self, sound_path):
        self._player.set_state(Gst.State.NULL)

        bus = self._player.get_bus()
        bus.connect('message::eos', self._eos_cb)
        bus.connect('message::error', self._error_cb)

        self._player.props.uri = 'file://' + sound_path
        self._player.set_state(Gst.State.PLAYING)

    def _eos_cb(self, bus, message):
        bus.disconnect_by_func(self._eos_cb)
        self._player.set_state(Gst.State.NULL)

    def _error_cb(self, bus, message):
        err, debug = message.parse_error()
        print('ERROR play_pipe: %s %s' % (err, debug))
        self._player.set_state(Gst.State.NULL)

    def _xsheet_changed_cb(self, xsheet):
        if xsheet.current_frame % 24 == 0:
            self._tick(self._strong_tick_sound_path)
        elif xsheet.current_frame % xsheet.frames_separation == 0:
            self._tick(self._soft_tick_sound_path)
