/** @file pac_settings.c
 *
 * @brief Manage the generation and parsing of settings packets on the comms
 * interface
 *
 *  Created on: 8 Nov 2021
 *      Author: h43191kb
 */


#include "pac_settings.h"
#include "pac_id.h"
#include "endian_conversion.h"
#include "packet.h"
#include "loop.h"
#include "settings.h"


/*!
 * @brief Generate a settings output packet
 *
 */
void command_setting_op_generate(void)
{

    pac_tx_packet_default(PAC_ID_SETTINGS);
    struct Packet * p_pac_tx =  pac_get_tx_packet();

    p_pac_tx->p_payload[0] = settings_op_use_accumulated_get();
    p_pac_tx->p_payload[1] = settings_decimation_rate_get();
    p_pac_tx->p_payload[2] = settings_ferrite_cal_ip_select_istrans_get();

    //temp_f = fabs(p_settings->settings_loop.loop_iir_alpha);
    // loop_iir_alpha may be negative or positive depending on pcb
    // version. Only present a positive number to the outside using
    // fabs
    float temp_f = fabs(loop_iir_alpha_get());
    endian_float_to_big_endian(temp_f, &p_pac_tx->p_payload[3]);
    p_pac_tx->nbytes_payload = 10u; // bytes
}



/*!
 * @brief Parse a settings output packet
 *
 */
void command_setting_op_parse(void)
{


    struct Packet * p_pac_rx =  pac_get_rx_packet();
    settings_op_use_accumulated_set(p_pac_rx->p_payload[0]);
    settings_decimation_rate_set(p_pac_rx->p_payload[1]);
    settings_ferrite_cal_ip_select_istrans_set(p_pac_rx->p_payload[2]);

    loop_iir_alpha_set(endian_big_endian_bytes_to_float(&p_pac_rx->p_payload[3]));
    command_setting_op_generate();
}



/*!
 * @brief Generate a settings streaming packet
 *
 */
void command_streaming_settings_generate(void)
{
    pac_tx_packet_default(PAC_ID_SETTINGS_STREAMING);
    struct Packet * p_pac_tx =  pac_get_tx_packet();
    p_pac_tx->p_payload[0] = settings_is_op_pac_enable_get_all();
    p_pac_tx->nbytes_payload = 2u;
}



/*!
 * @ brief Parse a settings streaming packet
 */
void command_streaming_settings_parse(void)
{


    struct Packet * p_pac_rx =  pac_get_rx_packet();
    settings_is_op_pac_enable_set_all(p_pac_rx->p_payload[0]);
    command_streaming_settings_generate();
}

/*** end of file ***/
