from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum

from accounts.models import User
from assets.models import Asset
from assignments.models import Assignment
from asset_requests.models import AssetRequest
from maintenance.models import MaintenanceRequest
from software_licenses.models import SoftwareLicense
from vendors.models import Vendor, Purchase
from audit_logs.models import AuditLog


def reports_access_required(request):
    allowed_roles = (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    )

    return request.user.role in allowed_roles


def employee_reports_access_required(request):
    allowed_roles = (
        User.Role.SUPER_ADMIN,
        User.Role.HR_MANAGER,
    )

    return request.user.role in allowed_roles


def audit_reports_access_required(request):
    return request.user.role == User.Role.SUPER_ADMIN


@login_required
def reports_home(request):
    if not reports_access_required(request):
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


@login_required
def asset_report(request):
    if not reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    status_counts = {
        "available": Asset.objects.filter(
            status=Asset.Status.AVAILABLE
        ).count(),
        "assigned": Asset.objects.filter(
            status=Asset.Status.ASSIGNED
        ).count(),
        "under_maintenance": Asset.objects.filter(
            status=Asset.Status.UNDER_MAINTENANCE
        ).count(),
        "damaged": Asset.objects.filter(
            status=Asset.Status.DAMAGED
        ).count(),
        "lost": Asset.objects.filter(
            status=Asset.Status.LOST
        ).count(),
        "retired": Asset.objects.filter(
            status=Asset.Status.RETIRED
        ).count(),
        "disposed": Asset.objects.filter(
            status=Asset.Status.DISPOSED
        ).count(),
    }

    category_counts = {
        item["category"]: item["total"]
        for item in Asset.objects.values("category").annotate(
            total=Count("id")
        )
    }

    department_counts = {
        item["department__name"]: item["total"]
        for item in Asset.objects.values(
            "department__name"
        ).annotate(
            total=Count("id")
        )
    }

    return JsonResponse(
        {
            "report": "ITARMS Asset Report",
            "data": {
                "total_assets": Asset.objects.count(),
                "status_wise": status_counts,
                "category_wise": category_counts,
                "department_wise": department_counts,
            },
        }
    )


@login_required
def assignment_report(request):
    if not reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    total_assignments = Assignment.objects.count()

    active_assignments = Assignment.objects.filter(
        is_active=True
    ).count()

    returned_assignments = Assignment.objects.filter(
        is_active=False
    ).count()

    department_counts = {
        item["employee__department__name"]: item["total"]
        for item in Assignment.objects.values(
            "employee__department__name"
        ).annotate(
            total=Count("id")
        )
    }

    employee_counts = {
        item["employee__employee_id"]: item["total"]
        for item in Assignment.objects.values(
            "employee__employee_id"
        ).annotate(
            total=Count("id")
        )
    }

    return JsonResponse(
        {
            "report": "ITARMS Assignment Report",
            "data": {
                "total_assignments": total_assignments,
                "active_assignments": active_assignments,
                "returned_assignments": returned_assignments,
                "department_wise": department_counts,
                "employee_wise": employee_counts,
            },
        }
    )


@login_required
def maintenance_report(request):
    if not reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    total_requests = MaintenanceRequest.objects.count()

    status_counts = {
        item["status"]: item["total"]
        for item in MaintenanceRequest.objects.values(
            "status"
        ).annotate(
            total=Count("id")
        )
    }

    priority_counts = {
        item["priority"]: item["total"]
        for item in MaintenanceRequest.objects.values(
            "priority"
        ).annotate(
            total=Count("id")
        )
    }

    request_type_counts = {
        item["request_type"]: item["total"]
        for item in MaintenanceRequest.objects.values(
            "request_type"
        ).annotate(
            total=Count("id")
        )
    }

    return JsonResponse(
        {
            "report": "ITARMS Maintenance Report",
            "data": {
                "total_requests": total_requests,
                "status_wise": status_counts,
                "priority_wise": priority_counts,
                "request_type_wise": request_type_counts,
            },
        }
    )


@login_required
def asset_request_report(request):
    if not reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    status_counts = {
        item["status"]: item["total"]
        for item in AssetRequest.objects.values(
            "status"
        ).annotate(
            total=Count("id")
        )
    }

    priority_counts = {
        item["priority"]: item["total"]
        for item in AssetRequest.objects.values(
            "priority"
        ).annotate(
            total=Count("id")
        )
    }

    category_counts = {
        item["asset_category"]: item["total"]
        for item in AssetRequest.objects.values(
            "asset_category"
        ).annotate(
            total=Count("id")
        )
    }

    return JsonResponse(
        {
            "report": "ITARMS Asset Request Report",
            "data": {
                "total_requests": AssetRequest.objects.count(),
                "status_wise": status_counts,
                "priority_wise": priority_counts,
                "category_wise": category_counts,
            },
        }
    )


