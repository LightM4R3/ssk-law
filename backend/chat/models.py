"""Chat app models – matches DATABASE_SPEC.md."""

from django.db import models


class ChatSession(models.Model):
    """익명 챗봇 대화 세션."""

    session_key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_session"

    def __str__(self):
        return self.session_key


class ChatMessage(models.Model):
    """챗봇 메시지."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    related_bill_ids = models.TextField(blank=True, default="", help_text="JSON array string")
    snapshot = models.JSONField(blank=True, null=True, help_text="질문 구조화 분석 결과 스냅샷")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"], name="idx_cm_session"),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
