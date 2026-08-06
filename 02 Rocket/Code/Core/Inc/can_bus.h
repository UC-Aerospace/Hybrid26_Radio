#ifndef CAN_BUS_H
#define CAN_BUS_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

#define CANBUS_MAX_DATA_LEN 8
#define CANBUS_RX_QUEUE_LEN 8

typedef struct
{
    uint32_t id;
    uint8_t len;
    uint8_t data[CANBUS_MAX_DATA_LEN];
    bool extended;
} CanBus_Message_t;

/* Configures the TCAN1046 (channel 1) into normal mode and brings up
 * FDCAN1. Call once after MX_FDCAN1_Init(). */
void CanBus_Init(void);

/* Scheduler task: drains the FDCAN1 RX FIFO into the internal queue.
 * Call periodically (e.g. every 5-10 ms) via Scheduler_AddTask. */
void CanBus_Task(void);

/* Sends a classic CAN frame (len 0-8). Returns false if the TX FIFO is full
 * or len is out of range. */
bool CanBus_Send(uint32_t id, const uint8_t *data, uint8_t len, bool extended);

/* Puts the TCAN1046 channel 1 into standby (silent, low power) or normal
 * mode. Polarity: STB1 high = standby, low = normal (TI TCAN1046A). */
void CanBus_SetStandby(bool standby);

bool CanBus_HasReceived(void);

/* Pops the oldest queued message into *msg. Returns false if none pending. */
bool CanBus_GetReceived(CanBus_Message_t *msg);

#ifdef __cplusplus
}
#endif

#endif /* CAN_BUS_H */
