from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from view_common import ViewCommon
import numpy as np

class ViewVectorPlot(ViewCommon):

    def __init__(self, tab_widget=None, color_lookup=None):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Vector")
        self._base_layout = tab_layout
        super().__init__(self._base_layout, nharmonics=15)

        self.color_lookup = color_lookup

        #self.averaging = dict(use_averaging=True, n_avg=0, magnitude_accumulator=[])
        plot_layout = self.create_plot_widgets('horiz', 1)

        buttons = {'labels': ['Show Mean', 'Clear Mean'], 'method': [self.select_data_source]*2}
        plot_control_group, plot_controls = self.create_groupbox("Plot Control", 'button', buttons)

        self.control_layout.addWidget(plot_control_group)
        self.add_label(self.control_layout, "Mean Frame Rate: ")

        self._base_layout.addLayout(plot_layout)

        self.vec_plot = []

        for k in range(self.nharmonics):
            self.vec_plot.append(self._init_line_plot(self._plot_widgets[0], 'Real', 'Imag', self.color_lookup[k], 3.0))

        self._plot_widgets[0].setAspectLocked()
        self.coordinate_circles(self._plot_widgets[0])
        self.radial_lines(self._plot_widgets[0])

        plot_range = [-0.1, 0.1]
        self.set_plot_range(self._plot_widgets[0], plot_range, plot_range, [0.1, 0.1])

        self._ref_show = False

    def update_plot(self, xdata, ydata):
        if self._plot_widgets[0].isVisible():
            for k in range(self.nharmonics):
                xvals = [0, xdata[k, -1]]
                yvals = [0, ydata[k, -1]]
                if self.harmonic_mask[k]:
                    self.vec_plot[k].setData(x=xvals, y=yvals)
                    self.vec_plot[k].setBrush(pg.mkBrush(self.color_lookup[k]))
                else:
                    self.vec_plot[k].setBrush(None)
                    self.vec_plot[k].clear()