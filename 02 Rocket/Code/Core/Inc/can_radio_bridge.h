// #ifndef CAN_RADIO_BRIDGE_H
// #define CAN_RADIO_BRIDGE_H

// #ifdef __cplusplus
// extern "C" {
// #endif

// /* Rocket-side bridge: drains CanBus's received-frame queue and forwards
//  * each frame over the radio, verbatim, as soon as the radio is free.
//  * Frames are left queued in CanBus (not dropped) while the radio is busy.
//  * Call periodically (e.g. every 5 ms) via Scheduler_AddTask. */
// void CanRadioBridge_Task(void);

// #ifdef __cplusplus
// }
// #endif

// #endif /* CAN_RADIO_BRIDGE_H */
