#!/usr/bin/env python3
"""
Interval-Based Scheduler for 24/7 Crypto Trading

Unlike time-based scheduler (stocks at 9:30am, 4pm, etc.), this scheduler
triggers tasks based on intervals (every 2 hours, every 15 minutes, etc.).
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IntervalTask:
    """Represents a task that runs at regular intervals."""
    name: str
    interval_minutes: int
    callback: Callable
    last_run: Optional[datetime] = None
    run_immediately: bool = False  # Run on first check vs wait for interval
    enabled: bool = True


class IntervalScheduler:
    """
    Scheduler that triggers tasks based on time intervals.

    Perfect for 24/7 crypto trading where tasks should run every N minutes/hours
    instead of at specific times like stock market hours.

    Example:
        scheduler = IntervalScheduler()
        scheduler.schedule_interval(
            "crypto_screening",
            interval_minutes=120,  # Every 2 hours
            callback=screen_crypto,
            run_immediately=True
        )
    """

    def __init__(self):
        self.tasks: Dict[str, IntervalTask] = {}

    def schedule_interval(
        self,
        name: str,
        interval_minutes: int,
        callback: Callable,
        run_immediately: bool = False
    ):
        """
        Schedule a task to run at regular intervals.

        Args:
            name: Unique task identifier
            interval_minutes: How often to run (in minutes)
            callback: Function to execute when interval triggers
            run_immediately: If True, run on first check. If False, wait for interval.
        """
        task = IntervalTask(
            name=name,
            interval_minutes=interval_minutes,
            callback=callback,
            run_immediately=run_immediately
        )

        self.tasks[name] = task
        logger.info(
            f"Scheduled interval task '{name}': every {interval_minutes} min "
            f"(immediate: {run_immediately})"
        )

    def schedule_hourly(self, name: str, hours: int, callback: Callable, run_immediately: bool = False):
        """Convenience method to schedule task every N hours."""
        self.schedule_interval(name, interval_minutes=hours * 60, callback=callback, run_immediately=run_immediately)

    def check_triggers(self) -> List[str]:
        """
        Check all tasks and execute any that are due.

        Returns:
            List of task names that were triggered
        """
        now = datetime.now()
        triggered = []

        for task in self.tasks.values():
            if not task.enabled:
                continue

            should_run = False

            # First run handling
            if task.last_run is None:
                should_run = task.run_immediately
                if not should_run:
                    # Don't run immediately, but mark as if we just ran
                    task.last_run = now
                    logger.debug(f"Task '{task.name}' initialized, next run in {task.interval_minutes} min")
                    continue
            else:
                # Check if interval has passed
                elapsed = now - task.last_run
                interval_duration = timedelta(minutes=task.interval_minutes)

                if elapsed >= interval_duration:
                    should_run = True

            if should_run:
                try:
                    logger.info(f"Triggering interval task: {task.name}")
                    task.callback()
                    task.last_run = now
                    triggered.append(task.name)
                except Exception as e:
                    logger.error(f"Error executing task '{task.name}': {e}")
                    # Still update last_run to prevent retry loops
                    task.last_run = now

        return triggered

    def enable_task(self, name: str):
        """Enable a disabled task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Enabled task: {name}")

    def disable_task(self, name: str):
        """Disable a task without removing it."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled task: {name}")

    def remove_task(self, name: str):
        """Remove a task from the scheduler."""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed task: {name}")

    def get_next_trigger(self) -> Optional[Dict[str, any]]:
        """
        Get information about the next task that will trigger.

        Returns:
            Dict with task name and time until next trigger, or None if no tasks
        """
        if not self.tasks:
            return None

        now = datetime.now()
        next_task = None
        min_wait = None

        for task in self.tasks.values():
            if not task.enabled:
                continue

            if task.last_run is None:
                if task.run_immediately:
                    # Will run on next check
                    return {
                        "task": task.name,
                        "seconds_until": 0,
                        "next_run": now
                    }
                else:
                    # Will run after first interval
                    wait_seconds = task.interval_minutes * 60
            else:
                elapsed = (now - task.last_run).total_seconds()
                interval_seconds = task.interval_minutes * 60
                wait_seconds = max(0, interval_seconds - elapsed)

            if min_wait is None or wait_seconds < min_wait:
                min_wait = wait_seconds
                next_task = task.name

        if next_task:
            return {
                "task": next_task,
                "seconds_until": int(min_wait),
                "next_run": now + timedelta(seconds=min_wait)
            }

        return None

    def get_status(self) -> List[Dict[str, any]]:
        """
        Get status of all scheduled tasks.

        Returns:
            List of task info dicts
        """
        now = datetime.now()
        status = []

        for task in self.tasks.values():
            task_info = {
                "name": task.name,
                "interval_minutes": task.interval_minutes,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None
            }

            if task.last_run:
                elapsed = (now - task.last_run).total_seconds()
                remaining = (task.interval_minutes * 60) - elapsed
                task_info["next_run_seconds"] = max(0, int(remaining))
            else:
                if task.run_immediately:
                    task_info["next_run_seconds"] = 0
                else:
                    task_info["next_run_seconds"] = task.interval_minutes * 60

            status.append(task_info)

        return sorted(status, key=lambda x: x["next_run_seconds"])
