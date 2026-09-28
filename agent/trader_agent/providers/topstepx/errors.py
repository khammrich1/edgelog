"""TopstepX/ProjectX provider-specific errors. Kept separate from the
generic ExecutionProvider interface so other providers can define their
own error hierarchy without EdgeLog's agent-level code needing to know
about TopstepX specifically."""


class TopstepXError(Exception):
    """Base class for every error raised by the TopstepX provider."""


class AuthenticationError(TopstepXError):
    """Raised when login fails, or a request is attempted before/after a
    valid session. Never includes the API key in its message."""


class ProviderConnectionError(TopstepXError):
    """Raised for network-level failures talking to the REST API or the
    real-time hubs (timeouts, DNS failures, refused connections)."""


class ProviderResponseError(TopstepXError):
    """Raised when the API responds but signals failure (non-2xx status,
    or a body with success=false)."""
