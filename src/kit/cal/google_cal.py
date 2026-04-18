"""Google Calendar API client."""

from __future__ import annotations

from pathlib import Path

from kit.cal.core import CalendarEvent, TravelBuffer
from kit.errors import CalendarError


class GoogleCalendarClient:
    def __init__(self, credentials_dir: Path | None = None) -> None:
        self._credentials_dir = credentials_dir
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_path = (self._credentials_dir or Path.home() / ".config" / "kit") / "token.json"
            if not token_path.exists():
                raise CalendarError("Not authenticated. Run: kit cal auth")
            creds = Credentials.from_authorized_user_file(str(token_path))
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request

                creds.refresh(Request())
                token_path.write_text(creds.to_json())
            self._service = build("calendar", "v3", credentials=creds)
            return self._service
        except CalendarError:
            raise
        except Exception as e:
            raise CalendarError(f"Calendar auth error: {e}") from e

    def add_event(self, event: CalendarEvent) -> dict:
        """Create a calendar event. Returns the API response dict."""
        service = self._get_service()
        body: dict = {
            "summary": event.title,
            "location": event.location or "",
            "description": event.description or "",
        }
        if event.all_day and event.date:
            body["start"] = {"date": event.date}
            body["end"] = {"date": event.date}
        elif event.start and event.end:
            body["start"] = {"dateTime": event.start.isoformat(), "timeZone": "Europe/Berlin"}
            body["end"] = {"dateTime": event.end.isoformat(), "timeZone": "Europe/Berlin"}
        else:
            raise CalendarError("Event must have start time or be all-day")

        try:
            return service.events().insert(calendarId=event.calendar_id, body=body).execute()
        except CalendarError:
            raise
        except Exception as e:
            raise CalendarError(f"Failed to create event: {e}") from e

    def add_travel_buffer(self, buffer: TravelBuffer) -> dict:
        """Create a travel buffer event (greyed out). Returns the API response dict."""
        service = self._get_service()
        body = {
            "summary": f"\U0001f687 {buffer.title}",
            "description": buffer.description,
            "start": {"dateTime": buffer.start.isoformat(), "timeZone": "Europe/Berlin"},
            "end": {"dateTime": buffer.end.isoformat(), "timeZone": "Europe/Berlin"},
            "colorId": "8",  # Graphite/grey
        }
        try:
            return service.events().insert(calendarId=buffer.calendar_id, body=body).execute()
        except CalendarError:
            raise
        except Exception as e:
            raise CalendarError(f"Failed to create travel buffer: {e}") from e

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 20,
    ) -> list[dict]:
        """List calendar events, optionally filtered by time range."""
        service = self._get_service()
        kwargs: dict = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            kwargs["timeMin"] = time_min
        if time_max:
            kwargs["timeMax"] = time_max
        try:
            result = service.events().list(**kwargs).execute()
            return result.get("items", [])
        except Exception as e:
            raise CalendarError(f"Failed to list events: {e}") from e

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        """Delete a calendar event by its ID."""
        service = self._get_service()
        try:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        except Exception as e:
            raise CalendarError(f"Failed to delete event: {e}") from e

    @staticmethod
    def setup(credentials_dir: Path | None = None) -> None:
        """Run OAuth2 consent flow to obtain and store credentials."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds_dir = credentials_dir or Path.home() / ".config" / "kit"
            client_secrets = creds_dir / "credentials.json"
            token_path = creds_dir / "token.json"

            if not client_secrets.exists():
                raise CalendarError(
                    f"Place your Google OAuth client_secrets file at {client_secrets}"
                )

            scopes = ["https://www.googleapis.com/auth/calendar"]
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), scopes=scopes)
            creds = flow.run_local_server(port=0)

            creds_dir.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())
            token_path.chmod(0o600)
        except CalendarError:
            raise
        except Exception as e:
            raise CalendarError(f"OAuth setup failed: {e}") from e
