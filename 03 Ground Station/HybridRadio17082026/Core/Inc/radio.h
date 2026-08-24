/*
 * sx1262.h
 *
 * Minimal SX1262 LoRa driver for the "Onboard Radio" board.
 * Configures the radio for LoRa, -9 dBm output (the lowest the physical
 * SX1262 PA supports), 915 MHz, SF7/BW125/CR4:5, and repeatedly
 * transmits a test packet.
 *
 * All opcodes, parameter encodings, and register/pin behaviour referenced
 * against: Semtech DS.SX1261-2.W.APP Rev 1.1 ("the datasheet" in comments).
 *
 * ---- Wiring assumptions (must match your CubeMX Pinout labels) ----
 * SPI1            -> SCK/MISO/MOSI to the SX1262 (CPOL=0, CPHA=0, per
 *                    datasheet Section 8.2, p.48). NSS is software-controlled
 *                    (NOT SPI1's hardware NSS) so we can hold it low/high
 *                    exactly when the datasheet's command framing needs it.
 * SX1262_CS       -> GPIO output driving the SX1262 NSS pin
 * SX1262_BUSY     -> GPIO input reading the SX1262 BUSY pin
 * SX1262_RESET    -> GPIO output driving the SX1262 NRESET pin
 * SX1262_DIO1     -> GPIO input reading the SX1262 DIO1 pin (TxDone/Timeout IRQ)
 * LDO_3V3A_EN     -> GPIO output enabling the analog 3V3 rail that powers
 *                    the SX1262 and the PE4259 antenna switch
 * ANT_SW          -> GPIO output driving the PE4259's VDD pin (pin 6,
 *                    single-pin control mode -- held high permanently,
 *                    never toggled; CTRL (pin 4) is driven by the SX1262's
 *                    own DIO2, not by the MCU)
 *
 * Set these exact User Labels on the corresponding pins in CubeMX's
 * Pinout view so main.h generates matching SX1262_xxx_GPIO_Port/Pin macros.
 */

#ifndef SX1262_H
#define SX1262_H

#include "main.h"
#include <stdint.h>

/* Enables the analog 3V3 rail (LDO_3V3A_EN) and the PE4259 antenna
 * switch's VDD (ANT_SW), waits for the rails to settle, then runs
 * SX1262_Init(). Call once at startup, after all MX_*_Init() calls. */
HAL_StatusTypeDef Radio_PowerOn(void);

/* Initializes the radio: STDBY_RC -> LoRa packet type -> 915 MHz ->
 * PA config for lowest available power -> -9 dBm TX power -> modulation
 * params (SF7/BW125/CR4:5) -> DIO2 handed to the PE4259 antenna switch ->
 * DIO1 wired to TxDone/Timeout IRQs. Call once at startup. */
HAL_StatusTypeDef SX1262_Init(void);

/* Loads `data` (up to 255 bytes) into the TX buffer, sets the packet
 * length, transmits, and blocks until TxDone or Timeout. Returns HAL_OK
 * if TxDone fired, HAL_ERROR if a Timeout IRQ fired instead. */
HAL_StatusTypeDef SX1262_SendPacket(const uint8_t *data, uint8_t len);

#endif /* SX1262_H */