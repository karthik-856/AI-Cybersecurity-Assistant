from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.network_event import NetworkEvent
from backend.app.models.user import User

from backend.app.schemas.network import (
    
    NetworkEventCreate,
    NetworkEventResponse,
    NetworkEventStats,
)
from backend.app.security.dependencies import (
    get_current_user,
    require_role,
)


router = APIRouter(
    prefix="/api/network",
    tags=["Network Monitor"],
)


@router.get(
    "/events",
    response_model=list[NetworkEventResponse],
)
def get_network_events(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(NetworkEvent)
        .order_by(NetworkEvent.event_time.desc())
        .limit(limit)
    )

    events = db.execute(statement).scalars().all()

    return events


@router.post(
    "/events",
    response_model=NetworkEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_network_event(
    event: NetworkEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role("ADMIN", "SOC_ANALYST")
    ),
):
    network_event = NetworkEvent(
        event_time=event.event_time,
        source_ip=event.source_ip,
        destination_ip=event.destination_ip,
        source_port=event.source_port,
        destination_port=event.destination_port,
        protocol=event.protocol,
        direction=event.direction,
        packets=event.packets,
        bytes_count=event.bytes_count,
        flow_duration_ms=event.flow_duration_ms,
        interface_name=event.interface_name,
        capture_source=event.capture_source,
        event_type=event.event_type,
        description=event.description,
        extra_metadata=event.extra_metadata,
    )

    db.add(network_event)
    db.commit()
    db.refresh(network_event)

    return network_event


@router.get(
    "/stats",
    response_model=NetworkEventStats,
)
def get_network_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_events = db.scalar(
        select(func.count(NetworkEvent.id))
    ) or 0

    unique_source_ips = db.scalar(
        select(
            func.count(
                func.distinct(NetworkEvent.source_ip)
            )
        )
    ) or 0

    unique_destination_ips = db.scalar(
        select(
            func.count(
                func.distinct(NetworkEvent.destination_ip)
            )
        )
    ) or 0

    tcp_events = db.scalar(
        select(func.count(NetworkEvent.id)).where(
            func.lower(NetworkEvent.protocol) == "tcp"
        )
    ) or 0

    udp_events = db.scalar(
        select(func.count(NetworkEvent.id)).where(
            func.lower(NetworkEvent.protocol) == "udp"
        )
    ) or 0

    other_protocol_events = (
        total_events
        - tcp_events
        - udp_events
    )

    return NetworkEventStats(
        total_events=total_events,
        unique_source_ips=unique_source_ips,
        unique_destination_ips=unique_destination_ips,
        tcp_events=tcp_events,
        udp_events=udp_events,
        other_protocol_events=other_protocol_events,
    )






