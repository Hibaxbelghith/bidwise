from rest_framework.throttling import SimpleRateThrottle


class OrganizationOpportunityPostThrottle(SimpleRateThrottle):
    """
    Per-organization publishing throttle.

    Only POST requests are limited. Listing the organization's own
    opportunities stays available so the dashboard is not degraded after the
    publish quota is reached.
    """

    scope = "organization_opportunity_post"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
