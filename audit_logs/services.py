from .models import AuditLog


def create_audit_log(
    *,
    user,
    action,
    module,
    description,
    object_type="",
    object_id="",
    ip_address=None,
):
    """
    Create a secure audit log entry.

    Audit logs are created through this service instead of
    allowing normal users to create them manually.
    """

    if not user or not user.is_authenticated:
        return None

    return AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        description=description,
        ip_address=ip_address,
    )