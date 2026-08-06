#ifndef LOG_H
#define LOG_H

#ifdef __cplusplus
extern "C" {
#endif

/* Blocking, formatted debug log over UART4 (115200 8N1). Include a
 * terminating "\r\n" in fmt yourself. */
void Log_Printf(const char *fmt, ...);

#ifdef __cplusplus
}
#endif

#endif /* LOG_H */
