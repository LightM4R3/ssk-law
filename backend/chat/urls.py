"""Chat URL configuration."""

from django.urls import path
from . import views

urlpatterns = [
    path("chat", views.chat_view, name="chat"),
    path("chat/history", views.chat_history_view, name="chat-history"),
]
