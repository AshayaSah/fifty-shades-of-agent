from mcp.server.lowlevel.server import TransportSecuritySettings

from technical_analyst.config import settings
from technical_analyst.server import mcp

if __name__ == "__main__":
    allowed_hosts = [h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()]

    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(allowed_hosts),
        allowed_hosts=allowed_hosts,
    )

    mcp.run(transport="streamable-http", port=8000, transport_security=security)
