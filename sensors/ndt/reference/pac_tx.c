/**
 * @file pac_tx.c
 * @brief Interface between TX configuration / control and comms packets
 *
 *
 *  Created on: 2 Nov 2021
 *      Author: h43191kb
 */


#include "pac_tx.h"
#include "tx_signal.h"
#include "endian_conversion.h"
#include "packet.h"
#include "pac_id.h"
#include "mode.h"



//
// Function Prototypes
//
static uint16_t pac_tx_config_nbytes_payload(void);


//
// Functions
//

/*!
 * @brief Generate a TX configuration packet for transmission
 *
 *
 */
void pac_tx_config_generate(void)
{
   uint16_t i;
   uint16_t offset = 0; // word offset into payload

   pac_tx_packet_default(PAC_ID_TX_CONFIGURATION);
   struct Packet * p_pac_tx =  pac_get_tx_packet();
   uint16_t* p_payload = &p_pac_tx->p_payload[0];

   p_pac_tx->nbytes_payload = pac_tx_config_nbytes_payload();

   p_pac_tx->p_payload[offset] = txsignal_enable_mask_get();

   offset += sizeof(uint16_t);

   endian_float_to_big_endian(txsignal_overall_scale_get(), &p_payload[offset]);
   offset += sizeof(float);

   for(i = 0u; i < txsignal_num_freq_max(); i++)
   {
       p_pac_tx->p_payload[offset] = txsignal_harmonic_freq_get(i);
       offset += sizeof(uint16_t);

       endian_float_to_big_endian(txsignal_harmonic_magnitude_get(i), &p_payload[offset]);
       offset += sizeof(float);

       endian_float_to_big_endian(txsignal_harmonic_phase_get(i), &p_payload[offset]);
       offset += sizeof(float);
   }
}



/*!
 * @brief Parse the TX configuration packet
 *
 *
 */
void pac_tx_config_payload_parse(void)
{
   uint16_t i;
   uint16_t offset = 0u; // word offset into payload

   //uint16_t* p_payload = &comm_cfg.p_packet_rx->p_payload[0];
   //uint16_t payload_len = comm_cfg.p_packet_rx->nbytes_payload;

   struct Packet * pac_rx =  pac_get_rx_packet();
   uint16_t* p_payload = &pac_rx->p_payload[0];

   //if (payload_len != command_payload_tx_config_nbytes_get())
   if (pac_rx->nbytes_payload != pac_tx_config_nbytes_payload())
   {// Sanity check the payload is the expected length
       // TODO: add an error flag - output error packet
       return;
   }
   else
   {

       txsignal_enable_mask_set(p_payload[offset]);
       offset += sizeof(uint16_t);

       float scale = endian_big_endian_bytes_to_float(&p_payload[offset]);
       // scale sanity check
       if ((scale < 0.0f) || (scale > 1.0f) )
       {
           scale = 0.5f;
       }

       txsignal_overall_scale_set(scale);
       offset += sizeof(float);

       for(i = 0u; i < txsignal_num_freq_max(); i++)
       {
           txsignal_harmonic_freq_set(i, p_payload[offset]);
           offset += sizeof(uint16_t);

           txsignal_harmonic_magnitude_set(i, endian_big_endian_bytes_to_float(&p_payload[offset]));
           offset += sizeof(float);

           txsignal_harmonic_phase_set(i, endian_big_endian_bytes_to_float(&p_payload[offset]));
           offset += sizeof(float);
       }

       mode_command_current_set(MODE_CMD_TX_GENERATE);


    }
   // echo the new settings back as confirmation
   // Now done in main ****
   // pac_tx_config_generate();
}



/*!
 * Generate a TX control packet ready for transmission
 *
 *
 */
void pac_tx_control_generate(void)
{
    pac_tx_packet_default(PAC_ID_TX_ENABLE);

    struct Packet * p_pac_tx =  pac_get_tx_packet();
    p_pac_tx->p_payload[0] = (uint16_t)txsignal_transmit_is_enabled();
    p_pac_tx->nbytes_payload = 2u;
}


/*!
 * @brief Parse a TX control packet
 *
 */
void pac_tx_control_parse(void)
{
  struct Packet * p_pac_rx =  pac_get_rx_packet();
  switch(0x1 & p_pac_rx->p_payload[0])
    {
       case 0: // transmit off
               txsignal_transmit_control_set(false);
               break;
       case 1: // transmit on
               txsignal_transmit_control_set(true);
               break;
       default: // Normal operation
               txsignal_transmit_control_set(true);
           break;
    }
}



/*!
 * @brief Number of bytes in a TX configuration packet
 * @return number of bytes
 */
static uint16_t pac_tx_config_nbytes_payload(void)
{
   return (2u + 4u + (5u * txsignal_num_freq_max() * sizeof(uint16_t) *2u));
}


/*** end of file ***/
