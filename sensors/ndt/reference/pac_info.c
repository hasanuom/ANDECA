/** @file info_packet.c
 *
 * @brief Handle generation of string payloads to be sent out
 *
 *  Created on: 24 May 2021
 *      Author: h43191kb
 */

#include <pac_info.h>
#include <stdint.h>
#include <stdbool.h>
#include "ustdlib.h"
#include "driverlib.h"
#include "pac_send.h"
#include "settings.h"


static int pac_info_create_payload(char *p_buf, uint16_t pcb_ver);
static int pac_info_pack_char(char *p_buf, uint16_t len);

/*!
 * @brief create information payload  - an ASCII string
 *
 * @param[in] Pointer to buffer
 *
 * @return Length in bytes
 */
static int pac_info_create_payload(char *p_buf, uint16_t pcb_ver)
{
    char git_version[] = VERSION;
    char *p_working = p_buf;
    uint16_t len;

    uint32_t revid = SysCtl_getDeviceRevision();
    //uint16_t partid = SysCtl_getDeviceParametric(SYSCTL_DEVICE_PARTID);
    uint32_t uid_unique = *(uint32_t *)0x000703C0;
//    uint32_t BootRomRevNr   = *(Uint16 *)0x003FFF7A;
//    uint32_t BootRomRevDate = *(Uint16 *)0x003FFF7B;

    char msg[] =        "\n"
                        "*** SEMIS De-Mining Project  ***\n"
                        "*** University of Manchester ***\n"
                        "\n\n"
                                "Git Version:       ";
    char compiled_date_msg[] =  "Compile Date:      ";
    char complier_ver_msg[]  =  "Compiler Ver:      ";

    char uid_msg[]           =  "Unique ID:         ";
    char rev_msg[]           =  "Silicon Rev:       ";
   char pcb_ver_msg[]       =  "PCB Version:       ";

    if(1)
    {
    len =  usprintf((char *)p_buf, "%s%s\n%s%s   %s\n%s%d\n%s0x%08X\n%s%d\n%s0x%04X\n",
                    msg,
                    git_version,
                    compiled_date_msg, __DATE__, __TIME__,
                    complier_ver_msg, __TI_COMPILER_VERSION__,
                    uid_msg, uid_unique,
                    rev_msg, revid,
                    pcb_ver_msg, (uint32_t)pcb_ver);
    }
    else
    {
        len =  usprintf((char *)p_buf, "Hello World\n");
    }

    len = pac_info_pack_char(p_working, len);
    return len;

}    /* func() */


/*!
 * @brief This function works on an ASCII string and removes the unused 'null' bytes
 * and repacks it in to the same buffer.
 * ASCII strings, from either a sprintf function or a #define
 * only use the lower byte of a 16-bit word. On the F28379D all chars are
 * uint16_t with the upper byte unused.
 *
 *
 * @param[in] Pointer to buffer - repack data into the same buffer
 * if the input len == even, then packed_len ==  input len
 * if input len is odd, then packed_len = inputlen + 1 as we always need an
 * even number of bytes to pack into a unit16_t.
 *
 * @return Length in bytes
 */
static int pac_info_pack_char(char *p_buf, uint16_t len)
{
    uint16_t i;
    uint16_t hbyte, lbyte;
    uint16_t *p_pack = (uint16_t *)p_buf;
    uint16_t *p_char = (uint16_t *)p_buf;
    uint16_t packed_len = 0;

    for (i = 0u; i < len; i++)
    {
         if(i%2u == 0u) //second byte is read
         {
             hbyte =  (uint16_t)p_char[i];
             hbyte = hbyte << 8;
         }
         else
         {
             lbyte =  (uint16_t)p_char[i];
             hbyte = hbyte | lbyte;
             *p_pack++ = hbyte;
             packed_len++;
         }
    }

    if(len%2u)
    {
        hbyte = hbyte | 0x000Au; // Line feed == "\n" == 0x0A
        *p_pack++ = hbyte;
        packed_len++;
    }

    packed_len = packed_len << 1; // we still need the correct number of bytes

    return packed_len;
}  /* func() */




void pac_info_fw_version_generate(void)
{
       pac_tx_packet_default(PAC_ID_FW_VERS);

       struct Packet * p_pac_tx =  pac_get_tx_packet();
       p_pac_tx->nbytes_payload = pac_info_create_payload((char *)p_pac_tx->p_payload,
                                                         settings_pcb_version_get());
}


