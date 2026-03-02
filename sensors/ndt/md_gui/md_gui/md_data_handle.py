import numpy as np
import os
import collections
import math
import md_const

class DataHandler:
    def __init__(self, tx_config, pcb_version=2):
        self._names = md_const.DataStreamingConst.names
        self._tx_config = tx_config
        # Create instances - one for each streaming type
        self._data_handles = {name: MdDataHandle(name, n_harmonics=tx_config.max_number_frequencies) for name in
                              md_const.DataStreamingConst.names}

        for key in md_const.DataStreamingConst.names:
            self._data_handles[key].update_series_enables(tx_config.get_harmonic_enables_all(),
                                                          tx_config.get_harmonic_names())

    def update_enables(self, enables, names):
        for key in md_const.DataStreamingConst.names:
            self._data_handles[key].update_series_enables(enables, names)

    def update_data(self, parsed_data):

        id = parsed_data[0]
        data = parsed_data[1]

        if id in self._data_handles:
            self._data_handles[id].update_data(id, data)

    def get_data(self):
        data = [self._data_handles[name].get_data() for name in self._names]
        return data

    #
    # def set_scaling_factors(self):
    #     for key in self._data_handles:
    #         if key =='trans':
    #             self._data_handles[key].scaling_factor = md_pcb_version


