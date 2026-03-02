"""
Frequency Response Analyser (FRA)

"""
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np
from enum import Enum, unique, auto
import pandas as pd

class ViewSpectrumFRA:

    def __init__(self, tab_widget=None, get_fra_btn_event=None):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "FRA")
        self._base_layout = tab_layout

        self._get_fra_btn_event = get_fra_btn_event

        self.xscale_select = 'harmonics'
        #self.yscale_select = 'dBFS'
        self.yscale_select = 'linear'

        self._averaging = dict(enable=False, n_avg=0, magnitude_accumulator=[])
        self._ref_visible = False

        self._ref_show = False
        self._magnitude = []

        self._fra_cal = FraCalibration()
        self._fra_data = {}

        # plot widgets
        self.mplot_rxv = MagnitudePlot('RXV', self._fra_cal.values, isTXI=False, lcolor='r')
        self.mplot_txi = MagnitudePlot('TXI', self._fra_cal.values, isTXI=True, lcolor='b')
        self.ph_plot = PhasePlot('Phase')

        # buttons
        self._fra_run_btn = QPushButton()
        self._average_btn = QPushButton()
        self._ref_visibility_btn = QPushButton()
        self._cal_btn = QCheckBox("Calibration")
        self._cal_clear_btn = QPushButton()

        self._save_btn = QPushButton()
        # Create layout
        self.create_layout()

    def create_layout(self):
        layout_plots = QVBoxLayout()
        self._base_layout.addWidget(self.create_button_groupbox())
        self._base_layout.addLayout(self.create_plot_widgets())
        self._base_layout.addLayout(layout_plots)

    def create_button_groupbox(self):

        self._fra_run_btn.setText("Run FRA")

        self._average_btn.setText("Avg. Enable")
        self._average_btn.setCheckable(True)
        self._average_btn.setChecked(self._averaging['enable'])

        _ref_btn = QPushButton()
        _ref_btn.setText("Reference")

        self._ref_visibility_btn.setText("Ref. Visibility")
        self._ref_visibility_btn.setCheckable(True)
        self._ref_visibility_btn.setChecked(self._ref_visible)

        _harm_label = QLabel("1 harmonic = 976Hz")

        self._fra_run_btn.clicked.connect(self._get_fra_btn_event)
        self._average_btn.clicked.connect(self._averaging_event)

        _ref_btn.clicked.connect(self._reference_event)
        self._ref_visibility_btn.clicked.connect(self._reference_visibility_event)


        self._cal_btn.setChecked(False)


        self._cal_clear_btn.setText("Cal Clear")
        #self._ref_visibility_btn.setCheckable(True)
        #self._ref_visibility_btn.setChecked(self._ref_visible)
        self._cal_clear_btn.clicked.connect(self.cal_clear_event)

        self._save_btn.setText("Save")
        self._save_btn.clicked.connect(self.write_df_to_pickle)

        self._save_filename = ''


        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        layout = QVBoxLayout()
        layout.addWidget(self._fra_run_btn)
        layout.addWidget(self._average_btn)
        layout.addWidget(_harm_label)
        layout.addWidget(_ref_btn)
        # layout.addWidget(self._ref_visibility_btn)
        layout.addWidget(self._cal_btn)
        layout.addWidget(self._cal_clear_btn)
        layout.addWidget(self._save_btn)
        layout.addItem(verticalSpacer)

        button_groupbox = QGroupBox("Spectrum")
        button_groupbox.setLayout(layout)
        return button_groupbox

    def create_plot_widgets(self):
        layout = QVBoxLayout()
        layout.addWidget(self.mplot_rxv.get_plot_widget())
        layout.addWidget(self.mplot_txi.get_plot_widget())
        #layout.addWidget(self._plot_widget_phase)
        layout.addWidget(self.ph_plot.get_plot_widget())

        #self._init_phase_plot()
        return layout


    # def _init_phase_plot(self):
    #     if self._plot_widget_phase is not None:
    #         self.phase_line = self._plot_widget_phase.plot(pen=pg.mkPen(color='k'))
    #         self._plot_widget_phase.showGrid(x=True, y=True, alpha=0.5)
    #         self._plot_widget_phase.setLabel('bottom', 'Harmonic Number', color='k')
    #         self._plot_widget_phase.setLabel('left', 'Phase(Degrees)', color='k')




    # def plot_phase(self, xvals, data):
    #
    #     #xvals = self.x_values(data)
    #
    #     # Calculate phase (Degrees)
    #     phase_deg = np.angle(data, deg=True)
    #
    #     # self.uiSpectrumMagPlotWidget.plot(xscale, mag)
    #     self.phase_line.setData(x=xvals, y=phase_deg)

    def _reference_event(self):
        self.plot_magnitude(self._magnitude, ref=True)

    def cal_clear_event(self):
        self._fra_cal.clear()

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

    def write_df_to_pickle(self):
        if self._fra_data is None:
            return
        filename = self.file_dialog()
        if len(filename)== 0:
            print('File not saved - no filename')
            return
        _xvals = np.abs(self._fra_data[0]['harmonic_freq']) # not complex
        rxv = np.array(self._fra_data[0]['data'], dtype=complex)
        txi = np.array(self._fra_data[1]['data'], dtype=complex)
        d = {'harmonic': _xvals, 'rxv': rxv, 'txi': txi}
        df = pd.DataFrame(data=d)
        df.to_pickle(filename)
        print('Frequency Response Saved')

    def file_dialog(self):
        file, check = QFileDialog.getSaveFileName(None, "Swept Frequency Response",
                                                  "", "All Files (*);")
        if check:
            print(file)
            return file



    def update(self, data: tuple):

        fra = data[0] # unpack the tuple
        #self._fra_data = fra
        if self._averaging['enable']==True and len(self._fra_data) != 0:

            self._fra_data[0]['data'] = np.add(self._fra_data[0]['data'], fra[0]['data'])/2
            self._fra_data[1]['data'] = np.add(self._fra_data[1]['data'], fra[1]['data'])/2

        else:
            self._fra_data = fra

        if self._cal_btn.isChecked():
            self._fra_cal.update(self._fra_data)
            self._cal_btn.setChecked(False)
        self.mplot_rxv.update(self._fra_data)
        self.mplot_txi.update(self._fra_data)
        self.ph_plot.update(self._fra_data)





