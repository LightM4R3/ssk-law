"""Custom DRF exception handler for SSK-Law."""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Wrap DRF errors into our standard format
        code = "INTERNAL_ERROR"
        message = "서버 내부 오류가 발생했습니다."

        if response.status_code == 400:
            code = "INVALID_PARAM"
            message = _extract_message(response.data) or "잘못된 요청입니다."
        elif response.status_code == 401:
            code = "UNAUTHORIZED"
            message = _extract_message(response.data) or "로그인이 필요합니다."
        elif response.status_code == 403:
            code = "FORBIDDEN"
            message = _extract_message(response.data) or "접근 권한이 없습니다."
        elif response.status_code == 404:
            code = "NOT_FOUND"
            message = "해당 리소스를 찾을 수 없습니다."
        elif response.status_code == 405:
            code = "METHOD_NOT_ALLOWED"
            message = "허용되지 않는 HTTP 메서드입니다."

        response.data = {"error": {"code": code, "message": message}}

    return response


def _extract_message(data):
    """Try to pull a human-readable message from DRF error data."""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str):
                return value
    if isinstance(data, list) and data:
        return str(data[0])
    return None
