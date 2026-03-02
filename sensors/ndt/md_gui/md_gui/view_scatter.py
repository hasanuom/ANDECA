from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
from view_common import ViewCommon
import numpy as np


class ViewScatterPlot(ViewCommon):

    def __init__(self, tab_widget=None, color_lookup=None):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Scatter")
        self._base_layout = tab_layout
        super().__init__(self._base_layout, nharmonics=15)

        self.color_lookup = color_lookup

        self.averaging = dict(use_averaging=True, n_avg=0, magnitude_accumulator=[])

        stats_btn = {'labels': ['View Statistics'], 'method': [self.clear_avg]}
        stats_group, stats_controls = self.create_groupbox("Statistics", 'button', stats_btn)

        self.control_layout.addWidget(stats_group)

        self.add_label(self.control_layout, "Mean Frame Rate: ")
        plot_layout = self.create_plot_widgets('vert', 1)

        self._base_layout.addLayout(plot_layout)

        self.scatter_plot = []

        for k in range(self.nharmonics):
            self.scatter_plot.append(
                self._init_scatter_plot(self._plot_widgets[0], 'Real', 'Imag', self.color_lookup[k]))

        self._plot_widgets[0].setAspectLocked()
        #self._legend = self._plot_widgets[0].addLegend(
        #    size=None, offset=None, horSpacing=25, verSpacing=-2, pen=None, brush=None, labelTextColor=None)

        self.coordinate_circles(self._plot_widgets[0])
        self.radial_lines(self._plot_widgets[0])

        plot_range = [-0.1, 0.1]
        self.set_plot_range(self._plot_widgets[0], plot_range, plot_range, [0.1, 0.1])

    def update_plot(self, xdata, ydata):

        if self.scatter_plot[0].isVisible():
            for k in range(self.nharmonics):
                xvals = xdata[k, -50:]
                yvals = ydata[k, -50:]
                if self.harmonic_mask[k]:
                    self.scatter_plot[k].setData(x=xvals, y=yvals)
                    self.scatter_plot[k].setBrush(pg.mkBrush(self.color_lookup[k]))
                else:
                    # self.scatter_plot[k].setData(x=xvals, y=yvals)
                    self.scatter_plot[k].setBrush(None)
                    self.scatter_plot[k].clear()



