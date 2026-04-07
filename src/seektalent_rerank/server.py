from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from pydantic import ValidationError

from seektalent_rerank.config import RerankSettings
from seektalent_rerank.engine import ModelNotReadyError, RerankEngine
from seektalent_rerank.models import RerankRequest


def create_server(host: str, port: int, engine: RerankEngine) -> ThreadingHTTPServer:
    class RerankApiHandler(BaseHTTPRequestHandler):
        server_version = "SeekTalentRerankApi/0.1"

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/healthz":
                self._send_not_found()
                return
            self._send_json(HTTPStatus.OK, engine.health().model_dump(mode="json"))

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/rerank":
                self._send_not_found()
                return
            try:
                payload = self._read_json()
                request = RerankRequest.model_validate(payload)
                response = engine.rerank_request(request)
            except json.JSONDecodeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON body: {exc.msg}"})
                return
            except ValidationError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": exc.errors()})
                return
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except ModelNotReadyError as exc:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
                return
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc) or "Rerank failed."})
                return
            self._send_json(HTTPStatus.OK, response.model_dump(mode="json"))

        def _read_json(self) -> dict[str, object]:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("Missing Content-Length header.")
            body = self.rfile.read(int(raw_length))
            return json.loads(body.decode("utf-8"))

        def _send_json(self, status: HTTPStatus, payload: object) -> None:
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(encoded)

        def _send_not_found(self) -> None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    server = ThreadingHTTPServer((host, port), RerankApiHandler)
    server.daemon_threads = True
    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local API server for Qwen3 reranking on Apple Silicon.")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--model-id")
    parser.add_argument("--batch-size", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = RerankSettings(_env_file=args.env_file).with_overrides(
            host=args.host,
            port=args.port,
            model_id=args.model_id,
            batch_size=args.batch_size,
        )
        engine = RerankEngine.load(
            model_id=settings.model_id,
            batch_size=settings.batch_size,
            max_length=settings.max_length,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to start rerank service: {exc}", file=sys.stderr)
        return 1

    server = create_server(settings.host, settings.port, engine)
    print(f"SeekTalent rerank API listening on http://{settings.host}:{settings.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
