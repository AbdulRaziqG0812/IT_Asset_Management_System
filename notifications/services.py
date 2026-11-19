from django.contrib.auth import get_user_model
from django.utils import timezone

from assets.models import Asset
from software_licenses.models import SoftwareLicense

from .models import Notification


User = get_user_model()


def create_notification(
    *,
    recipient,
    notification_type,
    title,
    message,
    severity=Notification.Severity.INFO,
    url="",
    reference_type="",
    reference_id="",
):
    """
    Creates one notification for one user.

    The same notification event is not duplicated while an existing
    matching notification is still unread.

    The notification title is included in the duplicate check so
    different status events for the same object can each create
    their own notification.
    """

    if not recipient or not recipient.is_active:
        return None

    filters = {
        "recipient": recipient,
        "notification_type": notification_type,
        "title": title,
        "reference_type": reference_type,
        "reference_id": str(reference_id or ""),
    }

    existing = Notification.objects.filter(
        **filters,
        is_read=False,
    ).first()

    if existing:
        return existing

    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        severity=severity,
        title=title,
        message=message,
        url=url,
        reference_type=reference_type,
        reference_id=str(reference_id or ""),
    )


def get_it_administrators():
    return User.objects.filter(
        role=User.Role.IT_ADMIN,
        is_active=True,
    )


def get_super_administrators():
    return User.objects.filter(
        role=User.Role.SUPER_ADMIN,
        is_active=True,
    )


def get_hr_managers():
    return User.objects.filter(
        role=User.Role.HR_MANAGER,
        is_active=True,
    )


def get_notification_staff():
    """
    Users who should receive system-level IT notifications.
    """

    return User.objects.filter(
        role__in=[
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        ],
        is_active=True,
    )


def notify_pending_asset_request(asset_request):
    """
    Notify authorized IT users about a newly submitted
    pending asset request.
    """

    for user in get_notification_staff():
        create_notification(
            recipient=user,
            notification_type=Notification.NotificationType.ASSET_REQUEST,
            severity=Notification.Severity.WARNING,
            title="New Asset Request",
            message=(
                f"Employee {asset_request.employee.employee_id} "
                f"submitted a new asset request for "
                f"{asset_request.asset_category}."
            ),
            reference_type="AssetRequest",
            reference_id=asset_request.pk,
        )


def notify_asset_request_status_change(
    asset_request,
    old_status,
):
    """
    Notify the employee when an asset request is approved
    or rejected.
    """

    if old_status == asset_request.status:
        return

    if asset_request.status == asset_request.Status.APPROVED:
        title = "Asset Request Approved"
        message = (
            f"Your asset request for "
            f"{asset_request.asset_category} has been approved."
        )
        severity = Notification.Severity.SUCCESS

    elif asset_request.status == asset_request.Status.REJECTED:
        title = "Asset Request Rejected"
        message = (
            f"Your asset request for "
            f"{asset_request.asset_category} has been rejected."
        )
        severity = Notification.Severity.DANGER

    else:
        return

    create_notification(
        recipient=asset_request.employee.user,
        notification_type=Notification.NotificationType.ASSET_REQUEST,
        severity=severity,
        title=title,
        message=message,
        reference_type="AssetRequest",
        reference_id=asset_request.pk,
    )


def notify_pending_maintenance_request(maintenance_request):
    """
    Notify IT users about a newly submitted maintenance request.
    """

    for user in get_notification_staff():
        create_notification(
            recipient=user,
            notification_type=Notification.NotificationType.MAINTENANCE,
            severity=Notification.Severity.WARNING,
            title="New Maintenance Request",
            message=(
                f"Employee {maintenance_request.employee.employee_id} "
                f"submitted a "
                f"{maintenance_request.get_request_type_display().lower()} "
                f"request for asset "
                f"{maintenance_request.asset.asset_id}."
            ),
            reference_type="MaintenanceRequest",
            reference_id=maintenance_request.pk,
        )


