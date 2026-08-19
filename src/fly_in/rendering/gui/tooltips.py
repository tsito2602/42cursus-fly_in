"""Word the panels shown while the pointer rests on a shape."""

from fly_in.models import Connection, Zone, ZoneRole


def zone_details(zone: Zone) -> str:
    """Return the lines describing a zone on its tooltip."""

    capacity = "unlimited" if zone.capacity is None else zone.capacity
    lines = [
        f"name: {zone.name}",
        f"type: {zone.zone_type.value}",
        f"capacity: {capacity}",
        f"position: ({zone.x}, {zone.y})",
    ]

    if zone.zone_role is not ZoneRole.HUB:
        lines.insert(1, f"role: {zone.zone_role.value}")

    if zone.color is not None:
        lines.append(f"color: {zone.color}")

    return "\n".join(lines)


def connection_details(connection: Connection) -> str:
    """Return the lines describing a connection on its tooltip."""

    return "\n".join(
        [
            f"zones: {connection.zone_a} - {connection.zone_b}",
            f"capacity: {connection.capacity}",
        ]
    )
