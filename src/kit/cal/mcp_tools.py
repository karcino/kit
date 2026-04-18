"""MCP tool registrations for calendar."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import dateparser
from mcp.server.fastmcp import FastMCP

from kit.cal.core import CalendarEvent, TravelBuffer
from kit.cal.google_cal import GoogleCalendarClient
from kit.config import KitConfig
from kit.errors import CalendarError, KitError
from kit.integrations import CalendarEventCandidate
from kit.route.planner import plan_day, plan_route

# Berlin timezone (CET = UTC+1, CEST = UTC+2). Simplified to +1 here;
# the Google Calendar API handles DST via the timeZone field.
_TZ = timezone(timedelta(hours=1))


def register_cal_tools(mcp: FastMCP, config: KitConfig) -> None:
    """Register calendar tools on the given FastMCP server."""

    @mcp.tool()
    def kit_cal_add(
        title: str,
        start: str,
        date: str | None = None,
        duration_minutes: int = 60,
        location: str | None = None,
        description: str | None = None,
        route_from: str | None = None,
        calendar_id: str = "primary",
    ) -> str:
        """Create a Google Calendar event.

        Syncs automatically to Notion Calendar and Apple Calendar.
        Can optionally calculate and add a travel buffer event with
        navigation deep links by providing route_from.

        Args:
            title: Event title / summary.
            start: Start time as HH:MM (24h format).
            date: Event date (ISO date string YYYY-MM-DD or natural language like 'morgen'). Defaults to today.
            duration_minutes: Duration in minutes (default 60).
            location: Event location / address.
            description: Optional event description.
            route_from: If set, calculates a travel buffer from this location to the event location.
            calendar_id: Google Calendar ID (default 'primary').
        """
        event_date = (
            dateparser.parse(date, languages=["de", "en"]).date()
            if date
            else datetime.now(tz=_TZ).date()
        )
        h, m = int(start.split(":")[0]), int(start.split(":")[1])
        start_dt = datetime(event_date.year, event_date.month, event_date.day, h, m, tzinfo=_TZ)

        event = CalendarEvent(
            title=title,
            start=start_dt,
            duration_minutes=duration_minutes,
            location=location,
            description=description,
            calendar_id=calendar_id,
        )

        client = GoogleCalendarClient()
        results: dict = {"event": None, "travel_buffer": None, "warnings": []}

        # Optional travel buffer
        if route_from and location:
            try:
                route_result = plan_route(route_from, location, config=config)
                travel_end = start_dt - timedelta(minutes=5)
                travel_start = travel_end - timedelta(seconds=route_result.duration_seconds)
                links = f"Google Maps: {route_result.deep_links.google_maps}"
                if route_result.deep_links.db_navigator:
                    links += f"\nDB Navigator: {route_result.deep_links.db_navigator}"
                buffer = TravelBuffer(
                    title=f"Anreise: {title}",
                    start=travel_start,
                    end=travel_end,
                    description=f"{route_result.duration_human} · {route_result.mode.value}\n{links}",
                    calendar_id=calendar_id,
                )
                client.add_travel_buffer(buffer)
                results["travel_buffer"] = {
                    "start": travel_start.isoformat(),
                    "end": travel_end.isoformat(),
                    "duration": route_result.duration_human,
                    "deep_links": route_result.deep_links.model_dump(),
                }
            except KitError as e:
                results["warnings"].append(
                    f"Route calculation failed: {e}. Event created without travel buffer."
                )

        ev_result = client.add_event(event)
        results["event"] = {
            "id": ev_result.get("id"),
            "start": start_dt.isoformat(),
            "title": title,
        }
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    def kit_cal_add_from_candidate(
        title: str,
        start: str,
        end: str | None = None,
        duration_seconds: int | None = None,
        location: str | None = None,
        description: str | None = None,
        source: str = "unknown",
        source_id: str | None = None,
        booking_url: str | None = None,
        calendar_id: str = "primary",
    ) -> str:
        """Create a Google Calendar event from a ``CalendarEventCandidate``.

        Cross-tool entry point (option d — Pydantic interchange). Any tool that
        emits a ``CalendarEventCandidate`` (flights, route, watch, …) can
        dump its model and call this MCP tool — cal never imports those tools
        directly.

        Field mapping (candidate → CalendarEvent):
            title → title
            start → start (ISO 8601 datetime)
            end or duration_seconds → duration_minutes (end wins)
            location → location
            description + booking_url → description (url appended)
            source / source_id → retained on the candidate only

        Args:
            title: Event title.
            start: ISO 8601 datetime string (e.g. "2026-05-03T07:30:00+01:00").
            end: Optional ISO 8601 end datetime. If omitted, duration_seconds used.
            duration_seconds: Fallback duration when end is unknown.
            location: Event location.
            description: Event description.
            source: Origin tag ("flight" | "route" | "manual" | …). Default "unknown".
            source_id: Source-specific ID (e.g. flight number).
            booking_url: Optional URL appended to the description.
            calendar_id: Target calendar (default 'primary').
        """
        # Parse ISO datetimes — strict, no natural-language fallback.
        try:
            start_dt = datetime.fromisoformat(start)
        except ValueError as e:
            raise CalendarError(f"Invalid 'start' datetime (must be ISO 8601): {start}") from e

        end_dt: datetime | None = None
        if end is not None:
            try:
                end_dt = datetime.fromisoformat(end)
            except ValueError as e:
                raise CalendarError(f"Invalid 'end' datetime (must be ISO 8601): {end}") from e

        # Build the candidate (Pydantic validation happens here).
        candidate = CalendarEventCandidate(
            title=title,
            start=start_dt,
            end=end_dt,
            duration_seconds=duration_seconds,
            location=location,
            description=description,
            source=source,
            source_id=source_id,
            booking_url=booking_url,
        )

        # Convert via the integration-module adapter (lazy-imports cal.core).
        event = candidate.to_calendar_event(calendar_id=calendar_id)

        client = GoogleCalendarClient()
        ev_result = client.add_event(event)

        return json.dumps(
            {
                "event": {
                    "id": ev_result.get("id"),
                    "title": event.title,
                    "start": event.start.isoformat() if event.start else None,
                    "end": event.end.isoformat() if event.end else None,
                    "location": event.location,
                    "calendar_id": event.calendar_id,
                },
                "candidate": candidate.model_dump(mode="json"),
            },
            indent=2,
            default=str,
        )

    @mcp.tool()
    def kit_cal_today() -> str:
        """List today's calendar events.

        Returns all events for today from the primary calendar,
        sorted by start time.
        """
        client = GoogleCalendarClient()
        now = datetime.now(tz=_TZ)
        t_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        t_max = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
        events = client.list_events(time_min=t_min, time_max=t_max)
        return json.dumps(events, indent=2, default=str)

    @mcp.tool()
    def kit_cal_list(
        range: str = "today",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> str:
        """List calendar events for a given time range.

        Args:
            range: Preset range — 'today', 'tomorrow', or 'week'.
            start_date: Custom start (ISO date or datetime). Overrides range if set.
            end_date: Custom end (ISO date or datetime). Overrides range if set.
        """
        client = GoogleCalendarClient()
        now = datetime.now(tz=_TZ)

        if start_date or end_date:
            t_min = start_date or now.isoformat()
            t_max = end_date or (now + timedelta(days=1)).isoformat()
        elif range == "today":
            t_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            t_max = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
        elif range == "tomorrow":
            tmrw = now + timedelta(days=1)
            t_min = tmrw.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            t_max = tmrw.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
        elif range == "week":
            t_min = now.isoformat()
            t_max = (now + timedelta(days=7)).isoformat()
        else:
            t_min = now.isoformat()
            t_max = (now + timedelta(days=1)).isoformat()

        events = client.list_events(time_min=t_min, time_max=t_max)
        return json.dumps(events, indent=2, default=str)

    @mcp.tool()
    def kit_plan_day(
        tasks: list[str],
        date: str | None = None,
        start_hour: int = 9,
        end_hour: int = 18,
    ) -> str:
        """Given a list of tasks/appointments, suggest a realistic daily schedule.

        Takes into account travel times between locations when tasks have
        locations specified (format: 'Task name @ Location').

        Args:
            tasks: List of tasks or appointments. Use 'Task @ Location' format
                   to include locations for travel time calculation.
            date: Date for the schedule (ISO or natural language). Defaults to today.
            start_hour: Earliest hour to schedule (default 9).
            end_hour: Latest hour to end (default 18).
        """
        schedule_date = (
            dateparser.parse(date, languages=["de", "en"]).date()
            if date
            else datetime.now(tz=_TZ).date()
        )
        result = plan_day(
            tasks, schedule_date=schedule_date,
            start_hour=start_hour, end_hour=end_hour, config=config,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
