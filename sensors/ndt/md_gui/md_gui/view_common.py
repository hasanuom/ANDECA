from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np


class ViewCommon:
    def __init__(self, base_h_layout=None, nharmonics=0, harmonic_select='checkbox'):
        self.plot_data = []
        self.nharmonics = nharmonics
        self.harmonic_mask = [False] * self.nharmonics
        self.harmonic_select_control = harmonic_select

        self._base_layout = base_h_layout
        self.create_base_layout()
        self._ref_show = False
        self.polar_col = (192, 192, 192)
        self._system_harmonics = {}
        self._system_harmonics = {'enables': [], 'freq': []}
        self._plot_widgets = []
        self._image_widgets = []

    def create_base_layout(self):
        layout_plots = QVBoxLayout()
        self._base_layout.addLayout(layout_plots)
        harmonic_checkboxes = {'labels': ["{} kHz".format(k * 976) for k in range(self.nharmonics)],
                               'method': [self.update_harmonics_mask] * self.nharmonics}

        if self.harmonic_select_control == 'radio':
            harmonic_group, self.harmonic_controls = self.create_groupbox("Harmonics", 'radio', harmonic_checkboxes)
        elif self.harmonic_select_control is None:
            pass
        else:
            harmonic_group, self.harmonic_controls = self.create_groupbox("Harmonics", 'checkbox', harmonic_checkboxes)

        data_radios = {'labels': ['Calibrated', 'Transimpedance', 'Rx', 'Tx current'],
                       'method': [self.select_data_source] * 4}
        data_group, self.data_radio_controls = self.create_groupbox("Data Source", 'radio', data_radios)

        self.control_layout = self.add_layout(direction='vert')

        if self.harmonic_select_control is not None:
            for ctrl in self.harmonic_controls:
                ctrl.setChecked(True)

        self.data_radio_controls[2].setChecked(True)
        self.control_layout.addWidget(data_group)
        if self.harmonic_select_control is not None:
            self.control_layout.addWidget(harmonic_group)
        self._base_layout.addLayout(self.control_layout)

    def add_layout(self, direction='vert'):
        if direction == 'vert':
            layout = QVBoxLayout()
        elif direction == 'horiz':
            layout = QHBoxLayout()
        elif direction == 'grid':
            layout = QGridLayout()

        return layout

    def create_plot_widgets(self, direction='vert', number=1):
        if direction == 'vert':
            layout = QVBoxLayout()
        else:
            layout = QHBoxLayout()
        self._plot_widgets = [pg.PlotWidget() for _ in range(number)]

        for widget in self._plot_widgets:
            layout.addWidget(widget)

        return layout

    def create_image_widgets(self, direction='vert', number=1):
        if direction == 'vert':
            layout = QVBoxLayout()
        else:
            layout = QHBoxLayout()
        self._image_widgets = [pg.ImageView() for _ in range(number)]

        for widget in self._image_widgets:
            widget.ui.histogram.hide()
            widget.ui.roiBtn.hide()
            widget.ui.menuBtn.hide()
            layout.addWidget(widget)

        return layout

    def _init_line_plot(self, plot_widget, xlabel, ylabel, col, w):
        if plot_widget is not None:
            line_plot = plot_widget.plot(pen=pg.mkPen(color=col, width=w))
            plot_widget.showGrid(x=True, y=True, alpha=0.5)
            plot_widget.setLabel('bottom', xlabel, color='k')
            plot_widget.setLabel('left', ylabel, color='k')
            plot_widget.enableAutoRange(axis='y', enable=True)
        return line_plot

    def _init_scatter_plot(self, plot_widget, xlabel, ylabel, col):
        if plot_widget is not None:
            scatter_plot = plot_widget.scatterPlot(pen=pg.mkPen(color='k', width=1), brush=pg.mkBrush(col))
            plot_widget.showGrid(x=True, y=True, alpha=0.5)
            plot_widget.setLabel('bottom', xlabel, color='k')
            plot_widget.setLabel('left', ylabel, color='k')
        return scatter_plot

    def set_plot_range(self, plot, xrange, yrange, pad):
        plot.setXRange(xrange[0], xrange[1], padding=pad[0])
        plot.setYRange(yrange[0], yrange[1], padding=pad[1])

    def coordinate_circles(self, plot_widget):
        circ = np.logspace(-6, 4, 11)
        for r in circ:
            circle = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
            circle.setPen(pg.mkPen(self.polar_col))
            plot_widget.addItem(circle)

    def radial_lines(self, plot_widget):
        angles = np.arange(0, 360, 30)
        for a in angles:
            radial = QtCore.QLineF.fromPolar(1e4, a)
            line = QGraphicsLineItem(radial)
            line.setPen(pg.mkPen(self.polar_col))
            plot_widget.addItem(line)

    def add_label(self, layout, label_text):
        label = QLabel()
        label.setText(label_text)
        layout.addWidget(label)
        return label

    def create_display_form(self, title, control_dict):

        controls1 = [QRadioButton() for _ in control_dict['labels']]
        controls2 = [QRadioButton() for _ in control_dict['labels']]
        labels = [QLabel() for _ in control_dict['labels']]
        n_controls = len(control_dict['labels'])

        for k, label in enumerate(control_dict['labels']):
            labels[k].setText(control_dict['labels'][k])
            controls1[k].clicked.connect(control_dict['method1'][k])
            controls2[k].clicked.connect(control_dict['method2'][k])

        verticalSpacer = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)

        layout = QHBoxLayout()
        layout0 = QGridLayout()
        layout1 = QGridLayout()
        layout2 = QGridLayout()

        group0 = QGroupBox('Data')
        group1 = QGroupBox('Scatter')
        group2 = QGroupBox('Scrolling')

        for k in range(n_controls):
            layout0.addWidget(labels[k], k, 0)
            layout1.addWidget(controls1[k], k, 1)
            layout2.addWidget(controls2[k], k, 2)

        group0.setLayout(layout0)
        group1.setLayout(layout1)
        group2.setLayout(layout2)
        groupbox = QGroupBox(title)
        groupbox.setLayout(layout)

        layout.addWidget(group0)
        layout.addWidget(group1)
        layout.addWidget(group2)
        layout.addItem(verticalSpacer)

        return groupbox, (labels, controls1, controls2)

    def create_groupbox(self, title, control_type, control_dict):
        if control_type == 'button':
            controls = [QPushButton() for _ in control_dict['labels']]
        elif control_type == 'radio':
            controls = [QRadioButton() for _ in control_dict['labels']]
        elif control_type == 'checkbox':
            controls = [QCheckBox() for _ in control_dict['labels']]
        elif control_type == 'spinbox':
            spin_text = [QLabel() for _ in control_dict['labels']]
            controls = []
            for k, label in enumerate(control_dict['labels']):
                if control_dict['type'][k] == 'int':
                    controls.append(QSpinBox())
                elif control_dict['type'][k] == 'double':
                    controls.append(QDoubleSpinBox())
                else:
                    'Default to double'
                    controls.append(QDoubleSpinBox())

        if control_type != 'spinbox':
            for k, label in enumerate(control_dict['labels']):
                controls[k].setText(label)
                controls[k].clicked.connect(control_dict['method'][k])
        else:
            for k, label in enumerate(control_dict['labels']):
                spin_text[k].setText(label)
                if 'limits' in control_dict.keys():
                    controls[k].setMinimum(control_dict['limits'][k][0])
                    controls[k].setValue(control_dict['limits'][k][1])
                    controls[k].setMaximum(control_dict['limits'][k][2])
                controls[k].valueChanged.connect(control_dict['method'][k])

        verticalSpacer = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)

        layout = QVBoxLayout()

        if control_type != 'spinbox':
            for i in controls:
                layout.addWidget(i)
        else:
            for i, ctrl in enumerate(controls):
                layout.addWidget(spin_text[i])
                layout.addWidget(ctrl)

        groupbox = QGroupBox(title)
        groupbox.setLayout(layout)
        layout.addItem(verticalSpacer)

        return groupbox, controls

    def create_list_groupbox(self, title, control_dict):
        control = QListWidget()
        for k, label in enumerate(control_dict['labels']):
            control.insertItem(k, label)

        control.currentRowChanged.connect(control_dict['method'])
        control.setCurrentRow(0)
        # control.setMaximumWidth(1)
        layout = QVBoxLayout()
        layout.addWidget(control)
        verticalSpacer = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        groupbox = QGroupBox(title)
        groupbox.setMaximumWidth(150)
        groupbox.setLayout(layout)
        layout.addItem(verticalSpacer)
        return groupbox, control

    def clear_avg(self):
        self.averaging['n_avg'] = 0
        self.averaging['magnitude_accumulator'] = []

    def select_data_source(self):
        calibrated = self.data_radio_controls[0]
        trans = self.data_radio_controls[1]
        rx = self.data_radio_controls[2]
        tx = self.data_radio_controls[3]

        if calibrated.isChecked():
            xdata, ydata = self.plot_data[0]
        elif trans.isChecked():
            xdata, ydata = self.plot_data[1]
        elif rx.isChecked():
            xdata, ydata = self.plot_data[2]
        elif tx.isChecked():
            xdata, ydata = self.plot_data[3]

        return xdata, ydata

    def update_plot(self, xdata, ydata):
        # This method is overwritten in the tab subclasses as the xdata, ydata is plotted differently by each tab so we
        # may not need it here at all.
        pass

    def update(self, plot_data):
        self.plot_data = plot_data
        xdata, ydata = self.select_data_source()
        if self._plot_widgets[0] is not None:
            self.update_plot(xdata, ydata)

    def update_harmonics_mask(self):
        for k, ctrl in enumerate(self.harmonic_controls):
            if ctrl.isChecked():
                self.harmonic_mask[k] = True
            else:
                self.harmonic_mask[k] = False

    def system_harmonics_set(self, enables, frequencies: dict):
        '''
        :param enables: boolean list of length max tx frequency
        :param frequencies: integer (harmonic) frequency list
        :return:
        '''
        # These are the harmonics transmited and recieved
        # (Not the possible subset selected by the gui controls)
        # self.harmonic_mask['enables'] = enables
        # self._system_harmonics['freq'] = frequencies

        for i, cbox in enumerate(self.harmonic_controls):
            cbox.setText(str(frequencies[i]))
            cbox.setChecked(enables[i])
            if self.harmonic_select_control == 'checkbox':
                cbox.checkState()
            # controls[k].setText(label)
            # controls[k].clicked.connect(control_dict['method'][k])

        self.update_harmonics_mask()

    def remove_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        del layout

    def apply_autoscale(self):
        for plot_widget in self._plot_widgets:
            plot_widget.enableAutoRange(axis='y', enable=True)

    def remove_autoscale(self):
        for plot_widget in self._plot_widgets:
            plot_widget.enableAutoRange(axis='y', enable=False)
