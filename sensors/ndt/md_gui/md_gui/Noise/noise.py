



import numpy as np



class NoiseConversion:
    def __init__(self, n_adc, n_adc_eff, v_full_scale, nfft, n_samples_averaged, adc_sample_rate_hz=1,gain=1):
        '''

        :param n_adc: Number of ADC bits
        :param n_adc_eff: Effective number of ADC bits (ENOB); - used for noise floor - set to n_adc if unknown
        :param v_full_scale: Voltage range full-scale. For a 3V differential input this is 6 volts
        :param nFFT: Number of points in the FFT
        :param n_samples_averaged: Number of points averaged in the addiional step
        :param adc_sample_rate_hz: Sample rate of the ADC
        :param gain: Analogue gain between the input and the ADC
        '''
        self._n_adc_bits = n_adc
        self._n_adc_eff = n_adc_eff
        self._v_fs = v_full_scale # full scale
        self._v_per_bit = self._v_fs / pow(2, self._n_adc_bits)

        # As the noise is calculated in bandwidth these parameters must not be 1
        self._nfft = nfft if nfft >=2 else 0
        self._n_samples_averaged = n_samples_averaged if n_samples_averaged >=2 else 0

        self._adc_sample_rate_hz = adc_sample_rate_hz
        self._gain = gain



    def system_noise_floor(self, isTheorectial = False, is_v_rti=False):
        '''
        System noise floor (FFT noise floor) in dBFS
        Note: The FFT noise floor calculated here also this takes into
        account the extra averaging step
        '''
        if isTheorectial:
            nbits = self._n_adc_bits
        else:
            nbits = self._n_adc_eff

        # As the noise is calculated in bandwidth these parameters must not be 1
        sqnr = self.ADC_quantisation_noise_level(nbits) + \
                    self.FFT_processing_gain() +\
                    self.TD_averaging_gain()
        sqnr = sqnr * -1 # make a negative number

        if is_v_rti:
            sqnr = self.dBFS_2_v_rti(sqnr, isRMS=True)


        return sqnr


    def ADC_quantisation_noise_level(self, nbits):
        RMS_dBFS = (6.02 * nbits) + 1.76
        return RMS_dBFS

    def FFT_processing_gain(self):
        M = self._nfft if self._nfft >=2 else 2
        FFT_dBFS  = 10*np.log10(M/2)
        return FFT_dBFS

    def TD_averaging_gain(self):
        N = self._n_samples_averaged if self._n_samples_averaged >=2 else 2
        td_avg_gain_dBFS = 10*np.log10(N/2)
        return td_avg_gain_dBFS


    def v_rti_2_dBFS(self, x , isRMS = False):
        '''
        Voltage (AMPLITUDE) RTI (Referenced to input) conversion to dBFS
        :param x: Voltage amplitude (NOT RMS!)
        :param isRMS: if input Vrms set to True else input is voltage amplitude
        :return: Power (dBFS)
        '''
        if isRMS:
            x = x * np.sqrt(2)
        y = x * self._gain / self._v_per_bit
        M = self._n_adc_bits -1
        dBFS = 20*np.log10(y / pow(2, M))
        return dBFS


    def dBFS_2_v_rti(self, dBFS, isRMS=False):
        '''
        dBFS to Voltage RTI (Referenced to input)
        :param dBFS: Power dBFS
        :param isRMS: when True the output is Vrms; if False output is voltage amplitude
        :return: Voltage RTI (Referenced to input)
        '''
        M = self._n_adc_bits -1
        ratio = pow(10, dBFS / 20)
        y = ratio * pow(2, M)
        x = y * self._v_per_bit / self._gain
        if isRMS:
            x = x / np.sqrt(2)
        return x


    def v_rti_2_fft_op(self, x, isRMS):
        '''
        Convert from input voltage to a bin output value
         - for a signal - assumes that this frequency is exactly in the middle of a bin
        :param x:
        :return:
        '''
        if isRMS:
            x = x * np.sqrt(2)
        y = x * self._gain / self._v_per_bit
        return y

    def fft_op_2_v_rti(self, y, isRMS):
        '''
        Convert from input voltage to a bin output value
         - for a signal - assumes that this frequency is exactly in the middle of a bin
        :param x:
        :return:
        '''
        x = y * self._v_per_bit / self._gain
        if isRMS:
            x = x / np.sqrt(2)
        return x

    def fft_op_2_dBFS(self, y):
        '''
        :return:
        '''
        M = self._n_adc_bits - 1
        #y_rms = y / np.sqrt(2) \
        # NB square roots cancel
        dBFS = 20* np.log10(y/(pow(2, M)) )
        return dBFS


