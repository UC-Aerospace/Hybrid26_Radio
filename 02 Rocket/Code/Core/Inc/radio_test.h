#ifndef RADIO_TEST_H
#define RADIO_TEST_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

void RadioTest_Init(void);

/* Scheduler task: increments a counter and transmits it as a 4-byte
 * big-endian payload over the radio. Register at a 50 ms period. */
void RadioTest_Task(void);

uint32_t RadioTest_GetCounter(void);

#ifdef __cplusplus
}
#endif

#endif /* RADIO_TEST_H */
