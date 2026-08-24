/*
 * sx1262.c
 *
 * See sx1262.h for wiring assumptions and the datasheet reference used
 * throughout ("the datasheet" = Semtech DS.SX1261-2.W.APP Rev 1.1).
 */

#include "radio.h"

/* CubeMX-generated SPI1 handle. If your project names it differently,
 * update this line. */
extern SPI_HandleTypeDef hspi1;

/* ---------------------------------------------------------------------
 * Opcodes (datasheet Section 11, Tables 11-1 to 11-5, pp.61-63)
 * ------------------------------------------------------------------- */
#define OP_SET_STANDBY              0x80
#define OP_SET_TX                   0x83
#define OP_SET_PA_CONFIG            0x95
#define OP_SET_RX_TX_FALLBACK_MODE  0x93
#define OP_WRITE_BUFFER             0x0E
#define OP_SET_DIO_IRQ_PARAMS       0x08
#define OP_GET_IRQ_STATUS           0x12
#define OP_CLEAR_IRQ_STATUS         0x02
#define OP_SET_DIO2_AS_RF_SWITCH    0x9D
#define OP_SET_RF_FREQUENCY         0x86
#define OP_SET_PACKET_TYPE          0x8A
#define OP_SET_TX_PARAMS            0x8E
#define OP_SET_MODULATION_PARAMS    0x8B
#define OP_SET_PACKET_PARAMS        0x8C
#define OP_SET_BUFFER_BASE_ADDRESS  0x8F

/* IRQ bit positions (Table 13-29, p.78) */
#define IRQ_TX_DONE_BIT   0
#define IRQ_TIMEOUT_BIT   9
#define IRQ_MASK_TX_DONE_AND_TIMEOUT  ((1u << IRQ_TX_DONE_BIT) | (1u << IRQ_TIMEOUT_BIT)) /* = 0x0201 */

/* ---------------------------------------------------------------------
 * Low-level SPI framing helpers
 * ------------------------------------------------------------------- */

/* BUSY low = SX1262 ready for the next SPI command; BUSY high = the
 * internal state machine is still processing the previous one.
 * (datasheet Section 8.3.1, p.51). We block here rather than using a
 * fixed delay because the wait time varies hugely by command and mode
 * -- from ~600 ns for a simple register write up to ~3.5 ms coming out
 * of full Sleep (Table 8-2, p.52). */
static void SX1262_WaitOnBusy(void)
{
    while (HAL_GPIO_ReadPin(SX1262_BUSY_GPIO_Port, SX1262_BUSY_Pin) == GPIO_PIN_SET)
    {
        /* spin */
    }
}

/* Generic "write" command: opcode followed by paramLen parameter bytes,
 * framed by NSS low/high (datasheet Section 8.2, p.48: "NSS pin goes low
 * at the beginning of the frame and goes high after the data byte"). */
static void SX1262_WriteCommand(uint8_t opcode, const uint8_t *params, uint8_t paramLen)
{
    SX1262_WaitOnBusy(); /* never start a new command while BUSY is high */

    HAL_GPIO_WritePin(SX1262_CS_GPIO_Port, SX1262_CS_Pin, GPIO_PIN_RESET); /* NSS low = start frame */
    HAL_SPI_Transmit(&hspi1, &opcode, 1, HAL_MAX_DELAY);
    if (paramLen > 0)
    {
        HAL_SPI_Transmit(&hspi1, (uint8_t *)params, paramLen, HAL_MAX_DELAY);
    }
    HAL_GPIO_WritePin(SX1262_CS_GPIO_Port, SX1262_CS_Pin, GPIO_PIN_SET); /* NSS high = end frame */
}

/* Generic "read" command: opcode, then NOP bytes are clocked out while
 * the SX1262 clocks its reply back on MISO. `respLen` is the number of
 * response bytes expected AFTER the opcode byte (per each command's own
 * table, e.g. GetIrqStatus returns Status + IrqStatus(15:0) = 3 bytes). */
