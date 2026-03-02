import sys
import unittest
import numpy as np
import numpy.testing as nt
import noise
sys.path.append("C:/Users/h43191kb/gitlab/md_gui/md_gui/noise")



class test_noise(unittest.TestCase):

    def setUp(self):
        n_adc = 16          # ADC number of bits
        n_adc_enob = 14.1   # ADC Effective number of bits
        v_full = 6.0        # Max ADC input voltage
        n_fft = 1024        # n-point FFT
        N = 10              # extra averging processing
        adc_sample_rate = 1e6  # ADC sample rate
        gain = 25.2
        self.nc = noise.NoiseConversion(n_adc, n_adc_enob, v_full, n_fft, N, adc_sample_rate, gain)

        self._NBW = 976  # Noise equivalent bandwidth (Hz)
        #print("setting up")

    def tearDown(self):
        try:
            del self.nc
        except:
            print("error")

    def test_v_rti_2_dBFS(self):
        x_rms = 3e-9 * np.sqrt(self._NBW)
        y_dbfs = self.nc.v_rti_2_dBFS(x_rms, isRMS=True)
        print("Power {:.3f} dBFS".format(y_dbfs))
        self.assertTrue(1)

    def test_dBFS_2_v_rti(self):
        y_dbfs = -12
        x_rms = self.nc.dBFS_2_v_rti(y_dbfs, isRMS=True)
        psd = x_rms / np.sqrt(self._NBW)
        print("x_rms {:.3E} V".format(x_rms))
        print("psd {:.3E} V".format(psd))
        self.assertTrue(1)

    def test_system_noise_floor(self):
        noise_floor = self.nc.system_noise_floor()
        print(noise_floor)
        self.assertTrue(1)

    def test_dBFS_round_trip(self):
        x = 10e-6
        y_dbfs = self.nc.v_rti_2_dBFS(x)
        print("Power {:.3f} dBFS".format(y_dbfs))

        res = self.nc.dBFS_2_v_rti(y_dbfs)
        print("res {:.3E} V".format(res))
        self.assertAlmostEqual(x, res)

    def test_rti_2_fft_op(self):
        v_amp = 3 / 25.2
        y = self.nc.v_rti_2_fft_op(v_amp, isRMS=False)
        print("y {:.3E} adc_units".format(y))
        self.assertTrue(1)

    # def test_upper(self):
    #     self.assertEqual('foo'.upper(), 'FOO')
    #
    # def test_isupper(self):
    #     self.assertTrue('FOO'.isupper())
    #     self.assertFalse('Foo'.isupper())
    #
    # def test_split(self):
    #     s = 'hello world'
    #     self.assertEqual(s.split(), ['hello', 'world'])
    #     # check that s.split fails when the separator is not a string
    #     with self.assertRaises(TypeError):
    #         s.split(2)


if __name__ == '__main__':
    unittest.main()
