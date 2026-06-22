from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AccountSessionAuthentication, SESSION_ACCOUNT_KEY
from .models import Account
from .serializers import AccountSerializer


@method_decorator(csrf_protect, name="dispatch")
class AccountListCreateView(generics.ListCreateAPIView):
    serializer_class = AccountSerializer

    def get_permissions(self):
        permission_classes = [AllowAny] if self.request.method == "POST" else [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if not self.request.user or not self.request.user.is_authenticated:
            return Account.objects.none()
        return Account.objects.filter(idx=self.request.user.idx)


class AccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "idx"
    lookup_url_kwarg = "idx"

    def get_queryset(self):
        return Account.objects.filter(idx=self.request.user.idx)

    def perform_destroy(self, instance):
        instance.delete()
        self.request.session.flush()


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = [AccountSessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        account_id = str(request.data.get("id", "")).strip()
        password = request.data.get("password", "")

        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "ACCOUNT_NOT_FOUND",
                        "message": "존재하지 않는 아이디입니다.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not account.check_password(password):
            return Response(
                {
                    "error": {
                        "code": "INVALID_PASSWORD",
                        "message": "비밀번호가 올바르지 않습니다.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        request.session.cycle_key()
        request.session[SESSION_ACCOUNT_KEY] = account.idx
        return Response({"account": AccountSerializer(account).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.session.flush()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CurrentAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"account": AccountSerializer(request.user).data})
