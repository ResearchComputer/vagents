import asyncio

import pytest

from vagents.core.executor import LMExecutor, get_executor


@pytest.mark.asyncio
async def test_executor_enqueue_and_complete():
    exec = LMExecutor()

    async def job():
        await asyncio.sleep(0.01)
        return 42

    task = asyncio.create_task(job())
    fut = exec.enqueue(task)
    res = await fut
    assert res == 42
    stats = exec.get_stats()
    assert stats["waiting_tasks"] == 0
    assert stats["running_tasks"] == 0


@pytest.mark.asyncio
async def test_executor_handles_exceptions():
    exec = LMExecutor()

    async def bad():
        await asyncio.sleep(0.01)
        raise ValueError("boom")

    task = asyncio.create_task(bad())
    fut = exec.enqueue(task)
    with pytest.raises(ValueError):
        await fut


def test_global_executor_instance():
    a = get_executor()
    b = get_executor()
    assert a is b
