/*
 * pac_tx.h
 *
 *  Created on: 2 Nov 2021
 *      Author: h43191kb
 */

#ifndef INC_PAC_TX_H_
#define INC_PAC_TX_H_


#include "stdint.h"
#include "stdbool.h"




//void pac_tx_control_generate(void);
//void pac_tx_config_generate(void);


void pac_tx_config_generate(void);

void pac_tx_config_payload_parse(void);

void pac_tx_control_generate(void);


void pac_tx_control_parse(void);

#endif /* INC_PAC_TX_H_ */
