from django.contrib import admin

from accounts.models import User
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "action",
        "module",
        "object_type",
        "object_id",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "action",
        "module",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "module",
        "object_type",
        "object_id",
        "description",
        "ip_address",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "user",
        "action",
        "module",
        "object_type",
        "object_id",
        "description",
        "ip_address",
        "created_at",
    )

    def has_view_permission(self, request, obj=None):
        return request.user.role == User.Role.SUPER_ADMIN

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False