
from dataclasses import dataclass, field

@dataclass
class Dataclass:
    """
    Test dataclasses

    See [content][(c).] for an example attribute.

    See [method][(c).]
    """
    content: str = "hi"
    """some content"""

    duration: float = field(default_factory=lambda: 0.0)
    """
    example: [`content`][(c).]
    """

    def method(self) -> str:
        """Example method."""
