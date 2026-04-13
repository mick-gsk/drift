"""Plugin host with intentional broad exception catching.

The host MUST catch all exceptions from plugin.execute() to prevent
a single misbehaving plugin from crashing the entire runtime.
Narrowing the exception type is explicitly harmful here.
"""

import logging

logger = logging.getLogger(__name__)


class Plugin:
    """Base class for plugins."""
    def execute(self, context: dict) -> dict:
        raise NotImplementedError


class PluginHost:
    """Executes plugins safely, isolating failures."""

    def __init__(self) -> None:
        self.plugins: list[Plugin] = []
        self.results: list[dict] = []
        self.errors: list[dict] = []

    def register(self, plugin: Plugin) -> None:
        self.plugins.append(plugin)

    def run_all(self, context: dict) -> list[dict]:
        """Run all plugins, catching ANY exception to prevent cascade failures."""
        self.results.clear()
        self.errors.clear()

        for plugin in self.plugins:
            try:
                # INTENTIONAL: broad except to isolate plugin failures
                result = plugin.execute(context)
                self.results.append(result)
            except Exception as exc:  # noqa: BLE001
                logger.error("Plugin %s failed: %s", type(plugin).__name__, exc)
                self.errors.append({
                    "plugin": type(plugin).__name__,
                    "error": str(exc),
                    "type": type(exc).__name__,
                })

        return self.results


class MetricsPlugin(Plugin):
    def execute(self, context: dict) -> dict:
        return {"metrics": len(context)}


class AuditPlugin(Plugin):
    def execute(self, context: dict) -> dict:
        return {"audit_log": list(context.keys())}
