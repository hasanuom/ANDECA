

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import numpy as np
import os
import copy
import collections
import winsound


class MdDetection(object):

    def __init__(self, n_harmonics):

        self.n_harmonics = n_harmonics
        # self.n_points = n_points

        sr_len = 100

        # just a single frequency as a test
        self.moving_avg = [np.zeros(sr_len)]

        self.ref_std_dev = []
        self.enables = []

        self.sound_enable = True
        self.sound_frequency = 2500  # Set Frequency To 2500 Hertz
        self.sound_duration = 100  # Set Duration To 1000 ms == 1 second

        self.dectect_enable = False
        self.std_dev_factor = 3.0

    def update_series_enables(self, enables):

        #     # enables should be a list of booleans
        #     # print(enables)
        self.enables = enables

#=================================================================================
    # ground calibration level ?
    def set_reference_level(self, xdata, ydata):
        print("set_reference_level")
        mean = []
        self.ref_std_dev = []
        # Assume 300 samples at the momement
        n_samples = 300

        for i in range(self.n_harmonics):
            if self.enables[i]:
                try:
                    # convert to complexes
                    temp = xdata[i] + 1j * ydata[i]
                    self.ref_std_dev.append(np.std(temp[-n_samples:]))
                    # mean.append(np.mean(temp[-n_samples:]))

                except IndexError:
                    print("ERROR  " + os.path.basename(__file__) +
                          "set_reference_level")
                    return

        # print(mean)
        print(self.ref_std_dev)
#=================================================================================

    def set_reference_level2(self, xdata, ydata):
        print("set_reference_level")
        self.ref_mean_x = []
        self.ref_mean_y = []
        self.ref_std_dev_x = []
        self.ref_std_dev_y = []
        # Assume 300 samples at the momement
        n_samples = 300

        for i in range(self.n_harmonics):
            if self.enables[i]:
                try:
                    self.ref_std_dev_x.append(np.std(xdata[i][-n_samples:]))
                    self.ref_std_dev_y.append(np.std(ydata[i][-n_samples:]))
                    self.ref_mean_x.append(np.mean(xdata[i][-n_samples:]))
                    self.ref_mean_y.append(np.mean(ydata[i][-n_samples:]))
                except IndexError:
                    print("ERROR  " + os.path.basename(__file__) +
                          "set_reference_level")
                    return
#=================================================================================

    def set_reference_level3(self, xdata, ydata):
        print("set_reference_level")
        self.ref_mean_mag = []
        self.ref_mean_phase = []
        self.ref_std_dev_mag = []
        self.ref_std_dev_phase = []
        # Assume 300 samples at the momement
        n_samples = 300

        for i in range(self.n_harmonics):
            if self.enables[i]:
                try:
                    mag = np.sqrt(xdata[i][-n_samples:] **
                                  2 + ydata[i][-n_samples:]**2)
                    phase = np.arctan2(
                        ydata[i][-n_samples:], xdata[i][-n_samples:])
                    self.ref_mean_mag.append(np.mean(mag))
                    self.ref_mean_phase.append(np.mean(phase))
                    self.ref_std_dev_mag.append(np.std(mag))
                    self.ref_std_dev_phase.append(np.std(phase))
                except IndexError:
                    print("ERROR  " + os.path.basename(__file__) +
                          "set_reference_level")
                    return

#=================================================================================
    def calc_std_dev(self, xdata, ydata, nsamples):
        # SD of complex
        std_dev = []
        for i in range(self.n_harmonics):
            if self.enables[i]:
                try:
                    # convert to complexes
                    temp = xdata[i] + 1j * ydata[i]
                    std_dev.append(np.std(temp[-nsamples:]))

                except IndexError:
                    print("ERROR  " + os.path.basename(__file__) +
                          "set_reference_level")
                    return

        return std_dev
#=================================================================================

    def calc_std_dev2(self, xdata, ydata, nsamples):
        # calculate sd for re and im separately
        mean_x = []
        mean_y = []
        std_dev_x = []
        std_dev_y = []
        for i in range(self.n_harmonics):
            if self.enables[i]:
                try:
                    mean_x.append(np.mean(xdata[i][-nsamples:]))
                    mean_y.append(np.mean(ydata[i][-nsamples:]))
                    std_dev_x.append(np.std(xdata[i][-nsamples:]))
                    std_dev_y.append(np.std(ydata[i][-nsamples:]))
                except IndexError:
                    print("ERROR  " + os.path.basename(__file__) +
                          "set_reference_level")
                    return

        return mean_x, mean_y, std_dev_x, std_dev_y
#=================================================================================
    def calc_std_dev3(self, xdata, ydata, nsamples):
        # calculate sd for mag and phase separately
        mean_mag = []
        mean_phase = []
        std_dev_mag = []
        std_dev_phase = []
        for i in range(self.n_harmonics):
            if self.enables[i]:
                try:
                    mag = np.sqrt(xdata[i][-nsamples:] **
                                  2 + ydata[i][-nsamples:]**2)
                    phase = np.arctan2(
                        ydata[i][-nsamples:], xdata[i][-nsamples:])
                    mean_mag.append(np.mean(mag))
                    mean_phase.append(np.mean(phase))
                    std_dev_mag.append(np.std(mag))
                    std_dev_phase.append(np.std(phase))

                except IndexError:
                    print("ERROR  " + os.path.basename(__file__) +
                          "set_reference_level")
                    return

        return mean_mag, mean_phase, std_dev_mag, std_dev_phase
