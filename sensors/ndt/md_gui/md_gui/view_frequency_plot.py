from view_common import ViewCommon
from PyQt5.QtWidgets import *
import numpy as np


class ViewFreqPlot(ViewCommon):
    def __init__(self, tab_widget=None,):
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Frequency")
        self._base_layout = tab_layout
        super().__init__(self._base_layout, nharmonics=15)

        plot_layout = self.create_plot_widgets('vert', 2)
        buttons = {'labels': [], 'method': []}

        plot_control_group, plot_controls_buttons = self.create_groupbox("Plot Control", 'button', buttons)
        self.control_layout.addWidget(plot_control_group)

        self.add_label(self.control_layout, "Mean Frame Rate: ")
        self._base_layout.addLayout(plot_layout)

        self.mag_plot = self._init_line_plot(self._plot_widgets[0], 'Freq', 'log10( Mag )', 'b', 2)
        self.ph_plot = self._init_line_plot(self._plot_widgets[1], 'Freq', 'Phase', 'b', 2)

        self.mag_plot.setLogMode(False, True)

        self.set_plot_range(self._plot_widgets[0], [0, 4], [-5, 5], [0.01, 0.01])
        self.set_plot_range(self._plot_widgets[1], [0, 4], [-180, 180], [0.01, 0.01])

    def update_plot(self, xdata, ydata):
        if self._plot_widgets[0].isVisible():
            freq_data = np.arange(self.nharmonics)
            mag_data, ph_data = self.calculate_mag_ph(xdata[:self.nharmonics], ydata[:self.nharmonics])
            self.mag_plot.setData(x=freq_data, y=mag_data)
            self.ph_plot.setData(x=freq_data, y=ph_data)
            # self._update_data(self.mag_plot, freq_data, mag_data[:self.nharmonics])
            # self._update_data(self.ph_plot, freq_data, ph_data[:self.nharmonics])

    @staticmethod
    def calculate_mag_ph(xdata, ydata):
        mag = np.sqrt(xdata[:, -1] ** 2 + ydata[:, -1] ** 2)
        ph = np.degrees(np.arctan2(ydata[:, -1], xdata[:, -1]))
        return mag, ph