static void SX1262_ReadCommand(uint8_t opcode, uint8_t *response, uint8_t respLen)
{
    uint8_t nop[4] = {0}; /* big enough for every read command this driver uses */

    SX1262_WaitOnBusy();

    HAL_GPIO_WritePin(SX1262_CS_GPIO_Port, SX1262_CS_Pin, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &opcode, 1, HAL_MAX_DELAY);
    HAL_SPI_TransmitReceive(&hspi1, nop, response, respLen, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(SX1262_CS_GPIO_Port, SX1262_CS_Pin, GPIO_PIN_SET);
}

/* WriteBuffer is its own shape: opcode, offset, then the payload bytes
 * (Table 13-26, p.77). Kept separate from SX1262_WriteCommand so the
 * payload doesn't need to be copied into a combined array first. */
static void SX1262_WriteBuffer(uint8_t offset, const uint8_t *data, uint8_t len)
{
    uint8_t opcode = OP_WRITE_BUFFER;

    SX1262_WaitOnBusy();

    HAL_GPIO_WritePin(SX1262_CS_GPIO_Port, SX1262_CS_Pin, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &opcode, 1, HAL_MAX_DELAY);
    HAL_SPI_Transmit(&hspi1, &offset, 1, HAL_MAX_DELAY);
    HAL_SPI_Transmit(&hspi1, (uint8_t *)data, len, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(SX1262_CS_GPIO_Port, SX1262_CS_Pin, GPIO_PIN_SET);
}

/* ---------------------------------------------------------------------
 * Public API
 * ------------------------------------------------------------------- */

HAL_StatusTypeDef Radio_PowerOn(void)
{
    /* Enable the analog 3V3 rail (powers the SX1262) and the PE4259's
     * VDD (single-pin control mode -- held high permanently, see
     * radio.h). No datasheet-specified rise time for this board's LDO,
     * so this delay is a conservative margin, not a spec value -- trim
     * it down once you've measured your actual rail settling time. */
    HAL_GPIO_WritePin(LDO_3V3A_EN_GPIO_Port, LDO_3V3A_EN_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(ANT_SW_GPIO_Port, ANT_SW_Pin, GPIO_PIN_SET);
    HAL_Delay(10);

    return SX1262_Init();
}

HAL_StatusTypeDef SX1262_Init(void)
{
    /* --- Hardware reset ---
     * NRESET held low >100 us triggers a full "factory reset"; the chip
     * then auto-calibrates and lands in STDBY_RC on its own, indicated
     * by BUSY going low (datasheet Section 8.1, p.48 and Section 13.1.2,
     * p.66). */
    HAL_GPIO_WritePin(SX1262_RESET_GPIO_Port, SX1262_RESET_Pin, GPIO_PIN_RESET);
    HAL_Delay(1); /* well over the 100 us minimum, easy to hit with HAL_Delay's 1 ms tick */
    HAL_GPIO_WritePin(SX1262_RESET_GPIO_Port, SX1262_RESET_Pin, GPIO_PIN_SET);
    SX1262_WaitOnBusy(); /* wait out the reset+auto-calibration BUSY window */

    /* --- SetStandby(STDBY_RC) ---
     * Forces STDBY_RC explicitly. Redundant right after reset (the chip
     * is already there) but required before some later commands can be
     * trusted to be in a known state (Table 13-4, p.66). */
    {
        uint8_t param = 0x00; /* STDBY_RC */
        SX1262_WriteCommand(OP_SET_STANDBY, &param, 1);
    }

    /* --- SetPacketType(LoRa) ---
     * Must be the first radio-configuration command sent (datasheet
     * Section 13.4.2, p.81: "must be the first of the radio configuration
     * sequence"). */
    {
        uint8_t param = 0x01; /* PACKET_TYPE_LORA, Table 13-38 */
        SX1262_WriteCommand(OP_SET_PACKET_TYPE, &param, 1);
    }

    /* --- SetRfFrequency(915 MHz) ---
     * Freq register = RfFrequency * 2^25 / Fxtal (Section 13.4.1, p.81).
     * Fxtal = 32 MHz (your Y1 crystal). For 915,000,000 Hz this works out
     * to 0x39300000 -- precomputed here rather than doing the division on
     * the MCU. 915 MHz matches the pi-matching/harmonic-filter network on
     * rf_rocket_module's lorav2 sheet, which was calculated for this band. */
    {
        uint8_t params[4] = {0x39, 0x30, 0x00, 0x00};
        SX1262_WriteCommand(OP_SET_RF_FREQUENCY, params, 4);
    }

    /* --- SetPaConfig ---
     * deviceSel=0x00 selects the SX1262 (this is the physical part on the
     * board -- it only has the high-power PA, there is no way to select
     * the SX1261 low-power PA in silicon that isn't fitted). paDutyCycle
     * and hpMax are both kept low: the datasheet's explicit caution
     * (p.75) is "For SX1262, paDutyCycle should not be higher than 0x04
     * ... exceeding the maximum ratings may cause irreversible damage to
     * the device" -- since we're deliberately running at minimum power
     * there's no reason to push either value up.
     * paLut is reserved and always 0x01 (Section 13.1.14, p.74). */
    {
        uint8_t params[4] = {
            0x02, /* paDutyCycle */
            0x00, /* hpMax */
            0x00, /* deviceSel: SX1262 */
            0x01  /* paLut: reserved, always 0x01 */
        };
        SX1262_WriteCommand(OP_SET_PA_CONFIG, params, 4);
    }

    /* --- SetTxParams(-9 dBm, 10 us ramp) ---
     * -9 dBm (0xF7 as a signed byte) is the lowest power SetTxParams can
     * command when the high-power PA is selected: "-9 (0xF7) to +22
     * (0x16) dBm ... if high power PA is selected" (Section 13.4.4,
     * p.83). The -17 dBm floor documented elsewhere only applies to the
     * SX1261's low-power PA, which this board's SX1262 doesn't have.
     * Ramp time of 10 us (SET_RAMP_10U) is the fastest/lowest-energy
     * ramp option (Table 13-41) -- fine here since we're not near any
     * power or spectral-mask limit. */
    {
        uint8_t params[2] = {
            0xF7, /* power = -9 dBm */
            0x00  /* RampTime = SET_RAMP_10U (10 us) */
        };
        SX1262_WriteCommand(OP_SET_TX_PARAMS, params, 2);
    }

    /* --- SetBufferBaseAddress ---
     * Fixes both TX and RX base addresses at 0 in the SX1262's internal
     * data buffer (Table 13-26 area, Section 13.4-adjacent command).
     * We only ever transmit, so RX base is unused but must still be set. */
    {
        uint8_t params[2] = {0x00, 0x00}; /* txBaseAddr, rxBaseAddr */
        SX1262_WriteCommand(OP_SET_BUFFER_BASE_ADDRESS, params, 2);
    }

    /* --- SetModulationParams(SF7, BW125, CR4:5, LDRO off) ---
     * LoRa modulation params occupy the first 4 of the 8 generic
     * ModParam bytes (Section 13.4.5.2, p.85-86); the remaining 4 bytes
     * are unused for LoRa and sent as 0. SF7/BW125/CR4:5 are reasonable
     * defaults for a first bring-up test, not derived from a link
     * budget. */
    {
        uint8_t params[8] = {
            0x07, /* ModParam1: SF7 */
            0x04, /* ModParam2: LORA_BW_125 */
            0x01, /* ModParam3: LORA_CR_4_5 */
            0x00, /* ModParam4: LowDataRateOptimize off */
            0x00, 0x00, 0x00, 0x00 /* unused for LoRa */
        };
        SX1262_WriteCommand(OP_SET_MODULATION_PARAMS, params, 8);
    }

    /* --- SetDIO2AsRfSwitchCtrl(enable) ---
     * Your schematic ties SX1262 DIO2 directly to the PE4259 antenna
     * switch's CTRL pin (net ANT_SW) -- there's no MCU GPIO in that
     * path. Enabling this makes the SX1262 toggle DIO2 automatically:
     * "DIO2 = 0 in SLEEP, STDBY, FS and RX modes, DIO2 = 1 in TX mode"
     * (Section 13.3.5, p.80), so the switch always points at the right
     * PE4259 leg a few microseconds before the PA ramps up. Skipping
     * this leaves the switch in whatever position it powered up in --
     * not something that damages the PE4259 (it's rated to +34 dBm in,
     * far above the SX1262's max +22 dBm out), but you could end up
     * transmitting into the wrong port and never see the packet on air. */
    {
        uint8_t param = 0x01; /* enable */
        SX1262_WriteCommand(OP_SET_DIO2_AS_RF_SWITCH, &param, 1);
    }

    /* --- SetDioIrqParams ---
     * Routes TxDone (bit 0) and Timeout (bit 9) to DIO1 -- the only DIO
     * actually wired to the MCU on this board (SX1262_DIO1). DIO2 is now
     * dedicated to the antenna switch and DIO3 isn't routed to the MCU,
     * so both their masks are left at 0 (Section 13.3.1, p.77-78).
     * IrqMask = DIO1Mask = 0x0201 (bit0 | bit9). */
    {
        uint8_t hi = (uint8_t)(IRQ_MASK_TX_DONE_AND_TIMEOUT >> 8);
        uint8_t lo = (uint8_t)(IRQ_MASK_TX_DONE_AND_TIMEOUT & 0xFF);
        uint8_t params[8] = {
            hi, lo, /* IrqMask */
            hi, lo, /* DIO1Mask: same two IRQs routed to DIO1 */
            0x00, 0x00, /* DIO2Mask: none -- DIO2 is the antenna switch */
            0x00, 0x00  /* DIO3Mask: none -- not routed to the MCU */
        };
        SX1262_WriteCommand(OP_SET_DIO_IRQ_PARAMS, params, 8);
    }

    return HAL_OK;
}

HAL_StatusTypeDef SX1262_SendPacket(const uint8_t *data, uint8_t len)
{
    /* --- WriteBuffer ---
     * Loads the payload into the SX1262's internal buffer starting at
     * offset 0 (matches the txBaseAddr set in SX1262_Init).
     * (Table 13-26, p.77). */
    SX1262_WriteBuffer(0x00, data, len);

    /* --- SetPacketParams ---
     * Set here (not just once at init) so the payload length always
     * matches what was just written to the buffer, even if `len` varies
     * between calls.
     *   PreambleLength = 8 symbols (PacketParam1-2, MSB first)
     *   HeaderType     = 0x00 explicit/variable-length header
     *   PayloadLength  = len
     *   CRCType        = 0x01 CRC on
     *   InvertIQ       = 0x00 standard IQ
     * (Section 13.4.6, LoRa packet params tables, p.90). */
    {
        uint8_t params[6] = {
            0x00, 0x08, /* PreambleLength = 8 */
            0x00,       /* HeaderType: explicit header */
            len,        /* PayloadLength */
            0x01,       /* CRCType: CRC on */
            0x00        /* InvertIQ: standard */
        };
        SX1262_WriteCommand(OP_SET_PACKET_PARAMS, params, 6);
    }

    /* --- SetTx(Tx Single mode) ---
     * Timeout = 0x000000 means "Tx Single mode": the chip stays in TX
     * until the packet is fully sent, then returns to STDBY_RC on its
     * own (Table 13-7, p.67) -- simplest option for a bring-up test,
     * and safe since we're only running at -9 dBm with nothing thermally
     * at risk. */
    {
        uint8_t params[3] = {0x00, 0x00, 0x00};
        SX1262_WriteCommand(OP_SET_TX, params, 3);
    }

    /* --- Wait for TxDone/Timeout on DIO1 ---
     * DIO1 goes high when either masked IRQ fires (TxDone or Timeout, as
     * configured in SX1262_Init's SetDioIrqParams call). We just poll
     * the pin here for simplicity; swap for an EXTI callback later if
     * you want this non-blocking. */
    while (HAL_GPIO_ReadPin(SX1262_DIO1_GPIO_Port, SX1262_DIO1_Pin) == GPIO_PIN_RESET)
    {
        /* spin */
    }

    /* --- GetIrqStatus ---
     * Confirms *which* IRQ fired -- DIO1 alone can't tell TxDone from
     * Timeout since both are routed to it. Response is [Status, IrqHi,
     * IrqLo] after the opcode (Table 13-30, p.79). */
    uint8_t irqResp[3];
    SX1262_ReadCommand(OP_GET_IRQ_STATUS, irqResp, 3);
    uint16_t irqStatus = ((uint16_t)irqResp[1] << 8) | irqResp[2];

    /* --- ClearIrqStatus ---
     * IRQ flags stay latched until explicitly cleared (Section 13.3.4,
     * p.79) -- skip this and the next SendPacket's IRQ will look
     * identical to a leftover flag from this one, or DIO1 will simply
     * never go back low. Clear the same bits we were watching for. */
    {
        uint8_t hi = (uint8_t)(IRQ_MASK_TX_DONE_AND_TIMEOUT >> 8);
        uint8_t lo = (uint8_t)(IRQ_MASK_TX_DONE_AND_TIMEOUT & 0xFF);
        uint8_t params[2] = {hi, lo};
        SX1262_WriteCommand(OP_CLEAR_IRQ_STATUS, params, 2);
    }

    return (irqStatus & (1u << IRQ_TX_DONE_BIT)) ? HAL_OK : HAL_ERROR;
}