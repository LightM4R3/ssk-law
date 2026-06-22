from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["idx", "id", "nickname", "created_at", "updated_at"]
    search_fields = ["id", "nickname"]
    readonly_fields = ["created_at", "updated_at"]
    exclude = ["password"]

    def has_add_permission(self, request):
        return False
