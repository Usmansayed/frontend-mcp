"""Multiplex CDP dev-insight events across collectors without clobbering browser-use handlers."""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

CDP_CONSOLE = "Runtime.consoleAPICalled"
CDP_EXCEPTION = "Runtime.exceptionThrown"
CDP_LOG = "Log.entryAdded"
CDP_RESPONSE = "Network.responseReceived"
CDP_LOADING_FAILED = "Network.loadingFailed"
CDP_LOADING_FINISHED = "Network.loadingFinished"
CDP_REQUEST = "Network.requestWillBeSent"

CDP_METHODS = (
	CDP_CONSOLE,
	CDP_EXCEPTION,
	CDP_LOG,
	CDP_RESPONSE,
	CDP_LOADING_FAILED,
	CDP_LOADING_FINISHED,
	CDP_REQUEST,
)

Handler = Callable[[Any, str | None], None]


class DevInsightsHub:
    """One hub per CDP client; fans out events to active collectors."""

    _by_client: dict[int, DevInsightsHub] = {}

    def __init__(self, client: Any, registry: Any, session_id: str) -> None:
        self._client = client
        self._registry = registry
        self._session_id = session_id
        self._collectors: list[Any] = []
        self._installed = False
        self._saved: dict[str, Handler] = {}
        self._network_enabled = False
        self._network_error: str | None = None

    @classmethod
    async def for_session(cls, session: Any) -> DevInsightsHub:
        cdp_session = await session.get_or_create_cdp_session(target_id=None, focus=True)
        client = cdp_session.cdp_client
        key = id(client)
        hub = cls._by_client.get(key)
        if hub is None:
            hub = cls(client, client._event_registry, cdp_session.session_id)
            cls._by_client[key] = hub
        return hub

    @property
    def network_error(self) -> str | None:
        return self._network_error

    async def ensure_domains(self) -> None:
        await self._client.send.Runtime.enable(session_id=self._session_id)
        try:
            await self._client.send.Log.enable(session_id=self._session_id)
        except Exception as exc:
            logger.debug("Log.enable failed: %s", exc)
        try:
            await self._client.send.Network.enable(session_id=self._session_id)
            self._network_enabled = True
        except Exception as exc:
            self._network_error = str(exc)
            self._network_enabled = False

    def attach(self, collector: Any) -> None:
        if collector not in self._collectors:
            self._collectors.append(collector)
        if not self._installed:
            self._install()

    def detach(self, collector: Any) -> None:
        if collector in self._collectors:
            self._collectors.remove(collector)
        if not self._collectors and self._installed:
            self._restore()
            self._by_client.pop(id(self._client), None)

    def _install(self) -> None:
        for method in CDP_METHODS:
            prev = self._registry._handlers.get(method)
            if prev is not None:
                self._saved[method] = prev

        reg = self._client.register
        reg.Runtime.consoleAPICalled(self._dispatch_console)
        reg.Runtime.exceptionThrown(self._dispatch_exception)
        reg.Log.entryAdded(self._dispatch_log)
        reg.Network.responseReceived(self._dispatch_response)
        reg.Network.loadingFailed(self._dispatch_loading_failed)
        reg.Network.loadingFinished(self._dispatch_loading_finished)
        reg.Network.requestWillBeSent(self._dispatch_request)
        self._installed = True

    def _restore(self) -> None:
        for method in CDP_METHODS:
            saved = self._saved.get(method)
            if saved is not None:
                self._registry.register(method, saved)
            else:
                self._registry.unregister(method)
        self._saved.clear()
        self._installed = False

    def _fanout(self, method: str, params: Any, session_id: str | None) -> None:
        saved = self._saved.get(method)
        if saved is not None:
            try:
                saved(params, session_id)
            except Exception:
                logger.debug("saved CDP handler failed for %s", method, exc_info=True)
        for collector in list(self._collectors):
            try:
                collector._handle_cdp(method, params, session_id)
            except Exception:
                logger.debug("collector handler failed for %s", method, exc_info=True)

    def _dispatch_console(self, params: Any, session_id: str | None = None) -> None:
        self._fanout(CDP_CONSOLE, params, session_id)

    def _dispatch_exception(self, params: Any, session_id: str | None = None) -> None:
        self._fanout(CDP_EXCEPTION, params, session_id)

    def _dispatch_log(self, params: Any, session_id: str | None = None) -> None:
        self._fanout(CDP_LOG, params, session_id)

    def _dispatch_response(self, params: Any, session_id: str | None = None) -> None:
        self._fanout(CDP_RESPONSE, params, session_id)

    def _dispatch_loading_failed(self, params: Any, session_id: str | None = None) -> None:
        self._fanout(CDP_LOADING_FAILED, params, session_id)

    def _dispatch_loading_finished(self, params: Any, session_id: str | None = None) -> None:
        self._fanout(CDP_LOADING_FINISHED, params, session_id)

    def _dispatch_request(self, params: Any, session_id: str | None = None) -> None:
        self._fanout(CDP_REQUEST, params, session_id)