@login_required
def software_license_report(request):
    if not reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    status_counts = {
        item["status"]: item["total"]
        for item in SoftwareLicense.objects.values(
            "status"
        ).annotate(
            total=Count("id")
        )
    }

    license_type_counts = {
        item["license_type"]: item["total"]
        for item in SoftwareLicense.objects.values(
            "license_type"
        ).annotate(
            total=Count("id")
        )
    }

    total_licenses = SoftwareLicense.objects.aggregate(
        total=Sum("total_licenses")
    )["total"] or 0

    assigned_licenses = SoftwareLicense.objects.aggregate(
        total=Sum("assigned_licenses")
    )["total"] or 0

    available_licenses = total_licenses - assigned_licenses

    return JsonResponse(
        {
            "report": "ITARMS Software License Report",
            "data": {
                "total_license_records": SoftwareLicense.objects.count(),
                "total_licenses": total_licenses,
                "assigned_licenses": assigned_licenses,
                "available_licenses": available_licenses,
                "status_wise": status_counts,
                "license_type_wise": license_type_counts,
            },
        }
    )


@login_required
def vendor_purchase_report(request):
    if not reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    vendor_status_counts = {
        "active": Vendor.objects.filter(
            is_active=True
        ).count(),
        "inactive": Vendor.objects.filter(
            is_active=False
        ).count(),
    }

    purchase_summary = Purchase.objects.aggregate(
        total_purchase_amount=Sum("total_amount")
    )

    vendor_purchase_counts = {
        item["vendor__name"]: item["total"]
        for item in Purchase.objects.values(
            "vendor__name"
        ).annotate(
            total=Count("id")
        )
    }

    vendor_purchase_amounts = {
        item["vendor__name"]: item["total_amount"] or 0
        for item in Purchase.objects.values(
            "vendor__name"
        ).annotate(
            total_amount=Sum("total_amount")
        )
    }

    return JsonResponse(
        {
            "report": "ITARMS Vendor and Purchase Report",
            "data": {
                "total_vendors": Vendor.objects.count(),
                "active_vendors": vendor_status_counts["active"],
                "inactive_vendors": vendor_status_counts["inactive"],
                "total_purchases": Purchase.objects.count(),
                "total_purchase_amount": (
                    purchase_summary["total_purchase_amount"] or 0
                ),
                "purchases_by_vendor": vendor_purchase_counts,
                "purchase_amount_by_vendor": vendor_purchase_amounts,
            },
        }
    )


@login_required
def employee_report(request):
    if not employee_reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access employee reports."
            },
            status=403,
        )

    employee_queryset = User.objects.filter(
        role=User.Role.EMPLOYEE
    )

    department_counts = {
        item["department__name"]: item["total"]
        for item in employee_queryset.values(
            "department__name"
        ).annotate(
            total=Count("id")
        )
    }

    active_count = employee_queryset.filter(
        is_active=True
    ).count()

    inactive_count = employee_queryset.filter(
        is_active=False
    ).count()

    return JsonResponse(
        {
            "report": "ITARMS Employee Report",
            "data": {
                "total_employees": employee_queryset.count(),
                "active_employees": active_count,
                "inactive_employees": inactive_count,
                "department_wise": department_counts,
            },
        }
    )


@login_required
def department_report(request):
    allowed_roles = (
        User.Role.SUPER_ADMIN,
        User.Role.HR_MANAGER,
        User.Role.DEPARTMENT_MANAGER,
    )

    if request.user.role not in allowed_roles:
        return JsonResponse(
            {
                "detail": "You do not have permission to access department reports."
            },
            status=403,
        )

    if request.user.role == User.Role.DEPARTMENT_MANAGER:
        department = request.user.department

        if not department:
            return JsonResponse(
                {
                    "report": "ITARMS Department Report",
                    "data": {
                        "department": None,
                        "employee_count": 0,
                        "assigned_asset_count": 0,
                    },
                }
            )

        employee_count = User.objects.filter(
            role=User.Role.EMPLOYEE,
            employee_profile__department=department,
        ).count()

        assigned_asset_count = Asset.objects.filter(
            department=department,
            status=Asset.Status.ASSIGNED,
        ).count()

        return JsonResponse(
            {
                "report": "ITARMS Department Report",
                "data": {
                    "department": department.name,
                    "employee_count": employee_count,
                    "assigned_asset_count": assigned_asset_count,
                },
            }
        )

    department_employee_counts = {
        item["department__name"]: item["total"]
        for item in User.objects.filter(
            role=User.Role.EMPLOYEE
        ).values(
            "department__name"
        ).annotate(
            total=Count("id")
        )
    }

    department_asset_counts = {
        item["department__name"]: item["total"]
        for item in Asset.objects.values(
            "department__name"
        ).annotate(
            total=Count("id")
        )
    }

    return JsonResponse(
        {
            "report": "ITARMS Department Report",
            "data": {
                "employee_wise": department_employee_counts,
                "asset_wise": department_asset_counts,
            },
        }
    )


@login_required
def audit_log_report(request):
    if not audit_reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access audit reports."
            },
            status=403,
        )

    action_counts = {
        item["action"]: item["total"]
        for item in AuditLog.objects.values(
            "action"
        ).annotate(
            total=Count("id")
        )
    }

    module_counts = {
        item["module"]: item["total"]
        for item in AuditLog.objects.values(
            "module"
        ).annotate(
            total=Count("id")
        )
    }

    user_counts = {
        item["user__username"]: item["total"]
        for item in AuditLog.objects.values(
            "user__username"
        ).annotate(
            total=Count("id")
        )
    }

    return JsonResponse(
        {
            "report": "ITARMS Audit Log Report",
            "data": {
                "total_audit_logs": AuditLog.objects.count(),
                "action_wise": action_counts,
                "module_wise": module_counts,
                "user_wise": user_counts,
            },
        }
    )