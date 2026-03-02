/*
 * packet.c
 *
 *  Created on: 19 Aug 2019
 *      Author: h43191kb
 */
#include <stdlib.h>
#include "packet.h"


typedef enum
{
    PAC_IDLE,
    PAC_ADDRESS,
    PAC_COMMAND,
    PAC_SEQ_NUM,
    PAC_SIZE,
    PAC_PAYLOAD,
    PAC_CHECKSUM
} PAC_State;

// Allocate header
static uint16_t pac_header[] = {0xDE, 0x7E, 0xC7, 0xED};

extern uint16_t g_sci_scratch[512]; // array for tx packet construction

/*
 * Create the packets as statics in this file
 * These packets contain all the necessary information related to
 * managing a packet.
 *
 *
 */
static struct Packet packet_tx = {0};
static struct Packet packet_rx = {0};

static void pac_check_checksum(struct Packet *p_pac);
static uint16_t pac_checksum_calc(const uint32_t sum);

void packet_msb_bytes_to_16bit(uint16_t *p_result, uint16_t byte_ip, bool is_lsb);


struct PacCfg
{
    int(*circ_buf_pop)(void* p_cbuf, void* p_data); // function pointer to circ buf pop
    void * p_circ_buf; // pointer to circular buffer

}pac_cfg;

struct Packet * pac_get_tx_packet(void)
{
    return &packet_tx;
}


struct Packet * pac_get_rx_packet(void)
{
    return &packet_rx;
}



/*!
 *
 * NOTE: when calling this function
 * int (*p_func)(void* , void*) = circ_buf_pop;
 * gives the complier warning -Wincompatible-pointer-types due to the voids
 * Cast the function pointer to get rid of the warning
 * int (*p_func_circ_buf_pop)(void*, void*) = (int(*)(void*, void*))circ_buf_pop;
 *
 *
 * @param p_buf_rx
 * @param nbytes_buf_rx
 * @param circ_buf_pop
 */
void pac_init(
              uint16_t *p_buf_rx,
              uint16_t nbytes_buf_rx,
              int(*circ_buf_pop)(void* p_cbuf, void* p_data),
              void * p_circ_buf)
{

    pac_cfg.circ_buf_pop = circ_buf_pop;
    pac_cfg.p_circ_buf = p_circ_buf;
    // set both packets
    bool use_checksum = true;

    //packet_tx.p_header = p_header;
    //packet_tx.header_nbytes = nbytes_header;
    packet_tx.p_header = &pac_header[0];
    packet_tx.header_nbytes = sizeof(pac_header) / sizeof(pac_header[0]);
    packet_tx.p_payload = NULL;

    // Transmit packet uses the heap
    // 128 bytes is a bit arbitrary but accounts for the header
    // times 2 is the 16-bits to bytes conversion
    // With the tx packet the payload_nbytes_max has a factor of two because the
    // transmit buffer makes use of 16-bit words. The receive buffer does not

    packet_tx.payload_nbytes_max = PAC_PAYLOAD_NBYTES_MAX;
    packet_tx.command = 0u;
    packet_tx.nbytes_payload = 0u;
    packet_tx.seq_num = 0u;
    packet_tx.device_address = 0u;
    packet_tx.checksum = 0u;
    packet_tx.use_checksum = use_checksum;
    pac_is_valid_set(&packet_tx, false);



     packet_rx.p_header = &pac_header[0];
     packet_rx.header_nbytes = sizeof(pac_header) / sizeof(pac_header[0]);

     // Receive packet uses a static memory (g_sci_buf_rx)
     packet_rx.p_payload = p_buf_rx;
     // There is no *2  with payload_nbytes_max for the Rx as the Rx interrupt
     // only writes an 8-bit at a time into the buffer
     packet_rx.payload_nbytes_max = nbytes_buf_rx;
     packet_rx.command = 0;
     packet_tx.seq_num = 0;
     packet_tx.device_address = 0;
     packet_rx.nbytes_payload = 0;
     packet_rx.checksum = 0;
     packet_rx.use_checksum = use_checksum;
     pac_is_valid_set(&packet_rx, false);

}





