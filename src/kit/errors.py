"""Custom exceptions for kit."""


class KitError(Exception):
    """Base exception for all kit errors."""


class ConfigError(KitError):
    """Missing or invalid configuration."""


class RouteNotFoundError(KitError):
    """No route found between locations."""


class GeocodingError(KitError):
    """Could not geocode address."""


class APIError(KitError):
    """External API error (rate limit, auth, network)."""


class CalendarError(KitError):
    """Calendar API error."""
