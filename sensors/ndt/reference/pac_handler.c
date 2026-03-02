/** @file command_handler.c
 *
 * @brief
 *
 * @date 16 Apr 2020
 * @author : h43191kb
 */


#include <pac_handler.h>
#include <pac_info.h>
#include "pac_send.h"
#include "error_handler.h"
#include "settings.h"
#include "pac_tx.h"
#include "pac_loop.h"
#include "pac_ferrite.h"
#include "pac_settings.h"
#include "pac_sfr.h"





/*!
 *
 */
void pac_handler(void)
{

    struct Packet * p_pac_rx =  pac_get_rx_packet();
    if(pac_is_valid_get(p_pac_rx))
    {
        switch(p_pac_rx->command)
        {
            case (PAC_ID_FW_VERS | GET_MASK):
                pac_info_fw_version_generate();
                break;

            case (PAC_ID_SETTINGS_STREAMING | GET_MASK):
                command_streaming_settings_generate();
                break;

            case (PAC_ID_SETTINGS_STREAMING | SET_MASK):
                command_streaming_settings_parse();
                break;

            case  (PAC_ID_TIME_DOMAIN_RX | GET_MASK):
                pac_send_large_add(PAC_ID_TIME_DOMAIN_RX);
                break;

            case  (PAC_ID_TIME_DOMAIN_TXI | GET_MASK):
                pac_send_large_add(PAC_ID_TIME_DOMAIN_TXI);
                break;

            case  (PAC_ID_TIME_DOMAIN_NULL | GET_MASK):
                pac_send_large_add(PAC_ID_TIME_DOMAIN_NULL);
                break;

            case  (PAC_ID_TIME_DOMAIN_TX | GET_MASK):
                pac_send_large_add(PAC_ID_TIME_DOMAIN_TX);
                break;

            case  (PAC_ID_SPECTRUM_RX | GET_MASK):
                pac_send_large_add(PAC_ID_SPECTRUM_RX);
                break;

            case  (PAC_ID_SPECTRUM_TXI | GET_MASK):
                pac_send_large_add(PAC_ID_SPECTRUM_TXI);
                break;


            case  (PAC_ID_TX_ENABLE | SET_MASK):
                pac_tx_control_parse();
                break;

            case  (PAC_ID_TX_ENABLE | GET_MASK):
                pac_tx_control_generate();
                break;

            case  (PAC_ID_LOOP_CONTROL | GET_MASK):
                pac_loop_control_settings_generate();
                break;


            case (PAC_ID_LOOP_CONTROL | SET_MASK):
                pac_loop_control_settings_parse();
                break;

            case (PAC_ID_LOOP_CAL_VALS | GET_MASK):
                pac_loop_cal_config_generate();
                break;

//
//                case (PAC_ID_SFR_VALS | GET_MASK):
//                sfr_output_generate();
//                break;

            case (PAC_ID_SFR_CONTROL | SET_MASK):
                sfr_control_settings_parse();
                break;

            case  (PAC_ID_FERRITE_CAL_CONTROL | SET_MASK):
                pac_ferrite_control_settings_parse();
                break;

            case  (PAC_ID_FERRITE_CAL_CONTROL | GET_MASK):
                pac_ferrite_control_settings_generate();
                break;

            case (PAC_ID_FERRITE_CAL_VALS | GET_MASK):
                pac_ferrite_calibration_generate();
                break;

            case (PAC_ID_SETTINGS | SET_MASK):
                command_setting_op_parse();
                break;

            case (PAC_ID_SETTINGS | GET_MASK):
                command_setting_op_generate();
                break;

            case (PAC_ID_TX_CONFIGURATION | GET_MASK):
                pac_tx_config_generate();
                break;

            case (PAC_ID_TX_CONFIGURATION | SET_MASK):
                pac_tx_config_payload_parse();
                break;

            case  (PAC_ID_ERROR | SET_MASK):
                error_handler_clear();
                break;

            default:
                pac_send_error(0xCAFE); // Just a catch at the moment
                break;

        }  // switch

    }
    // Mark the received packet as parsed
    pac_is_valid_set(p_pac_rx, false);
}




/*** end of file ***/

