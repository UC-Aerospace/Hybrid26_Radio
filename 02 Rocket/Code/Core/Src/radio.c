#include "radio.h"
#include "main.h"
#include "log.h"
#include <string.h>
#include <stdio.h>

/* ---- SX1262 command opcodes (Semtech SX126x datasheet, table "Commands") --- */
#define SX126X_CMD_GET_STATUS            0xC0
#define SX126X_CMD_WRITE_REGISTER        0x0D
#define SX126X_CMD_READ_REGISTER         0x1D
#define SX126X_CMD_WRITE_BUFFER          0x0E
#define SX126X_CMD_READ_BUFFER           0x1E
#define SX126X_CMD_SET_SLEEP             0x84
#define SX126X_CMD_SET_STANDBY           0x80
#define SX126X_CMD_SET_TX                0x83
#define SX126X_CMD_SET_RX                0x82
#define SX126X_CMD_SET_PACKET_TYPE       0x8A
#define SX126X_CMD_SET_RF_FREQUENCY      0x86
#define SX126X_CMD_SET_TX_PARAMS         0x8E
#define SX126X_CMD_SET_PA_CONFIG         0x95
#define SX126X_CMD_SET_MODULATION_PARAMS 0x8B
#define SX126X_CMD_SET_PACKET_PARAMS     0x8C
#define SX126X_CMD_SET_BUFFER_BASE_ADDR  0x8F
#define SX126X_CMD_SET_DIO_IRQ_PARAMS    0x08
#define SX126X_CMD_GET_IRQ_STATUS        0x12
#define SX126X_CMD_CLEAR_IRQ_STATUS      0x02
#define SX126X_CMD_CALIBRATE             0x89
#define SX126X_CMD_SET_REGULATOR_MODE    0x96
#define SX126X_CMD_GET_RX_BUFFER_STATUS  0x13
#define SX126X_CMD_GET_PACKET_STATUS     0x14

#define SX126X_STANDBY_RC                0x00
#define SX126X_REGULATOR_LDO             0x00
#define SX126X_PACKET_TYPE_LORA          0x01
#define SX126X_LORA_BW_125               0x04
#define SX126X_LORA_CR_4_5               0x01
#define SX126X_RAMP_200U                 0x04

#define SX126X_IRQ_TX_DONE                0x0001
#define SX126X_IRQ_RX_DONE                0x0002
#define SX126X_IRQ_CRC_ERR                0x0040
#define SX126X_IRQ_TIMEOUT                0x0200
#define SX126X_IRQ_ALL                    0xFFFF

#define SX126X_XTAL_FREQ_HZ               32000000UL

#define RADIO_DEFAULT_FREQ_HZ              915000000UL
#define RADIO_DEFAULT_TX_POWER_DBM         22
#define RADIO_SPI_TIMEOUT_MS               100
#define RADIO_BUSY_TIMEOUT_MS              1000
#define RADIO_TX_GUARD_TIMEOUT_MS          4000

#define LOG_HEX_MAX_BYTES                 16

extern SPI_HandleTypeDef hspi1;

static Radio_State_t s_state = RADIO_STATE_STANDBY;
static uint32_t s_tx_start_tick = 0;
static uint8_t s_rx_buffer[RADIO_MAX_PAYLOAD_LEN];
static uint8_t s_rx_len = 0;
static bool s_has_received = false;

/* ---- low-level SPI transport --------------------------------------------- */

static void Radio_NssLow(void)
{
    HAL_GPIO_WritePin(SX1262_NSS_GPIO_Port, SX1262_NSS_Pin, GPIO_PIN_RESET);
}

static void Radio_NssHigh(void)
{
    HAL_GPIO_WritePin(SX1262_NSS_GPIO_Port, SX1262_NSS_Pin, GPIO_PIN_SET);
}

