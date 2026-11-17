from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import AuditLog
from .services import create_audit_log


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip_address = request.META.get("REMOTE_ADDR") if request else None

    create_audit_log(
        user=user,
        action=AuditLog.Action.LOGIN,
        module="Authentication",
        description=f"User '{user.username}' logged in successfully.",
        object_type="User",
        object_id=user.id,
        ip_address=ip_address,
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if not user:
        return

    ip_address = request.META.get("REMOTE_ADDR") if request else None

    create_audit_log(
        user=user,
        action=AuditLog.Action.LOGOUT,
        module="Authentication",
        description=f"User '{user.username}' logged out.",
        object_type="User",
        object_id=user.id,
        ip_address=ip_address,
    )