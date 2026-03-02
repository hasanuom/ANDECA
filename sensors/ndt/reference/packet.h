/** @file packet.h
 *
 * @brief Basic packet template and functions
 *
 */

#ifndef PACKET_H_
#define PACKET_H_

#include <stdint.h>
#include <stdbool.h>
#include "pac_id.h"

//------------------------------------------------------------------------------
// Defines
//------------------------------------------------------------------------------

//
// Packet Configuration
//
#define PAC_NBYTES_HEADER       4u
#define PAC_NBYTES_SIZE         2u
#define PAC_NBYTES_ADDRESS      2u
#define PAC_NBYTES_COMMAND      2u
#define PAC_NBYTES_SEQ_NUM      2u
#define PAC_NBYTES_CSUM         2u

#define PAC_PAYLOAD_NBYTES_MAX  6144u

/*
 *
 * Structure members:
 * - p_header - pointer to header
 * - header_len - length of header in elements
 * - p_payload - Holds the complete payload including the checksum
 * - payload_max_len - payload maximum length
 * - command - Received command byte
 * - payload_len - Received number of payload bytes + number of checksum bytes
 * - checksum - keep track of the current checksum value
 * - is_valid - Set to true when valid. To be cleared after processing.
 *
 *
 * NOTE:
 * 1.   There is no uint8_t on the F28379D so we  use uint16_t to hold
 *      a byte in the payload buffer.
 * 2.   The upper byte is not used in this implementation except for the checksum.
 *
 *
 * Example initialisation:
 *
    static uint16_t payload[PAYLOAD_MAX_LEN] = {0};
    static uint16_t pac_rx_header[] = {0xAB, 0xAD, 0xCA, 0xFE};

    struct CParPacket packet = {
        .p_header = &pac_rx_header[0],
        .header_len = sizeof(pac_rx_header) / sizeof(pac_rx_header[0]),
        .p_payload = &payload[0],
        .payload_max_len = PAYLOAD_MAX_LEN,
        .command = 0,
        .payload_len = 0,
        .checksum = 0,
        .is_valid = false
        };
 *
 */

struct Packet {
    uint16_t header_nbytes;
    uint16_t *p_header;
    uint16_t payload_nbytes_max;
    uint16_t nbytes_payload;
    uint16_t *p_payload;
    uint16_t device_address;
    uint16_t seq_num;
    uint16_t command;
    uint16_t checksum;
    bool     use_checksum;
    bool     is_valid;
    };


struct Packet * pac_get_tx_packet(void);
struct Packet * pac_get_rx_packet(void);

//
// Function prototypes
//

void pac_init(
              uint16_t *p_buf_rx,
              uint16_t nbytes_buf_rx,
              int(*circ_buf_pop)(void* p_cbuf, void* p_data),
              void * p_circ_buf);



void pac_create_packet_in_mem(uint16_t *p_dest, struct Packet *p_packet);

void pac_receive_fsm(void);
uint16_t pac_get_total_bytes(uint16_t payload_nbytes);

bool pac_is_valid_get(const struct Packet *p_pac);
void pac_is_valid_set(struct Packet *p_pac, bool is_valid);

void pac_tx_packet_default(PacId op_id);
#endif /* PACKET_H_ */

/*** end of file ***/