/* Returns false on timeout (chip not responding / not wired correctly). */
static bool Radio_WaitOnBusy(void)
{
    uint32_t start = HAL_GetTick();

    while (HAL_GPIO_ReadPin(SX1262_BUSY_GPIO_Port, SX1262_BUSY_Pin) == GPIO_PIN_SET)
    {
        if ((uint32_t)(HAL_GetTick() - start) > RADIO_BUSY_TIMEOUT_MS)
        {
            return false;
        }
    }
    return true;
}

static void Radio_WriteCommand(uint8_t opcode, const uint8_t *params, uint16_t size)
{
    Radio_WaitOnBusy();
    Radio_NssLow();
    HAL_SPI_Transmit(&hspi1, &opcode, 1, RADIO_SPI_TIMEOUT_MS);
    if (size > 0)
    {
        HAL_SPI_Transmit(&hspi1, (uint8_t *)params, size, RADIO_SPI_TIMEOUT_MS);
    }
    Radio_NssHigh();
    if (opcode != SX126X_CMD_SET_SLEEP)
    {
        Radio_WaitOnBusy();
    }
}

/* opcode + 1 status byte (discarded) + size data bytes. Matches every
 * Get* command except GetStatus itself (see Radio_GetStatus). */
static void Radio_ReadCommand(uint8_t opcode, uint8_t *data, uint16_t size)
{
    uint8_t status;

    Radio_WaitOnBusy();
    Radio_NssLow();
    HAL_SPI_Transmit(&hspi1, &opcode, 1, RADIO_SPI_TIMEOUT_MS);
    HAL_SPI_Receive(&hspi1, &status, 1, RADIO_SPI_TIMEOUT_MS);
    if (size > 0)
    {
        HAL_SPI_Receive(&hspi1, data, size, RADIO_SPI_TIMEOUT_MS);
    }
    Radio_NssHigh();
    Radio_WaitOnBusy();
}

static void Radio_WriteBuffer(uint8_t offset, const uint8_t *data, uint8_t size)
{
    uint8_t header[2] = { SX126X_CMD_WRITE_BUFFER, offset };

    Radio_WaitOnBusy();
    Radio_NssLow();
    HAL_SPI_Transmit(&hspi1, header, sizeof(header), RADIO_SPI_TIMEOUT_MS);
    HAL_SPI_Transmit(&hspi1, (uint8_t *)data, size, RADIO_SPI_TIMEOUT_MS);
    Radio_NssHigh();
    Radio_WaitOnBusy();
}

static void Radio_ReadBuffer(uint8_t offset, uint8_t *data, uint8_t size)
{
    uint8_t header[2] = { SX126X_CMD_READ_BUFFER, offset };
    uint8_t status;

    Radio_WaitOnBusy();
    Radio_NssLow();
    HAL_SPI_Transmit(&hspi1, header, sizeof(header), RADIO_SPI_TIMEOUT_MS);
    HAL_SPI_Receive(&hspi1, &status, 1, RADIO_SPI_TIMEOUT_MS);
    HAL_SPI_Receive(&hspi1, data, size, RADIO_SPI_TIMEOUT_MS);
    Radio_NssHigh();
    Radio_WaitOnBusy();
}

/* ---- antenna switch (PE4259 SPDT, U3) ------------------------------------ */
/* Polarity assumed from the PE4259 truth table (Vctl high -> RF1/RFC); verify
 * against the schematic which RF1/RF2 leg feeds the SX1262 TX vs RX path
 * before relying on this for over-the-air use. */
