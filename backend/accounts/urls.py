from django.urls import path

from .views import (
    AccountDetailView,
    AccountListCreateView,
    CsrfTokenView,
    CurrentAccountView,
    LoginView,
    LogoutView,
)


urlpatterns = [
    path("auth/csrf", CsrfTokenView.as_view(), name="auth-csrf"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", CurrentAccountView.as_view(), name="auth-me"),
    path("accounts", AccountListCreateView.as_view(), name="account-list-create"),
    path("accounts/<int:idx>", AccountDetailView.as_view(), name="account-detail"),
]
