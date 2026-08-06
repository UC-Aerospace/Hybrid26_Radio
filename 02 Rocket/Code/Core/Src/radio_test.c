#include "radio_test.h"
#include "radio.h"

static uint32_t s_counter = 0;

void RadioTest_Init(void)
{
    s_counter = 0;
}

void RadioTest_Task(void)
{
    uint8_t payload[4] = {
        (uint8_t)(s_counter >> 24),
        (uint8_t)(s_counter >> 16),
        (uint8_t)(s_counter >> 8),
        (uint8_t)s_counter,
    };

    /* Best-effort: if the radio is still busy with the previous send, this
     * tick's packet is skipped but the counter still advances on schedule,
     * so a gap in the received sequence shows up as a dropped packet. */
    if (!Radio_IsBusy())
    {
        Radio_Send(payload, sizeof(payload));
    }

    s_counter++;
}

uint32_t RadioTest_GetCounter(void)
{
    return s_counter;
}
