"""
Task Manager Abstraction.
Executes background tasks asynchronously using an in-process ThreadPoolExecutor.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)


class TaskStatus(BaseModel):
    task_id: str
    status: str  # PENDING | PROCESSING | SUCCESS | FAILURE
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskManager:
    _thread_pool = None
    _tasks: Dict[str, TaskStatus] = {}

    @classmethod
    def get_thread_pool(cls):
        if cls._thread_pool is None:
            settings = get_settings()
            cls._thread_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=settings.MAX_WORKERS,
                thread_name_prefix="bg-worker"
            )
        return cls._thread_pool

    @classmethod
    async def enqueue(cls, task_fn: Callable, *args, **kwargs) -> str:
        """
        Enqueues a task for background processing.
        Returns a unique task_id.
        """
        import uuid
        task_id = str(uuid.uuid4())

        cls._tasks[task_id] = TaskStatus(task_id=task_id, status="PENDING")
        
        loop = asyncio.get_running_loop()
        
        def wrapper():
            cls._tasks[task_id].status = "PROCESSING"
            try:
                # If the function is a coroutine, we run it in a new event loop inside the thread
                if asyncio.iscoroutinefunction(task_fn):
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    res = new_loop.run_until_complete(task_fn(*args, **kwargs))
                    new_loop.close()
                else:
                    res = task_fn(*args, **kwargs)
                cls._tasks[task_id].status = "SUCCESS"
                cls._tasks[task_id].result = res
            except Exception as e:
                logger.error(f"Background task {task_id} failed: {e}")
                cls._tasks[task_id].status = "FAILURE"
                cls._tasks[task_id].error = str(e)

        pool = cls.get_thread_pool()
        loop.run_in_executor(pool, wrapper)
        
        return task_id

    @classmethod
    async def get_task_status(cls, task_id: str) -> TaskStatus:
        """Retrieves current status of a background task."""
        return cls._tasks.get(task_id, TaskStatus(task_id=task_id, status="PENDING"))
