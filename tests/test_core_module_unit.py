import asyncio
import pytest

from vagents.core.module import AgentModule, agent_action


class ToyAgent(AgentModule):
    @agent_action
    async def greet(self, name: str) -> str:
        await asyncio.sleep(0)
        return f"hello {name}"

    async def forward(self, x: int) -> int:
        await asyncio.sleep(0)
        return x + 1


@pytest.mark.asyncio
async def test_agentmodule_call_and_actions():
    a = ToyAgent()
    # autodiscovered actions
    assert "greet" in a.actions
    assert callable(a.actions["greet"]) is True

    # __call__ schedules forward through executor and returns a Future
    fut = a(1)
    res = await fut
    assert res == 2


def test_agentmodule_register_action_validates():
    a = ToyAgent()
    with pytest.raises(ValueError):
        a.register_action("", lambda: None)
