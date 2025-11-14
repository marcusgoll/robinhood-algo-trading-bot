#!/usr/bin/env python3
"""
Time-based Task Scheduler

Schedules trading workflows based on market hours and time triggers.
"""

from datetime import datetime, time
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Scheduled task definition"""
    name: str
    trigger_time: time
    callback: Callable
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_once_per_day: bool = True


class TradingScheduler:
    """
    Time-based scheduler for trading workflows.

    Triggers workflows at specific market times:
    - 6:30am EST: Pre-market screening
    - 9:30am EST: Market open execution
    - 10:00am, 11:00am, 2:00pm EST: Intraday monitoring
    - 4:00pm EST: End-of-day review
    - Friday 4:00pm EST: Weekly review
    """

    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.enabled = True

    def schedule(self, name: str, trigger_time: time, callback: Callable, run_once_per_day: bool = True):
        """Schedule a task to run at specific time."""
        task = ScheduledTask(
            name=name,
            trigger_time=trigger_time,
            callback=callback,
            run_once_per_day=run_once_per_day
        )
        self.tasks.append(task)
        logger.info(f"Scheduled task '{name}' at {trigger_time}")

    def check_triggers(self) -> List[str]:
        """Check if any tasks should be triggered. Returns list of triggered task names."""
        if not self.enabled:
            return []

        now = datetime.now()
        current_time = now.time()
        triggered = []

        for task in self.tasks:
            if not task.enabled:
                continue

            # Check if current time matches trigger time (within 1 minute)
            if self._time_matches(current_time, task.trigger_time):
                # Check if already run today (for daily tasks)
                if task.run_once_per_day and task.last_run:
                    if task.last_run.date() == now.date():
                        continue  # Already run today

                # For tasks that can run multiple times per day, add 5-minute cooldown
                # to prevent repeated triggers during the 1-minute tolerance window
                if not task.run_once_per_day and task.last_run:
                    minutes_since_last_run = (now - task.last_run).total_seconds() / 60
                    if minutes_since_last_run < 5:
                        continue  # Cooldown period

                # Execute task
                try:
                    logger.info(f"Triggering task: {task.name}")
                    task.callback()
                    task.last_run = now
                    triggered.append(task.name)
                except Exception as e:
                    logger.error(f"Error executing task {task.name}: {e}")

        return triggered

    def _time_matches(self, current: time, trigger: time, tolerance_minutes: int = 1) -> bool:
        """Check if current time matches trigger time within tolerance."""
        current_minutes = current.hour * 60 + current.minute
        trigger_minutes = trigger.hour * 60 + trigger.minute
        return abs(current_minutes - trigger_minutes) <= tolerance_minutes

    def enable_task(self, name: str):
        """Enable a scheduled task."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = True
                logger.info(f"Enabled task: {name}")
                return
        logger.warning(f"Task not found: {name}")

    def disable_task(self, name: str):
        """Disable a scheduled task."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = False
                logger.info(f"Disabled task: {name}")
                return
        logger.warning(f"Task not found: {name}")

    def get_next_trigger(self) -> Optional[tuple[str, time]]:
        """Get next task that will trigger."""
        now = datetime.now().time()
        upcoming = []

        for task in self.tasks:
            if not task.enabled:
                continue
            if task.trigger_time > now:
                upcoming.append((task.name, task.trigger_time))

        if upcoming:
            upcoming.sort(key=lambda x: x[1])
            return upcoming[0]

        return None
