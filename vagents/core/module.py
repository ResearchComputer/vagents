from abc import abstractmethod
from dataclasses import dataclass
from dask.distributed import Client
from dask.distributed import Future


@dataclass
class VModuleConfig:
    enable_async: bool = False

class VModule:
    def __init__(self, config: VModuleConfig):
        super().__init__()
        self.config = config
        if self.config.enable_async:
            self.dask_client = Client(timeout=60)
        self._post_init()

    def _post_init(self):
        if self.config.enable_async:
            pass

    @abstractmethod
    def forward(self, *args, **kwargs):
        ...

    def __call__(self, *args, **kwargs):
        result = self.forward(*args, **kwargs)
        if isinstance(result, Future):
            result = result.result()
        return result

    def close(self):
        if self.config.enable_async:
            self.dask_client.close()
