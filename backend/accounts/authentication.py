from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, CSRFCheck

from .models import Account


SESSION_ACCOUNT_KEY = "account_idx"


def _csrf_failure_reason(request):
    def dummy_get_response(_request):
        return None

    check = CSRFCheck(dummy_get_response)
    check.process_request(request)
    return check.process_view(request, None, (), {})


class AccountSessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        account_idx = request._request.session.get(SESSION_ACCOUNT_KEY)
        if account_idx is None:
            return None

        try:
            account = Account.objects.get(idx=account_idx)
        except Account.DoesNotExist:
            request._request.session.pop(SESSION_ACCOUNT_KEY, None)
            return None

        self.enforce_csrf(request)
        return account, None

    def enforce_csrf(self, request):
        reason = _csrf_failure_reason(request)
        if reason:
            raise exceptions.PermissionDenied(f"CSRF 검증에 실패했습니다: {reason}")

    def authenticate_header(self, request):
        return "Session"
