from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.models import EmployeeProfile
from asset_requests.models import AssetRequest
from assets.models import Asset
from maintenance.models import MaintenanceRequest
from software_licenses.models import SoftwareLicense

from .services import (
    notify_asset_request_status_change,
    notify_asset_warranty_expiry,
    notify_license_expiry,
    notify_maintenance_status_change,
    notify_new_employee,
    notify_pending_asset_request,
    notify_pending_maintenance_request,
)


# ---------------------------------------------------------------------------
# Asset Request Notifications
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=AssetRequest, dispatch_uid="notifications_asset_request_pre_save")
def asset_request_pre_save(sender, instance, **kwargs):
    """
    Store the previous status before saving so the post_save signal
    can detect an actual status transition.
    """

    if not instance.pk:
        instance._notification_old_status = None
        return

    try:
        old_instance = sender.objects.only("status").get(
            pk=instance.pk
        )
        instance._notification_old_status = old_instance.status
    except sender.DoesNotExist:
        instance._notification_old_status = None


@receiver(post_save, sender=AssetRequest, dispatch_uid="notifications_asset_request_post_save")
def asset_request_post_save(sender, instance, created, **kwargs):
    """
    Create notifications when:
    - a new pending asset request is created
    - an existing asset request changes status
    """

    if (
        created
        and instance.status == AssetRequest.Status.PENDING
    ):
        notify_pending_asset_request(instance)
        return

    old_status = getattr(
        instance,
        "_notification_old_status",
        None,
    )

    if not created and old_status and old_status != instance.status:
        notify_asset_request_status_change(
            instance,
            old_status,
        )


# ---------------------------------------------------------------------------
# Maintenance Request Notifications
# ---------------------------------------------------------------------------

@receiver(
    pre_save,
    sender=MaintenanceRequest,
    dispatch_uid="notifications_maintenance_request_pre_save",
)
def maintenance_request_pre_save(sender, instance, **kwargs):
    """
    Store the previous maintenance status before saving.
    """

    if not instance.pk:
        instance._notification_old_status = None
        return

    try:
        old_instance = sender.objects.only("status").get(
            pk=instance.pk
        )
        instance._notification_old_status = old_instance.status
    except sender.DoesNotExist:
        instance._notification_old_status = None


@receiver(
    post_save,
    sender=MaintenanceRequest,
    dispatch_uid="notifications_maintenance_request_post_save",
)
def maintenance_request_post_save(sender, instance, created, **kwargs):
    """
    Create notifications when:
    - a new pending maintenance request is created
    - an existing maintenance request changes status
    """

    if (
        created
        and instance.status == MaintenanceRequest.Status.PENDING
    ):
        notify_pending_maintenance_request(instance)
        return

    old_status = getattr(
        instance,
        "_notification_old_status",
        None,
    )

    if not created and old_status and old_status != instance.status:
        notify_maintenance_status_change(
            instance,
            old_status,
        )


# ---------------------------------------------------------------------------
# Software License Notifications
# ---------------------------------------------------------------------------

@receiver(
    post_save,
    sender=SoftwareLicense,
    dispatch_uid="notifications_software_license_post_save",
)
def software_license_post_save(sender, instance, created, **kwargs):
    """
    Check software license expiry after every save.
    The service handles whether an alert is actually required.
    """

    notify_license_expiry(instance)


# ---------------------------------------------------------------------------
# Asset Warranty Notifications
# ---------------------------------------------------------------------------

@receiver(
    post_save,
    sender=Asset,
    dispatch_uid="notifications_asset_post_save",
)
def asset_post_save(sender, instance, created, **kwargs):
    """
    Check asset warranty expiry after every save.
    The service handles whether an alert is actually required.
    """

    notify_asset_warranty_expiry(instance)


# ---------------------------------------------------------------------------
# Employee Notifications
# ---------------------------------------------------------------------------

@receiver(
    post_save,
    sender=EmployeeProfile,
    dispatch_uid="notifications_employee_profile_post_save",
)
def employee_profile_post_save(sender, instance, created, **kwargs):
    """
    Notify authorized staff when a new employee profile is created.
    """

    if created:
        notify_new_employee(instance)
