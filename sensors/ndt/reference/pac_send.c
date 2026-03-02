 /** @file pac_send.c
 *
 * @brief FSM for sending of packets
 *
 */

#include "pac_send.h"
#include "settings.h"
#include "stddef.h"
//#include "command_handler.h"
#include "pac_ferrite.h"

static bool isWaiting = false;
static PacId next_command;


static struct PacSendConfig
{
    struct Packet * p_tx_packet;
    struct queueState *p_qs;
    void (*start)(bool);
    void (*stop)(void);
    void (*fft_ip_buf_rxv)(float** p_buf, uint16_t* p_nbytes);
    void (*fft_ip_buf_txi)(float** p_buf, uint16_t* p_nbytes);
    void (*fft_op_buf_rxv)(float** p_buf, uint16_t* p_nbytes);
    void (*fft_op_buf_txi)(float** p_buf, uint16_t* p_nbytes);
    uint16_t (*get_n_active_harmonics)(void);
    void (*timp_harmonic_buffers)(float **p_buffers[]);
    void (*tx_signal_dac_buf)(uint16_t** p_buf, uint16_t* p_nbytes);
    void (*nulling_sig_buf)(uint16_t** p_buf, uint16_t* p_nbytes);
    uint16_t * harmonic_buf_cal_op;
    uint16_t * harmonic_buf_trans;
    uint16_t * harmonic_buf_rxv;
    uint16_t * harmonic_buf_txi;
} pac_send_cfg;





static void pac_send_add_streaming(PacId pac_id,
                                   uint16_t *p_payload,
                                   uint16_t nbytes,
                                   uint16_t seq_num);


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
        void (*timp_harmonic_buffers)(float * p_buffers[]))
{
     pac_send_cfg.p_tx_packet = p_tx_packet;
     pac_send_cfg.p_qs = p_qs;
     pac_send_cfg.start = start;
     pac_send_cfg.stop = stop;
     pac_send_cfg.fft_ip_buf_rxv = fft_ip_buf_rxv;
     pac_send_cfg.fft_ip_buf_txi = fft_ip_buf_txi;
     pac_send_cfg.fft_op_buf_rxv = fft_op_buf_rxv;
     pac_send_cfg.fft_op_buf_txi = fft_op_buf_txi;
     pac_send_cfg.get_n_active_harmonics = get_n_active_harmonics;
     pac_send_cfg.tx_signal_dac_buf = tx_signal_dac_buf;
     pac_send_cfg.nulling_sig_buf = nulling_sig_buf;
     //pac_send_cfg.timp_harmonic_buffers = timp_harmonic_buffers;

     float *p_array[4] = {NULL};
     timp_harmonic_buffers(p_array);
     // see transimpedance.c for the order - bit closely coupled(?)
     pac_send_cfg.harmonic_buf_cal_op = (uint16_t*) p_array[3];
     pac_send_cfg.harmonic_buf_trans  = (uint16_t*) p_array[2];
     pac_send_cfg.harmonic_buf_rxv    = (uint16_t*) p_array[1];
     pac_send_cfg.harmonic_buf_txi    = (uint16_t*) p_array[0];
}

/*
 * pac_send_large_fsm()
 * Sending an un-corrupted time domain signal.
 * Description of the problem:
 * First off this signal is assumed consist of 1024 floats = 4096 bytes (32768 bits)
 * Given a serial baud rate of 1e6 this rate this takes approx 0.032 seconds to send
 * Given a sampling rate of 1e6 and accumulation ten in the CLA.
 * This buffer changes at a rate of 97 Hz ()  i.e. every 0.01 seconds
 * Therefore because sending time > buffer change time the contents will change.
 *
 *
 */

