from django.contrib import admin

from .models import Comment, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["idx", "title", "bill", "user", "view_count", "created_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["title", "content", "bill__bill_id", "user__id", "user__nickname"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["idx", "post", "parent", "user", "is_deleted", "view_count", "created_at"]
    list_filter = ["is_deleted", "created_at", "updated_at"]
    search_fields = ["content", "post__title", "user__id", "user__nickname"]
    readonly_fields = ["created_at", "updated_at"]

