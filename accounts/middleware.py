"""Require a session for evidence pages; public entry and health stay accessible."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login


class WorkspaceAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public = request.path in {"/", "/accounts/login/", "/health/"}
        if (
            not public
            and not request.path.startswith(settings.STATIC_URL)
            and not request.user.is_authenticated
        ):
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)
