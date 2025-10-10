from __future__ import annotations

import importlib
import socket
import time
from collections.abc import Iterator

import httpx
import pytest

from hephaestus.telemetry import metrics


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(autouse=True)
def reset_metrics() -> Iterator[None]:
    importlib.reload(metrics)
    try:
        yield
    finally:
        metrics.shutdown_prometheus_exporter()


def test_prometheus_endpoint_exposes_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    port = _find_free_port()
    monkeypatch.setenv("HEPHAESTUS_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("HEPHAESTUS_PROMETHEUS_HOST", "127.0.0.1")
    monkeypatch.setenv("HEPHAESTUS_PROMETHEUS_PORT", str(port))

    importlib.reload(metrics)

    metrics.record_counter(
        "hephaestus.test.counter",
        value=3,
        attributes={"plugin": "example", "result": "success"},
    )
    metrics.record_histogram(
        "hephaestus.test.histogram",
        value=1.5,
        attributes={"plugin": "example"},
    )
    metrics.record_gauge(
        "hephaestus.test.gauge",
        value=7.0,
        attributes={"plugin": "example"},
    )

    endpoint = metrics.get_prometheus_endpoint()
    assert endpoint is not None
    host, bound_port = endpoint
    assert bound_port == port

    # Poll until the server responds since startup is asynchronous.
    for _ in range(20):
        try:
            response = httpx.get(f"http://{host}:{bound_port}/metrics", timeout=0.5)
        except (httpx.NetworkError, httpx.TimeoutException):
            time.sleep(0.1)
            continue
        break
    else:  # pragma: no cover - defensive branch for unexpected failures
        pytest.fail("Prometheus endpoint did not respond in time")

    assert response.status_code == 200
    body = response.text
    assert "hephaestus_test_counter_total" in body
    assert "hephaestus_test_histogram_bucket" in body
    assert "hephaestus_test_gauge" in body
