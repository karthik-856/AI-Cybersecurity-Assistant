from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommonFeature:
    name: str
    description: str
    unit: str


COMMON_FEATURES = [
    CommonFeature(
        "duration_sec",
        "Flow duration",
        "seconds",
    ),
    CommonFeature(
        "src_packets",
        "Packets in the forward/source direction",
        "packets",
    ),
    CommonFeature(
        "dst_packets",
        "Packets in the backward/destination direction",
        "packets",
    ),
    CommonFeature(
        "src_bytes",
        "Bytes in the forward/source direction",
        "bytes",
    ),
    CommonFeature(
        "dst_bytes",
        "Bytes in the backward/destination direction",
        "bytes",
    ),
    CommonFeature(
        "flow_packet_rate",
        "Total packets per second",
        "packets/sec",
    ),
    CommonFeature(
        "src_packet_rate",
        "Forward/source packets per second",
        "packets/sec",
    ),
    CommonFeature(
        "dst_packet_rate",
        "Backward/destination packets per second",
        "packets/sec",
    ),
    CommonFeature(
        "src_byte_rate",
        "Forward/source bytes per second",
        "bytes/sec",
    ),
    CommonFeature(
        "dst_byte_rate",
        "Backward/destination bytes per second",
        "bytes/sec",
    ),
    CommonFeature(
        "src_packet_size_mean",
        "Mean forward/source packet size",
        "bytes",
    ),
    CommonFeature(
        "dst_packet_size_mean",
        "Mean backward/destination packet size",
        "bytes",
    ),
    CommonFeature(
        "src_iat_mean_sec",
        "Mean source-direction inter-arrival time",
        "seconds",
    ),
    CommonFeature(
        "dst_iat_mean_sec",
        "Mean destination-direction inter-arrival time",
        "seconds",
    ),
]


CIC_MAPPING = {
    "duration_sec": {
        "source": "Flow Duration",
        "transform": "microseconds_to_seconds",
    },
    "src_packets": {
        "source": "Total Fwd Packets",
        "transform": "identity",
    },
    "dst_packets": {
        "source": "Total Backward Packets",
        "transform": "identity",
    },
    "src_bytes": {
        "source": "Total Length of Fwd Packets",
        "transform": "identity",
    },
    "dst_bytes": {
        "source": "Total Length of Bwd Packets",
        "transform": "identity",
    },
    "flow_packet_rate": {
        "source": "Flow Packets/s",
        "transform": "identity",
    },
    "src_packet_rate": {
        "source": "Fwd Packets/s",
        "transform": "identity",
    },
    "dst_packet_rate": {
        "source": "Bwd Packets/s",
        "transform": "identity",
    },
    "src_byte_rate": {
        "source": None,
        "transform": "derive_bytes_over_duration",
    },
    "dst_byte_rate": {
        "source": None,
        "transform": "derive_bytes_over_duration",
    },
    "src_packet_size_mean": {
        "source": "Fwd Packet Length Mean",
        "transform": "identity",
    },
    "dst_packet_size_mean": {
        "source": "Bwd Packet Length Mean",
        "transform": "identity",
    },
    "src_iat_mean_sec": {
        "source": "Fwd IAT Mean",
        "transform": "microseconds_to_seconds",
    },
    "dst_iat_mean_sec": {
        "source": "Bwd IAT Mean",
        "transform": "microseconds_to_seconds",
    },
}


UNSW_MAPPING = {
    "duration_sec": {
        "source": "dur",
        "transform": "identity",
    },
    "src_packets": {
        "source": "spkts",
        "transform": "identity",
    },
    "dst_packets": {
        "source": "dpkts",
        "transform": "identity",
    },
    "src_bytes": {
        "source": "sbytes",
        "transform": "identity",
    },
    "dst_bytes": {
        "source": "dbytes",
        "transform": "identity",
    },
    "flow_packet_rate": {
        "source": "rate",
        "transform": "identity",
    },
    "src_packet_rate": {
        "source": None,
        "transform": "derive_packets_over_duration",
    },
    "dst_packet_rate": {
        "source": None,
        "transform": "derive_packets_over_duration",
    },
    "src_byte_rate": {
        "source": "sload",
        "transform": "identity",
    },
    "dst_byte_rate": {
        "source": "dload",
        "transform": "identity",
    },
    "src_packet_size_mean": {
        "source": "smean",
        "transform": "identity",
    },
    "dst_packet_size_mean": {
        "source": "dmean",
        "transform": "identity",
    },
    "src_iat_mean_sec": {
        "source": "sinpkt",
        "transform": "identity",
    },
    "dst_iat_mean_sec": {
        "source": "dinpkt",
        "transform": "identity",
    },
}


ZUKA_LABEL_COLUMNS = [
    "zuka_attack_class",
    "original_attack_category",
    "label",
    "dataset_name",
    "dataset_split",
]