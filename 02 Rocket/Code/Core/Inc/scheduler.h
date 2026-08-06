#ifndef SCHEDULER_H
#define SCHEDULER_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

#define SCHEDULER_MAX_TASKS 8

typedef void (*SchedulerTaskFn)(void);

void Scheduler_Init(void);
bool Scheduler_AddTask(SchedulerTaskFn task, uint32_t period_ms);
void Scheduler_Run(void);

#ifdef __cplusplus
}
#endif

#endif /* SCHEDULER_H */
