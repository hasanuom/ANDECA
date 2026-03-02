import numpy as np
import cam_const

class CamDataHandler:
    def __init__(self):
        self._data_handles = {}

        self._pos_series = cam_const.CamDataConst.names
        self._data_handles = {name: CamDataHandle(name) for name in self._pos_series}

        enables = [True] * len(self._pos_series)
        self.update_enables(enables)

    def update_enables(self, enables):
        for key in self._pos_series:
            self._data_handles[key].update_series_enable(enables, key)

    def update_cam_data(self, parsed_data):
        data = parsed_data[0]
        for ix in self._pos_series:
            self._data_handles[ix].update_data(ix, data)


    def get_data(self):
        data = [self._data_handles[name].get_data() for name in self._pos_series]
        return data


class CamDataHandle(object):

    def __init__(self, names='', sr_len=1000):
        self.names = names
        self.enables = False
        self.pos = np.zeros((sr_len))
        self.last_data = []

    def update_data(self, ix, pos_data):
        self.last_data = pos_data[ix]

        if self.enables:
            try:
                pos = pos_data[ix]
            except:
                print("ERROR: ????")
                return
        self.pos[0:-1] = self.pos[1:]
        self.pos[-1] = 0.0 or pos

    def update_series_enable(self, enables, names):
        self.names = names
        # enables should be a boolean
        self.enables = enables

    def update_names(self, names):
        self.names = names

    def get_data(self):
        return self.pos

    def notify(self):
        pass