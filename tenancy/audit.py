"""Who is asking: the client IP as the proxy in front of Django saw it."""


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
