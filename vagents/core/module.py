from abc import abstractmethod
from dataclasses import dataclass

@dataclass
class VModuleConfig:
    enable_async: bool = False

class VModule:
    def __init__(self, config: VModuleConfig):
        super().__init__()
        self.config = config
        self._post_init()

    def _post_init(self):
        if self.config.enable_async:
            pass

    @abstractmethod
    def forward(self, *args, **kwargs):
        ...