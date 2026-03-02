import sounddevice as sd
import time
import numpy as np


class AudioController:
    def __init__(self):
        sd.query_devices()
        kwargs = {'blocksize': 441 * 5, 'samplerate': 44100.0, 'latency': 'high'}

        self._samplerate = kwargs['samplerate']
        self._strm = sd.OutputStream(callback=self.__audio_callback, **kwargs)

        self.__heartbeat_length = 1
        self.__beat = 300

        self._two_pi_t = 2 * np.pi * np.arange(kwargs['blocksize']) / kwargs['samplerate']

        self._done = False
        self._samples = 0
        self._iteration = 0

        self._current_frequency = 500
        self.freq_input = 0
        self.vol_input = 0

    def __audio_callback(self, outdata, frames, time, status):
        # freq_input = getattr(self, 'freq_input', 1.0)
        # vol_input = getattr(self, 'vol_input', 1.0)

        base = 500

        target_freq = base + base * self.freq_input
        target_freq = np.round(self.freq_input / 10) * 10

        freq_increment = (target_freq - self._current_frequency) / frames
        audio = np.zeros(frames)

        vol = (10 * self.vol_input)**2 / 20

        for i in range(frames):
            self._current_frequency += freq_increment
            audio[i] = np.sin(2 * np.pi * self._current_frequency * i / self._samplerate) * vol
        window = np.hanning(frames)
        audio *= window
        self._current_frequency = target_freq
        # audio = np.sin(freq * self._two_pi_t ) * vol

        outdata[:, 0] = audio
        outdata[:, 1] = audio


    def loop(self):
        self._strm.start()

        while not self._done:
            self.freq_input = 5500
            self.vol_input = 1
            self._iteration += 1
            start = time.time()
            time.sleep(0.5)
            stop = time.time()
            sps = self._samples / (stop - start)
            self._samples = 0
            print(f"SPS = {sps:.04f}")

    def close(self):
        self._strm.stop()


def main():
    controller = AudioController()
    # outdata = np.zeros([10, 2])
    controller.loop()

if __name__ == "__main__":
    main()