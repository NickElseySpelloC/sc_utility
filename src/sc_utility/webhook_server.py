
import threading
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

from sc_utility.sc_logging import SCLogger

DEFAULT_WEBHOOK_PATH = "/shelly/webhook"


class _ShellyWebhookHandler(BaseHTTPRequestHandler):
    # `server` attribute will be a ThreadingHTTPServer with `.controller` and `.config_path` attributes attached.

    @property
    def app_wake_event(self) -> threading.Event:
        return getattr(self.server, "app_wake_event", None)  # pyright: ignore[reportReturnType]

    @property
    def logger(self) -> SCLogger:
        return getattr(self.server, "logger", None)  # pyright: ignore[reportReturnType]

    def _ok(self, body: bytes = b"OK"):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        # Validate path like do_POST
        try:
            expected_path = getattr(self.server, "webhook_path", DEFAULT_WEBHOOK_PATH)
        except AttributeError:
            expected_path = DEFAULT_WEBHOOK_PATH

        # Split path and query
        path_only = self.path.split("?")[0]
        query_string = self.path[len(path_only):].lstrip("?") if "?" in self.path else ""

        if expected_path and path_only != expected_path:
            self.send_error(404, "Not Found")
            return

        args = {}
        if query_string:
            args = parse_qs(query_string)
            self.logger.log_message(f"Received webhook GET request {self.path}. Arguments: {args}.", "debug")
        else:
            self.logger.log_message(f"Received webhook GET request {self.path} with no arguments.", "debug")

        # Report the event and wake the controller's run loop immediately
        try:
            controller = getattr(self.server, "controller", None)
            if controller is not None:
                # Add self.path as the first key/value pair to args
                args["path"] = self.path  # pyright: ignore[reportArgumentType]
                controller._push_webhook_event(args)  # noqa: SLF001

            wake_event = getattr(self.server, "app_wake_event", None)
            if wake_event is not None:
                wake_event.set()
        except AttributeError:
            pass

        self._ok(b"LightingController webhook up")
