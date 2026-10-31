"""Public entry, role-aware navigation, and deployment health."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_safe
from django.db import connection


@require_safe
def landing(request):
    return render(request, "accounts/landing.html")


@login_required
@require_safe
def workspace(request):
    return redirect("planning:index")


@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
