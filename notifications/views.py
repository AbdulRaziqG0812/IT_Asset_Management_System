from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Notification


@login_required
def notification_list(request):
    """
    Display notifications belonging only to the currently authenticated user.
    """

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by("-created_at")

    unread_count = notifications.filter(
        is_read=False
    ).count()

    return render(
        request,
        "notifications/list.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark one notification as read.

    Security:
    - User must be authenticated.
    - Only POST is accepted.
    - Notification must belong to the current user.
    - Redirect URLs are validated to prevent unsafe external redirects.
    """

    if request.method != "POST":
        raise PermissionDenied(
            "Notification state can only be changed using POST."
        )

    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        recipient=request.user,
    )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()

        notification.save(
            update_fields=[
                "is_read",
                "read_at",
            ]
        )

    if notification.url:
        if url_has_allowed_host_and_scheme(
            url=notification.url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(notification.url)

    return redirect("notifications:list")


@login_required
def mark_all_notifications_read(request):
    """
    Mark all unread notifications belonging to the current user as read.

    Security:
    - User must be authenticated.
    - Only POST is accepted.
    - Only the current user's notifications are modified.
    """

    if request.method != "POST":
        raise PermissionDenied(
            "Notification state can only be changed using POST."
        )

    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(
        is_read=True,
        read_at=timezone.now(),
    )

    return redirect("notifications:list")
