"""Central validation for reservation time policies."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("America/Bogota")
MINIMUM_ADVANCE = timedelta(hours=24)
MAXIMUM_ADVANCE = timedelta(days=30)
OPENING_TIME = time(7, 0)
CLOSING_TIME = time(21, 0)
BLOCK_MINUTES = 30
MAX_CONSECUTIVE_DURATION = timedelta(hours=4)


class ReservationPolicyError(ValueError):
    """A reservation interval violates a confirmed business policy."""


def validate_consecutive_reservation_limit(
    starts_at: datetime,
    ends_at: datetime,
    existing_intervals: list[tuple[datetime, datetime]],
) -> None:
    """Reject a candidate whose exactly-touching interval sequence exceeds 4h.

    ``existing_intervals`` must contain only the relevant user's active
    reservations for the same space, normalized to aware datetimes. The
    candidate is measured only against the sequence that contains it, so
    unrelated legacy sequences over the limit do not block a separate slot.
    """
    candidate_start = _as_local(starts_at, "El inicio").astimezone(timezone.utc)
    candidate_end = _as_local(ends_at, "El fin").astimezone(timezone.utc)
    if candidate_start >= candidate_end:
        raise ReservationPolicyError("El inicio debe ser anterior al fin")

    intervals = [
        (candidate_start, candidate_end, True),
        *(
            (
                _as_local(start, "El inicio existente").astimezone(timezone.utc),
                _as_local(end, "El fin existente").astimezone(timezone.utc),
                False,
            )
            for start, end in existing_intervals
        ),
    ]
    intervals.sort(key=lambda interval: (interval[0], interval[1]))

    sequence_start: datetime | None = None
    sequence_end: datetime | None = None
    candidate_in_sequence = False

    def check_candidate_sequence() -> None:
        if (
            candidate_in_sequence
            and sequence_start is not None
            and sequence_end is not None
            and sequence_end - sequence_start > MAX_CONSECUTIVE_DURATION
        ):
            raise ReservationPolicyError(
                "El tiempo consecutivo reservado no puede superar cuatro horas"
            )

    for interval_start, interval_end, is_candidate in intervals:
        if sequence_end != interval_start:
            check_candidate_sequence()
            sequence_start = interval_start
            sequence_end = interval_end
            candidate_in_sequence = is_candidate
        else:
            sequence_end = interval_end
            candidate_in_sequence = candidate_in_sequence or is_candidate

    check_candidate_sequence()


def _as_local(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ReservationPolicyError(f"{field} debe ser una fecha y hora válida")
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=LOCAL_TIMEZONE)
    return value.astimezone(LOCAL_TIMEZONE)


def validate_reservation_interval(
    starts_at: datetime,
    ends_at: datetime,
    *,
    requested_at: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Validate a local reservation interval and return both instants in UTC.

    Naive date-times are interpreted as America/Bogota, in line with the
    application plan. Aware date-times are converted to that local zone for
    calendar checks and normalized to UTC for storage and advance checks.
    """
    local_start = _as_local(starts_at, "El inicio")
    local_end = _as_local(ends_at, "El fin")
    start_utc = local_start.astimezone(timezone.utc)
    end_utc = local_end.astimezone(timezone.utc)

    if start_utc >= end_utc:
        raise ReservationPolicyError("El inicio debe ser anterior al fin")

    if local_start.date() != local_end.date():
        raise ReservationPolicyError("La reserva debe terminar el mismo día que inicia")
    if local_start.weekday() == 6:
        raise ReservationPolicyError("No se permiten reservas los domingos")
    if local_start.time().replace(tzinfo=None) < OPENING_TIME:
        raise ReservationPolicyError("La reserva no puede iniciar antes de las 07:00")
    if local_end.time().replace(tzinfo=None) > CLOSING_TIME:
        raise ReservationPolicyError("La reserva no puede terminar después de las 21:00")

    for label, local_value in (("inicio", local_start), ("fin", local_end)):
        if (
            local_value.minute % BLOCK_MINUTES != 0
            or local_value.second != 0
            or local_value.microsecond != 0
        ):
            raise ReservationPolicyError(
                f"La hora de {label} debe coincidir con un bloque de 30 minutos"
            )

    if (end_utc - start_utc).total_seconds() % (BLOCK_MINUTES * 60) != 0:
        raise ReservationPolicyError(
            "La duración debe ser múltiplo de 30 minutos"
        )

    request_local = _as_local(
        requested_at if requested_at is not None else datetime.now(timezone.utc),
        "La fecha de solicitud",
    )
    request_utc = request_local.astimezone(timezone.utc)
    advance = start_utc - request_utc
    if advance < MINIMUM_ADVANCE:
        raise ReservationPolicyError(
            "La reserva debe solicitarse con al menos 24 horas de anticipación"
        )
    if advance > MAXIMUM_ADVANCE:
        raise ReservationPolicyError(
            "La reserva no puede solicitarse con más de 30 días de anticipación"
        )

    return start_utc, end_utc
