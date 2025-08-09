from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .model import LM


def agent_action(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark an instance method as an Agent action.

    Example:
        class MyAgent(AgentModule):
            @agent_action
            async def step(self, x: int) -> int: ...
    """

    setattr(func, "__agent_action__", True)
    return func


class AgentModule:
    """Thin wrapper base to build PyTorch-like async modules around an LM.

    - Subclasses implement `async def forward(...)`.
    - Optionally provide an `LM` instance at construction, accessible via `self.lm`.
    - Mark action methods with `@agent_action` (registry is lightweight for convenience).
    - Call the instance directly to schedule `forward` using the internal executor.
    """

    def __init__(self, lm: Optional["LM"] = None) -> None:
        self.lm: Optional["LM"] = lm
        self._actions: Dict[str, Callable[..., Any]] = {}
        self._autodiscover_actions()

    # --- Public API -----------------------------------------------------
    @property
    def actions(self) -> Dict[str, Callable[..., Any]]:
        return self._actions

    def register_action(self, name: str, fn: Callable[..., Any]) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("Action name must be a non-empty string")
        self._actions[name] = fn

    async def forward(
        self, *args: Any, **kwargs: Any
    ) -> Any:  # pragma: no cover - to be overridden
        raise NotImplementedError("Subclasses must implement async forward(...)")

    def __call__(self, *args: Any, **kwargs: Any) -> asyncio.Future:
        """Schedule `forward` and return a Future.

        Usage:
            result_future = my_agent(input=...)
            result = await result_future
        """
        # Local import to avoid any potential import cycles at module import time
        from vagents.core.executor import get_executor

        task = asyncio.create_task(self.forward(*args, **kwargs))
        return get_executor().enqueue(task)

    # --- Internal helpers -----------------------------------------------
    def _autodiscover_actions(self) -> None:
        # Register methods decorated with @agent_action
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            attr_obj = getattr(self, attr_name, None)
            if not callable(attr_obj):
                continue

            # For bound methods, the underlying function is at __func__
            func_obj = getattr(attr_obj, "__func__", attr_obj)
            if getattr(func_obj, "__agent_action__", False):
                self._actions[attr_name] = attr_obj

    # --- Convenience wrappers around LM ---------------------------------
    def lm_call(self, *args: Any, **kwargs: Any) -> asyncio.Future:
        """Proxy to `self.lm(*args, **kwargs)`.

        Raises if no LM is attached.
        """
        if self.lm is None:
            raise RuntimeError(
                "No LM attached to this AgentModule. Pass an LM to the constructor."
            )
        return self.lm(*args, **kwargs)

    async def lm_invoke(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Proxy to `await self.lm.invoke(func, *args, **kwargs)`.

        Raises if no LM is attached.
        """
        if self.lm is None:
            raise RuntimeError(
                "No LM attached to this AgentModule. Pass an LM to the constructor."
            )
        return await self.lm.invoke(func, *args, **kwargs)
