import enum

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from view_common import ViewCommon
import numpy as np
from enum import Enum, auto, unique


class ViewScrolling(ViewCommon):
    @unique
    class __state(Enum):
        OFF = auto()
        RE_IM = auto()
        MAG_PH = auto()

    def __init__(self, tab_widget=None, color_lookup=None):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Scrolling")
        self._base_layout = tab_layout
        super().__init__(self._base_layout, nharmonics=15)

        self._n_points = 300 # points to plot
        self.color_lookup = color_lookup

        plot_layout = self.create_plot_widgets('vert', 2)

        upper_control = {'labels': ['Off', 'Real', 'Mag'],
                         'method': [self.set_plot_type_upper] * 3}

        lower_control = {'labels': ['Off', 'Imag', 'Phase'],
                         'method': [self.set_plot_type_lower] * 3}

        control_group_upp, self.plotting_controls_upp = self.create_groupbox("Upper plot", 'radio', upper_control)
        control_group_low, self.plotting_controls_low = self.create_groupbox("Lower plot", 'radio', lower_control)

        self.plotting_controls_upp[1].setChecked(True)
        self.plotting_controls_low[1].setChecked(True)

        self._upper_plot_state = self.__state.OFF
        self._lower_plot_state = self.__state.OFF

        self.control_layout.addWidget(control_group_upp)
        self.control_layout.addWidget(control_group_low)
        self._base_layout.addLayout(plot_layout)

        self.line_plot_1 = []
        self.line_plot_2 = []

        for k in range(self.nharmonics):
            self.line_plot_1.append(
                self._init_line_plot(self._plot_widgets[0], 'Samples', 'ylabel', self.color_lookup[k], 2))
            self.line_plot_2.append(
                self._init_line_plot(self._plot_widgets[1], 'Samples', 'ylabel', self.color_lookup[k], 2))



    def set_plot_type_upper(self):

        if self.plotting_controls_upp[0].isChecked():
            self._upper_plot_state = self.__state.OFF
        elif self.plotting_controls_upp[1].isChecked():
            self._upper_plot_state = self.__state.RE_IM
            self._plot_widgets[0].setLabel('left', 'Real', color='k')
        elif self.plotting_controls_upp[2].isChecked():
            self._upper_plot_state = self.__state.MAG_PH
            self._plot_widgets[0].setLabel('left', 'Magnitude', color='k')

    def set_plot_type_lower(self):
        if self.plotting_controls_low[0].isChecked():
            self._lower_plot_state = self.__state.OFF
        elif self.plotting_controls_low[1].isChecked():
            self._lower_plot_state = self.__state.RE_IM
            self._plot_widgets[1].setLabel('left', 'Imag', color='k')
        elif self.plotting_controls_low[2].isChecked():
            self._lower_plot_state = self.__state.MAG_PH
            self._plot_widgets[1].setLabel('left', 'Phase', color='k')


    def update_plot(self, xdata, ydata):
            if self._upper_plot_state == self.__state.RE_IM:
                for k in range(self.nharmonics):
                    if self.harmonic_mask[k]:
                        self.line_plot_1[k].setData(xdata[k, -self._n_points:])
                        #self.line_plot_1[k].setBrush(pg.mkBrush(self.color_lookup[k]))
                    else:
                        #self.line_plot_1[k].setBrush(None)
                        self.line_plot_1[k].clear()

            elif self._upper_plot_state == self.__state.MAG_PH:
                mag = np.sqrt(xdata ** 2 + ydata ** 2)
                for k in range(self.nharmonics):
                    if self.harmonic_mask[k]:
                        self.line_plot_1[k].setData(mag[k, -self._n_points:])
                        #self.line_plot_1[k].setBrush(pg.mkBrush(self.color_lookup[k]))
                    else:
                        #self.line_plot_1[k].setBrush(None)
                        self.line_plot_1[k].clear()
            else:
                pass

            if self._lower_plot_state == self.__state.RE_IM:

                for k in range(self.nharmonics):
                    if self.harmonic_mask[k]:
                        self.line_plot_2[k].setData(ydata[k, -self._n_points:])
                        #self.line_plot_2[k].setBrush(pg.mkBrush(self.color_lookup[k]))
                    else:
                        #self.line_plot_2[k].setBrush(None)
                        self.line_plot_2[k].clear()
            elif self._lower_plot_state == self.__state.MAG_PH:
                ph = np.degrees(np.arctan2(ydata, xdata))
                for k in range(self.nharmonics):
                    if self.harmonic_mask[k]:
                        self.line_plot_2[k].setData(ph[k, -self._n_points:])
                        #self.line_plot_2[k].setBrush(pg.mkBrush(self.color_lookup[k]))
                    else:

                        #self.line_plot_2[k].setBrush(None)
                        self.line_plot_2[k].clear()
            else:
                pass


