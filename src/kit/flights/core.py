"""Core data models for flight search."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FlightSearch(BaseModel):
    """A user-facing flight search query.

    Executed against Ryanair's public fare API inside
    kit.flights.ryanair.RyanairFareClient.run_search.
    """

    origin: str = Field(description="IATA code (e.g. 'BER') or airport name")
    destination: str = Field(description="IATA code or airport name")
    date_from: date = Field(description="Earliest outbound departure date")
    date_to: date = Field(description="Latest date to consider")
    trip_type: Literal["one_way", "round_trip"] = "one_way"
    nights_min: int | None = Field(default=None, description="Round-trip: min nights")
    nights_max: int | None = Field(default=None, description="Round-trip: max nights")
    max_results: int = 20

    @model_validator(mode="after")
    def _check_dates(self) -> FlightSearch:
        if self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        if (
            self.trip_type == "round_trip"
            and self.nights_min is not None
            and self.nights_max is not None
            and self.nights_max < self.nights_min
        ):
            raise ValueError("nights_max must be >= nights_min")
        return self


class FlightOption(BaseModel):
    """A single flight option returned by the scraper."""

    origin: str
    destination: str
    departure: datetime
    return_departure: datetime | None = None
    price: float
    currency: str = "EUR"
    flight_number: str | None = None
    booking_url: str | None = None

    # ── Cross-tool interchange (option d — kit.integrations) ──────────────

    def as_calendar_event_candidate(self) -> "CalendarEventCandidate":
        """Convert this flight to a CalendarEventCandidate.

        The cal tool can consume this shape to create a calendar event and
        travel buffer without ever importing ``kit.flights`` directly.
        """
        from kit.integrations import CalendarEventCandidate  # lazy — avoids parse-time coupling

        desc_parts = [
            f"{self.origin} → {self.destination}",
            f"{self.price} {self.currency}",
        ]
        if self.flight_number:
            desc_parts.append(f"Flight: {self.flight_number}")
        if self.booking_url:
            desc_parts.append(f"Book: {self.booking_url}")

        # Short-haul default: 2h block when only departure is known.
        end = self.return_departure
        duration_seconds = None if end is not None else 2 * 60 * 60

        return CalendarEventCandidate(
            title=f"Flight {self.origin}→{self.destination}",
            start=self.departure,
            end=end,
            duration_seconds=duration_seconds,
            location=self.origin,
            description="\n".join(desc_parts),
            source="flight",
            source_id=self.flight_number,
            booking_url=self.booking_url,
        )

    def as_route_leg(self) -> "RouteLeg":
        """Return an airport-transfer RouteLeg for travel-buffer planning.

        Callers can pass the ``origin`` as the departure airport and ask
        ``kit route`` to compute the transfer time — without coupling cal
        to flights directly.
        """
        from kit.integrations import RouteLeg  # lazy — avoids parse-time coupling

        return RouteLeg(
            origin=self.origin,
            destination=self.destination,
            departure=self.departure,
            mode="plane",
        )


class FlightSearchResult(BaseModel):
    """Result of a flight search: all options plus the cheapest pick."""

    query: FlightSearch
    options: list[FlightOption]
    cheapest: FlightOption | None
    searched_at: datetime
    source: Literal["ryanair"] = "ryanair"
