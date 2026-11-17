from __future__ import annotations

from typing import Any


def resolve_network_telemetry(
    alert_id: str,
    attack_class: str | None,
    source_ip: str | None = None,
    destination_ip: str | None = None,
    source_port: int | None = None,
    destination_port: int | None = None,
    protocol: str | None = None,
    dataset_name: str | None = None,
    capture_source: str | None = None,
) -> dict[str, Any]:
    """
    Resolve network detection telemetry for alerts and incidents.
    Never fabricates fake IP addresses or simulated network indicators.
    Retain known dataset provenance and leave unknown sources explicit.
    """
    valid_source_ip = (
        source_ip.strip()
        if source_ip and isinstance(source_ip, str) and source_ip.strip().lower() not in {"", "none", "null", "undefined"}
        else None
    )
    valid_dest_ip = (
        destination_ip.strip()
        if destination_ip and isinstance(destination_ip, str) and destination_ip.strip().lower() not in {"", "none", "null", "undefined"}
        else None
    )
    valid_protocol = (
        protocol.strip().upper()
        if protocol and isinstance(protocol, str) and protocol.strip().lower() not in {"", "none", "null", "undefined"}
        else None
    )

    return {
        "source_ip": valid_source_ip,
        "destination_ip": valid_dest_ip,
        "source_port": source_port if (isinstance(source_port, int) and source_port > 0) else None,
        "destination_port": destination_port if (isinstance(destination_port, int) and destination_port > 0) else None,
        "protocol": valid_protocol,
        "dataset_name": dataset_name or "Not provided",
        "capture_source": capture_source or "Not provided",
    }