/*!
 * @brief take the two's compliment of a sum
 *
 * @param sum
 *
 * @return void
 *
 *
 */
static uint16_t pac_checksum_calc(const uint32_t sum)
{
    // Discard high bits
    uint32_t temp = sum & 0x0000FFFF;

    // Take 'ones' compliment
    temp = ~temp;

    // Make two's compliment
    temp += 1u;

    // Although casting should just remove the high bits we perform an AND
    // operation here
    temp = temp & 0x0000FFFFu;

    return (uint16_t) temp;

}


/*!
 * @brief
 *
 * payload is assumed to be in a 16-bit wide buffer with
 * @param

 *
 * @return void
 *
 *
 */
void
pac_create_packet_in_mem(uint16_t *p_dest, struct Packet *p_packet)
{

    uint32_t i;
    uint16_t *p_buff = p_dest;
    uint32_t sum = 0u; // checksum initial value
    uint16_t val;

    val = (p_packet->p_header[0] << 8) | (p_packet->p_header[1] & 0x00FFu);
    *p_buff++ = val;

    val = (p_packet->p_header[2] << 8) | (p_packet->p_header[3] & 0x00FFu);
    *p_buff++ = val;

    *p_buff++ = p_packet->device_address;
    sum += p_packet->device_address;

    *p_buff++ = p_packet->command;
    sum += p_packet->command;

    *p_buff++ = p_packet->seq_num;
    sum += p_packet->seq_num;

    *p_buff++ = p_packet->nbytes_payload;
    sum += p_packet->nbytes_payload;

    uint32_t nwords = (p_packet->nbytes_payload) >> 1;

    for (i = 0u; i < nwords; i++)
    {
        val = p_packet->p_payload[i];
        *p_buff++ = val;
        sum += val;
    }

    p_packet->checksum = pac_checksum_calc(sum);

    *p_buff++ = p_packet->checksum;

}   /* end of func() */



uint16_t
pac_get_total_bytes(uint16_t payload_nbytes)
{
    uint16_t nbytes = PAC_NBYTES_HEADER + PAC_NBYTES_ADDRESS +
                      PAC_NBYTES_COMMAND + PAC_NBYTES_SEQ_NUM +
                      PAC_NBYTES_SIZE + payload_nbytes + PAC_NBYTES_CSUM;
    return nbytes;
}




/*!
 * @brief Finite State Machine (FSM) to check an input buffer for a valid packet
 *
 *
 * @param Pointer to the received packet
 * @param Pointer to the function to use to pop a value out of the buffer
 *            Requirements for function are:
 *              first input is to the buffer (maybe a structure)
 *              second pointer is the output character. A uart is assumed and if the size is larger than 8-bits only the
 *              lowest 8-bits are assumed to be valid.
 *              return type is a signed integer. A value of -1 means that the buffer is empty.
 * @param Pointer to the (circular?) buffer
 *
 * @return
 */

