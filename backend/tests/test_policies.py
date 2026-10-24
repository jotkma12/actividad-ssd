from datetime import datetime, timedelta, timezone

import pytest

from backend.politicas.validation import (
    LOCAL_TIMEZONE,
    ReservationPolicyError,
    validate_consecutive_reservation_limit,
    validate_reservation_interval,
)
from backend.politicas.approval import initial_reservation_status


REQUESTED_AT = datetime(2030, 1, 6, 7, 0, tzinfo=LOCAL_TIMEZONE)


def test_consecutive_limit_accepts_exactly_four_hours():
    validate_consecutive_reservation_limit(
        datetime(2030, 1, 7, 7, 0), datetime(2030, 1, 7, 11, 0), []
    )


def test_consecutive_limit_rejects_single_interval_over_four_hours():
    with pytest.raises(ReservationPolicyError, match="cuatro horas"):
        validate_consecutive_reservation_limit(
            datetime(2030, 1, 7, 7, 0), datetime(2030, 1, 7, 11, 30), []
        )


def test_consecutive_limit_accumulates_touching_active_intervals():
    # Existing intervals may come from both pending and approved records.
    with pytest.raises(ReservationPolicyError, match="cuatro horas"):
        validate_consecutive_reservation_limit(
            datetime(2030, 1, 7, 10, 0),
            datetime(2030, 1, 7, 12, 0),
            [
                (datetime(2030, 1, 7, 7, 0), datetime(2030, 1, 7, 9, 0)),
                (datetime(2030, 1, 7, 9, 0), datetime(2030, 1, 7, 10, 0)),
            ],
        )


def test_consecutive_limit_resets_after_a_pause():
    validate_consecutive_reservation_limit(
        datetime(2030, 1, 7, 12, 0),
        datetime(2030, 1, 7, 14, 0),
        [(datetime(2030, 1, 7, 7, 0), datetime(2030, 1, 7, 11, 0))],
    )


def test_rejects_five_hour_reservation_under_consecutive_limit():
    starts_at = datetime(2030, 1, 7, 7, 0)
    ends_at = datetime(2030, 1, 7, 12, 0)

    with pytest.raises(ReservationPolicyError, match="cuatro horas"):
        validate_consecutive_reservation_limit(starts_at, ends_at, [])


def test_rejects_full_allowed_day_under_consecutive_limit():
    with pytest.raises(ReservationPolicyError, match="cuatro horas"):
        validate_consecutive_reservation_limit(
            datetime(2030, 1, 7, 7, 0), datetime(2030, 1, 7, 21, 0), []
        )


@pytest.mark.parametrize(
    ("starts_at", "ends_at", "requested_at", "message"),
    [
        (
            datetime(2030, 1, 7, 7, 0),
            datetime(2030, 1, 7, 8, 0),
            datetime(2030, 1, 6, 7, 1, tzinfo=LOCAL_TIMEZONE),
            "24 horas",
        ),
        (
            datetime(2030, 2, 6, 7, 0),
            datetime(2030, 2, 6, 8, 0),
            datetime(2030, 1, 6, 7, 0, tzinfo=LOCAL_TIMEZONE),
            "30 días",
        ),
        (
            datetime(2030, 1, 7, 6, 30),
            datetime(2030, 1, 7, 7, 30),
            REQUESTED_AT,
            "07:00",
        ),
        (
            datetime(2030, 1, 7, 20, 30),
            datetime(2030, 1, 7, 21, 30),
            REQUESTED_AT,
            "21:00",
        ),
        (
            datetime(2030, 1, 6, 8, 0),
            datetime(2030, 1, 6, 9, 0),
            datetime(2030, 1, 5, 8, 0, tzinfo=LOCAL_TIMEZONE),
            "domingos",
        ),
        (
            datetime(2030, 1, 7, 7, 0),
            datetime(2030, 1, 8, 8, 0),
            REQUESTED_AT,
            "mismo día",
        ),
        (
            datetime(2030, 1, 7, 7, 17),
            datetime(2030, 1, 7, 8, 2),
            REQUESTED_AT,
            "múltiplo de 30 minutos",
        ),
        (
            datetime(2030, 1, 7, 8, 0),
            datetime(2030, 1, 7, 7, 0),
            REQUESTED_AT,
            "anterior al fin",
        ),
    ],
)
def test_rejects_intervals_outside_confirmed_policies(
    starts_at, ends_at, requested_at, message
):
    with pytest.raises(ReservationPolicyError, match=message):
        validate_reservation_interval(
            starts_at, ends_at, requested_at=requested_at
        )


def test_accepts_inclusive_advance_boundaries():
    requested_at = datetime(2030, 1, 7, 12, 0, tzinfo=timezone.utc)
    minimum_start = requested_at + timedelta(hours=24)
    maximum_start = requested_at + timedelta(days=30)

    # Pick the allowed boundary dates/times in local Bogota time.
    validate_reservation_interval(
        minimum_start.astimezone(LOCAL_TIMEZONE),
        (minimum_start + timedelta(hours=1)).astimezone(LOCAL_TIMEZONE),
        requested_at=requested_at,
    )
    validate_reservation_interval(
        maximum_start.astimezone(LOCAL_TIMEZONE),
        (maximum_start + timedelta(hours=1)).astimezone(LOCAL_TIMEZONE),
        requested_at=requested_at,
    )


def test_accepts_arbitrary_minute_start_with_thirty_minute_duration():
    starts_at = datetime(2030, 1, 7, 10, 17)
    ends_at = datetime(2030, 1, 7, 10, 47)

    start_utc, end_utc = validate_reservation_interval(
        starts_at, ends_at, requested_at=REQUESTED_AT
    )

    assert end_utc - start_utc == timedelta(minutes=30)


def test_rejects_seconds_when_reservation_precision_is_minutes():
    with pytest.raises(ReservationPolicyError, match="precisión de minuto"):
        validate_reservation_interval(
            datetime(2030, 1, 7, 10, 17, 1),
            datetime(2030, 1, 7, 10, 47, 1),
            requested_at=REQUESTED_AT,
        )


def test_aware_input_is_checked_in_bogota_and_returned_in_utc():
    starts_at = datetime(2030, 1, 7, 12, 0, tzinfo=timezone.utc)
    ends_at = datetime(2030, 1, 7, 17, 0, tzinfo=timezone.utc)

    start_utc, end_utc = validate_reservation_interval(
        starts_at, ends_at, requested_at=REQUESTED_AT
    )

    assert start_utc == starts_at
    assert end_utc == ends_at


@pytest.mark.parametrize(
    ("requires_approval", "expected_status"),
    [(True, "pending"), (False, "approved")],
)
def test_current_space_approval_setting_determines_new_reservation_status(
    requires_approval, expected_status
):
    assert initial_reservation_status(requires_approval) == expected_status


def test_initial_reservation_status_requires_a_configured_boolean():
    with pytest.raises(TypeError, match="booleano"):
        initial_reservation_status(None)