def notify_maintenance_status_change(
    maintenance_request,
    old_status,
):
    """
    Notify the employee when maintenance status changes.
    """

    if old_status == maintenance_request.status:
        return

    if (
        maintenance_request.status
        == maintenance_request.Status.IN_PROGRESS
    ):
        title = "Maintenance Request In Progress"
        message = (
            f"Your maintenance request for asset "
            f"{maintenance_request.asset.asset_id} "
            f"is now in progress."
        )
        severity = Notification.Severity.INFO

    elif (
        maintenance_request.status
        == maintenance_request.Status.COMPLETED
    ):
        title = "Maintenance Request Completed"
        message = (
            f"Your maintenance request for asset "
            f"{maintenance_request.asset.asset_id} "
            f"has been completed."
        )
        severity = Notification.Severity.SUCCESS

    elif (
        maintenance_request.status
        == maintenance_request.Status.REJECTED
    ):
        title = "Maintenance Request Rejected"
        message = (
            f"Your maintenance request for asset "
            f"{maintenance_request.asset.asset_id} "
            f"has been rejected."
        )
        severity = Notification.Severity.DANGER

    else:
        return

    create_notification(
        recipient=maintenance_request.employee.user,
        notification_type=Notification.NotificationType.MAINTENANCE,
        severity=severity,
        title=title,
        message=message,
        reference_type="MaintenanceRequest",
        reference_id=maintenance_request.pk,
    )


def notify_license_expiry(license_obj):
    """
    Notify IT/Super Admin users when a license becomes
    expired or expiring soon.

    The existing SoftwareLicense model already uses
    a 30-day Expiring Soon threshold.
    """

    if not license_obj.expiry_date:
        return

    today = timezone.now().date()
    days_remaining = (
        license_obj.expiry_date - today
    ).days

    if days_remaining < 0:
        title = "Software License Expired"
        message = (
            f"The software license for "
            f"{license_obj.software_name} has expired."
        )
        severity = Notification.Severity.DANGER

    elif days_remaining <= 30:
        title = "Software License Expiring Soon"
        message = (
            f"The software license for "
            f"{license_obj.software_name} expires on "
            f"{license_obj.expiry_date}."
        )
        severity = Notification.Severity.WARNING

    else:
        return

    for user in get_notification_staff():
        create_notification(
            recipient=user,
            notification_type=Notification.NotificationType.LICENSE_EXPIRY,
            severity=severity,
            title=title,
            message=message,
            reference_type="SoftwareLicense",
            reference_id=license_obj.pk,
        )


def notify_asset_warranty_expiry(asset):
    """
    Notify IT/Super Admin users when an asset warranty is
    expired or within 30 days of expiry.
    """

    if not asset.warranty_expiry_date:
        return

    today = timezone.now().date()
    days_remaining = (
        asset.warranty_expiry_date - today
    ).days

    if days_remaining < 0:
        title = "Asset Warranty Expired"
        message = (
            f"The warranty for asset {asset.asset_id} "
            f"({asset.asset_name}) has expired."
        )
        severity = Notification.Severity.DANGER

    elif days_remaining <= 30:
        title = "Asset Warranty Expiring Soon"
        message = (
            f"The warranty for asset {asset.asset_id} "
            f"({asset.asset_name}) expires on "
            f"{asset.warranty_expiry_date}."
        )
        severity = Notification.Severity.WARNING

    else:
        return

    for user in get_notification_staff():
        create_notification(
            recipient=user,
            notification_type=Notification.NotificationType.WARRANTY_EXPIRY,
            severity=severity,
            title=title,
            message=message,
            reference_type="Asset",
            reference_id=asset.pk,
        )


def notify_new_employee(employee_profile):
    """
    Notify HR/IT/Super Admin users when a new employee profile
    is created.
    """

    employee_name = (
        employee_profile.user.get_full_name()
        or employee_profile.user.username
    )

    recipients = User.objects.filter(
        role__in=[
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
            User.Role.HR_MANAGER,
        ],
        is_active=True,
    ).exclude(
        pk=employee_profile.user_id,
    )

    for user in recipients:
        create_notification(
            recipient=user,
            notification_type=Notification.NotificationType.EMPLOYEE_EVENT,
            severity=Notification.Severity.INFO,
            title="New Employee Added",
            message=(
                f"Employee {employee_name} "
                f"({employee_profile.employee_id}) "
                f"has been added to the system."
            ),
            reference_type="EmployeeProfile",
            reference_id=employee_profile.pk,
        )
