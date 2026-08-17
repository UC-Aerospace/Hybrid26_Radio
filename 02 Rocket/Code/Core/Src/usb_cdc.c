#include "usb_cdc.h"
#include "main.h"
#include "tusb.h"
#include <stdio.h>
#include <string.h>

#define USB_VID 0xCafeu
#define USB_PID 0x4a01u

void UsbCdc_Init(void)
{
    tusb_rhport_init_t rh_init = {
        .role = TUSB_ROLE_DEVICE,
        .speed = TUSB_SPEED_FULL,
    };

    tusb_rhport_init(0, &rh_init);
}

void UsbCdc_Task(void)
{
    tud_task();
}

void UsbCdc_Write(const uint8_t *data, uint32_t len)
{
    if (!tud_cdc_connected())
    {
        return;
    }

    uint32_t available = tud_cdc_write_available();
    if (available == 0)
    {
        return;
    }

    if (len > available)
    {
        len = available;
    }

    tud_cdc_write(data, len);
    tud_cdc_write_flush();
}

/* -------------------------------------------------------------------
 * USB descriptors
 * ------------------------------------------------------------------- */

static tusb_desc_device_t const s_device_descriptor = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,

    /* IAD-based CDC-ACM, per USB CDC spec recommendation. */
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,

    .idVendor = USB_VID,
    .idProduct = USB_PID,
    .bcdDevice = 0x0100,

    .iManufacturer = 0x01,
    .iProduct = 0x02,
    .iSerialNumber = 0x03,

    .bNumConfigurations = 0x01,
};

uint8_t const *tud_descriptor_device_cb(void)
{
    return (uint8_t const *)&s_device_descriptor;
}

enum
{
    ITF_NUM_CDC = 0,
    ITF_NUM_CDC_DATA,
    ITF_NUM_TOTAL,
};

#define EPNUM_CDC_NOTIF 0x81u
#define EPNUM_CDC_OUT   0x02u
#define EPNUM_CDC_IN    0x82u

#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_CDC_DESC_LEN)

static uint8_t const s_config_descriptor[] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x00, 100),

    TUD_CDC_DESCRIPTOR(ITF_NUM_CDC, 4, EPNUM_CDC_NOTIF, 16,
                       EPNUM_CDC_OUT, EPNUM_CDC_IN, CFG_TUD_CDC_TX_EPSIZE),
};

uint8_t const *tud_descriptor_configuration_cb(uint8_t index)
{
    (void)index;
    return s_config_descriptor;
}

enum
{
    STRID_LANGID = 0,
    STRID_MANUFACTURER,
    STRID_PRODUCT,
    STRID_SERIAL,
    STRID_CDC_INTERFACE,
};

static char const *s_string_descriptors[] = {
    NULL,
    "Hybrid26 Radio",
    "Rocket Radio Debug Console",
    NULL, /* serial number, filled in from the MCU UID below */
    "Debug Log",
};

static uint16_t s_desc_str[32 + 1];

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
    (void)langid;
    size_t char_count;

    if (index == STRID_LANGID)
    {
        s_desc_str[1] = 0x0409; /* English (US) */
        char_count = 1;
    }
    else if (index == STRID_SERIAL)
    {
        static char serial[25];
        uint32_t uid0 = *(volatile uint32_t *)(UID_BASE);
        uint32_t uid1 = *(volatile uint32_t *)(UID_BASE + 4);
        uint32_t uid2 = *(volatile uint32_t *)(UID_BASE + 8);

        snprintf(serial, sizeof(serial), "%08lX%08lX%08lX",
                 (unsigned long)uid0, (unsigned long)uid1, (unsigned long)uid2);

        char_count = strlen(serial);
        for (size_t i = 0; i < char_count; i++)
        {
            s_desc_str[1 + i] = (uint16_t)serial[i];
        }
    }
    else
    {
        if (index >= (sizeof(s_string_descriptors) / sizeof(s_string_descriptors[0])))
        {
            return NULL;
        }

        char const *str = s_string_descriptors[index];
        if (str == NULL)
        {
            return NULL;
        }

        char_count = strlen(str);
        size_t const max_count = (sizeof(s_desc_str) / sizeof(s_desc_str[0])) - 1;
        if (char_count > max_count)
        {
            char_count = max_count;
        }

        for (size_t i = 0; i < char_count; i++)
        {
            s_desc_str[1 + i] = (uint16_t)str[i];
        }
    }

    s_desc_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * char_count + 2));
    return s_desc_str;
}
