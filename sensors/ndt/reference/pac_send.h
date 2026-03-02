/** @file pac_send.h
 *
 * @brief Handle transmitting of data packets
 *
 */

#ifndef PAC_SEND_H_
#define PAC_SEND_H_


#include <stdbool.h>
#include <stdint.h>
#include "packet.h"
#include "queue.h"

#include "pac_id.h"

//
// Function prototypes
//


 //void pac_send_init(
//        struct Packet * p_tx_packet,
//        struct queueState *p_qs,
//        void (*start)(void),
//        void (*stop)(void),
//        void (*fft_ip_buf_rxv)(float**, uint16_t*),
//        void (*fft_ip_buf_txi)(float**, uint16_t*),
//        void (*fft_op_buf_rxv)(float**, uint16_t*),
//        void (*fft_op_buf_txi)(float**, uint16_t*),
//        uint16_t (*get_n_active_harmonics)(),
//        void (*tx_signal_dac_buf)(uint16_t**, uint16_t*),
//        void (*nulling_sig_buf)(float**, uint16_t*));

void pac_send_init(
        struct Packet * p_tx_packet,
        struct queueState *p_qs,
        void (*start)(bool),
        void (*stop)(void),
        void (*fft_ip_buf_rxv)(float** p_buf, uint16_t* p_nbytes),
        void (*fft_ip_buf_txi)(float** p_buf, uint16_t* p_nbytes),
        void (*fft_op_buf_rxv)(float** p_buf, uint16_t* p_nbytes),
        void (*fft_op_buf_txi)(float** p_buf, uint16_t* p_nbytes),
        uint16_t (*get_n_active_harmonics)(void),
        void (*tx_signal_dac_buf)(uint16_t** p_buf, uint16_t* p_nbytes),
        void (*nulling_sig_buf)(uint16_t** p_buf, uint16_t* p_nbytes),
        void (*timp_harmonic_buffers)(float *p_buffer[]));

void pac_send_large_fsm(void);
int pac_send_large_add(PacId pac_id);
void pac_send_streaming(void);

void pac_send_ferrite_status(void);

void pac_send_error(uint16_t error_code);
int pac_send_queue(void);

#endif

/*** end of file ***/
