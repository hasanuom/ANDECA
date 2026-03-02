/*
 * pac_parse_common.h
 *
 *  Created on: 19 Nov 2021
 *      Author: h43191kb
 */

#ifndef INC_PAC_COMMON_H_
#define INC_PAC_COMMON_H_

#include "stdint.h"
#include "fpu_types.h"

void pac_common_cf_harmonic_payload(uint16_t n,
                              uint16_t *p_dest,
                              uint16_t *p_src_freq_num,
                              complex_float *p_src_data,
                              uint16_t *p_offset);

#endif /* INC_PAC_COMMON_H_ */
