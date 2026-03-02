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
import scipy.linalg as linalg
from plotter import Plotter as Pt
import matplotlib.pyplot as plt


class ViewPosScatterPlot(ViewCommon):

    def __init__(self, tab_widget=None, color_lookup=None):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Position")

        self._base_layout = tab_layout
        super().__init__(self._base_layout, nharmonics=4, harmonic_select='radio')

        self.color_lookup = color_lookup
        self.averaging = dict(use_averaging=True, n_avg=0, magnitude_accumulator=[])

        # Number of samples to plot
        self.n_samples = 300
        # Initialise plots - 1 scatter and 1 scrolling
        T = 50
        plot_layout = self.create_plot_widgets('vert', 2)
        self.set_plot_range(self._plot_widgets[0], (-T, T), (10, T), pad=(0, 0))
        self._plot_widgets[0].setAspectLocked()
        self.line_plot = self._init_line_plot(self._plot_widgets[1], 'Sample', 'z [cm]', 'r', 2)
        self.set_plot_range(self._plot_widgets[1], (0, self.n_samples), (0, 50), pad=(0, 0))
        self._base_layout.addLayout(plot_layout)
        self._plot_widgets[1].setFixedHeight(225)
        self.scatter_plot = self._init_scatter_plot_self(self._plot_widgets[0], 'x [cm]', 'y [cm]')

        # Data validator for colour limit controls
        self.colour_limits = (-1e4, 1e4)
        self.data_validator = QDoubleValidator(self.colour_limits[0], self.colour_limits[1], 4)
        self.data_validator.setNotation(QDoubleValidator.ScientificNotation)

        # Initialise plot controls
        processing_btn = {'labels': ['Store Data', 'Process'], 'method': [self.record_cscan, self.process_cscan]}
        clear_display_btn = {'labels': ['Clear Display'], 'method': [self.clear_display]}
        scatter_display_radio = {'labels': ['Re', 'Im', 'Mag', 'Ph', 'z', 'Fx PCA', 'Auto'],
                                 'method1': [self.scatter_plot_data] * 7, 'method2': [self.scrolling_plot_data] * 7}

        display_controlgroup, display_controls = self.create_display_form('Display Data', scatter_display_radio)
        self.display_labels = display_controls[0]
        self.scatter_controls = display_controls[1]
        self.scrolling_controls = display_controls[2]

        self.view_group, view_controls = self.create_cmap_controls("Display Controls", clear_display_btn)
        self.process_group, process_controls = self.create_groupbox("Processing", 'button', processing_btn)

        self.scatter_controls[5].setChecked(True)
        self.scrolling_controls[5].setChecked(True)

        view_controls[0].setMaximumWidth(150)
        self.view_group.setMaximumWidth(150)
        # display_controlgroup.setMinimumHeight(400)
        self.control_layout.addWidget(self.process_group)
        self.control_layout.addWidget(self.view_group)
        self.control_layout.addWidget(display_controlgroup)

        # Create brushes in advance
        # nColPts = Resolution of the colour space
        self.nColPts = 1024
        colormap = pg.colormap.get('viridis')
        colours = colormap.getLookupTable(0, 1, nPts=self.nColPts)
        self.brush_table = [QtGui.QBrush(QtGui.QColor(*col)) for col in colours]

        # Calculate fps so we can compare performance. ~15 fps is sufficient
        self.last_time = 0
        self.fps = None
        # self.fps_label = self.add_label(self.control_layout, "Mean Frame Rate: ")

        # Initialise data queues
        self.x_queue = [0.0] * self.n_samples
        self.y_queue = [0.0] * self.n_samples
        self.z_queue = np.zeros(self.n_samples)
        self.colour_queue = [0] * self.n_samples
        self.raw_complex_data_queue = np.zeros([4, self.n_samples])
        self.transformed_data_queue = np.zeros([8, self.n_samples])
        self.auto_transformed_data_queue = np.zeros([8, self.n_samples])
        self.line_data = [0.0] * self.n_samples
        self.scatter_colour_data = [0] * self.n_samples

        # Data for PCA Algorithm
        # directory = r'C:\Users\mchijaf3\Documents\Data\202211 Lab Trials'
        directory = r'C:\Users\mchijaf3\logfile\processed'
        # directory = os.getcwd()
        files = os.listdir(directory)
        # pca_select = 1 isn't too bad
        # Use pca_select = 0 if using _v2
        pca_select = 0
        pca_fname = [f for f in files if f.endswith('_pca_reim_comps.csv')]
        # pca_fname = 'pca_mean.csv'
        stats_fname = [f for f in files if f.endswith('_stats_reim.csv')]

        print('Using {:} for PCA transform'.format(pca_fname[pca_select]))
        print('Using {:} for PCA stats'.format(stats_fname[pca_select]))
        # self.pca_comps = pd.read_csv(os.path.join(directory1, pca_fname), header=0, index_col=0)
        self.pca_comps = pd.read_csv(os.path.join(directory, pca_fname[pca_select]), header=0, index_col=0)
        self.pca_stats = pd.read_csv(os.path.join(directory, stats_fname[pca_select]), header=0, index_col=0)
        self.norm_transform = self.pca_comps / np.max(np.abs(self.pca_comps))
        print('Norm transform: ')
        print(self.norm_transform)

        # ============================================
        # Filter parameters
        # self.filt_b, self.filt_a = scipy.signal.butter(3, 22, fs=50, btype='lowpass')
        self.filt_b, self.filt_a = scipy.signal.cheby2(4, 40, 22, fs=50, btype='lowpass')
        self.filt_zi = scipy.signal.lfilter_zi(self.filt_b, self.filt_a)
        # ============================================

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

    def clear_display(self):
        self.x_queue = [0.0] * self.n_samples
        self.y_queue = [0.0] * self.n_samples
        self.colour_queue = [0] * self.n_samples

    def update_plot(self, pos_data, md_data):
        # self.plot_data gets all the MD data being streamed
        self.plot_data = md_data
        x = pos_data[0][-1]
        y = pos_data[1][-1]
        zvals = pos_data[2][-self.n_samples:]

        re, im = self.select_data_source()

        cmplx_data = re[:4, -1] + 1j * im[:4, -1]
        data = np.hstack((np.real(cmplx_data), np.imag(cmplx_data)))
        self.raw_complex_data_queue = np.append(self.raw_complex_data_queue, np.reshape(cmplx_data, [4, 1]), axis=1)
        self.raw_complex_data_queue = np.delete(self.raw_complex_data_queue, 0, axis=1)

        data = data - self.pca_stats['mean'].to_numpy()
        data = data / self.pca_stats['sd'].to_numpy()

        # transform
        transformed_data = np.dot(data, self.norm_transform)

        self.x_queue.append(x)
        self.y_queue.append(y)
        self.z_queue = np.append(self.z_queue, zvals[-1])

        self.transformed_data_queue = np.append(self.transformed_data_queue, np.reshape(transformed_data, [8, 1]),
                                                axis=1)

        # Do PCA on complex data queue every time we receive a new sample
        auto_pca_data = np.vstack((np.real(self.raw_complex_data_queue), np.imag(self.raw_complex_data_queue)))
        _, _, _, self.auto_transformed_data_queue = self.pca(auto_pca_data.T, n_comps=8)
        self.auto_transformed_data_queue = self.auto_transformed_data_queue.T
        self.x_queue.pop(0)
        self.y_queue.pop(0)

        self.z_queue = np.delete(self.z_queue, 0, axis=0)
        self.transformed_data_queue = np.delete(self.transformed_data_queue, 0, axis=1)
        # =================================
        samples = np.arange(0, self.n_samples)

        self.update_harmonics_mask()
        for k, mask in enumerate(self.harmonic_mask):
            if mask:
                self.harmonic_to_plot = k

        self.set_line_data(harmonic=self.harmonic_to_plot)
        self.set_scatter_data(harmonic=self.harmonic_to_plot)

        self.line_plot.setData(x=samples, y=self.line_data)
        self.scatter_plot.setData(x=self.x_queue, y=self.y_queue, brush=self.scatter_colour_data)

        self.update_fps()

    def set_colour_map(self, data_queue):
        norm_data_queue = self.normalise_data(data_queue, self.colour_limits)
        data_cmap_idx = np.ceil([v * (self.nColPts - 1) for v in norm_data_queue]).astype(int)
        brush_list = [self.brush_table[k] for k in data_cmap_idx]
        return brush_list

    def set_scatter_data(self, harmonic=1):
        if self.scatter_controls[0].isChecked():
            # Re
            self.scatter_colour_data = self.set_colour_map(np.real(self.raw_complex_data_queue[harmonic, :]))
        elif self.scatter_controls[1].isChecked():
            # Im
            self.scatter_colour_data = self.set_colour_map(np.imag(self.raw_complex_data_queue[harmonic, :]))
        elif self.scatter_controls[2].isChecked():
            # Mag
            self.scatter_colour_data = self.set_colour_map(np.abs(self.raw_complex_data_queue[harmonic, :]))
        elif self.scatter_controls[3].isChecked():
            # Ph
            self.scatter_colour_data = self.set_colour_map(np.angle(self.raw_complex_data_queue[harmonic, :]))
        elif self.scatter_controls[4].isChecked():
            # z
            self.scatter_colour_data = self.set_colour_map(self.z_queue)
        elif self.scatter_controls[5].isChecked():
            # Fixed transformed data
            self.scatter_colour_data = self.set_colour_map(self.transformed_data_queue[2, :])
        elif self.scatter_controls[6].isChecked():
            # Auto transformed data
            self.scatter_colour_data = self.set_colour_map(np.abs(self.auto_transformed_data_queue[2, :]))
            # self.scatter_colour_data = self.set_colour_map(self.auto_transformed_data_queue[2, :])

    def set_line_data(self, harmonic=1):
        if self.scrolling_controls[0].isChecked():
            # Re
            self.line_data = np.real(self.raw_complex_data_queue[harmonic, :])
        elif self.scrolling_controls[1].isChecked():
            # Im
            self.line_data = np.imag(self.raw_complex_data_queue[harmonic, :])
        elif self.scrolling_controls[2].isChecked():
            # Mag
            self.line_data = np.abs(self.raw_complex_data_queue[harmonic, :])
        elif self.scrolling_controls[3].isChecked():
            # Ph
            self.line_data = np.angle(self.raw_complex_data_queue[harmonic, :])
        elif self.scrolling_controls[4].isChecked():
            # z
            self.line_data = self.z_queue
        elif self.scrolling_controls[5].isChecked():
            # Fixed transformed data
            self.line_data = self.transformed_data_queue[2, :]
        elif self.scrolling_controls[6].isChecked():
            # Auto transformed data
            self.line_data = self.auto_transformed_data_queue[2, :]

    def scrolling_plot_data(self):
        # 0: 'Re', 1: 'Im', 2: 'Mag', 3: 'Ph', 4: 'z', 5: 'C ind', 6: 'Fx PCA', 7:'Auto PCA'
        if self.scrolling_controls[0].isChecked():
            self._plot_widgets[1].setLabel('left', 'Re')
        elif self.scrolling_controls[1].isChecked():
            self._plot_widgets[1].setLabel('left', 'Im')
        elif self.scrolling_controls[2].isChecked():
            self._plot_widgets[1].setLabel('left', 'Mag')
        elif self.scrolling_controls[3].isChecked():
            self._plot_widgets[1].setLabel('left', 'Ph')
        elif self.scrolling_controls[4].isChecked():
            self._plot_widgets[1].setLabel('left', 'z [cm]')
        elif self.scrolling_controls[5].isChecked():
            self._plot_widgets[1].setLabel('left', 'Fx PCA')
        elif self.scrolling_controls[6].isChecked():
            self._plot_widgets[1].setLabel('left', 'Auto PCA')

    def _init_scatter_plot_self(self, plot_widget, xlabel, ylabel):
        if plot_widget is not None:
            scatter_plot = pg.ScatterPlotItem(pxmode=False, size=12)
            plot_widget.showGrid(x=True, y=True, alpha=0.5)
            plot_widget.setLabel('bottom', xlabel, color='k')
            plot_widget.setLabel('left', ylabel, color='k')
            plot_widget.addItem(scatter_plot)
        return scatter_plot

    def update_fps(self):
        now = perf_counter()
        dt = now - self.last_time
        self.last_time = now
        if self.fps is None:
            self.fps = 1.0 / dt
        else:
            s = np.clip(dt * 3., 0, 1)
            self.fps = self.fps * (1 - s) + (1.0 / dt) * s

        # print(self.fps)
        # self.fps_label.setText("Mean frame rate: {:3.2f}".format(self.fps))

    # def plotting_controls(self):
    #     self.lower_limit_ctrl, lower_label = self.line_edit('Lower', 85.4)
    #     self.upper_limit_ctrl, upper_label = self.line_edit('Upper', 86.4)
    #     self.view_group.layout().addWidget(QLabel('Colour Scale Limits'))
    #     self.view_group.layout().addWidget(lower_label)
    #     self.view_group.layout().addWidget(self.lower_limit_ctrl)
    #     self.view_group.layout().addWidget(upper_label)
    #     self.view_group.layout().addWidget(self.upper_limit_ctrl)
    #
    #     self.lower_limit_ctrl.textChanged.connect(self.update_colour_limits)
    #     self.upper_limit_ctrl.textChanged.connect(self.update_colour_limits)

    def line_edit(self, label_str, val):
        ctrl = QLineEdit()
        ctrl.setMaximumWidth(120)
        label = QLabel()
        label.setText(label_str)
        ctrl.setText(str(val))
        ctrl.setValidator(self.data_validator)
        return ctrl, label

    def update_colour_limits(self):
        # print('Colour limit changed')
        self.colour_limits = (float(self.lower_limit_ctrl.text()),
                              float(self.upper_limit_ctrl.text()))

    def scatter_plot_data(self):
        # 0: 'Re', 1: 'Im', 2: 'Mag', 3: 'Ph', 4: 'z', 5: 'C ind', 6: 'Fx PCA', 7:'Auto PCA'
        if self.scatter_controls[0].isChecked():
            self._plot_widgets[0].setTitle('Real')
        elif self.scatter_controls[1].isChecked():
            self._plot_widgets[0].setTitle('Imag')
        elif self.scatter_controls[2].isChecked():
            self._plot_widgets[0].setTitle('Mag')
        elif self.scatter_controls[3].isChecked():
            self._plot_widgets[0].setTitle('Ph')
        elif self.scatter_controls[4].isChecked():
            self._plot_widgets[0].setTitle('z [cm]')
        elif self.scatter_controls[5].isChecked():
            self._plot_widgets[0].setTitle('Fx PCA')
        elif self.scatter_controls[6].isChecked():
            self._plot_widgets[0].setTitle('Auto PCA')

    def record_cscan(self):
        path = r'C:\Users\Adam\Documents\Lab Trials Nov 2022\recorded'
        timestr = time.strftime("%Y%m%d_%H%M%S")
        fname = os.path.join(path, timestr + '.pkl')
        output = np.vstack((np.real(self.raw_complex_data_queue), np.imag(self.raw_complex_data_queue)))
        output = {'data': output, 'x': self.x_queue, 'y': self.y_queue, 'z': self.z_queue}
        with open(fname, "wb") as file:
            print('Writing data...')
            pickle.dump(output, file)
        print('Done')

    def process_cscan(self):
        root = tk.Tk()
        root.wm_attributes('-topmost', 1)
        root.withdraw()
        path = r'C:\Users\Adam\Documents\Lab Trials Nov 2022\recorded'
        file = fd.askopenfilename(initialdir=path, parent=root, filetypes=[("pkl", ".pkl")])
        print("Data file: {}".format(file))
        print('Unpickling ', file)
        with open(file, "rb") as f:
            data = pickle.load(f)

        _, s, pca_comps, transf_data = self.pca(data['data'].T, n_comps=8)
        pt = Pt(file.split('/')[-1])
        pos = np.array([data['x'], data['y'], data['z']])
        print(transf_data.shape)
        pos_time_idx = np.arange(0, self.n_samples)
        pt.interp_cscan(pos, transf_data, pos_time_idx, singular_values=s)
        plt.show()

    @staticmethod
    def pca(data, axis=None, n_comps=1):
        d = np.copy(data)
        d -= np.mean(data, axis=axis)
        std = np.std(data, axis=axis)
        if std.all() != 0:
            d /= np.std(data, axis=axis)
        else:
            pass
        U, s, V = linalg.svd(d)
        s = s[:n_comps]
        V = V.T[:, :n_comps]
        return U, s, V, np.dot(d, V)

    def create_cmap_controls(self, title, control_dict):
        controls = [QPushButton() for _ in control_dict['labels']]

        for k, label in enumerate(control_dict['labels']):
            controls[k].setText(label)
            controls[k].clicked.connect(control_dict['method'][k])

        layout = QGridLayout()
        for c in controls:
            layout.addWidget(c, 0, 0, 1, 2)

        self.upper_limit_ctrl, upper_label = self.line_edit('Lower', 0.0)
        self.lower_limit_ctrl, lower_label = self.line_edit('Upper', 1.0)

        layout.addWidget(upper_label, 1, 0)
        layout.addWidget(lower_label, 1, 1)
        layout.addWidget(self.upper_limit_ctrl, 2, 0)
        layout.addWidget(self.lower_limit_ctrl, 2, 1)

        self.lower_limit_ctrl.textChanged.connect(self.update_colour_limits)
        self.upper_limit_ctrl.textChanged.connect(self.update_colour_limits)

        groupbox = QGroupBox(title)
        groupbox.setLayout(layout)

        verticalSpacer = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        layout.addItem(verticalSpacer)

        return groupbox, controls
