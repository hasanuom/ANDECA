from audio import AudioController
import numpy as np

class Detection:
    def __init__(self, print_signal=False):
        self.print_signal = print_signal
        self.audio_controller = AudioController()
        self.audio_controller._strm.start()
        self._base_audio_freq = 1000
        self._threshold = 1.5
        self._signal_comp = 0

    def update(self, data_queue):
        s = np.mean(data_queue[self.signal_component][-1])
        # m = np.mean(data_queue[comp][-50:])
        # sd = np.std(data_queue[comp][-50:])
        sig = np.abs(s)

        sig = 0 if sig < self.threshold else sig

        sig = sig * self._base_audio_freq

        if self.print_signal:
            print('s = {:}, m = {:}'.format(s, m))
            print('sig_raw = {:}'.format(sig))

        self.audio_controller.freq_input = sig
        # self.audio_controller.vol_input = sig / 80

    def audio_active(self, active):
        if isinstance(active, tuple):
            active = active[0]
        if active:
            self.audio_controller.vol_input = 100
        else:
            self.audio_controller.vol_input = 0

    @property
    def signal_component(self):
        return self._signal_comp

    @signal_component.setter
    def signal_component(self, value):
        self._signal_comp = value

    def set_audio_comp(self, value):
        if isinstance(value, tuple):
            value = value[0]
        self.signal_component = value
        print("Detection signal component updated: ", self.signal_component)

    @property
    def threshold(self):
        return self._threshold

    @threshold.setter
    def threshold(self, value):
        self._threshold = value

    def update_threshold(self, value):
        if isinstance(value, tuple):
            value = value[0]
        self.threshold = value
        print("Detection threshold updated: ", self.threshold)
