"""DRF serializers for the chat app."""

from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    """POST /api/chat 요청."""

    session_key = serializers.CharField(required=False, allow_blank=True, default="")
    message = serializers.CharField(min_length=1, max_length=1000)


class RelatedBillSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()


class ChatResponseSerializer(serializers.Serializer):
    """POST /api/chat 응답."""

    session_key = serializers.CharField()
    reply = serializers.CharField()
    related_bills = RelatedBillSerializer(many=True)
    snapshot = serializers.JSONField(required=False, allow_null=True)


class ChatMessageSerializer(serializers.Serializer):
    """대화 내역의 각 메시지."""

    role = serializers.CharField()
    content = serializers.CharField()
    related_bills = serializers.SerializerMethodField()
    snapshot = serializers.JSONField(required=False, allow_null=True)
    created_at = serializers.DateTimeField()

    def get_related_bills(self, obj):
        import json
        if obj.related_bill_ids:
            try:
                return json.loads(obj.related_bill_ids)
            except (json.JSONDecodeError, TypeError):
                pass
        return []
