from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np


class ViewSpectrum:

    def __init__(self, tab_widget=None, rxv_btn_event=None, txi_btn_event=None):

        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Spectrum")
        self._base_layout = tab_layout

        self._get_spectrum_rx_event = rxv_btn_event
        self._get_spectrum_tx_event = txi_btn_event

        self.xscale_select = 'harmonics'
        #self.yscale_select = 'dBFS'
        self.yscale_select = 'linear'

        self._averaging = dict(enable=False, n_avg=0, magnitude_accumulator=[])
        self._ref_visible = False
        self.create_layout()

        #self._ref_show = False
        self._magnitude = []

    def create_layout(self):
        layout_plots = QVBoxLayout()
        self._base_layout.addWidget(self.create_button_groupbox())
        self._base_layout.addLayout(self.create_plot_widgets())
        self._base_layout.addLayout(layout_plots)

    def create_button_groupbox(self):

        _rxv_btn = QPushButton()
        _rxv_btn.setText("Rx Volts")
        # _rxv_btn.setAutoDefault(False)
        # _rxv_btn.setDefault(False)
        # _rxv_btn.clicked.connect(self._refresh)

        _txi_btn = QPushButton()
        _txi_btn.setText("TX Current")

        self._average_btn = QPushButton()
        self._average_btn.setText("Avg. Enable")
        self._average_btn.setCheckable(True)
        self._average_btn.setChecked(self._averaging['enable'])

        _ref_btn = QPushButton()
        _ref_btn.setText("Reference")

        self._ref_visibility_btn = QPushButton()
        self._ref_visibility_btn.setText("Ref. Visibility")
        self._ref_visibility_btn.setCheckable(True)
        self._ref_visibility_btn.setChecked(self._ref_visible)

        _harm_label = QLabel("1 harmonic = 976Hz")

        _rxv_btn.clicked.connect(self._get_spectrum_rx_event)
        _txi_btn.clicked.connect(self._get_spectrum_tx_event)
        self._average_btn.clicked.connect(self._averaging_event)

        _ref_btn.clicked.connect(self._reference_event)
        self._ref_visibility_btn.clicked.connect(self._reference_visibility_event)

        verticalSpacer = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)

        layout = QVBoxLayout()
        layout.addWidget(_rxv_btn)
        layout.addWidget(_txi_btn)
        layout.addWidget(self._average_btn)
        layout.addWidget(_harm_label)
        layout.addWidget(_ref_btn)
        layout.addWidget(self._ref_visibility_btn)
        layout.addItem(verticalSpacer)

        button_groupbox = QGroupBox("Spectrum")
        button_groupbox.setLayout(layout)
        return button_groupbox

    def create_plot_widgets(self):
        layout = QVBoxLayout()
        self._plot_widget_mag = pg.PlotWidget()
        self._plot_widget_phase = pg.PlotWidget()

        layout.addWidget(self._plot_widget_mag)
        layout.addWidget(self._plot_widget_phase)

        self._init_magnitude_plot()
        self._init_phase_plot()

        return layout

    def _init_magnitude_plot(self):
        if self._plot_widget_mag is not None:
            self.mag_line = self._plot_widget_mag.plot(pen=pg.mkPen(color='k'))
            self.ref_line = self._plot_widget_mag.plot(pen=None)  # pen=None disables line drawing

            self._plot_widget_mag.showGrid(x=True, y=True, alpha=0.5)
            self._plot_widget_mag.setLogMode(y=True)

            self._plot_widget_mag.setLabel('bottom', 'Harmonic Number', color='k')
            self._plot_widget_mag.setLabel('left', '\u01c0H(\u03C9)\ (ADC units)', color='k')

    def _init_phase_plot(self):
        if self._plot_widget_phase is not None:
            self.phase_line = self._plot_widget_phase.plot(pen=pg.mkPen(color='k'))
            self._plot_widget_phase.showGrid(x=True, y=True, alpha=0.5)
            self._plot_widget_phase.setLabel('bottom', 'Harmonic Number', color='k')
            self._plot_widget_phase.setLabel('left', 'Phase(Degrees)', color='k')

    def _calc_magnitude(self, magnitude):

        if self.yscale_select == 'dBc':
            x_ = abs(magnitude)
            y_ = x_ / np.max(x_)
            mag = 20 * np.log10(y_)

        elif self.yscale_select == 'dBFS':
            # See Wikipedia dBFS entry. Additionally this from a forum post:
            # A sine of Amplitude A will give you a bin magnitude of N * A / 2 (if sine frequency fits the bin exactly),
            # where N is your FFT length. So if you want the dB scale in your analyzer to have some actual
            # quantitative meaning, it would be appropriate to scale it so that a 0dB sine will give you a 0dB bin
            # amplitude.
            # So your dB value would be 20 * log(2 * magnitude / N). That's what most analyzers do.
            #
            k = abs(magnitude)

            # A full-scale sinusoid would has an amplitude of ADC_range / 2 i.e. 2**(number bits) / 2
            # i.e. for a 16-bit ADC 2**16/2 = 2**15
            k = k / (2 ** 15)  # normalise to Full scale

            # Note: The TI board performs a pre-scaling so that the outputs are in ADC units. This pre-scaling factor is
            # equal to 2/N = 2/1024
            # Therefore the following line is commented out!
            # k = 2 * k / 1024 # factor of two due to a FS sine-wave being A/2
            mag = 20 * np.log10(k)
            self._plot_widget_mag.setLabel('left', '\u01c0H(\u03C9)\ (dBFS)', color='k')
        elif self.yscale_select == 'linear':
            mag = abs(magnitude)
            self._plot_widget_mag.setLabel('left', '\u01c0H(\u03C9)\ (ADC units)', color='k')
        else:
            raise ValueError("Spectrum yscale selection failed")

        return mag


    def plot_magnitude(self, magnitude, ref=False):

        xvals = self.x_values(magnitude)
        mag = self._calc_magnitude(magnitude)
        if not ref:
            self.mag_line.setData(x=xvals, y=mag)
        else:
            self.ref_line.setData(x=xvals, y=mag)

    def plot_phase(self, data):

        xvals = self.x_values(data)

        # Calculate phase (Degrees)
        phase_deg = np.angle(data, deg=True)

        # self.uiSpectrumMagPlotWidget.plot(xscale, mag)
        self.phase_line.setData(x=xvals, y=phase_deg)

    def _reference_event(self):
        self.plot_magnitude(self._magnitude, ref=True)

    def _reference_visibility_event(self):
        self._ref_visible = self._ref_visibility_btn.isChecked()

        if self._ref_visible:
            pen = pg.mkPen('b', width=0, style=QtCore.Qt.DashLine)
            self.ref_line.setPen(pen)
            self._reference_event()
        else:
            self.ref_line.setPen(None)

    def x_values(self, data):

        k = len(data)
        # Calculate X-axis
        if self.xscale_select == 'harmonics':
            xscale = np.linspace(0, k, k, endpoint=False)
        elif self.xscale_select == 'kilohertz':
            xscale = np.linspace(0, 1e6 / 2, k, endpoint=False)
            xscale = xscale / 1000  # covert to kHz
        else:
            raise ValueError("Spectrum xscale selection failed")

        return xscale

    def _averaging_event(self):
        self._averaging['enable'] = self._average_btn.isChecked()
        if self._averaging['enable'] == False:
            self._averaging['n_avg'] = 0
            self._averaging['magnitude_accumulator'] = []

    def update(self, data):
        if self._plot_widget_mag is not None:
            self._data = data[0]
            x = abs(self._data)
            # The RFFT does not scale the DC and Nyquist bins the same as other bins.
            x[0]  *= 2   # DC frequency
            x[-1] *= 2   # Nyquist frequency
            if self._averaging['enable'] == True:
                if not len(self._averaging['magnitude_accumulator']):
                    self._averaging['magnitude_accumulator'] = x

                else:
                    self._averaging['magnitude_accumulator'] = self._averaging['magnitude_accumulator'] + x
                self._averaging['n_avg'] += 1
                self._magnitude = self._averaging['magnitude_accumulator'] / self._averaging['n_avg']
            else:
                self._magnitude = abs(self._data)

            self.plot_magnitude(self._magnitude)

        if self._plot_widget_phase is not None:
            self.plot_phase(self._data)
