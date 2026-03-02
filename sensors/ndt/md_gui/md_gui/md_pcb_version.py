

class MdPcbVersion:
    '''

    Grx: This is the RX amplifer gain
    Gtx: this is the amplifier gain for the current sense but MUST take
    into account the value of the current sense resistor
    Rcs: Current sense resistor value
    '''


    # The head gain did not change for this project
    # This gain assumes a instrumentation amplifier with gain 10
    # followed by an LTC6263 with gain 0.85
    rx_head_gain_typical = 10 * 0.85

    rx_board_gain_typical = 3 * 0.85

    # Note: check the PCB with this version - a variety of configurations were used
    v1 = {
        'name': 'V1',
        'desc': 'Linear TX, narrow form-factor shield',
        'Grx': rx_head_gain_typical,
        'Rcs': 0.1,  # ohms
        'Gtx': 1.0
    }

    # Version 2 was designed not utilise a head amplifier but this
    # a head amplifier was found to be required - therefore the board / gain was modified to
    # allow this

    v2 = {
        'name': 'V2',
        'desc': 'Linear TX, wider form-factor shield',
        'Grx': rx_board_gain_typical * rx_head_gain_typical,
        'Rcs': 0.1,  # ohms
        'Gcs_amp': 1, #'?
        'Gcs_sig': 1, #?
    }

    # INA240A1  - 20 V/V
    # INA240A2  - 50 V/V
    # INA240A3 - 100 V/V
    # INA240A4 - 200 V/V

    v3 = {
        'name': 'V3',
        'desc': 'H-bridge TX, shield, wider form-factor shield',
        'Grx': rx_board_gain_typical, # unadjusted
        'Rcs': 0.1,  # ohms
        'Gcs_amp': 20,
        'Gcs_sig': 0.85
    }


    # V4 was never designed to work without a head but this has been included as it is useful to test the PCB without the head
    # V4 used the INA240A3 - which has a gain of 100
    v4_rev0 = {
        'name': 'V4_rev0',
        'desc': 'H-bridge TX, standalone',
        'Grx': rx_board_gain_typical,
        'Rcs': 0.02,  # ohms
        'Gcs_amp': 100,  # ohms
        'Gcs_sig': 0.85
    }

    v4_rev1 = {
        'name': 'V4_rev1',
        'desc': 'H-bridge TX, standalone',
        'Grx': rx_board_gain_typical,
        'Rcs': 0.01,  # ohms
        'Gcs_amp': 100, # v/v
        'Gcs_sig': 0.85
    }

    pcbs = [v1, v2, v2, v3, v3, v4_rev0, v4_rev1]

    Vadc_one_bit = 6.0 / (2 ^ 16) # 91.55e-6

    @staticmethod
    def rxv_adc2volts(pcb_ver: dict):
        return MdPcbVersion.Vadc_one_bit / pcb_ver['Grx']


    @staticmethod
    def txi_adc2amps(pcb_ver: dict):
        return MdPcbVersion.Vadc_one_bit / pcb_ver['Gtx']


    @staticmethod
    def trans_adc2ohms(pcb_ver: dict):
        return pcb_ver['Grx'] / pcb_ver['Gtx']
