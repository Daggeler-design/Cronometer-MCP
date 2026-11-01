"""
Run the Cronometer MCP server over HTTPS for Render (or any host).

Claude connects to:  https://<your-service>.onrender.com/<MCP_PATH_SECRET>/mcp
Every other path returns 404, so the long random secret acts as the password.

Env vars: CRONOMETER_USERNAME, CRONOMETER_PASSWORD, MCP_PATH_SECRET, PORT (set by Render), TZ.
"""
import os

import uvicorn

import cronometer_mcp_server as server

secret = os.environ.get("MCP_PATH_SECRET", "").strip()
if len(secret) < 24:
    raise SystemExit("Set MCP_PATH_SECRET to a long random value (24+ characters).")

mcp = server.mcp
mcp.settings.stateless_http = True        # no sticky sessions needed
mcp.settings.json_response = True         # plain JSON replies, no long-lived streams
mcp.settings.streamable_http_path = f"/{secret}/mcp"

try:  # the default host check only allows localhost; the public hostname must pass
    from mcp.server.transport_security import TransportSecuritySettings
    mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
except ImportError:
    pass

app = mcp.streamable_http_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), proxy_headers=True,
                forwarded_allow_ips="*")