void pac_send_large_fsm(void)
{
    float * p_payload = NULL; // set to NULL to avoid complier warning
    uint16_t nbytes = 0;

    if(isWaiting)
    {
        if(queue_is_empty(pac_send_cfg.p_qs))
        {
            pac_send_cfg.stop();
            switch(next_command)
            {
            case PAC_ID_TIME_DOMAIN_RX:
                pac_send_cfg.fft_ip_buf_rxv(&p_payload, &nbytes);
                break;
            case PAC_ID_TIME_DOMAIN_TXI:
                pac_send_cfg.fft_ip_buf_txi(&p_payload, &nbytes);
                break;
            case PAC_ID_SPECTRUM_RX:
                pac_send_cfg.fft_op_buf_rxv(&p_payload, &nbytes);
                break;
            case PAC_ID_SPECTRUM_TXI:
                pac_send_cfg.fft_op_buf_txi(&p_payload, &nbytes);
                break;
            case PAC_ID_TIME_DOMAIN_NULL:
                pac_send_cfg.nulling_sig_buf((uint16_t **)&p_payload, &nbytes);
                break;
            case PAC_ID_TIME_DOMAIN_TX:
                pac_send_cfg.tx_signal_dac_buf((uint16_t **)&p_payload, &nbytes);
                break;

            default:
                asm("     ESTOP0"); //  Stop!
                break;
            }

            pac_send_cfg.p_tx_packet->command = next_command;
            pac_send_cfg.p_tx_packet->p_payload = (uint16_t*) p_payload;
            pac_send_cfg.p_tx_packet->nbytes_payload = nbytes;
            pac_send_cfg.p_tx_packet->checksum  = 0xFAFBu; // Value is for debug
            pac_is_valid_set(pac_send_cfg.p_tx_packet, true);
            pac_send_queue();
            isWaiting = false;
        }
    }
    else{
        if(queue_is_empty(pac_send_cfg.p_qs))
        {
            pac_send_cfg.start(false);
        }
    }
}




// op_id - id of packet to send
int pac_send_large_add(PacId pac_id)
{
    if( !isWaiting )
    {
        next_command = pac_id;
        isWaiting = true;
        return 0;
    }
    else
    {
        return 1; // failed
    }

}

void pac_send_ferrite_status(void)
{
    //command_setting_ferrite_control_generate();
    pac_ferrite_control_settings_generate();
    pac_send_queue();
}



void pac_send_error(uint16_t error_code)
{
    pac_tx_packet_default(PAC_ID_ERROR);
    pac_send_cfg.p_tx_packet->p_payload[0] = error_code;
    pac_send_cfg.p_tx_packet->nbytes_payload = 2u;
    pac_send_queue();
}

/*
 * Manage transmission of streaming packets
 */

void pac_send_streaming(void)
{

    static uint16_t seq_num = 0u;

    uint16_t nbytes = pac_send_cfg.get_n_active_harmonics() * sizeof(float) * 4u; // *4 because (i) data is complex (ii) sizeof returns number of uint16_t on C2000;  not bytes



    if (settings_is_op_pac_enable_get(OP_PAC_EN_CAL))
    {
        pac_send_add_streaming(PAC_ID_HARMONICS_CAL_OP, pac_send_cfg.harmonic_buf_cal_op, nbytes, seq_num);
    }

    if (settings_is_op_pac_enable_get(OP_PAC_EN_TRANS))
    {
        pac_send_add_streaming(PAC_ID_HARMONICS_TRANS, pac_send_cfg.harmonic_buf_trans, nbytes, seq_num);
    }

    if (settings_is_op_pac_enable_get(OP_PAC_EN_RXV))
    {
        pac_send_add_streaming(PAC_ID_HARMONICS_RX, pac_send_cfg.harmonic_buf_rxv, nbytes, seq_num);
    }

    if (settings_is_op_pac_enable_get(OP_PAC_EN_TXI))
    {
        pac_send_add_streaming(PAC_ID_HARMONICS_TXI, pac_send_cfg.harmonic_buf_txi, nbytes, seq_num);
    }

    seq_num++;
}



static void pac_send_add_streaming(PacId pac_id, uint16_t *p_payload, uint16_t nbytes, uint16_t seq_num)
{
    pac_tx_packet_default(pac_id);
    pac_send_cfg.p_tx_packet->p_payload = p_payload;
    pac_send_cfg.p_tx_packet->nbytes_payload = nbytes;
    pac_send_cfg.p_tx_packet->seq_num = seq_num;
    pac_send_queue();
}



int
pac_send_queue(void)
{
    uint16_t *p_mem;
    uint16_t temp_nbytes = 0;
    int retval = 0;
    uint16_t total_bytes = pac_get_total_bytes(pac_send_cfg.p_tx_packet->nbytes_payload);


    if(!pac_is_valid_get(pac_send_cfg.p_tx_packet))
    {
        return -1;
    }


    if(queue_enqueue_no_copy(pac_send_cfg.p_qs, total_bytes))
    {
       p_mem = queue_front(pac_send_cfg.p_qs, &temp_nbytes);
       pac_create_packet_in_mem(p_mem, pac_send_cfg.p_tx_packet);
       // 24-01-2022 - see below
       //pac_is_valid_set(pac_send_cfg.p_tx_packet, false); // WARNING: we are throwing the packet away with this
    }
    else
    {
       //  error memory not allocated
       retval = -1;
    };
    // 24-01-2022 this is what we had
    pac_is_valid_set(pac_send_cfg.p_tx_packet, false); // WARNING: we are throwing the packet away with this

    return retval;

}  /* func() */
