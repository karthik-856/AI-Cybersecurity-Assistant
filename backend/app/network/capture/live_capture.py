from __future__ import annotations
from backend.app.core.time import utc_now

import threading
from datetime import datetime
from typing import Callable

from scapy.all import IP, IPv6, TCP, UDP, sniff


class LiveCaptureService:
    """
    Captures real network packets from the host machine.

    The service converts packets into lightweight network events
    that can later be persisted to PostgreSQL and passed into
    the ZUKA detection pipeline.

    Detection is intentionally NOT performed here.
    """

    def __init__(
        self,
        event_callback: Callable[[dict], None],
    ):
        self.event_callback = event_callback

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self.running = False
        self.interface: str | None = None

        self.packet_count = 0

    def start(
        self,
        interface: str | None = None,
    ) -> None:
        if self.running:
            return

        self.interface = interface
        self.packet_count = 0
        self._stop_event.clear()
        self.running = True

        self._thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
        )

        self._thread.start()

    def stop(self) -> None:
        if not self.running:
            return

        self._stop_event.set()
        self.running = False

    def _capture_loop(self) -> None:
        try:
            sniff(
                iface=self.interface,
                prn=self._process_packet,
                store=False,
                stop_filter=lambda packet: self._stop_event.is_set(),
            )
        except Exception as exc:
            self.running = False

            error_event = {
                "event_time": utc_now(),
                "capture_source": "live",
                "event_type": "capture_error",
                "description": str(exc),
                "extra_metadata": {
                    "interface": self.interface,
                },
            }

            self.event_callback(error_event)

    def _process_packet(self, packet) -> None:
        if self._stop_event.is_set():
            return

        event = self._packet_to_event(packet)

        if event is None:
            return

        self.packet_count += 1

        self.event_callback(event)

    def _packet_to_event(
        self,
        packet,
    ) -> dict | None:

        source_ip = None
        destination_ip = None

        if IP in packet:
            source_ip = packet[IP].src
            destination_ip = packet[IP].dst

        elif IPv6 in packet:
            source_ip = packet[IPv6].src
            destination_ip = packet[IPv6].dst

        else:
            return None

        protocol = "OTHER"
        source_port = None
        destination_port = None

        if TCP in packet:
            protocol = "TCP"
            source_port = int(packet[TCP].sport)
            destination_port = int(packet[TCP].dport)

        elif UDP in packet:
            protocol = "UDP"
            source_port = int(packet[UDP].sport)
            destination_port = int(packet[UDP].dport)

        packet_length = len(packet)

        return {
            "event_time": utc_now(),

            "source_ip": source_ip,
            "destination_ip": destination_ip,

            "source_port": source_port,
            "destination_port": destination_port,

            "protocol": protocol,

            "direction": self._determine_direction(
                source_ip,
                destination_ip,
            ),

            "packets": 1,
            "bytes_count": packet_length,

            "flow_duration_ms": 0,

            "interface_name": self.interface,

            "capture_source": "live",
            "event_type": "network_packet",

            "description": (
                f"{protocol} traffic "
                f"{source_ip}:{source_port or '-'} → "
                f"{destination_ip}:{destination_port or '-'}"
            ),

            "extra_metadata": {
                "packet_length": packet_length,
                "capture_mode": "live",
            },
        }

    @staticmethod
    def _determine_direction(
        source_ip: str,
        destination_ip: str,
    ) -> str:

        source_private = (
            source_ip.startswith("10.")
            or source_ip.startswith("192.168.")
            or source_ip.startswith("172.")
        )

        destination_private = (
            destination_ip.startswith("10.")
            or destination_ip.startswith("192.168.")
            or destination_ip.startswith("172.")
        )

        if source_private and not destination_private:
            return "OUTBOUND"

        if not source_private and destination_private:
            return "INBOUND"

        return "INTERNAL"

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "interface": self.interface,
            "packet_count": self.packet_count,
        }