from signalbar.models import ProviderOutput


class IdleProvider:
    name = "idle"

    def output(self):
        # Vanilla is deliberately the only idle behavior.
        return ProviderOutput(self.name, None, "idle is Vanilla")