class MagnitudePlot:
    def __init__(self, title: str, calibration_callback=None, isTXI=False, lcolor='k'):

        self._title = title
        self._calibration_callback = calibration_callback

        self._xscale_type = 'harmonics'
        # self.yscale_select = 'dBFS'
        self._yscale_type = 'linear'

        self._averaging = dict(enable=False, n_avg=0, magnitude_accumulator=[])
        self._ref_visible = False

        self._ref_show = False
        self.data = []
        self._mag_raw = []
        self._ref = []

        if isTXI:
            self._idx = 1
        else:
            self._idx = 0

        # plot widgets
        self._pwidget = pg.PlotWidget()
        self.mag_line = self._pwidget.plot(pen=pg.mkPen(color=lcolor), title=self._title)
        self.ref_line = self._pwidget.plot(pen=None, title=self._title )  # pen=None disables line drawing

        self._pwidget.showGrid(x=True, y=True, alpha=0.5)

        self._pwidget.setTitle(self._title, color='k', size='14')
        self._pwidget.setLabel('bottom', 'Harmonic Number', color='k')
        self._pwidget.setLabel('left', '\u01c0H(\u03C9)\u01c0\ (ADC units)', color='k')


    def get_plot_widget(self):
        return self._pwidget

    @property
    def yscale_type(self):
        return self._yscale_type

    @yscale_type.setter
    def yscale_type(self, yscale_type : str):
        self._yscale_type = yscale_type

    @property
    def xscale_type(self):
        return self._xscale_type

    @xscale_type.setter
    def xscale_type(self, xscale_type: str):
        self._xscale_type = xscale_type

    def _calc_magnitude(self):

        mag = np.abs(self.data)
        if self._calibration_callback is not None:
            if len(self._calibration_callback()) != 0:
                if self._idx == 0:
                    mag_cal = np.abs(np.array(self._calibration_callback()['rxv']))
                else:
                    mag_cal = np.abs(np.array(self._calibration_callback()['txi']))
                mag = mag / mag_cal

        if self._yscale_type == 'dBc':
            x_ = mag
            y_ = x_ / np.max(x_)
            mag = 20 * np.log10(y_)

        elif self._yscale_type == 'dBFS':
            # See Wikipedia dBFS entry. Additionally this from a forum post:
            # A sine of Amplitude A will give you a bin magnitude of N * A / 2 (if sine frequency fits the bin exactly),
            # where N is your FFT length. So if you want the dB scale in your analyzer to have some actual
            # quantitative meaning, it would be appropriate to scale it so that a 0dB sine will give you a 0dB bin
            # amplitude.
            # So your dB value would be 20 * log(2 * magnitude / N). That's what most analyzers do.
            #
            k = mag

            # A full-scale sinusoid would has an amplitude of ADC_range / 2 i.e. 2**(number bits) / 2
            # i.e. for a 16-bit ADC 2**16/2 = 2**15
            k = k / (2**15)  # normalise to Full scale

            # Note: The TI board performs a pre-scaling so that the outputs are in ADC units. This pre-scaling factor is
            # equal to 2/N = 2/1024
            # Therefore the following line is commented out!
            # k = 2 * k / 1024 # factor of two due to a FS sine-wave being A/2
            mag = 20 * np.log10(k)
            self._pwidget.setLabel('left', '\u01c0H(\u03C9)\u01c0\ (dBFS)', color='k')
        elif self._yscale_type == 'linear':
            self._pwidget.setLabel('left', '\u01c0H(\u03C9)\u01c0\ (ADC units)', color='k')
        else:
            raise ValueError("Spectrum yscale selection failed")

        return mag


    def plot_magnitude(self, ref=False):

        #xvals = self.x_values(magnitude)
        mag = self._calc_magnitude()
        if not ref:
            self.mag_line.setData(x=self._xvals, y=mag)
        else:
            self.ref_line.setData(x=self._xvals, y=mag)

    def update(self, fra):

        if self._pwidget is not None:
            self._xvals = fra[self._idx]['harmonic_freq']
            #np_data = np.array(fra['data'], dtype=complex)

            self.data = np.array(fra[self._idx]['data'], dtype=complex)
            self.plot_magnitude()


