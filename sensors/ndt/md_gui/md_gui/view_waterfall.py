import os

import scipy.signal
from PyQt5.QtWidgets import *

from view_common import ViewCommon
import numpy as np
from time import perf_counter
import pandas as pd

from filters import Filter


class ViewWaterfall(ViewCommon):

    def __init__(self, tab_widget=None):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Waterfall")

        self._base_layout = tab_layout
        super().__init__(self._base_layout, nharmonics=4, harmonic_select='radio')

        # Number of samples to plot
        self.n_samples = 300
        self.samples = np.arange(0, self.n_samples)
        plot_layout = self.create_image_widgets('vert', 2)

        self._base_layout.addLayout(plot_layout)

        # Initialise flags for processing options
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

        # Initialise plot controls
        processing_labels = ['Detrend', 'PCA', 'Apply Filter', 'Standardise', 'FFT', 'Cepstrum', 'Difference',
                             'Adaptive Background', 'Freq. Diff.', 'Harmonic Removal']
        component_ctrl = {'labels': ['Re/Im', 'Mag/Ph'], 'method': [self.set_scrolling_data] * 2}
        processing_btn = {'labels': processing_labels,
                          'method': [self.set_processing_flags] * len(processing_labels)}
        filter_param_ctrl = {
            'labels': ['Order', 'Critical Freq.', 'Sampling Freq.', 'Min Stop Atten.', 'Passband Ripple'],
            'method': [self.create_filter] * 5,
            'limits': [(1, 3, 15), (1, 15, 100), (1, 50, 100), (3, 40, 100), (1, 3, 100)] * 5,
            'type': ['int'] * 5}
        view_ctrl = {'labels': ['Autoscale', 'Fixed scale'], 'method': [self.apply_autoscale, self.remove_autoscale]}

        filter_list = list(Filter().filter_design.keys())
        filter_list_ctrl = {'labels': filter_list, 'method': self.create_filter}
        cepstrum_input_ctrl = {'labels': ['Re/Mag', 'Im/Ph'], 'method': [self.set_cepstrum_input] * 2}

        self.process_group, self.process_controls = self.create_groupbox("Processing", 'checkbox', processing_btn)
        self.view_group, view_controls = self.create_groupbox("View Control", 'button', view_ctrl)
        self.component_group, self.component_ctrl = self.create_groupbox("Plot Component", 'radio', component_ctrl)
        self.component_ctrl[0].setChecked(True)
        self.filter_ctrl_group, self.filter_controls = self.create_groupbox("Filter Design", 'spinbox',
                                                                            filter_param_ctrl)
        self.process_scroll = QScrollArea()
        self.filter_ctrl_scroll = QScrollArea()
        self.process_scroll.setWidget(self.process_group)
        self.filter_ctrl_scroll.setWidget(self.filter_ctrl_group)
        self.process_scroll.setMaximumWidth(150)
        self.filter_ctrl_scroll.setMaximumWidth(150)
        self.filter_list_group, self.filter_list_control = self.create_list_groupbox('Filters', filter_list_ctrl)
        self.cepstrum_input_group, self.cepstrum_input_ctrl = self.create_groupbox('FFT/Cepstrum Input', 'radio',
                                                                                   cepstrum_input_ctrl)
        self.cepstrum_input_ctrl[0].setChecked(True)
        self.control_layout.addWidget(self.view_group)
        self.control_layout.addWidget(self.process_scroll)
        self.control_layout.addWidget(self.component_group)
        self.control_layout.addWidget(self.cepstrum_input_group)
        self.control_layout.addWidget(self.filter_list_group)
        self.control_layout.addWidget(self.filter_ctrl_scroll)

        self.create_filter()

        # Calculate fps so we can compare performance. ~15 fps is sufficient
        self.last_time = 0
        self.fps = None
        # self.fps_label = self.add_label(self.control_layout, "Mean Frame Rate: ")

        # Initialise data queues
        self.raw_complex_data_queue = np.zeros([self.nharmonics, self.n_samples])
        self.transformed_data_queue = np.zeros([2*self.nharmonics, self.n_samples])
        self.processed_data_queue = np.zeros([2*self.nharmonics, self.n_samples])
        self.temp_queue = [0.0] * self.n_samples

        self.image_data = [[0.0] * self.n_samples] * 2

        directory = r'C:\Users\mchijaf3\Documents\Data\202211 Lab Trials'
        files = os.listdir(directory)
        pca_select = 0
        pca_fname = [f for f in files if f.endswith('_pca_reim_comps_v2.csv')]
        stats_fname = [f for f in files if f.endswith('_stats_reim.csv')]
        self.pca_comps = pd.read_csv(os.path.join(directory, pca_fname[pca_select]), header=0, index_col=0)
        self.pca_stats = pd.read_csv(os.path.join(directory, stats_fname[pca_select]), header=0, index_col=0)
        self.norm_transform = self.pca_comps / np.max(np.abs(self.pca_comps))

    def update(self, md_data):
        # self.plot_data gets all the MD data being streamed
        self.update_queues(md_data)

        self.update_harmonics_mask()
        self.set_components()
        self.set_scrolling_data()
        upper_image_data = self.processed_data_queue[:self.nharmonics]
        lower_image_data = self.processed_data_queue[self.nharmonics:]
        # upper_image_data = np.repeat(upper_image_data, self.n_samples//self.nharmonics, axis=0)
        # lower_image_data = np.repeat(lower_image_data, self.n_samples//self.nharmonics, axis=0)

        self._image_widgets[0].setImage(upper_image_data.T, autoRange=True, scale=(1, 20))
        self._image_widgets[1].setImage(lower_image_data.T, autoRange=True, scale=(1, 20))
        self.update_fps()

    def update_fps(self):
        now = perf_counter()
        dt = now - self.last_time
        self.last_time = now
        if self.fps is None:
            self.fps = 1.0 / dt
        else:
            s = np.clip(dt * 3., 0, 1)
            self.fps = self.fps * (1 - s) + (1.0 / dt) * s

    def set_components(self):
        if self.component_ctrl[0].isChecked():
            self.use_reim = True
        else:
            self.use_reim = False

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


        if self.use_reim:
            self.image_data[0] = self.processed_data_queue[:self.nharmonics, :]
            self.image_data[1] = self.processed_data_queue[self.nharmonics:, :]
        else:
            z = self.processed_data_queue[:self.nharmonics, :] + 1j * self.processed_data_queue[self.nharmonics:, :]
            self.image_data[0] = np.abs(z)
            self.image_data[1] = np.angle(z)

    def update_queues(self, new_sample):
        self.plot_data = new_sample
        re, im = self.select_data_source()
        cmplx_data = re[:self.nharmonics, -1] + 1j * im[:self.nharmonics, -1]
        data_queue = np.hstack((np.real(cmplx_data), np.imag(cmplx_data)))
        self.raw_complex_data_queue = np.append(self.raw_complex_data_queue, np.reshape(cmplx_data, [self.nharmonics, 1]), axis=1)
        self.raw_complex_data_queue = np.delete(self.raw_complex_data_queue, 0, axis=1)
        if self.use_pca:
            self.apply_pca(data_queue)

    def apply_pca(self, data_queue):
        data_queue = data_queue - self.pca_stats['mean'].to_numpy()
        data_queue = data_queue / self.pca_stats['sd'].to_numpy()
        transformed_data_queue = np.dot(data_queue, self.norm_transform)
        self.transformed_data_queue = np.append(self.transformed_data_queue, np.reshape(transformed_data_queue, [2*self.nharmonics, 1]),
                                                axis=1)
        self.transformed_data_queue = np.delete(self.transformed_data_queue, 0, axis=1)

    def set_processing_flags(self):
        flag_num = 0
        # set detrend flag
        if self.process_controls[flag_num].isChecked():
            self.use_detrend = True
        else:
            self.use_detrend = False
        flag_num += 1
        # Set PCA flag
        if self.process_controls[flag_num].isChecked():
            self.use_pca = True
        else:
            self.use_pca = False
        flag_num += 1
        # Set filter flag
        if self.process_controls[flag_num].isChecked():
            self.use_filter = True
        else:
            self.use_filter = False
        flag_num += 1
        # Set standard normal flag
        if self.process_controls[flag_num].isChecked():
            self.use_standard_normal = True
        else:
            self.use_standard_normal = False
        flag_num += 1
        # set FFT flag
        if self.process_controls[flag_num].isChecked():
            self.use_fft = True
        else:
            self.use_fft = False
        flag_num += 1
        # set cepstrum flag
        if self.process_controls[flag_num].isChecked():
            self.use_cepstrum = True
        else:
            self.use_cepstrum = False
        flag_num += 1
        # set differencing flag
        if self.process_controls[flag_num].isChecked():
            self.use_difference = True
        else:
            self.use_difference = False
        flag_num += 1
        if self.process_controls[flag_num].isChecked():
            self.use_adaptive_background = True
        else:
            self.use_adaptive_background = False
        flag_num += 1
        if self.process_controls[flag_num].isChecked():
            self.use_freq_diff = True
        else:
            self.use_freq_diff = False
        flag_num += 1
        if self.process_controls[flag_num].isChecked():
            self.use_harmonic_removal = True
        else:
            self.use_harmonic_removal = False

    def set_cepstrum_input(self):
        # set cepstrum input component
        if self.cepstrum_input_ctrl[0].isChecked():
            self.cepstrum_input = 0
        elif self.cepstrum_input_ctrl[1].isChecked():
            self.cepstrum_input = 1
        else:
            self.cepstrum_input = 0

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
