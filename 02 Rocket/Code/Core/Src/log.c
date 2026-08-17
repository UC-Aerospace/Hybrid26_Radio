#include "log.h"
#include "main.h"
#include "usb_cdc.h"
#include <stdio.h>
#include <stdarg.h>

#define LOG_BUFFER_SIZE   160
#define LOG_UART_TIMEOUT_MS 100

extern UART_HandleTypeDef huart4;

void Log_Printf(const char *fmt, ...)
{
    char buffer[LOG_BUFFER_SIZE];
    va_list args;

    va_start(args, fmt);
    int len = vsnprintf(buffer, sizeof(buffer), fmt, args);
    va_end(args);

    if (len <= 0)
    {
        return;
    }
    if ((size_t)len >= sizeof(buffer))
    {
        len = sizeof(buffer) - 1;
    }

    HAL_UART_Transmit(&huart4, (uint8_t *)buffer, (uint16_t)len, LOG_UART_TIMEOUT_MS);
    UsbCdc_Write((uint8_t *)buffer, (uint32_t)len);
}
