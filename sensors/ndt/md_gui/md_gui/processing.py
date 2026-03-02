import numpy as np


class Processing:
    def __init__(self):
        self.use_detrend = False
        self.use_pca = False
        self.use_filter = False
        self.use_standard_normal = False
        self.use_fft = False
        self.use_cepstrum = False
        self.cepstrum_input = 0
        self.use_fft_2d = False
        self.use_difference = False
        self.use_adaptive_background = False
        self.background = np.zeros(1000)
        self.fft_output = 'MagPh'
        self.use_freq_diff = False
        self.use_harmonic_removal = False
        self.use_peak_finder = False

        self.processed_data_queue = np.zeros([8, self.n_samples])
        self.temp_queue = [0.0] * self.n_samples

        self.create_filter()

    def apply_pca(self, data_queue):
        data_queue = data_queue - self.pca_stats['mean'].to_numpy()
        data_queue = data_queue / self.pca_stats['sd'].to_numpy()
        transformed_data_queue = np.dot(data_queue, self.norm_transform)
        self.transformed_data_queue = np.append(self.transformed_data_queue, np.reshape(transformed_data_queue, [8, 1]),
                                                axis=1)
        self.transformed_data_queue = np.delete(self.transformed_data_queue, 0, axis=1)

    def set_scrolling_data(self):
        for k in range(self.nharmonics):
            # Input PCA-ed data
            if self.use_pca:
                self.processed_data_queue[k, :] = self.transformed_data_queue[k, :]
                self.processed_data_queue[k + self.nharmonics, :] = self.transformed_data_queue[k + self.nharmonics, :]

            # Input Raw Data
            else:
                if self.use_reim:
                    self.processed_data_queue[k, :] = np.real(self.raw_complex_data_queue[k, :])
                    self.processed_data_queue[k + self.nharmonics, :] = np.imag(self.raw_complex_data_queue[k, :])
                else:
                    self.processed_data_queue[k, :] = np.abs(self.raw_complex_data_queue[k, :])
                    self.processed_data_queue[k + self.nharmonics, :] = np.degrees(
                        np.angle(self.raw_complex_data_queue[k, :]))

            if self.use_detrend:
                self.processed_data_queue[k, :] = scipy.signal.detrend(self.processed_data_queue[k, :])
                self.processed_data_queue[k + self.nharmonics, :] = scipy.signal.detrend(
                    self.processed_data_queue[k + self.nharmonics, :])

            if self.use_filter:
                self.processed_data_queue[k, :] = self.filter.apply_filter(self.processed_data_queue[k, :])
                self.processed_data_queue[k + self.nharmonics, :] = self.filter.apply_filter(
                    self.processed_data_queue[k + self.nharmonics, :])

            if self.use_standard_normal:
                self.processed_data_queue[k, :] = self.standardise(self.processed_data_queue[k, :])
                self.processed_data_queue[k + self.nharmonics, :] = self.standardise(
                    self.processed_data_queue[k + self.nharmonics, :])

            if self.use_fft:
                if self.cepstrum_input_ctrl[0].isChecked():
                    # Use first half of processed queue as input data (either Re or Mag)
                    self.processed_data_queue[k, :], self.processed_data_queue[k + self.nharmonics, :] = self.apply_fft(
                        self.processed_data_queue[k, :])
                else:
                    # Use second half of processed queue as input data (either Im or Ph)
                    self.processed_data_queue[k, :], self.processed_data_queue[k + self.nharmonics, :] = self.apply_fft(
                        self.processed_data_queue[k + self.nharmonics, :])

            if self.use_cepstrum:
                if self.cepstrum_input_ctrl[0].isChecked():
                    # Use first half of processed queue as input data (either Re or Mag)
                    self.processed_data_queue[k, :], self.processed_data_queue[k + self.nharmonics, :] \
                        = self.apply_cepstrum(self.processed_data_queue[k, :])
                else:
                    # Use second half of processed queue as input data (either Im or Ph)
                    self.processed_data_queue[k, :], self.processed_data_queue[k + self.nharmonics, :] = self.apply_fft(
                        self.processed_data_queue[k + self.nharmonics, :])

            if self.use_difference:
                self.processed_data_queue[k, :] = self.apply_differencing(self.processed_data_queue[k, :])
                self.processed_data_queue[k + self.nharmonics, :] = self.apply_differencing(
                    self.processed_data_queue[k + self.nharmonics, :])

            if self.use_harmonic_removal:
                self.processed_data_queue[k, :] = self.apply_harmonic_removal(self.processed_data_queue[k, :])

            if self.use_peak_finder:
                self.processed_data_queue[k, :] = self.peak_finder(self.processed_data_queue[k, :])

        # Methods which act on multiple harmonics simultaneously
        # if self.use_fft_2d:
        #     z = self.processed_data_queue[k, :] + 1j * self.processed_data_queue[k + self.nharmonics, :]
        #     self.processed_data_queue[k, :] = self.apply_2d_fft()

        if self.use_freq_diff:
            self.processed_data_queue = self.freq_differencing(self.processed_data_queue)

        # Choose the harmonic to plot
        for m, mask in enumerate(self.harmonic_mask):
            if mask:
                if self.use_reim:
                    self.line_data[0] = self.processed_data_queue[m, :]
                    self.line_data[1] = self.processed_data_queue[m + self.nharmonics, :]
                else:
                    z = self.processed_data_queue[m, :] + 1j * self.processed_data_queue[m + self.nharmonics, :]
                    self.line_data[0] = np.abs(z)
                    self.line_data[1] = np.angle(z)

    def apply_harmonic_removal(self, data):
        data_fft = np.fft.rfft(data)
        data_fft[20:30] = 0
        data_filt = np.fft.irfft(data_fft)
        return data_filt

    def freq_differencing(self, data):
        y = np.zeros_like(data)
        for comp in range(2 * self.nharmonics):
            c1, _ = self.adjacent_comps(comp)
            y[comp, :] = data[comp, :] - data[c1, :]
        return y

    def adjacent_comps(self, comp):
        n = 2 * self.nharmonics
        mid = self.nharmonics

        # Ensure the element_index is within bounds
        if comp < 0 or comp >= n:
            raise IndexError("Element index is out of bounds.")

        # Handle the lower half (wrap around to the midpoint)
        if comp < self.nharmonics:
            c1 = (comp - 1) % self.nharmonics
            c2 = (comp + 1) % self.nharmonics
        else:
            # Handle the upper half (wrap around to the end)
            c1 = (comp - 1 - mid) % self.nharmonics + mid
            c2 = (comp + 1 - mid) % self.nharmonics + mid

        return c1, c2

    def apply_differencing(self, data):
        y = np.diff(data, n=1, prepend=0)
        y[0] = 0
        return y
        # return np.ediff1d(data, to_begin=0)

    def apply_fft(self, data):
        y = np.fft.fft(data, n=self.n_samples)
        if self.fft_output == 'MagPh':
            return np.log10(np.abs(y)), np.unwrap(np.angle(y))
        elif self.fft_output == 'ReIm':
            return np.log10(np.real(y)), np.log10(np.imag(y))

    def apply_2d_fft(self, data):
        y = np.fft.fft2(data)
        if self.fft_output == 'MagPh':
            return np.log10(np.abs(y)), np.unwrap(np.angle(y))
        elif self.fft_output == 'ReIm':
            return np.log10(np.real(y)), np.log10(np.imag(y))

    def apply_cepstrum(self, data):
        # Complex Cepstrum
        spect = np.fft.fft(data)
        unwrapped_ph = np.unwrap(np.angle(spect))
        log_spect = np.log(np.abs(spect)) + 1j * unwrapped_ph
        cep = np.fft.ifft(log_spect)
        if self.fft_output == 'MagPh':
            return np.log10(np.abs(cep)), np.unwrap(np.angle(cep))
        elif self.fft_output == 'ReIm':
            return np.log10(np.real(cep)), np.log10(np.imag(cep))

    @staticmethod
    def standardise(data):
        m = np.mean(data)
        sd = np.std(data)
        return (data - m) / sd

    def create_filter(self):
        try:
            filter_type = self.filter_list_control.currentItem().text()
        except AttributeError:
            filter_type = 'Butterworth'
        order = self.filter_controls[0].value()
        crit_freq = self.filter_controls[1].value()
        sampling_freq = self.filter_controls[2].value()
        min_atten = self.filter_controls[3].value()
        pass_ripple = self.filter_controls[4].value()

        args = {'filter_type': filter_type, 'order': order, 'crit_freq': crit_freq, 'sampling_freq': sampling_freq,
                'min_atten': min_atten,
                'pass_type': 'lowpass', 'pass_ripple': pass_ripple}

        self.filter = Filter(**args)