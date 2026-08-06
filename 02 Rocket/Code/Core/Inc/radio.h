#ifndef RADIO_H
#define RADIO_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

#define RADIO_MAX_PAYLOAD_LEN 255

typedef enum
{
    RADIO_STATE_STANDBY = 0,
    RADIO_STATE_TX,
    RADIO_STATE_RX,
} Radio_State_t;

/* Resets and configures the SX1262 for LoRa (default 915 MHz, SF7/BW125/CR4:5).
 * Call once after MX_SPI1_Init(). */
void Radio_Init(void);

/* Scheduler task: services TX/RX completion and timeouts. Call periodically
 * (e.g. every 5-10 ms) via Scheduler_AddTask. */
void Radio_Task(void);

/* Changes the RF carrier frequency in Hz (e.g. 915000000 for 915 MHz). */
void Radio_SetFrequency(uint32_t freq_hz);

/* Sets TX output power in dBm (-9..22 for SX1262 high-power PA). */
void Radio_SetTxPower(int8_t power_dbm);

/* Queues a packet for transmission. Returns false if the radio is busy
 * with another TX/RX or size exceeds RADIO_MAX_PAYLOAD_LEN. */
bool Radio_Send(const uint8_t *data, uint8_t size);

/* Puts the radio into continuous RX. Call again after a received packet
 * is consumed if you want to keep listening. */
void Radio_StartReceive(void);

bool Radio_IsBusy(void);
Radio_State_t Radio_GetState(void);

/* True once after a packet lands; consumed by Radio_GetReceived(). */
bool Radio_HasReceived(void);

/* Copies the last received payload into buffer (caller-sized) and clears
 * the "has received" flag. Returns the payload length, 0 if none pending. */
uint8_t Radio_GetReceived(uint8_t *buffer, uint8_t buffer_size);

#ifdef __cplusplus
}
#endif

#endif /* RADIO_H */
