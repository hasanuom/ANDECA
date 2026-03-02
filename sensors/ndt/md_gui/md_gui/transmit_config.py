
import pandas as pd
from tabulate import tabulate
import struct
import json
import json

class TransmitConfig(object):
    """
    classdocs
    """
    def __init__(self, callback):
        self.callback = callback
        self._max_n_frequencies = 15
        self._harmonics = {'enable': [], 'freq': [], 'magnitude': [], 'phase' : [], 'scale': 0.0}
        self._set_defaults()

    def _set_defaults(self):

        self._harmonics["scale"] = 0.6

        self._harmonics["freq"] = [0] * self.max_number_frequencies
        self._harmonics["magnitude"] = [0.25] * self.max_number_frequencies
        self._harmonics["phase"] = [0] * self.max_number_frequencies  # radians
        self._harmonics["enable"] = [False] * self.max_number_frequencies

        self._harmonics["freq"][0:5]      = [5, 13, 19, 31, 49]
        self._harmonics["magnitude"][0:5] = [0.3, 1.0, 0.68, 0.43, 0.25]
        self._harmonics["enable"][0:5]    = [True, True, True, True, True]
        #self._harmonics = {'enable': enable, 'freq': freq, 'magnitude': magnitude, 'phase' : phase, 'scale': scale}

    @property
    def harmonics(self):
        return self._harmonics

    def print_tx_config(self):
        print("-------    TX config  ---------")
        print("enable mask:      " + '0x%04X' % int.from_bytes(self.get_mask(), byteorder='big'))
        print("overall scaling:     " + str(self._harmonics["scale"]))
        print("")

        df = pd.DataFrame(data=self._harmonics)
        print(tabulate(df, headers='keys', tablefmt='psql'))

    @property
    def scale(self):
        return self._harmonics["scale"]

    @scale.setter
    def scale(self, val):
        self._harmonics["scale"] = val
        self.callback()

    @property
    def max_number_frequencies(self):
        return self._max_n_frequencies

    @property
    def mask(self):
        temp = 0

        for i in range(len(self._harmonics["enable"])):
            temp |= self._harmonics["enable"][i] << i

        mask = temp.to_bytes(2, byteorder='big')

        return mask

    @mask.setter
    def mask(self, val):
        try: 
            # input is bytearray
            #temp = mask.decode()
            x = int.from_bytes(val, byteorder='big')
        except(UnicodeDecodeError, AttributeError):
            # input is string
            x = bytes.fromhex(val)

        # for i in range(len(self._harmonics["enable"])):
        for i in range(self._max_n_frequencies):
            if x & 1:
                self._harmonics["enable"][i] = True
            else: 
                self._harmonics["enable"][i] = False
            x = x >> 1

        self.callback()


    def _check_idx_range(self, idx):
        if idx >= 0 and idx < self.max_number_frequencies:
            return True
        else:
            return False


    def set_harmonic_freq(self, idx, val):
        if self._check_idx_range(idx) == False:
            return
        self._harmonics["freq"][idx] = val
        self.callback()

    def set_harmonic_magnitude(self, idx, val):
        if self._check_idx_range(idx) == False:
            return
        self._harmonics["magnitude"][idx] = val
        self.callback()

    def set_harmonic_phase(self, idx, val):
        if self._check_idx_range(idx) == False:
            return
        self._harmonics["phase"][idx] = val
        self.callback()

    def set_harmonic_enable(self, idx, val):
        if self._check_idx_range(idx) == False:
            return
        self._harmonics["enable"][idx] = val
        self.callback()

    def get_harmonic_freq(self, idx):
        return self._harmonics["freq"][idx]

    def get_harmonic_magnitude(self, idx):
        return self._harmonics["magnitude"][idx]

    def get_harmonic_phase(self, idx):
        return self._harmonics["phase"][idx]

    def get_harmonic_enable(self, idx):
        return self._harmonics["enable"][idx]

    def get_frequencies_all(self):
        return self._harmonics['freq']

    def get_harmonic_enables_all(self):
        return self._harmonics["enable"]

    def get_harmonic_names(self):

        names =[]
        for i in range(self._max_n_frequencies):
            names.append(str(self._harmonics["freq"][i]))
        #print(names)
        return names

    def get_harmonics(self):
        return self._harmonics

    def to_bytearray(self):

        payload = self.mask
        payload += struct.pack(">f", self.scale)

        for i in range(self._max_n_frequencies):
            payload += self.get_harmonic_freq(i).to_bytes(2, byteorder='big')
            payload += struct.pack(">f", self.get_harmonic_magnitude(i))
            payload += struct.pack(">f", self.get_harmonic_phase(i))

        return payload

    def file_read(self, file):
        print("Reading {}".format(file))

        if isinstance(file, tuple):
            file = file[0]

        with open(file, "r") as f:
            tx_cfg = json.load(f)

        print(self._harmonics)
        self._harmonics = tx_cfg
        print(self._harmonics)
        self.callback()

    def file_save(self, file):
        print("Write {}".format(file))

        if isinstance(file, tuple):
            file = file[0]

        # check for json file ?
        with open(file, "w") as f:
            json.dump(self._harmonics, f)












