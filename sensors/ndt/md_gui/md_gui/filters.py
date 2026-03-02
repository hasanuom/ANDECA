import numpy as np
import scipy
from skimage.restoration import denoise_tv_chambolle as denoise_tv
from skimage.restoration import denoise_nl_means, estimate_sigma


class Filter:
    def __init__(self, **kwargs):
        self.filter_type = kwargs.get('filter_type', 'Butterworth')
        self.order = kwargs.get('order', 2)
        self.sampling_freq = kwargs.get('sampling_freq', 50)
        self.critical_freq = kwargs.get('crit_freq', 11)
        self.min_attenuation = kwargs.get('min_atten', 40)
        self.pass_type = kwargs.get('pass_type', 'lowpass')
        self.pass_ripple = kwargs.get('pass_ripple', 1)

        self.filter_design = {'Butterworth': self.butter,
                              'Chebyshev 1': self.cheby1,
                              'Chebyshev 2': self.cheby2,
                              'Elliptic': self.ellip,
                              'Bessel': self.bessel,
                              'IIR Notch': self.iirnotch,
                              'IIR Peak': self.iirpeak,
                              'Sav-Goy': self.sav_goy,
                              'Median': self.median,
                              'TV': self.total_var,
                              'NL Means': self.non_local_means}

        self.filt_b, self.filt_a = self.filter_design.get(self.filter_type)()

        self.filt_zi = scipy.signal.lfilter_zi(self.filt_b, self.filt_a)
        print('Filter created')

    def apply_filter(self, data):
        if self.filter_type == 'Sav-Goy':
            x = scipy.signal.savgol_filter(data, self.critical_freq, self.order)
        elif self.filter_type == 'Median':
            x = scipy.signal.medfilt(data, kernel_size=self.critical_freq)
        elif self.filter_type == 'TV':
            x = denoise_tv(data, weight=self.critical_freq / 100)
        elif self.filter_type == 'NL Means':
            sigma_est = np.mean(estimate_sigma(data))
            denoised_signal = denoise_nl_means(data.reshape(1, -1), patch_size=self.order, patch_distance=self.critical_freq,
                                               h=self.sampling_freq/50 * sigma_est, fast_mode=True)
            x = denoised_signal.flatten()
        else:
            x, _ = scipy.signal.lfilter(self.filt_b, self.filt_a, data, zi=self.filt_zi * data[0])
        return x

    def butter(self):
        b, a = scipy.signal.butter(self.order, self.critical_freq, fs=self.sampling_freq,
                                   btype=self.pass_type, output='ba')
        return b, a

    def cheby1(self):
        b, a = scipy.signal.cheby1(self.order, self.pass_ripple, self.critical_freq,
                                   fs=self.sampling_freq, btype=self.pass_type, output='ba')
        return b, a

    def cheby2(self):
        b, a = scipy.signal.cheby2(self.order, self.min_attenuation, self.critical_freq,
                                   fs=self.sampling_freq, btype=self.pass_type, output='ba')
        return b, a

    def ellip(self):
        b, a = scipy.signal.ellip(self.order, self.pass_ripple, self.min_attenuation, self.critical_freq,
                                  fs=self.sampling_freq, btype=self.pass_type, output='ba')
        return b, a

    def median(self):
        return [1, 1], [1, 1]

    def bessel(self):
        b, a = scipy.signal.bessel(self.order, self.critical_freq, fs=self.sampling_freq, btype=self.pass_type,
                                   output='ba')
        return b, a

    def iirnotch(self):
        b, a = scipy.signal.iirnotch(self.critical_freq, self.min_attenuation, fs=self.sampling_freq)
        return b, a

    def iirpeak(self):
        b, a = scipy.signal.iirpeak(self.critical_freq, self.min_attenuation, fs=self.sampling_freq)
        return b, a

    def sav_goy(self):
        return [1, 1], [1, 1]

    def total_var(self):
        return [1, 1], [1, 1]

    def non_local_means(self):
        return [1, 1], [1, 1]
