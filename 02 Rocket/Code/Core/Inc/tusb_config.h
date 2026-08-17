#ifndef TUSB_CONFIG_H
#define TUSB_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

/* CFG_TUSB_MCU/CFG_TUSB_OS are supplied via CMake compile definitions
 * (see CMakeLists.txt) so this file stays board-agnostic. */
#ifndef CFG_TUSB_MCU
#error CFG_TUSB_MCU must be defined
#endif

#ifndef CFG_TUSB_OS
#define CFG_TUSB_OS OPT_OS_NONE
#endif

#ifndef CFG_TUSB_DEBUG
#define CFG_TUSB_DEBUG 0
#endif

#define BOARD_TUD_RHPORT 0
#define CFG_TUD_ENABLED  1
#define CFG_TUD_MAX_SPEED OPT_MODE_FULL_SPEED

#ifndef CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_SECTION
#endif

#ifndef CFG_TUSB_MEM_ALIGN
#define CFG_TUSB_MEM_ALIGN __attribute__((aligned(4)))
#endif

/* -------------------- Device configuration -------------------- */

#define CFG_TUD_ENDPOINT0_SIZE 64

#define CFG_TUD_CDC    1
#define CFG_TUD_MSC    0
#define CFG_TUD_HID    0
#define CFG_TUD_MIDI   0
#define CFG_TUD_VENDOR 0

#define CFG_TUD_CDC_NOTIFY 1

#define CFG_TUD_CDC_RX_BUFSIZE 128
#define CFG_TUD_CDC_TX_BUFSIZE 256

#define CFG_TUD_CDC_RX_EPSIZE 64
#define CFG_TUD_CDC_TX_EPSIZE 64

#ifdef __cplusplus
}
#endif

#endif /* TUSB_CONFIG_H */
