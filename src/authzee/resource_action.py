
from enum import Enum


class ResourceAction(Enum):
    """Base class for resource action enums

    """

    @staticmethod
    def _generate_next_value_(
        name: str, 
        start: int, 
        count: int, 
        last_values: list
    ) -> str:
        return name

