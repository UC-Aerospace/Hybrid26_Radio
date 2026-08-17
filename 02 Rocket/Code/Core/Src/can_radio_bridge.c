// #include "can_radio_bridge.h"
// #include "can_bus.h"
// #include "radio.h"
// #include <string.h>

// /* Wire format sent to the ground station: [flags(1)][id(4, big-endian)]
//  * [len(1)][data(0-8)]. flags bit0 = extended CAN ID. */
// #define BRIDGE_HEADER_LEN 6

// void CanRadioBridge_Task(void)
// {
//     if (Radio_IsBusy())
//     {
//         return; /* leave the frame queued in CanBus until the radio frees up */
//     }

//     CanBus_Message_t msg;
//     if (!CanBus_GetReceived(&msg))
//     {
//         return;
//     }

//     uint8_t payload[BRIDGE_HEADER_LEN + CANBUS_MAX_DATA_LEN];
//     payload[0] = msg.extended ? 0x01 : 0x00;
//     payload[1] = (uint8_t)(msg.id >> 24);
//     payload[2] = (uint8_t)(msg.id >> 16);
//     payload[3] = (uint8_t)(msg.id >> 8);
//     payload[4] = (uint8_t)msg.id;
//     payload[5] = msg.len;
//     memcpy(&payload[BRIDGE_HEADER_LEN], msg.data, msg.len);

//     Radio_Send(payload, BRIDGE_HEADER_LEN + msg.len);
// }
