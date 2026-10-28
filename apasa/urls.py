from django.contrib.auth import views as auth_views
from django.urls import include, path
from accounts import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("workspace/", views.workspace, name="workspace"),
    path("health/", views.health, name="health"),
    path("", include("evidence.urls")),
]