void
//pac_receive_fsm(int(*p_buf_pop)(void*, void*), void *p_buf)
pac_receive_fsm(void)
{



    static PAC_State state = PAC_IDLE;
    static uint32_t idx = 0u;
    static uint32_t word_idx = 0u;

    uint16_t c;

    struct Packet * p_pac = pac_get_rx_packet();

    // check the input buffer
    //while( ((*p_buf_pop)(p_buf, &c) != -1) && (!pac_is_valid_get(p_pac)) )
    //while( ((*pac_cfg.circ_buf_pop)(p_buf, &c) != -1) && (!pac_is_valid_get(p_pac)) )
    while( ((*pac_cfg.circ_buf_pop)(pac_cfg.p_circ_buf, &c) != -1) && (!pac_is_valid_get(p_pac)) )
    {
        switch (state)
          {
          case PAC_IDLE:
            p_pac->checksum = 0u;
            //p_pac->is_valid = false;
            pac_is_valid_set(p_pac, false);

            if (c == p_pac->p_header[idx])
            {
                idx++;
            }
            else
            {
                state = PAC_IDLE;
                idx = 0u;
            }

            if (idx == p_pac->header_nbytes) // success
            {
                // Clear fields in packet so we can use bitwise OR later
                p_pac->device_address = 0u;
                p_pac->command = 0u;
                p_pac->seq_num = 0u;
                p_pac->nbytes_payload = 0u;
                p_pac->checksum = 0u;

                // set next state
                state = PAC_ADDRESS;
                idx = 0u;
            }
            break;


          case PAC_ADDRESS:
              packet_msb_bytes_to_16bit(&p_pac->device_address, c, idx%2u);
              idx++;
              if(idx == PAC_NBYTES_ADDRESS)
              {
                  p_pac->checksum += p_pac->device_address;
                  state = PAC_COMMAND;
                  idx = 0u;
              }
              break;

        case PAC_COMMAND:
            packet_msb_bytes_to_16bit(&p_pac->command, c, idx%2u);
            idx++;
            if(idx == PAC_NBYTES_COMMAND)
            {
                p_pac->checksum += p_pac->command;
                state = PAC_SEQ_NUM;
                idx = 0u;
            }
            break;

        case PAC_SEQ_NUM:
            packet_msb_bytes_to_16bit(&p_pac->seq_num, c, idx%2u);
            idx++;
            if(idx == PAC_NBYTES_SEQ_NUM)
            {
                p_pac->checksum += p_pac->seq_num;
                state = PAC_SIZE;
                idx = 0u;
            }
            break;

        case PAC_SIZE:
            packet_msb_bytes_to_16bit(&p_pac->nbytes_payload, c, idx%2u);
            idx++;
            if(idx == PAC_NBYTES_SIZE)
            {
                state = (p_pac->nbytes_payload > p_pac->payload_nbytes_max) ? PAC_IDLE : PAC_PAYLOAD;
                p_pac->checksum += p_pac->nbytes_payload;
                idx = 0u;
                word_idx = 0u;
            }
            break;

        case PAC_PAYLOAD:
            // Pack the received bytes into 16-bits
            if(idx%2u)
            {
                p_pac->p_payload[word_idx] = p_pac->p_payload[word_idx] << 8 | c;
                p_pac->checksum += p_pac->p_payload[word_idx];
                word_idx++;
            }
            else
            {
                p_pac->p_payload[word_idx] = c;
            }

            idx++;

            if (idx == p_pac->nbytes_payload + PAC_NBYTES_CSUM)
            {
                pac_check_checksum(p_pac);
                state = PAC_IDLE;
                idx = 0u;
            }
            break;

        default: // ERROR
            idx = 0u;
            break;

          } /* switch */
    }       /* while */
}           /* func() */



//
// Bytes arrive MSB first
//
void
packet_msb_bytes_to_16bit(uint16_t *p_result, uint16_t byte_ip, bool is_lsb)
{
    if(is_lsb)
    {
        byte_ip = byte_ip & 0x00FFu;
    }
    else
    {
        byte_ip = byte_ip << 8;
    }

    *p_result = *p_result | byte_ip;

}


/*!
 * @brief Compare the received checksum with the calculated checksum
 *
 * @param Pointer to structure contained received checksum
 * @param calculated checksum
 *
 * @return void
 */
static void
pac_check_checksum(struct Packet *p_pac )
{
    pac_is_valid_set(p_pac, true);

    if(p_pac->use_checksum == (true && (p_pac->checksum != 0u)))
    {
        pac_is_valid_set(p_pac, false);
    }

}    /* func() */



bool
pac_is_valid_get(const struct Packet *p_pac)
{
    return p_pac->is_valid;
}   /* func() */


void
pac_is_valid_set(struct Packet *p_pac, bool is_valid)
{
    p_pac->is_valid = is_valid;
}   /* func() */



void pac_tx_packet_default(PacId op_id)
{

    packet_tx.command = op_id;
    packet_tx.p_payload = &g_sci_scratch[0];
    packet_tx.checksum  = 0xFAFBu; // something odd to check

    pac_is_valid_set(&packet_tx, true);
}

/*** end of file ***/