class MdDataHandle(object):

    def __init__(self, name='', n_harmonics=16, sr_len=1000, n_sample_avg=4, filepath='', scaling_factor=1,
                 scaling_factor_active=False):
        self.name = name
        self.n_harmonics = n_harmonics
        self.sr_len = sr_len

        self.enables = [False] * n_harmonics
        self.names = [''] * n_harmonics
        self.sr_len = sr_len

        # single_sr=np.zeros((2,sr_len))
        # data is x and y data
        # self.data = [np.zeros((2,sr_len))] * n_harmonics
        self.data_re = np.zeros((n_harmonics, sr_len))
        self.data_im = np.zeros((n_harmonics, sr_len))

        self.data_mag = np.zeros((n_harmonics, sr_len))
        self.data_ph = np.zeros((n_harmonics, sr_len))

        # store last data for easy pass-though
        self.last_data_x = []
        self.last_data_y = []

        self.stat_cnt = 0
        self.stat_nsamples = 16
        self._filepath = filepath

        self.handlers = collections.defaultdict(list)
        self.isRecording = False
        self.last_seq_num = 0
        self.marked = False
        self._scaling_factor = scaling_factor
        self._scaling_factor_active = scaling_factor_active
        self._max_seq_num = 65525  # (2**16) - 1  # 16-bit unsigned number

    @property
    def scaling_factor_active(self):
        return self._scaling_factor_active

    @scaling_factor_active.setter
    def scaling_factor_active(self, value):
        if (type(value) == bool):
            self._scaling_factor_active = value
        else:
            raise TypeError("scaling_factor_active expects boolean")

    @property
    def scaling_factor(self):
        return self._scaling_factor

    @scaling_factor.setter
    def scaling_factor(self, value):
        self._scaling_factor = value

    def update_names(self, names):
        self.names = names

    def update_series_enables(self, enables, names):
        self.names = names
        # enables should be a list of booleans
        # print(enables)
        self.enables = enables

    def check_contiguous_sequence(self, num):

        if num != (self.last_seq_num + 1):
            if self.last_seq_num != self._max_seq_num:
                print("Warning - Sequence number missing:\tlast " + str(self.last_seq_num) + "\tcurrent " + str(num))
        else:
            pass
            # print("Sequence number :\t"  + str(num))
        self.last_seq_num = num

    # data_x and data_y are float vectors with length == number of active harmonic frequencies
    def update_data(self, id, harmonic_data):

        # harmonic_data = {'seq_num': seq_num, 'x_data': x_data, 'y_data': y_data}

        self.last_data_x = harmonic_data['x_data']
        self.last_data_y = harmonic_data['y_data']
        # temp = np.empty((2, 1))
        ip_idx = 0
        # is_data_new = False
        # delimiter = '\t'
        # op_str = str(harmonic_data['seq_num']) + delimiter
        self.check_contiguous_sequence(harmonic_data['seq_num'])

        for i in range(self.n_harmonics):
            if self.enables[i]:
                # re = harmonic_data['x_data'][ip_idx]
                # im = harmonic_data['y_data'][ip_idx]
                try:
                    re = harmonic_data['x_data'][ip_idx]
                    im = harmonic_data['y_data'][ip_idx]

                # except IndexError:
                except:
                    print("ERROR: {0}{1}".format(os.path.basename(__file__),
                                                 " Update_data mismatch - Press TX Config 'get'"))
                    return

                if 0:
                    sc_mag = self.update_mag(i, re, im)
                    ph = self.update_phase(i, re, im)

                    sc_re, sc_im = self.cartesian(sc_mag, ph)

                    self.data_re[i][0:-1] = self.data_re[i][1:]
                    self.data_re[i][-1] = sc_re

                    self.data_im[i][0:-1] = self.data_im[i][1:]
                    self.data_im[i][-1] = sc_im

                    # op_str += str(sc_re) + delimiter + str(sc_im) + delimiter
                else:
                    self.data_re[i][0:-1] = self.data_re[i][1:]
                    self.data_re[i][-1] = re

                    self.data_im[i][0:-1] = self.data_im[i][1:]
                    self.data_im[i][-1] = im

                    # op_str += str(re) + delimiter + str(im) + delimiter
                # is_data_new = True

                # increase the input index
                ip_idx += 1

        if (0):
            if self.stat_cnt == self.stat_nsamples:
                self.stat_cnt = 0
                self.stat_calc(self.n_harmonics, self.enables[i])
            else:
                self.stat_cnt += 1

        # if is_data_new:
        #     if self.marked == False:
        #         if self.isRecording and op_str != '':
        #             self.filehandle.write(
        #                 op_str[:-len(delimiter)] + delimiter + "0" + '\n')
        #         # self.update_stats()
        #         self.notify()
        #     else:
        #         if self.isRecording and op_str != '':
        #             self.filehandle.write(
        #                 op_str[:-len(delimiter)] + delimiter + "1" + '\n')
        #             self.marked = False
        #         # self.update_stats()
        #         self.notify()

    def update_mag(self, idx, re, im):
        mag = math.sqrt(re ** 2 + im ** 2)
        if (self._scaling_factor_active == True):
            mag = mag * self._scaling_factor

        self.data_mag[idx][:-1] = self.data_mag[idx][1:]
        self.data_mag[idx][-1] = mag

        return mag

        # self.data_mag[idx] = np.append(self.data_mag[idx], mag)
        # #print(self.data[i])
        # self.data_mag[idx] = np.delete(self.data_mag[idx], 0, axis=0)
        # print(len(self.data_mag[idx]))

    def update_phase(self, idx, re, im):
        ph = np.arctan2(im, re) * 180 / np.pi
        self.data_ph[idx][:-1] = self.data_ph[idx][1:]
        self.data_ph[idx][-1] = ph
        return ph

        # self.data_ph[idx] = np.append(self.data_ph[idx], ph)
        # #print(self.data[i])
        # self.data_ph[idx] = np.delete(self.data_ph[idx], 0, axis=0)

    def cartesian(self, r, theta):
        """theta in degrees

        returns tuple; (float, float); (x,y)
        """
        x = r * math.cos(math.radians(theta))
        y = r * math.sin(math.radians(theta))
        return x, y

    def get_data(self):
        return self.data_re, self.data_im

    def get_data_re_im(self):
        return (self.data_re, self.data_im)

    def get_data_re(self):
        return self.data_re

    def get_data_im(self):
        return self.data_im

    def get_data_mag(self):
        return self.data_mag

    def get_data_ph(self):
        return self.data_ph

    def get_data_mag_ph_rad(self):
        return (self.data_mag, self.data_ph)

    # Send data to the callback
    # this data is

    def notify(self):
        pass
