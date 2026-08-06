#include "scheduler.h"
#include "stm32h5xx_hal.h"

typedef struct
{
    SchedulerTaskFn task;
    uint32_t period_ms;
    uint32_t last_run_ms;
} SchedulerTask_t;

static SchedulerTask_t s_tasks[SCHEDULER_MAX_TASKS];
static uint8_t s_task_count = 0;

void Scheduler_Init(void)
{
    s_task_count = 0;
}

bool Scheduler_AddTask(SchedulerTaskFn task, uint32_t period_ms)
{
    if ((task == NULL) || (s_task_count >= SCHEDULER_MAX_TASKS))
    {
        return false;
    }

    s_tasks[s_task_count].task = task;
    s_tasks[s_task_count].period_ms = period_ms;
    s_tasks[s_task_count].last_run_ms = HAL_GetTick();
    s_task_count++;

    return true;
}

/* Call this once per main loop iteration. Runs any due task at most once
 * per call; a busy iteration can starve lower-priority tasks. Unsigned
 * wraparound of HAL_GetTick() is handled correctly since both operands
 * are uint32_t. */
void Scheduler_Run(void)
{
    uint32_t now = HAL_GetTick();

    for (uint8_t i = 0; i < s_task_count; i++)
    {
        if ((uint32_t)(now - s_tasks[i].last_run_ms) >= s_tasks[i].period_ms)
        {
            s_tasks[i].last_run_ms = now;
            s_tasks[i].task();
        }
    }
}
