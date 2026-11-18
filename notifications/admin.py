from django.contrib import admin

from accounts.models import User

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "notification_type",
        "severity",
        "title",
        "is_read",
        "created_at",
        "read_at",
    )

    list_filter = (
        "notification_type",
        "severity",
        "is_read",
        "created_at",
    )

    search_fields = (
        "recipient__username",
        "recipient__email",
        "title",
        "message",
        "reference_type",
        "reference_id",
    )

    readonly_fields = (
        "recipient",
        "notification_type",
        "severity",
        "title",
        "message",
        "url",
        "is_read",
        "created_at",
        "read_at",
        "reference_type",
        "reference_id",
    )

    ordering = (
        "-created_at",
    )

    def has_view_permission(self, request, obj=None):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.SUPER_ADMIN
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False