#ifndef USB_CDC_H
#define USB_CDC_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Native USB virtual COM port (CDC-ACM) on the USB_DRD_FS peripheral,
 * driven by TinyUSB. Call UsbCdc_Init() once after MX_USB_PCD_Init() (which
 * only does the clock/VDDUSB/NVIC bring-up -- TinyUSB owns the peripheral
 * itself, see the comment in main.c), then schedule UsbCdc_Task() to run
 * frequently (every 1 ms is enough for a full-speed CDC port). */
void UsbCdc_Init(void);
void UsbCdc_Task(void);

/* Non-blocking: silently drops data if no host has the port open, or if the
 * host isn't reading fast enough and the TX buffer is full. Never call this
 * from an ISR. */
void UsbCdc_Write(const uint8_t *data, uint32_t len);

#ifdef __cplusplus
}
#endif

#endif /* USB_CDC_H */