class PhasePlot:
    def __init__(self, title: str):

        self._title = title
        self._xscale_type = 'harmonics'
        # self.yscale_select = 'dBFS'
        self._yscale_type = 'linear'

        self._data_txi = []
        self._data_rxv = []
        self._ph_raw_txi = []
        self._ph_raw_rxv = []
        self._ref = []

        self._unwrap = True

        # plot widgets
        self._pwidget = pg.PlotWidget()

        self._legend = self._pwidget.addLegend()

        self._lines = []
        self._lines.append(self._pwidget.plot(pen=pg.mkPen(color='r'), name='RXV'))
        self._lines.append(self._pwidget.plot(pen=pg.mkPen(color='b'), name='TXI'))

        self._pwidget.setTitle(self._title, color='k', size='14')
        self._pwidget.setLabel('bottom', 'Harmonic Number', color='k')
        self._pwidget.setLabel('left', 'Phase(Degrees)', color='k')
        self._pwidget.showGrid(x=True, y=True, alpha=0.5)

    def get_plot_widget(self):
        return self._pwidget

    @property
    def unwrap(self):
        return self._unwrap

    @unwrap.setter
    def unwrap(self, unwrap : bool):
        self._unwrap = unwrap

    def plot_phase(self):
        # Calculate phase (Degrees)
        ph= self.phase_calc(self._data_rxv)
        self._lines[0].setData(x=self._xvals, y=ph)

        ph= self.phase_calc(self._data_txi)
        self._lines[1].setData(x=self._xvals, y=ph)

    def phase_calc(self, data):
        ph = np.angle(data)

        if self._unwrap:
            ph = np.unwrap(ph)

        # convert to degrees
        ph = np.rad2deg(ph)
        return ph

    def update(self, fra):
        if self._pwidget is not None:
            self._xvals = fra[0]['harmonic_freq']
            self._data_rxv = np.array(fra[0]['data'], dtype=complex)
            self._data_txi = np.array(fra[1]['data'], dtype=complex)
            self.plot_phase()


class FraCalibration:
    def __init__(self):
        self._cal = {}


    def values(self):
        return self._cal

    def clear(self):
        del self._cal
        self._cal = {}
        print('clear')

    def update(self, fra):
        print('running cal update')
        self._cal['rxv'] = np.array(fra[0]['data'], dtype=complex)
        self._cal['txi'] = np.array(fra[1]['data'], dtype=complex)


@unique
class XScale(Enum):
    HARMONIC = auto()
    LINEAR = auto()

@unique
class YScale(Enum):
    dBc = auto()
    LINEAR = auto()
    dBFS = auto()

class SpectumData:
    def __init__(self):

        self._data = []
        self._cal = []
        self._ref = []

        self._xscale = XScale.LINEAR
        self._yscale = YScale.LINEAR

