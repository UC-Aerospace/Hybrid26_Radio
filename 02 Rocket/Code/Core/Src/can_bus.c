// #include "can_bus.h"
// #include "main.h"
// #include <string.h>

// extern FDCAN_HandleTypeDef hfdcan1;

// static CanBus_Message_t s_rx_queue[CANBUS_RX_QUEUE_LEN];
// static uint8_t s_rx_head = 0;
// static uint8_t s_rx_tail = 0;
// static uint8_t s_rx_count = 0;

// static uint32_t CanBus_LenToDlc(uint8_t len)
// {
//     switch (len)
//     {
//         case 0: return FDCAN_DLC_BYTES_0;
//         case 1: return FDCAN_DLC_BYTES_1;
//         case 2: return FDCAN_DLC_BYTES_2;
//         case 3: return FDCAN_DLC_BYTES_3;
//         case 4: return FDCAN_DLC_BYTES_4;
//         case 5: return FDCAN_DLC_BYTES_5;
//         case 6: return FDCAN_DLC_BYTES_6;
//         case 7: return FDCAN_DLC_BYTES_7;
//         default: return FDCAN_DLC_BYTES_8;
//     }
// }

// static uint8_t CanBus_DlcToLen(uint32_t dlc)
// {
//     switch (dlc)
//     {
//         case FDCAN_DLC_BYTES_0: return 0;
//         case FDCAN_DLC_BYTES_1: return 1;
//         case FDCAN_DLC_BYTES_2: return 2;
//         case FDCAN_DLC_BYTES_3: return 3;
//         case FDCAN_DLC_BYTES_4: return 4;
//         case FDCAN_DLC_BYTES_5: return 5;
//         case FDCAN_DLC_BYTES_6: return 6;
//         case FDCAN_DLC_BYTES_7: return 7;
//         default: return 8;
//     }
// }

// static void CanBus_Enqueue(const CanBus_Message_t *msg)
// {
//     if (s_rx_count >= CANBUS_RX_QUEUE_LEN)
//     {
//         return; /* queue full: drop the incoming frame */
//     }

//     s_rx_queue[s_rx_tail] = *msg;
//     s_rx_tail = (uint8_t)((s_rx_tail + 1) % CANBUS_RX_QUEUE_LEN);
//     s_rx_count++;
// }

// void CanBus_SetStandby(bool standby)
// {
//     HAL_GPIO_WritePin(CAN_STB1_GPIO_Port, CAN_STB1_Pin, standby ? GPIO_PIN_SET : GPIO_PIN_RESET);
// }

// void CanBus_Init(void)
// {
//     CanBus_SetStandby(false); /* TCAN1046 channel 1: normal mode */

//     /* No dedicated filters are configured (StdFiltersNbr = 0 in the .ioc),
//      * so accept all non-matching data frames into FIFO0 and drop remote
//      * frames. */
//     HAL_FDCAN_ConfigGlobalFilter(&hfdcan1, FDCAN_ACCEPT_IN_RX_FIFO0, FDCAN_ACCEPT_IN_RX_FIFO0,
//                                   FDCAN_REJECT_REMOTE, FDCAN_REJECT_REMOTE);

//     HAL_FDCAN_Start(&hfdcan1);

//     s_rx_head = 0;
//     s_rx_tail = 0;
//     s_rx_count = 0;
// }

// bool CanBus_Send(uint32_t id, const uint8_t *data, uint8_t len, bool extended)
// {
//     if ((len > CANBUS_MAX_DATA_LEN) || (HAL_FDCAN_GetTxFifoFreeLevel(&hfdcan1) == 0))
//     {
//         return false;
//     }

//     FDCAN_TxHeaderTypeDef header;
//     uint8_t payload[CANBUS_MAX_DATA_LEN] = {0};

//     if (len > 0)
//     {
//         memcpy(payload, data, len);
//     }

//     header.Identifier = id;
//     header.IdType = extended ? FDCAN_EXTENDED_ID : FDCAN_STANDARD_ID;
//     header.TxFrameType = FDCAN_DATA_FRAME;
//     header.DataLength = CanBus_LenToDlc(len);
//     header.ErrorStateIndicator = FDCAN_ESI_ACTIVE;
//     header.BitRateSwitch = FDCAN_BRS_OFF;
//     header.FDFormat = FDCAN_CLASSIC_CAN;
//     header.TxEventFifoControl = FDCAN_NO_TX_EVENTS;
//     header.MessageMarker = 0;

//     return HAL_FDCAN_AddMessageToTxFifoQ(&hfdcan1, &header, payload) == HAL_OK;
// }

// void CanBus_Task(void)
// {
//     FDCAN_RxHeaderTypeDef rx_header;
//     uint8_t rx_data[CANBUS_MAX_DATA_LEN];

//     while (HAL_FDCAN_GetRxFifoFillLevel(&hfdcan1, FDCAN_RX_FIFO0) > 0)
//     {
//         if (HAL_FDCAN_GetRxMessage(&hfdcan1, FDCAN_RX_FIFO0, &rx_header, rx_data) != HAL_OK)
//         {
//             break;
//         }

//         CanBus_Message_t msg;
//         msg.id = rx_header.Identifier;
//         msg.extended = (rx_header.IdType == FDCAN_EXTENDED_ID);
//         msg.len = CanBus_DlcToLen(rx_header.DataLength);
//         memcpy(msg.data, rx_data, msg.len);

//         CanBus_Enqueue(&msg);
//     }
// }

// bool CanBus_HasReceived(void)
// {
//     return s_rx_count > 0;
// }

// bool CanBus_GetReceived(CanBus_Message_t *msg)
// {
//     if (s_rx_count == 0)
//     {
//         return false;
//     }

//     *msg = s_rx_queue[s_rx_head];
//     s_rx_head = (uint8_t)((s_rx_head + 1) % CANBUS_RX_QUEUE_LEN);
//     s_rx_count--;
//     return true;
// }
