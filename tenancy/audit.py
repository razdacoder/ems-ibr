"""Who is asking, and the console's own audit trail (spec 0003, child 0003)."""
import ipaddress


def client_ip(request):
    """The last ``X-Forwarded-For`` entry, else the socket peer.

    The last hop is the one our own proxy added (Traefik on the VPS, Render's
    proxy on test); anything before it came from the client and can be
    forged (spec 0003, child 0002).
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    if hops:
        return hops[-1]
    return request.META.get("REMOTE_ADDR") or None


def request_ip(request):
    """``client_ip`` as stored: None unless it parses as an address."""
    value = client_ip(request)
    try:
        return str(ipaddress.ip_address(value)) if value else None
    except ValueError:
        return None


def record(request, action, school=None, *, admin=None, **detail):
    """Write one ``PlatformAuditLog`` row.

    ``admin`` defaults to the signed in platform admin. Pass it for the sign
    in steps, where nobody is signed in yet.
    """
    from tenancy.models import PlatformAdmin, PlatformAuditLog

    if admin is None and isinstance(getattr(request, "user", None), PlatformAdmin):
        admin = request.user
    return PlatformAuditLog.objects.create(
        admin=admin,
        school=school,
        action=action,
        detail=detail,
        ip=request_ip(request),
    )
