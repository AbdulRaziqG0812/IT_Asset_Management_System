from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
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


def render_report_page(
    request,
    title,
    summary=None,
    tables=None,
    chart_data=None,
):
    return render(
        request,
        "reports/report_detail.html",
        {
            "report_title": title,
            "summary": summary or [],
            "tables": tables or [],
            "chart_data": chart_data or {},
        },
    )


@login_required
def reports_home(request):
    if not reports_access_required(request):
        return JsonResponse(
            {
                "detail": "You do not have permission to access reports."
            },
            status=403,
        )

    # ---------------------------------------------------------
    # Summary statistics
    # ---------------------------------------------------------

    total_assets = Asset.objects.count()

    total_employees = User.objects.filter(
        role=User.Role.EMPLOYEE
    ).count()

    total_assignments = Assignment.objects.count()

    active_assignments = Assignment.objects.filter(
        is_active=True
    ).count()

    total_asset_requests = AssetRequest.objects.count()

    pending_asset_requests = AssetRequest.objects.filter(
        status=AssetRequest.Status.PENDING
    ).count()

    total_maintenance_requests = MaintenanceRequest.objects.count()

    pending_maintenance_requests = MaintenanceRequest.objects.filter(
        status=MaintenanceRequest.Status.PENDING
    ).count()

    total_software_licenses = SoftwareLicense.objects.count()

    total_vendors = Vendor.objects.count()

    total_purchases = Purchase.objects.count()

    # ---------------------------------------------------------
    # Asset status data
    # ---------------------------------------------------------

    asset_status_counts = {
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

    # ---------------------------------------------------------
    # Asset category data
    # ---------------------------------------------------------

    asset_category_counts = {
        item["category"]: item["total"]
        for item in Asset.objects.values(
            "category"
        ).annotate(
            total=Count("id")
        )
    }

    # ---------------------------------------------------------
    # Asset department data
    # ---------------------------------------------------------

    asset_department_counts = {
        item["department__name"]: item["total"]
        for item in Asset.objects.values(
            "department__name"
        ).annotate(
            total=Count("id")
        )
    }

    # ---------------------------------------------------------
    # Maintenance status data
    # ---------------------------------------------------------

    maintenance_status_counts = {
        item["status"]: item["total"]
        for item in MaintenanceRequest.objects.values(
            "status"
        ).annotate(
            total=Count("id")
        )
    }

    # ---------------------------------------------------------
    # Asset request status data
    # ---------------------------------------------------------

    asset_request_status_counts = {
        item["status"]: item["total"]
        for item in AssetRequest.objects.values(
            "status"
        ).annotate(
            total=Count("id")
        )
    }

    # ---------------------------------------------------------
    # Dashboard data
    # ---------------------------------------------------------

    data = {
        "total_assets": total_assets,
        "total_employees": total_employees,
        "total_assignments": total_assignments,
        "active_assignments": active_assignments,
        "total_asset_requests": total_asset_requests,
        "pending_asset_requests": pending_asset_requests,
        "total_maintenance_requests": total_maintenance_requests,
        "pending_maintenance_requests": pending_maintenance_requests,
        "total_software_licenses": total_software_licenses,
        "total_vendors": total_vendors,
        "total_purchases": total_purchases,
    }

    chart_data = {
        "asset_status": asset_status_counts,
        "asset_category": asset_category_counts,
        "asset_department": asset_department_counts,
        "maintenance_status": maintenance_status_counts,
        "asset_request_status": asset_request_status_counts,
    }

    return render(
        request,
        "reports/reports_home.html",
        {
            "data": data,
            "chart_data": chart_data,
        },
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
        for item in Asset.objects.values(
            "category"
        ).annotate(
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

    summary = [
        {
            "label": "Total Assets",
            "value": Asset.objects.count(),
        },
    ]

    tables = [
        {
            "title": "Assets by Status",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in status_counts.items()
            ],
        },
        {
            "title": "Assets by Category",
            "rows": [
                {
                    "label": key or "Unspecified",
                    "value": value,
                }
                for key, value in category_counts.items()
            ],
        },
        {
            "title": "Assets by Department",
            "rows": [
                {
                    "label": key or "Unassigned",
                    "value": value,
                }
                for key, value in department_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Asset Report",
        summary=summary,
        tables=tables,
        chart_data={
            "status": status_counts,
            "category": category_counts,
            "department": department_counts,
        },
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

    summary = [
        {
            "label": "Total Assignments",
            "value": total_assignments,
        },
        {
            "label": "Active Assignments",
            "value": active_assignments,
        },
        {
            "label": "Returned Assignments",
            "value": returned_assignments,
        },
    ]

    tables = [
        {
            "title": "Assignments by Department",
            "rows": [
                {
                    "label": key or "Unassigned",
                    "value": value,
                }
                for key, value in department_counts.items()
            ],
        },
        {
            "title": "Assignments by Employee",
            "rows": [
                {
                    "label": key or "Unknown Employee",
                    "value": value,
                }
                for key, value in employee_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Assignment Report",
        summary=summary,
        tables=tables,
        chart_data={
            "department": department_counts,
            "employee": employee_counts,
        },
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

    summary = [
        {
            "label": "Total Maintenance Requests",
            "value": total_requests,
        },
    ]

    tables = [
        {
            "title": "Requests by Status",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in status_counts.items()
            ],
        },
        {
            "title": "Requests by Priority",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in priority_counts.items()
            ],
        },
        {
            "title": "Requests by Type",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in request_type_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Maintenance Report",
        summary=summary,
        tables=tables,
        chart_data={
            "status": status_counts,
            "priority": priority_counts,
            "request_type": request_type_counts,
        },
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

    summary = [
        {
            "label": "Total Asset Requests",
            "value": AssetRequest.objects.count(),
        },
    ]

    tables = [
        {
            "title": "Requests by Status",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in status_counts.items()
            ],
        },
        {
            "title": "Requests by Priority",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in priority_counts.items()
            ],
        },
        {
            "title": "Requests by Category",
            "rows": [
                {
                    "label": key or "Unspecified",
                    "value": value,
                }
                for key, value in category_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Asset Request Report",
        summary=summary,
        tables=tables,
        chart_data={
            "status": status_counts,
            "priority": priority_counts,
            "category": category_counts,
        },
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

    summary = [
        {
            "label": "License Records",
            "value": SoftwareLicense.objects.count(),
        },
        {
            "label": "Total Licenses",
            "value": total_licenses,
        },
        {
            "label": "Assigned Licenses",
            "value": assigned_licenses,
        },
        {
            "label": "Available Licenses",
            "value": available_licenses,
        },
    ]

    tables = [
        {
            "title": "Licenses by Status",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in status_counts.items()
            ],
        },
        {
            "title": "Licenses by Type",
            "rows": [
                {
                    "label": key or "Unspecified",
                    "value": value,
                }
                for key, value in license_type_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Software License Report",
        summary=summary,
        tables=tables,
        chart_data={
            "status": status_counts,
            "license_type": license_type_counts,
        },
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

    summary = [
        {
            "label": "Total Vendors",
            "value": Vendor.objects.count(),
        },
        {
            "label": "Active Vendors",
            "value": vendor_status_counts["active"],
        },
        {
            "label": "Inactive Vendors",
            "value": vendor_status_counts["inactive"],
        },
        {
            "label": "Total Purchases",
            "value": Purchase.objects.count(),
        },
        {
            "label": "Total Purchase Amount",
            "value": purchase_summary["total_purchase_amount"] or 0,
        },
    ]

    tables = [
        {
            "title": "Vendor Status",
            "rows": [
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
                for key, value in vendor_status_counts.items()
            ],
        },
        {
            "title": "Purchases by Vendor",
            "rows": [
                {
                    "label": key or "Unknown Vendor",
                    "value": value,
                }
                for key, value in vendor_purchase_counts.items()
            ],
        },
        {
            "title": "Purchase Amount by Vendor",
            "rows": [
                {
                    "label": key or "Unknown Vendor",
                    "value": value,
                }
                for key, value in vendor_purchase_amounts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Vendor and Purchase Report",
        summary=summary,
        tables=tables,
        chart_data={
            "vendor_status": vendor_status_counts,
            "purchases_by_vendor": vendor_purchase_counts,
            "purchase_amount_by_vendor": vendor_purchase_amounts,
        },
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

    total_employees = employee_queryset.count()

    summary = [
        {
            "label": "Total Employees",
            "value": total_employees,
        },
        {
            "label": "Active Employees",
            "value": active_count,
        },
        {
            "label": "Inactive Employees",
            "value": inactive_count,
        },
    ]

    tables = [
        {
            "title": "Employees by Department",
            "rows": [
                {
                    "label": key or "Unassigned",
                    "value": value,
                }
                for key, value in department_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Employee Report",
        summary=summary,
        tables=tables,
        chart_data={
            "department": department_counts,
            "employee_status": {
                "active": active_count,
                "inactive": inactive_count,
            },
        },
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
            summary = [
                {
                    "label": "Department",
                    "value": "Not Assigned",
                },
                {
                    "label": "Employee Count",
                    "value": 0,
                },
                {
                    "label": "Assigned Asset Count",
                    "value": 0,
                },
            ]

            return render_report_page(
                request,
                "ITARMS Department Report",
                summary=summary,
                tables=[],
                chart_data={},
            )

        employee_count = User.objects.filter(
            role=User.Role.EMPLOYEE,
            employee_profile__department=department,
        ).count()

        assigned_asset_count = Asset.objects.filter(
            department=department,
            status=Asset.Status.ASSIGNED,
        ).count()

        summary = [
            {
                "label": "Department",
                "value": department.name,
            },
            {
                "label": "Employee Count",
                "value": employee_count,
            },
            {
                "label": "Assigned Asset Count",
                "value": assigned_asset_count,
            },
        ]

        return render_report_page(
            request,
            "ITARMS Department Report",
            summary=summary,
            tables=[],
            chart_data={
                "department_summary": {
                    "employees": employee_count,
                    "assigned_assets": assigned_asset_count,
                }
            },
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

    tables = [
        {
            "title": "Employees by Department",
            "rows": [
                {
                    "label": key or "Unassigned",
                    "value": value,
                }
                for key, value in department_employee_counts.items()
            ],
        },
        {
            "title": "Assets by Department",
            "rows": [
                {
                    "label": key or "Unassigned",
                    "value": value,
                }
                for key, value in department_asset_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Department Report",
        summary=[],
        tables=tables,
        chart_data={
            "employees": department_employee_counts,
            "assets": department_asset_counts,
        },
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

    summary = [
        {
            "label": "Total Audit Logs",
            "value": AuditLog.objects.count(),
        },
    ]

    tables = [
        {
            "title": "Audit Logs by Action",
            "rows": [
                {
                    "label": key or "Unknown",
                    "value": value,
                }
                for key, value in action_counts.items()
            ],
        },
        {
            "title": "Audit Logs by Module",
            "rows": [
                {
                    "label": key or "Unknown",
                    "value": value,
                }
                for key, value in module_counts.items()
            ],
        },
        {
            "title": "Audit Logs by User",
            "rows": [
                {
                    "label": key or "Unknown User",
                    "value": value,
                }
                for key, value in user_counts.items()
            ],
        },
    ]

    return render_report_page(
        request,
        "ITARMS Audit Log Report",
        summary=summary,
        tables=tables,
        chart_data={
            "action": action_counts,
            "module": module_counts,
            "user": user_counts,
        },
    )