static void Radio_SetAntennaSwitch(bool tx)
{
    HAL_GPIO_WritePin(Antenna_Switch_GPIO_Port, Antenna_Switch_Pin,
                       tx ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* ---- chip bring-up --------------------------------------------------------*/

static void Radio_Reset(void)
{
    HAL_GPIO_WritePin(SX1262_RESET_GPIO_Port, SX1262_RESET_Pin, GPIO_PIN_RESET);
    HAL_Delay(2);
    HAL_GPIO_WritePin(SX1262_RESET_GPIO_Port, SX1262_RESET_Pin, GPIO_PIN_SET);
    HAL_Delay(6);
    Radio_WaitOnBusy();
}

static void Radio_SetStandby(uint8_t mode)
{
    uint8_t param = mode;
    Radio_WriteCommand(SX126X_CMD_SET_STANDBY, &param, 1);
}

static void Radio_SetRegulatorMode(uint8_t mode)
{
    uint8_t param = mode;
    Radio_WriteCommand(SX126X_CMD_SET_REGULATOR_MODE, &param, 1);
}

static void Radio_Calibrate(void)
{
    uint8_t param = 0x7F;
    Radio_WriteCommand(SX126X_CMD_CALIBRATE, &param, 1);
    HAL_Delay(5);
}

static void Radio_SetPacketTypeLora(void)
{
    uint8_t param = SX126X_PACKET_TYPE_LORA;
    Radio_WriteCommand(SX126X_CMD_SET_PACKET_TYPE, &param, 1);
}

static void Radio_SetBufferBaseAddress(uint8_t tx_base, uint8_t rx_base)
{
    uint8_t params[2] = { tx_base, rx_base };
    Radio_WriteCommand(SX126X_CMD_SET_BUFFER_BASE_ADDR, params, sizeof(params));
}

static void Radio_SetModulationParams(void)
{
    /* SF7 / 125 kHz / 4:5, no low-data-rate optimization */
    uint8_t params[4] = { 0x07, SX126X_LORA_BW_125, SX126X_LORA_CR_4_5, 0x00 };
    Radio_WriteCommand(SX126X_CMD_SET_MODULATION_PARAMS, params, sizeof(params));
}

static void Radio_SetPacketParams(uint8_t payload_len)
{
    uint8_t params[6] = {
        0x00, 0x08,   /* preamble length = 8 symbols */
        0x00,         /* explicit header */
        payload_len,
        0x01,         /* CRC on */
        0x00,         /* standard IQ */
    };
    Radio_WriteCommand(SX126X_CMD_SET_PACKET_PARAMS, params, sizeof(params));
}

static void Radio_SetDioIrqParams(uint16_t irq_mask, uint16_t dio1_mask)
{
    uint8_t params[8] = {
        (uint8_t)(irq_mask >> 8), (uint8_t)irq_mask,
        (uint8_t)(dio1_mask >> 8), (uint8_t)dio1_mask,
        0x00, 0x00,
        0x00, 0x00,
    };
    Radio_WriteCommand(SX126X_CMD_SET_DIO_IRQ_PARAMS, params, sizeof(params));
}

static void Radio_ClearIrqStatus(uint16_t mask)
{
    uint8_t params[2] = { (uint8_t)(mask >> 8), (uint8_t)mask };
    Radio_WriteCommand(SX126X_CMD_CLEAR_IRQ_STATUS, params, sizeof(params));
}

static uint16_t Radio_GetIrqStatus(void)
{
    uint8_t data[2];
    Radio_ReadCommand(SX126X_CMD_GET_IRQ_STATUS, data, sizeof(data));
    return ((uint16_t)data[0] << 8) | data[1];
}

static void Radio_GetRxBufferStatus(uint8_t *payload_len, uint8_t *start_ptr)
{
    uint8_t data[2];
    Radio_ReadCommand(SX126X_CMD_GET_RX_BUFFER_STATUS, data, sizeof(data));
    *payload_len = data[0];
    *start_ptr = data[1];
}

static void Radio_GetPacketStatus(int16_t *rssi_dbm, int8_t *snr_db)
{
    uint8_t data[3];
    Radio_ReadCommand(SX126X_CMD_GET_PACKET_STATUS, data, sizeof(data));
    *rssi_dbm = (int16_t)(-(int16_t)data[0] / 2);
    *snr_db = (int8_t)((int8_t)data[1] / 4);
}

/* Renders up to LOG_HEX_MAX_BYTES of data as space-separated hex, "..." if
 * truncated. Keeps log lines (and their stack buffers) bounded regardless
 * of payload size. */
static void Radio_FormatHex(char *out, size_t out_size, const uint8_t *data, uint8_t len)
{
    size_t pos = 0;
    uint8_t n = (len > LOG_HEX_MAX_BYTES) ? LOG_HEX_MAX_BYTES : len;

    for (uint8_t i = 0; i < n && (pos + 3) < out_size; i++)
    {
        pos += (size_t)snprintf(out + pos, out_size - pos, "%02X ", data[i]);
    }
    if ((len > LOG_HEX_MAX_BYTES) && ((pos + 4) < out_size))
    {
        snprintf(out + pos, out_size - pos, "...");
    }
}

void Radio_SetFrequency(uint32_t freq_hz)
{
    uint32_t freq_reg = (uint32_t)(((uint64_t)freq_hz << 25) / SX126X_XTAL_FREQ_HZ);
    uint8_t params[4] = {
        (uint8_t)(freq_reg >> 24), (uint8_t)(freq_reg >> 16),
        (uint8_t)(freq_reg >> 8), (uint8_t)freq_reg,
    };
    Radio_WriteCommand(SX126X_CMD_SET_RF_FREQUENCY, params, sizeof(params));
}

void Radio_SetTxPower(int8_t power_dbm)
{
    /* PA config for SX1262 max-power operation (datasheet table 13-21) */
    uint8_t pa_config[4] = { 0x04, 0x07, 0x00, 0x01 };
    uint8_t tx_params[2] = { (uint8_t)power_dbm, SX126X_RAMP_200U };

    Radio_WriteCommand(SX126X_CMD_SET_PA_CONFIG, pa_config, sizeof(pa_config));
    Radio_WriteCommand(SX126X_CMD_SET_TX_PARAMS, tx_params, sizeof(tx_params));
}

void Radio_Init(void)
{
    Radio_Reset();
    Radio_SetStandby(SX126X_STANDBY_RC);
    Radio_SetRegulatorMode(SX126X_REGULATOR_LDO);
    Radio_Calibrate();
    Radio_SetPacketTypeLora();
    Radio_SetFrequency(RADIO_DEFAULT_FREQ_HZ);
    Radio_SetTxPower(RADIO_DEFAULT_TX_POWER_DBM);
    Radio_SetBufferBaseAddress(0, 0);
    Radio_SetModulationParams();
    Radio_SetPacketParams(RADIO_MAX_PAYLOAD_LEN);
    Radio_SetDioIrqParams(SX126X_IRQ_TX_DONE | SX126X_IRQ_RX_DONE | SX126X_IRQ_TIMEOUT | SX126X_IRQ_CRC_ERR,
                           SX126X_IRQ_TX_DONE | SX126X_IRQ_RX_DONE | SX126X_IRQ_TIMEOUT | SX126X_IRQ_CRC_ERR);
    Radio_ClearIrqStatus(SX126X_IRQ_ALL);

    s_state = RADIO_STATE_STANDBY;
    s_has_received = false;
}

bool Radio_Send(const uint8_t *data, uint8_t size)
{
    if ((data == NULL) || (size == 0) || (size > RADIO_MAX_PAYLOAD_LEN) || (s_state != RADIO_STATE_STANDBY))
    {
        return false;
    }

    Radio_SetAntennaSwitch(true);
    Radio_WriteBuffer(0, data, size);
    Radio_SetPacketParams(size);
    Radio_ClearIrqStatus(SX126X_IRQ_ALL);

    uint8_t timeout_params[3] = { 0x00, 0x00, 0x00 }; /* timeout disabled, rely on TxDone IRQ */
    Radio_WriteCommand(SX126X_CMD_SET_TX, timeout_params, sizeof(timeout_params));

    s_state = RADIO_STATE_TX;
    s_tx_start_tick = HAL_GetTick();

    char hex[3 * LOG_HEX_MAX_BYTES + 8];
    Radio_FormatHex(hex, sizeof(hex), data, size);
    Log_Printf("[%lu] RADIO TX len=%u data=%s\r\n", HAL_GetTick(), size, hex);

    return true;
}

void Radio_StartReceive(void)
{
    Radio_SetAntennaSwitch(false);
    Radio_SetPacketParams(RADIO_MAX_PAYLOAD_LEN);
    Radio_ClearIrqStatus(SX126X_IRQ_ALL);

    uint8_t timeout_params[3] = { 0xFF, 0xFF, 0xFF }; /* continuous RX */
    Radio_WriteCommand(SX126X_CMD_SET_RX, timeout_params, sizeof(timeout_params));

    s_state = RADIO_STATE_RX;
}

bool Radio_IsBusy(void)
{
    return s_state != RADIO_STATE_STANDBY;
}

Radio_State_t Radio_GetState(void)
{
    return s_state;
}

bool Radio_HasReceived(void)
{
    return s_has_received;
}

uint8_t Radio_GetReceived(uint8_t *buffer, uint8_t buffer_size)
{
    if (!s_has_received)
    {
        return 0;
    }

    uint8_t len = (s_rx_len < buffer_size) ? s_rx_len : buffer_size;
    memcpy(buffer, s_rx_buffer, len);
    s_has_received = false;
    return len;
}

void Radio_Task(void)
{
    if (s_state == RADIO_STATE_STANDBY)
    {
        return;
    }

    if (s_state == RADIO_STATE_TX &&
        (uint32_t)(HAL_GetTick() - s_tx_start_tick) > RADIO_TX_GUARD_TIMEOUT_MS)
    {
        /* Defensive fallback: TxDone IRQ never arrived (miswiring, etc). */
        Radio_ClearIrqStatus(SX126X_IRQ_ALL);
        s_state = RADIO_STATE_STANDBY;
        return;
    }

    if (HAL_GPIO_ReadPin(SX1262_DIO1_GPIO_Port, SX1262_DIO1_Pin) != GPIO_PIN_SET)
    {
        return;
    }

    uint16_t irq = Radio_GetIrqStatus();
    Radio_ClearIrqStatus(irq);

    if (s_state == RADIO_STATE_TX && (irq & SX126X_IRQ_TX_DONE))
    {
        Log_Printf("[%lu] RADIO TXDONE\r\n", HAL_GetTick());
        s_state = RADIO_STATE_STANDBY;
    }
    else if (s_state == RADIO_STATE_RX && (irq & SX126X_IRQ_RX_DONE) && !(irq & SX126X_IRQ_CRC_ERR))
    {
        uint8_t payload_len, start_ptr;
        Radio_GetRxBufferStatus(&payload_len, &start_ptr);
        if (payload_len > RADIO_MAX_PAYLOAD_LEN)
        {
            payload_len = RADIO_MAX_PAYLOAD_LEN;
        }
        Radio_ReadBuffer(start_ptr, s_rx_buffer, payload_len);
        s_rx_len = payload_len;
        s_has_received = true;

        int16_t rssi_dbm;
        int8_t snr_db;
        Radio_GetPacketStatus(&rssi_dbm, &snr_db);
        char hex[3 * LOG_HEX_MAX_BYTES + 8];
        Radio_FormatHex(hex, sizeof(hex), s_rx_buffer, payload_len);
        Log_Printf("[%lu] RADIO RX len=%u rssi=%d snr=%d data=%s\r\n",
                   HAL_GetTick(), payload_len, rssi_dbm, snr_db, hex);

        s_state = RADIO_STATE_STANDBY;
    }
    else if (irq & SX126X_IRQ_TIMEOUT)
    {
        Log_Printf("[%lu] RADIO TIMEOUT state=%s\r\n", HAL_GetTick(),
                   (s_state == RADIO_STATE_TX) ? "TX" : "RX");
        s_state = RADIO_STATE_STANDBY;
    }
}
