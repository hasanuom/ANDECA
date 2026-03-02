import matplotlib

import matplotlib.pyplot as pyplot
matplotlib.use('Qt5Agg',  force=True)
import numpy as np
import math
import noise







class AD8421():

    # “AD8421 Datasheet,” Analog Devices, [Online]. Available: https://www.analog.com/media/en/technical-documentation/data-sheets/AD8421.pdf.

    # Input and output noise values are from the datasheet and are in nV/sqrt(Hz)

    INPUT_NOISE = 3.2e-9
    OUTPUT_NOISE = 60e-9

    #from datasheet current noise = 0.2 pico-Amps/sqrt(Hz)
    CURRENT_NOISE = 0.2e-12

    def __init__(self):
        print("using instrumentation amplifier AD8421")


    # The impedance input may be complex or real.
    # It must be in units of Ohms.
    # This impedance assumed to be the total the load equally divided between each arm
    def source_noise(self, imp):

        # Todo: both input arms to the amplifier are assumed to have the same input impedance
        if isinstance(imp, complex):
            r = np.real(imp) # Just use the real part for source resistance
        else:
            r = imp

        # convert to kOhms
        rkohms = r / 1000

        # Each of th
        rkohms_a = rkohms / 2
        rkohms_b = rkohms / 2


        # nsd = noise spectral density in nV / sqrt(Hz)
        self.source_nsd = np.sqrt( (4*np.sqrt(rkohms_a))**2 + (4*np.sqrt(rkohms_b))**2)

        return self.source_nsd

    def voltage_noise(self, Rg, gain):

        Rgkhz = Rg / 1000

        a = (self.OUTPUT_NOISE / gain)**2
        b = self.INPUT_NOISE**2
        c = (4*np.sqrt(Rgkhz) * 1e-9)**2

        # Need to convert to nV / root(Hz) hence multiply by 1e9
        self.voltage_nsd = np.sqrt(a + b + c) * 1e9
        return self.voltage_nsd

    def current_noise(self, impedance):

        if isinstance(impedance, complex):
            z = np.abs(impedance)
        else:
            z = impedance

        self.current_nsd = np.sqrt( (2*((z/2) * self.CURRENT_NOISE * 1e9) **2))
        return self.current_nsd

    def total_noise(self, impedance, Rg, gain):

        vnoise = self.voltage_noise(Rg, gain)
        cnoise = self.current_noise(impedance)
        snoise = self.source_noise(impedance)

        self.total_nsd = np.sqrt(vnoise**2 + cnoise**2 + snoise**2)
        return self.total_nsd

    def __str__(self):
        string = "Instrumentation Amplifier AD8421\n"
        string = string + "Source_nsd:\t\t{:.3f} nV/\u221AHz\nVoltage_nsd:\t{:.3f} nV/\u221AHz\n".format(self.source_nsd, self.voltage_nsd)
        string = string + "Current_nsd:\t{:.3f} nV/\u221AHz\n".format(self.current_nsd)
        string = string + "Total_nsd:\t\t{:.3f} nV/\u221AHz\n".format(self.total_nsd)

        return string







if __name__ == "__main__":


    print("Noise analysis")

    n_adc = 16
    n_adc_eff = 14.1
    v_full = 6.0
    n_fft = 1024
    N = 10
    adc_sample_rate = 1e6
    NBW = 976  # Noise equivalent bandwidth (Hz)
    gain = 25.2
    nc = noise.NoiseConversion(n_adc, n_adc_eff, v_full, n_fft, N, adc_sample_rate, gain)
    noise_floor_dBFS = nc.system_noise_floor()
    print("Noise floor: {:.4f}".format(noise_floor_dBFS))

    x_rms = 5.1e-9 * np.sqrt(NBW)
    y_dbfs = nc.v_rti_2_dBFS(x_rms, isRMS=True)
    print("Power {:.3f} dBFS".format(y_dbfs))
    y_op = nc.v_rti_2_fft_op(x_rms, isRMS=True)

    print("OP amplitude {:.2f} ADC units".format(y_op))

    # x_rms = nc.dBFS_2_v_rti(y_dbfs, isRMS=True)
    # psd = x_rms / np.sqrt(NBW)
    # print("x_rms {:.3E} V".format(x_rms))
    # print("psd {:.3E} V".format(psd))
    #
    # x = 10e-6
    # y_dbfs = nc.v_rti_2_dBFS(x)
    # print("Power {:.3f} dBFS".format(y_dbfs))
    #
    # x = nc.dBFS_2_v_rti(y_dbfs)
    # print("x {:.3E} V".format(x))
    #
    # v_amp =
    # y = nc.v_rti_2_fft_op(v_amp, isRMS=False)
    #
    # print("y {:.3E} adc_units".format(y))

    y = 0.8
    v_rms = nc.fft_op_2_v_rti(y, isRMS=True)
    print("Vrms {:.3E} volts ".format(v_rms))



    inamp = AD8421()
    R = 300 # semis 12+12 receive
    gain = 25.2 # SEMIS typical
    inamp.voltage_noise(340, 30)
    inamp.source_noise(200)
    tn = inamp.total_noise(R, 340, gain)
    print("In-amp: Total Noise Spectral Density {:.3E} Vrms/\u221AHz".format(tn))


    # Inductance does not add to this noise so the following has been commented out
    # See https://en.wikipedia.org/wiki/Johnson%E2%80%93Nyquist_noise#Reactive_impedances
    # R = 300 # ohms
    # x=[]
    # L= 0.016  # Henries
    # freq = np.logspace(2,5,num=(5-2)*10 +1, base=10)
    # for f in freq:
    #     xl = 2 * np.pi * f * L
    #     imp = complex(R,  xl)
    #     x.append(inamp.total_noise(imp,  340, gain))
    #
    # fig = pyplot.plot(freq, x)
    # pyplot.grid()
    # pyplot.show()

