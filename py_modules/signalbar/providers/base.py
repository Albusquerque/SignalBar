"""Provider protocol documentation."""

from typing import Protocol

from signalbar.models import ProviderOutput


class Provider(Protocol):
    name: str

    def output(self, *args, **kwargs) -> ProviderOutput:
        ...

