from abc import ABC, abstractmethod


class BaseTool(ABC):

    name: str
    description: str

    @abstractmethod
    async def execute(self, **args):
        pass