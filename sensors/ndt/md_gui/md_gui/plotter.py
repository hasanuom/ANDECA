import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import scipy.fft
import scipy.signal as signal
import scipy.stats as stats
import scipy.interpolate as interp


class Plotter:
    def __init__(self, title):
        self.title = title

    @staticmethod
    def nearest_index(time, pos_time):
        try:
            time_diff = [np.abs(pt - time) for pt in pos_time]
        except TypeError:
            pos_time = [pos_time]
            time_diff = [np.abs(pt - time) for pt in pos_time]

        time_idx = np.array([np.argmin(dt) for dt in time_diff])
        return time_idx

    @staticmethod
    def filter_slice(filter_length):
        # Build a slice object to remove the ends of filtered data
        if filter_length != 0:
            filt_slice = slice(filter_length, -filter_length)
        else:
            filt_slice = slice(0, None)

        return filt_slice

    @staticmethod
    def extract_pos(pos):
        x = pos[0]
        y = pos[1]
        z = pos[2]
        return x, y, z

    def plot_time_series(self, time, data, detrend=False, marks=None, mean=None,
                         filter_length=0, title=None, xlab=None):

        filt_slice = self.filter_slice(filter_length)
        fig, ax, N, n_plots, data = self.setup_subplots(data)

        if title is None:
            fig.suptitle(self.title)
        else:
            fig.suptitle(self.title + ' ' + title)

        for ax_idx in range(n_plots):
            y = data[:, ax_idx]
            if detrend:
                y = signal.detrend(y)
            ax[ax_idx].plot(time[filt_slice], y, color='C' + str(ax_idx))

            ax[ax_idx].grid('on')
            if xlab is None:
                ax[ax_idx].set_xlabel('Time [s]')
            else:
                ax[ax_idx].set_xlabel(xlab)
            if marks is not None:
                style = ['dashdot', 'dashed', 'dashdot']
                for q, m in enumerate(marks):
                    ax[ax_idx].axvline(m, 0, 1, linestyle=style[q], color='k')

            if mean is not None:
                ax[ax_idx].axhline(mean[ax_idx], 0, 1, linestyle='dotted', color='k')

        self.remove_unused_subplots(fig, ax, n_plots, N)

        plt.get_current_fig_manager().window.state('zoomed')
        ax[-1].set_xlabel('Time [s]')

    def cscan_data(self, pos, data, pos_index, comp_index, method='linear', weight=None):
        x, y, z = self.extract_pos(pos)

        try:
            mag = data[pos_index, comp_index]
        except IndexError:
            mag = data[pos_index]

        if weight is not None:
            mag *= weight

        x_min, x_max = self.min_max(x)
        y_min, y_max = self.min_max(y)
        n_points = 80
        grid_x, grid_y = np.mgrid[x_min:x_max:n_points * 1j, y_min:y_max:n_points * 1j]
        grid_m1 = interp.griddata((x, y), mag, (grid_x, grid_y), method=method)
        sd = np.std(mag)
        m = np.mean(mag)
        mag -= m
        mag /= sd

        return grid_x, grid_y, grid_m1

    def interp_cscan(self, pos, data, pos_index, singular_values=None, weight=None, clims=None, title=None):
        """interp_cscan(pos, data, pos_index)"""

        fig, ax, N, ncomps, data = self.setup_subplots(data)
        ax1 = [None] * N ** 2

        if title is not None:
            fig.suptitle(self.title + '\n' + title)
        else:
            fig.suptitle(self.title)

        for k in range(ncomps):
            grid_x, grid_y, grid_m = self.cscan_data(pos, data, pos_index, k, weight=weight)
            if clims is None:
                ax1[k] = ax[k].contourf(grid_x, grid_y, grid_m, 50, cmap='jet')
                fig.colorbar(ax1[k], ax=ax[k])
            else:
                ax1[k] = ax[k].contourf(grid_x, grid_y, grid_m, 50, cmap='jet', vmin=clims['min'][k],
                                        vmax=clims['max'][k])
                mp = plt.cm.ScalarMappable(cmap='jet')
                mp.set_array(grid_m)
                mp.set_clim(clims['min'][k], clims['max'][k])
                fig.colorbar(mp, ax=ax[k], boundaries=np.linspace(clims['min'][k], clims['max'][k]))

            ax[k].set_xlabel('x [cm]')
            ax[k].set_ylabel('y [cm]')
            ax[k].set_aspect(1)
            ax[k].set_title('{:}'.format(k))

        fig.tight_layout()
        if singular_values is not None:
            ax[ncomps].semilogy(singular_values, '-+')
            ax[ncomps].set_xlabel('Component')
            ax[ncomps].set_ylabel('Singular Value')
            ax[ncomps].grid('on')
            ax[ncomps].set_ylim([1e-3, 1e3])
            # self.remove_unused_subplots(fig, ax, ncomps, N+1)
        else:
            self.remove_unused_subplots(fig, ax, ncomps, N)

        # plt.get_current_fig_manager().window.state('zoomed')

    def cscan(self, pos, data, title=None):
        x, y, z = self.extract_pos(pos)
        fig, ax, N, ncomps, data = self.setup_subplots(data)
        if title is not None:
            fig.suptitle(self.title + '\n' + title)
        else:
            fig.suptitle(self.title)

        ax1 = [None] * N ** 2

        for k in range(ncomps):
            ax1[k] = ax[k].scatter(x, y, c=data[:, k], cmap='jet', s=50)
            fig.colorbar(ax1[k], ax=ax[k])
            ax[k].set_xlabel('x [cm]')
            ax[k].set_ylabel('y [cm]')

        fig.tight_layout()
        self.remove_unused_subplots(fig, ax, ncomps, N)

    def cscan_3d(self, pos, data, pos_index, idx):
        x, y, z = self.extract_pos(pos)

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        mag = data[pos_index, idx]
        ax.scatter(x, y, z, c=mag, cmap='jet')

        fig.suptitle(self.title)
        ax.set_xlabel('x [cm]')
        ax.set_ylabel('y [cm]')
        ax.set_zlabel('z [cm]')

    @staticmethod
    def min_max(x):
        return np.min(x), np.max(x)

    def plot_ssa(self):
        self.fig2, self.ax2 = plt.subplots(self.data.n_groups + 1, figsize=(19, 10), sharex='all')

        ax_lim = self.data.get_lims(self.data.X_ssa[0, 0])
        self.ax2[0].plot(self.data.time, self.data.X[0], label='Raw Data')
        self.ax2[0].legend(loc='upper left')
        self.ax2[0].grid('on')

        for i in range(0, self.data.n_groups):
            self.ax2[i + 1].plot(self.data.time, self.data.X_ssa[0, i], label='SSA {0}'.format(i + 1),
                                 color='C' + str(i + 1))
            self.ax2[i + 1].set_ylim(ax_lim)
            self.ax2[i + 1].legend(loc='upper left')
            self.ax2[i + 1].grid('on')
            lims = self.data.get_lims(self.data.X_ssa[0, i])
            # ax2[i].vlines(d1.mark_times, lims[0], lims[1], linestyles='dashed', colors='m')

        self.fig2.suptitle('Singular Spectrum Analysis :' + self.data.short_fname)
        plt.tight_layout()
        plt.subplots_adjust(top=0.88)
        plt.get_current_fig_manager().window.state('zoomed')

    def plot_fft(self, time, data, fft_data, fft_freq):
        try:
            nplots = data.shape[1]
            fig, ax = plt.subplots(nplots, 2, figsize=(19, 10))
        except IndexError:
            nplots = 1
            fig, ax = plt.subplots(nplots, 2, figsize=(19, 10))
            ax = [ax]
            data = np.reshape(data, [data.shape[0], 1])

        fig.suptitle(self.title)

        for ax_idx in range(nplots):
            ax[ax_idx, 0].plot(time, data[:, ax_idx], color='C' + str(ax_idx))
            ax[ax_idx, 1].semilogy(fft_freq, fft_data[:, ax_idx], color='C' + str(ax_idx))

            ax[ax_idx, 1].set_ylabel('FFT')

        ax[-1, 0].set_xlabel('Time [s]')
        ax[0, 0].set_title('Data')
        ax[0, 1].set_title('Spectrum')
        ax[-1, 1].set_xlabel('Frequency [Hz]')

        [ax[j, k].grid('on') for j in range(nplots) for k in range(2)]
        plt.tight_layout()
        plt.get_current_fig_manager().window.state('zoomed')

    @staticmethod
    def color_str(x):
        return 'C{:}'.format(x)

    def plot_impedance_plane(self, data, col_data=None, labels=(None, None), marks=False, filter_length=0,
                             mark_indices=None, aspect=True):

        fig, ax, N, n_plots, data = self.setup_subplots(data)
        x_comp = np.real(data)
        y_comp = np.imag(data)
        fig.suptitle(self.title)
        filt = self.filter_slice(filter_length)

        for ax_idx in range(n_plots):
            if col_data is None:
                ax[ax_idx].scatter(x_comp[filt, ax_idx],
                                   y_comp[filt, ax_idx],
                                   s=10, c=self.color_str(ax_idx))
            else:
                ax[ax_idx].scatter(x_comp[filt, ax_idx],
                                   y_comp[filt, ax_idx],
                                   s=10, c=col_data[filt])

            ax[ax_idx].set_xlabel(labels[0])
            ax[ax_idx].set_ylabel(labels[1])

            if marks:
                ax[ax_idx].scatter(x_comp[mark_indices, ax_idx],
                                   y_comp[mark_indices, ax_idx],
                                   s=30, c='m')
            ax[ax_idx].grid('on')
            if aspect:
                ax[ax_idx].set_aspect(1)

        self.remove_unused_subplots(fig, ax, n_plots, N)
        plt.get_current_fig_manager().window.state('zoomed')
        fig.tight_layout()

    def setup_subplots(self, data):
        try:
            nplots = data.shape[1]
            N = self.nearest_sq(nplots)
            fig, ax = plt.subplots(N, N, figsize=(19, 10))
            ax = ax.reshape(N ** 2)
        except IndexError:
            nplots = 1
            N = self.nearest_sq(nplots)
            fig, ax = plt.subplots(N, N, figsize=(19, 10))
            ax = [ax]
            data = np.reshape(data, [data.shape[0], 1])

        return fig, ax, N, nplots, data

    def normal_probability_plot(self, data, cdata):
        fig, ax, N, ncomps, data = self.setup_subplots(data)

        fig.suptitle(self.title)

        for k in range(ncomps):
            z, t, Y, idx = self.normal_probability_data(data[:, k])
            ax[k].scatter(z, Y, c=cdata[idx], cmap='jet')
            ax[k].plot(t, t, 'C1', linestyle='dashed')
            ax[k].set_xlabel('Theoretical')
            ax[k].set_ylabel('Experimental')
            ax[k].grid('on')
            ax[k].set_aspect(1)

        self.remove_unused_subplots(fig, ax, ncomps, N)
        plt.get_current_fig_manager().window.state('zoomed')

    def plot_mark_spectrum(self, data, source, comp, random_non_marked=False):
        fig, ax = plt.subplots(1)
        for k in data.mark_indices:
            ax.plot(data.freq, data.data[source][comp][k, :], linewidth=3, label=str(k))
        ax.set_xlabel('Freq [kHz]')
        ax.grid('on')

        if random_non_marked:
            idx = np.random.randint(0, data.n_samples, size=10)
            for k in idx:
                ax.plot(data.freq, data.data[source][comp][k, :], '--', label=str(k))
        ax.legend()

    def pca_components(self, pcs, mean_pc=None):
        nfiles, npc1, npc2 = pcs.shape
        N = self.nearest_sq(npc1)

        fig, ax = plt.subplots(N, N)
        ax = ax.reshape(N ** 2)
        for k in range(npc2):
            ax[k].plot(pcs[:, :, k])
            ax[k].set_xlabel('Raster file number')
            ax[k].set_ylabel('PC')
            ax[k].grid('on')
            if mean_pc is not None:
                self.add_mean(ax[k], mean_pc[:, k])

        ax[npc2 - 1].legend(np.arange(0, npc1))
        self.remove_unused_subplots(fig, ax, npc2, N)

    def plot_polar(self, pc_data):
        nfiles, npc1, npc2 = pc_data.shape
        N = self.nearest_sq(npc1)
        fig, ax = plt.subplots(N, N, subplot_kw={'projection': 'polar'}, figsize=(19, 10))
        ax = ax.reshape(N ** 2)

        theta = np.linspace(0, np.radians(360 - 360 / npc1), npc1)
        for k in range(npc2):
            for f in range(nfiles):
                ax[k].plot(theta, pc_data[f, :, k], label='{:}'.format(f))
            ax[k].set_title('{:}'.format(k))

            ax[k].set_thetagrids(np.degrees(theta), labels=np.arange(0, npc1))
            ax[k].set_rticks(np.arange(0, 0.8, 0.2))
        # plt.tight_layout()
        ax[-2].legend()
        self.remove_unused_subplots(fig, ax, npc2, N)

    def add_mean(self, ax, mean):
        col = ['C' + str(k) for k in range(mean.shape[0])]
        ax.hlines(mean, 0, 19, linestyles='dashed', colors=col)

    @staticmethod
    def nearest_sq(X):
        return int(np.ceil(X ** 0.5))

    @staticmethod
    def remove_unused_subplots(fig, ax, Nstop, N):
        [fig.delaxes(ax[q]) for q in range(Nstop, N ** 2)]

    def plot_matrix(self, data):
        fig, ax, N, n_plots, data = self.setup_subplots(data)

        vmin, vmax = self.min_max(data)
        for k in range(n_plots):
            ax[k].pcolor(data[k, :, :], cmap='jet', vmin=vmin, vmax=vmax)
            ax[k].set_aspect(1)
            ax[k].grid('on')
            ax[k].set_xticks(np.arange(0, npc1 + 1, 2))
            ax[k].set_yticks(np.arange(0, npc2 + 1, 2))

        self.remove_unused_subplots(fig, ax, nfiles, N)

    def ppcc_plot(self, data):
        # Probability plot correlation coefficient
        fig, ax, N, nplots, data = self.setup_subplots(data)
        for k in range(nplots):
            stats.ppcc_plot(data[:, k], -4, 4, plot=ax[k], dist='tukeylambda')
            ax[k].grid('on')
            ax[k].vlines(0.14, 0, 1, colors='C1', linestyles='dashed')
        self.remove_unused_subplots(fig, ax, nplots, N)
        plt.get_current_fig_manager().window.state('zoomed')

    def normal_probability_plot(self, data, color_data=None):
        fig, ax, N, ncomps, data = self.setup_subplots(data)

        fig.suptitle(self.title)

        for k in range(ncomps):
            z, t, Y, idx = self.normal_probability_data(data[:, k])
            if color_data is not None:
                ax[k].scatter(z, Y, c=color_data[idx], cmap='jet')
            else:
                ax[k].scatter(z, Y)
            ax[k].plot(t, t, 'C1', linestyle='dashed')
            ax[k].set_xlabel('Theoretical')
            ax[k].set_ylabel('Experimental')
            ax[k].grid('on')
            ax[k].set_aspect(1)

        self.remove_unused_subplots(fig, ax, ncomps, N)
        plt.get_current_fig_manager().window.state('zoomed')

    def histogram(self, data, nbins=40, plot_titles=None):
        fig, ax, N, nplots, data = self.setup_subplots(data)
        for k in range(nplots):
            ax[k].hist(data[:, k], nbins, ec='k')
            # ax[k].grid('on')
            ax[k].set_xlabel('Data Bin')
            ax[k].set_ylabel('No. samples')
            if plot_titles is not None:
                ax[k].set_title(plot_titles[k])
        self.remove_unused_subplots(fig, ax, nplots, N)
        plt.get_current_fig_manager().window.state('zoomed')
        fig.tight_layout()

    def lag_plot(self, data, i=1):
        fig, ax, N, nplots, data = self.setup_subplots(data)
        for k in range(nplots):
            data_shift = np.roll(data[:, k], shift=i)
            ax[k].scatter(data_shift, data[:, k], s=1, color='C{:}'.format(k))
            ax[k].grid('on')
            ax[k].set_xlabel('X_i')
            ax[k].set_ylabel('X_(i - {:})'.format(i))

        fig.suptitle(self.title + '\n Lag Plot k = {:}'.format(i))
        self.remove_unused_subplots(fig, ax, nplots, N)
        plt.get_current_fig_manager().window.state('zoomed')

    def auto_corr_plot(self, data):
        fig, ax, N, nplots, data = self.setup_subplots(data)
        for k in range(nplots):
            ax[k].acorr(data[:, k], usevlines=False, maxlags=None)
            ax[k].grid('on')
            ax[k].set_xlabel('Lag')
            ax[k].set_ylabel('Autocorrelation')

        fig.suptitle(self.title)
        self.remove_unused_subplots(fig, ax, nplots, N)
        plt.get_current_fig_manager().window.state('zoomed')

    def four_plot(self, time, data, lag_type='lag'):
        try:
            nplots = data.shape[1]
            N = self.nearest_sq(nplots)
            fig = plt.figure()
            subfigs = fig.subfigures(N, N, wspace=0.01)
            subfigs = np.reshape(subfigs, N ** 2)

        except IndexError:
            nplots = 1
            N = 1
            fig = plt.figure()
            subfigs = [fig.subfigures(N)]
            subfigs = np.reshape(subfigs, N ** 2)
            data = np.reshape(data, [data.shape[0], 1])

        p = -100
        for k in range(nplots):
            subplots = subfigs[k].subplots(2, 2)
            plt.subplots_adjust(right=0.94, hspace=0.85, left=0.1, wspace=0.3)

            # Run sequence plot
            subplots[0, 0].plot(time, data[:, k], 'C0')
            subplots[0, 0].set_title('Run Sequence Plot', pad=p)
            subplots[0, 0].set_xlabel('Time [s]')
            subplots[0, 0].set_ylabel('Component {:}'.format(k + 1))

            if lag_type == 'lag':
                # Lag plot
                data_shift = np.roll(data[:, k], shift=1)
                subplots[0, 1].scatter(data_shift, data[:, k], color='C1', s=0.5, alpha=0.5)
                subplots[0, 1].set_title('Lag Plot', pad=p)
                subplots[0, 1].set_xlabel('$X_i$')
                subplots[0, 1].set_ylabel('$X_{i-1}$')
                # subplots[0, 1].set_aspect(1)
            elif lag_type == 'auto':
                # Autocorrelation
                subplots[0, 1].acorr(data[:, k], usevlines=False, maxlags=None, color='C1', markersize=0.5)
                subplots[0, 1].set_xlim([0, None])
                subplots[0, 1].set_title('Autocorrelation', pad=p)
                subplots[0, 1].set_xlabel('Lag')
                subplots[0, 1].set_ylabel('Autocorrelation')
            elif lag_type == 'pacf':
                nlags = 40
                x = np.arange(1, nlags + 2)
                y = sm.graphics.tsa.pacf(data[:, k], nlags=nlags)
                subplots[0, 1].scatter(x, y, marker='o', color='C1', s=10)
                subplots[0, 1].vlines(x, 0, y, colors='C1')
                subplots[0, 1].axhline(0, 0, 1)
                subplots[0, 1].set_xlim([0, None])
                subplots[0, 1].set_title('Partial Autocorrelation', pad=p)
                subplots[0, 1].set_xlabel('Lag')
                subplots[0, 1].set_ylabel('PACF')

            # Histogram
            subplots[1, 0].hist(data[:, k], 35, ec='k', color='C2')
            subplots[1, 0].set_title('Histogram', pad=p)
            subplots[1, 0].set_xlabel('Bin')
            subplots[1, 0].set_ylabel('No. Samples')

            # Normal probability plot
            z, t, Y, idx = self.normal_probability_data(data[:, k])
            subplots[1, 1].scatter(z, Y, c='C3', s=2)
            subplots[1, 1].plot(t, t, 'k', linestyle='dashed')
            subplots[1, 1].set_title('Normal Probability Plot')
            subplots[1, 1].set_xlabel('Theoretical')
            subplots[1, 1].set_ylabel('Experimental')
            # subplots[1, 1].grid('on')
            # subplots[1, 1].set_aspect(1)

        subfigs[int(N / 2)].suptitle(self.title)

        plt.get_current_fig_manager().window.state('zoomed')

    @staticmethod
    def normal_probability_data(data):
        idx = np.argsort(data)
        Y = data[idx]
        Y -= np.nanmean(data)
        Y /= np.nanstd(data)

        n = len(data)
        if n <= 10:
            a = 3 / 8
        else:
            a = 0.5

        i = np.arange(1, n + 1)

        q = (i - a) / (n + 1 - 2 * a)
        z = stats.norm.ppf(q)
        t = np.linspace(-3, 3)
        return z, t, Y, idx
