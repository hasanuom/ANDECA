from PyQt5.QtWidgets import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np


class ViewTD:

    def __init__(self, tab_widget=None, tx_btn_event=None, null_btn_event=None, rx_btn_event=None, txi_btn_event=None):

        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Time Domain")
        self._base_layout = tab_layout

        self._tx_event = tx_btn_event
        self._null_event = null_btn_event
        self._rx_event = rx_btn_event
        self._txi_event = txi_btn_event

        self._ref_visible = False
        self.create_layout()
        self._data = None

    def create_layout(self):
        layout_plots = QVBoxLayout()
        control = QVBoxLayout()
        control.addWidget(self.create_dac_button_groupbox())
        control.addWidget(self.create_adc_button_groupbox())
        control.addWidget(self.create_ref_button_groupbox())

        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        control.addItem(verticalSpacer)

        self._base_layout.addLayout(control)
        self._base_layout.addLayout(self.create_plot_widgets())
        self._base_layout.addLayout(layout_plots)


    def create_ref_button_groupbox(self):
        _ref_btn = QPushButton("Ref.")

        self._ref_visibility_btn = QPushButton()
        self._ref_visibility_btn.setText("Ref. Visibility")
        self._ref_visibility_btn.setCheckable(True)
        self._ref_visibility_btn.setChecked(self._ref_visible)

        _ref_btn.clicked.connect(self._reference_event)
        self._ref_visibility_btn.clicked.connect(self._reference_visibility_event)
        layout = QVBoxLayout()
        layout.addWidget(_ref_btn)
        layout.addWidget(self._ref_visibility_btn)

        button_groupbox = QGroupBox("Reference")
        button_groupbox.setLayout(layout)
        return button_groupbox


    def create_dac_button_groupbox(self):
        _tx_btn = QPushButton("TX")
        _null_btn = QPushButton("Null")

        _tx_btn.clicked.connect(self._tx_event)
        _null_btn.clicked.connect(self._null_event)

        layout = QVBoxLayout()
        layout.addWidget(_tx_btn)
        layout.addWidget(_null_btn)
        button_groupbox = QGroupBox("DAC (12-bit)")
        button_groupbox.setLayout(layout)
        return button_groupbox


    def create_adc_button_groupbox(self):

        _rx_btn = QPushButton("RX")
        _txi_btn = QPushButton("TXI")

        _rx_btn.clicked.connect(self._rx_event)
        _txi_btn.clicked.connect(self._txi_event)

        layout = QVBoxLayout()
        layout.addWidget(_rx_btn)
        layout.addWidget(_txi_btn)
        button_groupbox = QGroupBox("ADC (16-bit)")
        button_groupbox.setLayout(layout)
        return button_groupbox

    def create_plot_widgets(self):
        layout = QVBoxLayout()
        self._plot_widget_td = pg.PlotWidget()
        layout.addWidget(self._plot_widget_td)

        self._init_td_plot()
        return layout

    def _init_td_plot(self):
        if self._plot_widget_td is not None:
            self.td_line = self._plot_widget_td.plot(pen=pg.mkPen(color='k'))
            self.ref_line = self._plot_widget_td.plot(pen=None)  # pen=None disables line drawing

            self._plot_widget_td.showGrid(x=True, y=True, alpha=0.5)
            self._plot_widget_td.setLabel('bottom', 'Sample Number', color='k')
            self._plot_widget_td.setLabel('left', 'ADC units', color='k')


    def plot_td(self, ref=False):
        if not ref:
            self.td_line.setData(x=self._xvals, y=self._data)
        else:
            self.ref_line.setData(x=self._xvals, y=self._data)
        #self._plot_widget_td.autoPixelRange(True)
        pitem = self._plot_widget_td.getPlotItem()
        pitem.autoRange()

    def _reference_event(self):
        self.plot_td(ref=True)

    def _reference_visibility_event(self):
        self._ref_visible = self._ref_visibility_btn.isChecked()

        if self._ref_visible:
            pen = pg.mkPen('b', width=0, style=QtCore.Qt.DashLine)
            self.ref_line.setPen(pen)
            self._reference_event()
        else:
            self.ref_line.setPen(None)

    def update(self, data: tuple):
        if self._plot_widget_td is not None:
            self._data = data[0]
            self._xvals = range(0, len(self._data))
            self.plot_td()

            # move this? - temp addition
            # temp = np.array(self._data)
            pk2pk = np.max(self._data) - np.min(self._data)
            print("peak-peak {} ADC units".format(pk2pk))
