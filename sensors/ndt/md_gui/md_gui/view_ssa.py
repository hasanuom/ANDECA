import math
import os
import time
import pickle
import tkinter as tk
from tkinter import filedialog as fd

import scipy.signal
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from view_common import ViewCommon
import numpy as np
from time import perf_counter
import pandas as pd
from scipy.linalg import svd
from plotter import Plotter as Pt
import matplotlib.pyplot as plt


class ViewSSALinePlot(ViewCommon):

    def __init__(self, tab_widget=None):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "SSA")

        self.detection_count = 0

        self._base_layout = tab_layout
        super().__init__(self._base_layout, nharmonics=4, harmonic_select='radio')

        self._n_groups = 7
        self._window_size = 11

        self.averaging = dict(use_averaging=True, n_avg=0, magnitude_accumulator=[])

        # Number of samples to plot
        self.n_samples = 300
        plot_controls = {'labels': ['Autoscale', 'Fixed Scale', 'Reset Queue'],
                         'method': [self.apply_autoscale, self.remove_autoscale, self.reset_data]}
        plot_control_group, plot_controls = self.create_groupbox('Controls', 'button', plot_controls)

        ssa_control_dict = {'labels': ['Num Groups', 'Window size'], 'method': [self.update_ssa_params] * 2,
                            'type': ['int', 'int'], 'limits': [(0, self._n_groups, 10), (0, self._window_size, self.n_samples)]}
        ssa_control_group, self.ssa_controls = self.create_groupbox('SSA Params', 'spinbox', ssa_control_dict)

        # Initialise plots - n_groups * scrolling plots
        self.plot_layout = self.create_plot_widgets('vert', self._n_groups)
        self.line_plots = [None] * self._n_groups
        for k in range(self._n_groups):
            self.set_plot_range(self._plot_widgets[k], (0, self.n_samples), (-1, 1), pad=(0, 0))
            self.line_plots[k] = self._init_line_plot(self._plot_widgets[k], 'Sample', 'SSA Comp {:}'.format(k), 'r', 2)

        self._base_layout.addLayout(self.plot_layout)

        # Initialise plot controls
        scrolling_title_labels = ['Re', 'Im', 'Mag', 'Ph', 'FFT']
        scrolling_plot_title_ctrl = {'labels': scrolling_title_labels,
                                     'method': [self.set_scrolling_plot_titles] * len(scrolling_title_labels)}

        display_control_group, display_controls = self.create_groupbox('Display Data', 'radio',
                                                                       scrolling_plot_title_ctrl)

        self.scrolling_controls = display_controls
        self.scrolling_controls[0].setChecked(True)

        self.control_layout.addWidget(plot_control_group)
        self.control_layout.addWidget(display_control_group)
        self.control_layout.addWidget(ssa_control_group)

        # Calculate fps so we can compare performance. ~15 fps is sufficient
        self.last_time = 0
        self.fps = None
        # self.fps_label = self.add_label(self.control_layout, "Mean Frame Rate: ")

        # Initialise data queues
        self.raw_data_queue = np.zeros([4, self.n_samples])
        self.cmplx_data_queue = np.zeros([4, self.n_samples], dtype=complex)

        self.line_data = [[0.0] * self.n_samples] * self._n_groups

    @staticmethod
    def normalise_data(data, limits=None):
        if limits is not None:
            data = (data - limits[0]) / (limits[1] - limits[0])
        else:
            data = (data - np.min(data)) / (np.max(data) - np.min(data))

        # if data > 1:
        #     data = 1
        # if data < 0:
        #     data = 0
        data[data > 1] = 1
        data[data < 0] = 0
        return data

    def set_line_data(self):
        for k in range(self._n_groups):
            self.line_data[k] = self.dynamic_ssa_queue[k]

    def _init_scatter_plot_self(self, plot_widget, xlabel, ylabel):
        if plot_widget is not None:
            scatter_plot = pg.ScatterPlotItem(pxmode=False, size=12)
            plot_widget.showGrid(x=True, y=True, alpha=0.5)
            plot_widget.setLabel('bottom', xlabel, color='k')
            plot_widget.setLabel('left', ylabel, color='k')
            plot_widget.addItem(scatter_plot)
        return scatter_plot

    def update_fps(self, display=False):
        now = perf_counter()
        dt = now - self.last_time
        self.last_time = now
        if self.fps is None:
            self.fps = 1.0 / dt
        else:
            s = np.clip(dt * 3., 0, 1)
            self.fps = self.fps * (1 - s) + (1.0 / dt) * s
        if display:
            print(self.fps)

    def line_edit(self, label_str, val):
        ctrl = QLineEdit()
        ctrl.setMaximumWidth(120)
        label = QLabel()
        label.setText(label_str)
        ctrl.setText(str(val))
        ctrl.setValidator(self.data_validator)
        return ctrl, label

    def set_scrolling_plot_titles(self):
        pass

    def select_data_component(self, cmplx_data):
        # 0: 'Re', 1: 'Im', 2: 'Mag', 3: 'Ph'
        real = self.scrolling_controls[0]
        imag = self.scrolling_controls[1]
        mag = self.scrolling_controls[2]
        ph = self.scrolling_controls[3]
        fft = self.scrolling_controls[4]

        if real.isChecked():
            d = np.real(cmplx_data)
        elif imag.isChecked():
            d = np.imag(cmplx_data)
        elif mag.isChecked():
            d = np.abs(cmplx_data)
        elif ph.isChecked():
            d = np.angle(cmplx_data)
        elif fft.isChecked():
            d = np.abs(cmplx_data)

        return d

    def dynamic_ssa(self, data):
        freq_sel = 0
        y = data
        K = len(y) - self._window_size + 1
        # Form Hankel matrix
        X = np.array([y[i:i + self._window_size] for i in range(0, K)]).T
        U, s, Vt = svd(X, full_matrices=False)
        V = Vt.T
        X_recon = [None] * self._n_groups
        recon = [None] * self._n_groups

        for k in range(1, self._n_groups + 1):
            if k < self._n_groups:
                X_recon[k - 1] = np.dot(U[:, (k - 1):k], np.dot(np.diag(s[k - 1:k]), Vt[(k - 1):k, :]))
            else:
                X_recon[k - 1] = np.dot(U[:, k - 1:], np.dot(np.diag(s[k - 1:]), Vt[k - 1:, :]))
            recon[k - 1] = self.diagonal_average(X_recon[k - 1])

        return recon

    @staticmethod
    def diagonal_average(X):
        N, K = X.shape
        L = N + K - 1
        result = np.zeros(L)
        counts = np.zeros(L)
        for i in range(N):
            for j in range(K):
                result[i + j] += X[i, j]
                counts[i + j] += 1
        return result / counts

    def reset_data(self):
        self.dynamic_ssa_queue = [[0.0] * self.n_samples] * self._n_groups
        samples = np.arange(0, self.n_samples)
        for k in range(self._n_groups):
            self.line_plots[k].setData(x=samples, y=self.dynamic_ssa_queue[k])

    def update_ssa_params(self):
        self._window_size = self.ssa_controls[1].value()
        self._n_groups = self.ssa_controls[0].value()
        self.remove_layout(self.plot_layout)
        self.plot_layout = self.create_plot_widgets('vert', self._n_groups)

        self.line_plots = [None] * self._n_groups
        for k in range(self._n_groups):
            self.set_plot_range(self._plot_widgets[k], (0, self.n_samples), (-1, 1), pad=(0, 0))
            self.line_plots[k] = self._init_line_plot(self._plot_widgets[k], 'Sample', 'SSA Comp {:}'.format(k), 'r', 2)

        self._base_layout.addLayout(self.plot_layout)

    def update(self, md_data):
        # self.plot_data gets all the MD data being streamed
        self.plot_data = md_data
        re, im = self.select_data_source()
        cmplx_data = re[:4, -1] + 1j * im[:4, -1]
        d = self.select_data_component(cmplx_data)

        self.update_harmonics_mask()
        for k, mask in enumerate(self.harmonic_mask):
            if mask:
                self.harmonic_to_plot = k

        self.raw_data_queue = np.append(self.raw_data_queue, np.reshape(d, [4, 1]), axis=1)
        self.raw_data_queue = np.delete(self.raw_data_queue, 0, axis=1)

        # Apply transform
        self.dynamic_ssa_queue = self.dynamic_ssa(self.raw_data_queue[self.harmonic_to_plot, :])

        samples = np.arange(0, self.n_samples)

        for k in range(self._n_groups):
            if self.scrolling_controls[-1].isChecked():
                plot_data = np.fft.rfft(self.dynamic_ssa_queue[k])
                self.line_plots[k].setData(x=np.arange(0, len(plot_data)), y=np.abs(plot_data))
                self._plot_widgets[k].setXRange(0, len(plot_data))
            else:
                self.line_plots[k].setData(x=samples, y=self.dynamic_ssa_queue[k])

        self.update_fps(display=False)

