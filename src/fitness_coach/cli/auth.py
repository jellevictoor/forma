"""Strava OAuth authentication handler."""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import httpx


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from Strava."""

    auth_code: str | None = None
    error: str | None = None

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/callback":
            params = parse_qs(parsed.query)

            if "code" in params:
                OAuthCallbackHandler.auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html>
                    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                        <h1>Authorization successful!</h1>
                        <p>You can close this window and return to the terminal.</p>
                    </body>
                    </html>
                """)
            elif "error" in params:
                OAuthCallbackHandler.error = params.get("error_description", ["Unknown error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                    <html>
                    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                        <h1>Authorization failed</h1>
                        <p>{OAuthCallbackHandler.error}</p>
                    </body>
                    </html>
                """.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging


def get_auth_url(client_id: str, redirect_uri: str = "http://localhost:8000/callback") -> str:
    """Build the Strava authorization URL."""
    scopes = "read,activity:read,activity:read_all"
    return (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes}"
    )


async def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    code: str,
) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


def run_callback_server(port: int = 8000, timeout: int = 120) -> str | None:
    """Run a temporary server to catch the OAuth callback.

    Returns the authorization code or None if timeout/error.
    """
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.error = None

    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server.timeout = timeout

    # Run server until we get a code or timeout
    while OAuthCallbackHandler.auth_code is None and OAuthCallbackHandler.error is None:
        server.handle_request()

    server.server_close()

    if OAuthCallbackHandler.error:
        raise Exception(OAuthCallbackHandler.error)

    return OAuthCallbackHandler.auth_code