#=================================================================================

    def set_sound_enable(self, val):
        self.sound_enable = val

    def get_sound_enable(self):
        return self.sound_enable

    def set_detect_enable(self, val):
        self.dectect_enable = val

    def get_detect_enable(self):
        return self.detect_enable

    def set_std_dev_setting(self, val):

        if val >= 1.0 and val < 100:
            self.std_dev_factor = val

    def get_std_dev_setting(self):
        return self.std_dev_factor

    # 68% = 1sd, 95% = 2sd, 99.7% = 3sd

    def update_data(self, xdata, ydata):
        # standard deviation as complex
        if not self.dectect_enable:
            return

        # check that some enables are set
        if not self.enables:
            return

        # TODO: make this a paramter !!!!
        window_len = 8

        data_std_dev = self.calc_std_dev(xdata, ydata, window_len)

        if len(self.ref_std_dev) != len(data_std_dev):
            print("List length mismatch - md_detection")
            return

        # compare
        cnt = 0
        for i in range(len(self.ref_std_dev)):
            if data_std_dev[i] > (self.ref_std_dev[i] * self.std_dev_factor):
                cnt += 1

        if cnt >= 3:
            isDetected = True
            print(cnt)
            if self.sound_enable:
                winsound.Beep(self.sound_frequency, self.sound_duration)
        else:
            isDetected = False

        return isDetected

    def update_data2(self, xdata, ydata):
        # re or im deviation from mean
        if not self.dectect_enable:
            return

        # check that some enables are set
        if not self.enables:
            return

        # TODO: make this a paramter !!!!
        window_len = 2

        data_mean_x, data_mean_y, data_std_dev_x, data_std_dev_y = self.calc_std_dev2(
            xdata, ydata, window_len)

        if len(self.ref_std_dev_x) != len(data_std_dev_x) or len(self.ref_std_dev_y) != len(data_std_dev_y):
            print("List length mismatch - md_detection")
            return

        # compare
        cnt = 0
        detect_freq = [False] * self.n_harmonics
        # for i in range(len(self.ref_std_dev_x)):
        i = 1
        #     if (data_std_dev_x[i] > (self.ref_std_dev_x[i] * self.std_dev_factor) or
        # data_std_dev_y[i] > (self.ref_std_dev_y[i] * self.std_dev_factor)):
        if (data_mean_x[i] > self.ref_mean_x[i] + self.ref_std_dev_x[i] * self.std_dev_factor or
            data_mean_x[i] < self.ref_mean_x[i] - self.ref_std_dev_x[i] * self.std_dev_factor or
            data_mean_y[i] > self.ref_mean_y[i] + self.ref_std_dev_y[i] * self.std_dev_factor or
                data_mean_y[i] < self.ref_mean_y[i] - self.ref_std_dev_y[i] * self.std_dev_factor):
            cnt += 1
            detect_freq[i] = True

        if cnt >= 1:
            isDetected = True
            # print(detect_freq)
            if self.sound_enable:
                winsound.Beep(self.sound_frequency, self.sound_duration)
        else:
            isDetected = False

        return isDetected

    def update_data3(self, xdata, ydata):
        # re or im deviation from mean
        if not self.dectect_enable:
            return

        # check that some enables are set
        if not self.enables:
            return

        # TODO: make this a paramter !!!!
        window_len = 2

        data_mean_mag, data_mean_phase, data_std_dev_mag, data_std_dev_phase = self.calc_std_dev3(
            xdata, ydata, window_len)

        # compare
        cnt = 0
        detect_freq = [False] * self.n_harmonics
        # for i in range(len(self.ref_std_dev_x)):
        i = 1

        if (data_mean_mag[i] > self.ref_mean_mag[i] + self.ref_std_dev_mag[i] * self.std_dev_factor or
            data_mean_mag[i] < self.ref_mean_mag[i] - self.ref_std_dev_mag[i] * self.std_dev_factor or
            data_mean_phase[i] > self.ref_mean_phase[i] + self.ref_std_dev_phase[i] * self.std_dev_factor or
                data_mean_phase[i] < self.ref_mean_phase[i] - self.ref_std_dev_phase[i] * self.std_dev_factor):
            cnt += 1
            detect_freq[i] = True

        if cnt >= 1:
            isDetected = True
            # print(detect_freq)
            if self.sound_enable:
                winsound.Beep(self.sound_frequency, self.sound_duration)
        else:
            isDetected = False

        return isDetected


# for debugging
if __name__ == '__main__':

    detection = MdDetection(16)
    x_data = np.random.random([16, 300])
    y_data = np.random.random([16, 300])
    detection.enables = [True] * 16
    detection.set_reference_level3(x_data, y_data)
    print(detection.ref_mean_mag[1])
    print(detection.calc_std_dev3(x_data, y_data, 8)[1])
