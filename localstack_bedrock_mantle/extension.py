"""Expose Ollama's OpenAI-compatible API through Bedrock Mantle endpoints."""

import logging
import os
from threading import Lock
from typing import TYPE_CHECKING

import requests
from localstack import config
from localstack.extensions.api import Extension, http
from localstack.pro.core import config as pro_config

if TYPE_CHECKING:
    from localstack.pro.core.services.bedrock.backends import Ollama

LOG = logging.getLogger(__name__)


class OllamaProxyHandler(http.ProxyHandler):
    """Ensure models requested through the OpenAI API are available before forwarding."""

    def __init__(self, ollama: "Ollama"):
        super().__init__(forward_base_url=f"http://{ollama.host}:{ollama.port}")
        self.ollama = ollama
        self._pull_lock = Lock()

    def __call__(self, request: http.Request, **kwargs) -> http.Response:
        if request.method == "POST" and request.path.startswith("/v1/"):
            # Werkzeug caches the body, so the proxy can still forward it unchanged.
            payload = request.get_json(silent=True)
            model = payload.get("model") if isinstance(payload, dict) else None
            if isinstance(model, str) and model.strip():
                self._ensure_model(model)
        return super().__call__(request, **kwargs)

    def _ensure_model(self, model: str):
        # Serialize the check and pull so concurrent requests do not download the same
        # model twice. Query disk inventory (/tags), not the loaded models (/ps).
        with self._pull_lock:
            response = requests.get(f"{self.ollama.api_url}/tags", timeout=10)
            try:
                response.raise_for_status()
                installed = {entry["name"] for entry in response.json().get("models", [])}
            finally:
                response.close()

            # Ollama defaults untagged names to :latest (registry hosts may contain ':').
            canonical_model = model if ":" in model.rsplit("/", 1)[-1] else f"{model}:latest"
            if model not in installed and canonical_model not in installed:
                LOG.info("Pulling Ollama model %s for Bedrock Mantle", model)
                self.ollama.pull_model(model_id=model)


class BedrockMantleExtension(Extension):
    """Run Ollama and proxy Bedrock Mantle OpenAI API requests to it."""

    name = "bedrock-mantle"

    hostname_prefix = "bedrock-mantle."
    """Used for serving through a host rule."""

    region = "us-east-1"
    """Default region segment used in the Mantle hostname."""

    def __init__(self):
        self.ollama: "Ollama | None" = None

    @property
    def lambda_base_url(self) -> str:
        return f"http://{self.hostname_prefix}{self.region}.{config.LOCALSTACK_HOST}/v1"

    @property
    def lambda_docker_flag(self) -> str:
        return f"-e AWS_BEDROCK_BASE_URL={self.lambda_base_url}"

    def on_extension_load(self):
        # TODO: logging should be configured automatically for extensions
        if config.DEBUG:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.getLogger("localstack_bedrock_mantle").setLevel(level=level)

        self._configure_lambda_docker_flags()

    def on_platform_start(self):
        # Import lazily so the extension can be discovered before LocalStack Pro modules are loaded.
        from localstack.pro.core.services.bedrock.backends import Ollama

        self.ollama = Ollama()
        LOG.info("starting Ollama for the Bedrock Mantle emulator")
        self.ollama.start()

    def update_gateway_routes(self, router: http.Router[http.RouteHandler]):
        if not self.ollama:
            raise RuntimeError("Ollama must be started before registering Bedrock Mantle routes")

        # Ollama exposes its OpenAI-compatible API at /v1. Proxy from the server root so
        # requests such as /v1/chat/completions retain their complete path.
        endpoint = OllamaProxyHandler(self.ollama)

        # hostname aliases, e.g. bedrock-mantle.<region>.<host>. the wildcard converters make
        # the emulator reachable for any region and any host (e.g. localhost.localstack.cloud,
        # api.aws, ...) without enumerating hosts.
        hostname = f"{self.hostname_prefix}<region>.<host>"
        router.add("/", host=hostname, endpoint=endpoint)
        router.add("/<path:path>", host=hostname, endpoint=endpoint)

    def on_platform_ready(self):
        hostname_edge_url = f"{config.LOCALSTACK_HOST}"
        url = f"http://{self.hostname_prefix}{hostname_edge_url}/v1"
        LOG.info("serving bedrock mantle emulator on host: %s", url)

    def on_platform_shutdown(self):
        if self.ollama:
            self.ollama.shutdown()
            self.ollama = None

    def _configure_lambda_docker_flags(self):
        """Make the Mantle endpoint available as AWS_BEDROCK_BASE_URL in Lambda containers."""
        flags = pro_config.LAMBDA_DOCKER_FLAGS
        if self.lambda_docker_flag not in flags:
            flags = " ".join(filter(None, (flags, self.lambda_docker_flag)))

        # LocalStack reads the module setting when creating Lambda containers; retain the
        # environment value too for components that consult it after extension loading.
        pro_config.LAMBDA_DOCKER_FLAGS = flags
        os.environ["LAMBDA_DOCKER_FLAGS"] = flags

        LOG.info("updated LAMBDA_DOCKER_FLAGS: %s", pro_config.LAMBDA_DOCKER_FLAGS)
