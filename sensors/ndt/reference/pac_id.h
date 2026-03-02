/*
 * pac_id.h
 *
 *  Created on: 2 Nov 2021
 *      Author: h43191kb
 */

#ifndef INC_PAC_ID_H_
#define INC_PAC_ID_H_



//------------------------------------------------------------------------------
// Typedefs
//------------------------------------------------------------------------------


/*!
 * @brief enum
 *
 *
 * The highest two bit is set i.e. 0xC000 for get
 * for a set the two highest bits should be set 0x8000
 *
 */


typedef enum
{

    PAC_ID_HARMONICS_CAL_OP         = 0x0001U,
    PAC_ID_HARMONICS_TRANS          = 0x0002U,
    PAC_ID_HARMONICS_RX             = 0x0003U,
    PAC_ID_HARMONICS_TXI            = 0x0004U,

    PAC_ID_TIME_DOMAIN_RX           = 0x0010U,
    PAC_ID_TIME_DOMAIN_TXI          = 0x0011U,
    PAC_ID_TIME_DOMAIN_NULL         = 0x0012U,
    PAC_ID_TIME_DOMAIN_TX           = 0x0013U,

    PAC_ID_SPECTRUM_RX              = 0x0020U,
    PAC_ID_SPECTRUM_TXI             = 0x0021U,

    PAC_ID_FW_VERS                  = 0x0080U,
    PAC_ID_SETTINGS                 = 0x0081U,
    PAC_ID_SETTINGS_STREAMING       = 0x0082U,

    PAC_ID_TX_CONFIGURATION         = 0x0084U,
    PAC_ID_TX_ENABLE                = 0x0085U,

    PAC_ID_LOOP_CAL_VALS            = 0x0086U,
    PAC_ID_LOOP_CONTROL             = 0x0087U,

    PAC_ID_FERRITE_CAL_VALS         = 0x0088U,
    PAC_ID_FERRITE_CAL_CONTROL      = 0x0089U,

    PAC_ID_SFR_VALS                 = 0x008AU,
    PAC_ID_SFR_CONTROL              = 0x008BU,

    PAC_ID_ERROR                    = 0x00E0U

} PacId;




// All gets are 0xC
// All set are  0x8
#define GET_MASK        (0xC000u)
#define SET_MASK        (0x8000u)
#endif /* INC_PAC_ID_H_ */
