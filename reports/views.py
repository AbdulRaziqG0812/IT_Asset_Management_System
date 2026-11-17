from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from accounts.models import User
from assets.models import Asset
from assignments.models import Assignment
from asset_requests.models import AssetRequest
from maintenance.models import MaintenanceRequest
from software_licenses.models import SoftwareLicense
from vendors.models import Vendor, Purchase


@login_required
def reports_home(request):
    allowed_roles = (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    )

    if request.user.role not in allowed_roles:
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    data = {
        "total_assets": Asset.objects.count(),
        "total_employees": User.objects.filter(
            role=User.Role.EMPLOYEE
        ).count(),
        "total_assignments": Assignment.objects.count(),
        "active_assignments": Assignment.objects.filter(
            is_active=True
        ).count(),
        "total_asset_requests": AssetRequest.objects.count(),
        "pending_asset_requests": AssetRequest.objects.filter(
            status=AssetRequest.Status.PENDING
        ).count(),
        "total_maintenance_requests": MaintenanceRequest.objects.count(),
        "pending_maintenance_requests": MaintenanceRequest.objects.filter(
            status=MaintenanceRequest.Status.PENDING
        ).count(),
        "total_software_licenses": SoftwareLicense.objects.count(),
        "total_vendors": Vendor.objects.count(),
        "total_purchases": Purchase.objects.count(),
    }

    return JsonResponse(
        {
            "report": "ITARMS Summary Report",
            "data": data,
        }
    )