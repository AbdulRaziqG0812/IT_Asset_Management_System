from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.models import EmployeeProfile, User
from assets.models import Asset
from assignments.models import Assignment
from asset_requests.models import AssetRequest
from maintenance.models import MaintenanceRequest
from software_licenses.models import SoftwareLicense
from vendors.models import Purchase


def _base_asset_queryset(user):
    """
    Return only the assets the current user is authorized to see.

    Super Admin / IT Admin:
        All assets.

    HR Manager:
        All assets because HR needs employee/assigned-asset reporting.

    Department Manager:
        Assets belonging to the manager's department.

    Employee:
        Only assets currently assigned to that employee.
    """
    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
        User.Role.HR_MANAGER,
    ):
        return Asset.objects.all()

    if user.role == User.Role.DEPARTMENT_MANAGER:
        if not user.department_id:
            return Asset.objects.none()

        return Asset.objects.filter(
            department_id=user.department_id
        )

    if user.role == User.Role.EMPLOYEE:
        return Asset.objects.filter(
            assignments__employee__user=user,
            assignments__is_active=True,
        ).distinct()

    return Asset.objects.none()


def _base_assignment_queryset(user):
    """
    Return only assignments the current user is authorized to see.
    """
    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
        User.Role.HR_MANAGER,
    ):
        return Assignment.objects.all()

    if user.role == User.Role.DEPARTMENT_MANAGER:
        if not user.department_id:
            return Assignment.objects.none()

        return Assignment.objects.filter(
            employee__department_id=user.department_id
        )

    if user.role == User.Role.EMPLOYEE:
        return Assignment.objects.filter(
            employee__user=user
        )

    return Assignment.objects.none()


def _base_asset_request_queryset(user):
    """
    Return only asset requests the current user is authorized to see.

    Super Admin / IT Admin:
        All requests.

    HR Manager:
        HR is not given global asset-request management data.

    Department Manager:
        Requests belonging to their department.

    Employee:
        Own requests only.
    """
    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    ):
        return AssetRequest.objects.all()

    if user.role == User.Role.HR_MANAGER:
        return AssetRequest.objects.none()

    if user.role == User.Role.DEPARTMENT_MANAGER:
        if not user.department_id:
            return AssetRequest.objects.none()

        return AssetRequest.objects.filter(
            department_id=user.department_id
        )

    if user.role == User.Role.EMPLOYEE:
        return AssetRequest.objects.filter(
            employee__user=user
        )

    return AssetRequest.objects.none()


def _base_maintenance_queryset(user):
    """
    Return only maintenance requests the current user is authorized to see.

    Super Admin / IT Admin:
        All maintenance requests.

    HR Manager:
        HR is not given global maintenance management data.

    Department Manager:
        Maintenance requests belonging to their department.

    Employee:
        Own maintenance requests only.
    """
    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    ):
        return MaintenanceRequest.objects.all()

    if user.role == User.Role.HR_MANAGER:
        return MaintenanceRequest.objects.none()

    if user.role == User.Role.DEPARTMENT_MANAGER:
        if not user.department_id:
            return MaintenanceRequest.objects.none()

        return MaintenanceRequest.objects.filter(
            employee__department_id=user.department_id
        )

    if user.role == User.Role.EMPLOYEE:
        return MaintenanceRequest.objects.filter(
            employee__user=user
        )

    return MaintenanceRequest.objects.none()


def _base_employee_queryset(user):
    """
    Return only employee records the current user is authorized to see.

    Super Admin / IT Admin / HR Manager:
        All employee records.

    Department Manager:
        Employees in their own department.

    Employee:
        Own employee profile only.
    """
    if user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
        User.Role.HR_MANAGER,
    ):
        return EmployeeProfile.objects.select_related(
            "user",
            "department",
        )

    if user.role == User.Role.DEPARTMENT_MANAGER:
        if not user.department_id:
            return EmployeeProfile.objects.none()

        return EmployeeProfile.objects.filter(
            department_id=user.department_id
        ).select_related(
            "user",
            "department",
        )

    if user.role == User.Role.EMPLOYEE:
        return EmployeeProfile.objects.filter(
            user=user
        ).select_related(
            "user",
            "department",
        )

    return EmployeeProfile.objects.none()


def _can_view_license_data(user):
    """
    Software license information is restricted to Super Admin
    and IT Admin according to the RBAC model.
    """
    return user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    )


def _can_view_purchase_data(user):
    """
    Purchase information is restricted to Super Admin
    and IT Admin.
    """
    return user.role in (
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    )


def _serialize_recent_asset(asset):
    return {
        "id": asset.id,
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "category": asset.category,
        "status": asset.status,
        "department": (
            asset.department.name
            if asset.department
            else None
        ),
        "location": asset.asset_location,
        "created_at": (
            asset.created_at.isoformat()
            if asset.created_at
            else None
        ),
    }


def _serialize_recent_assignment(assignment):
    employee = assignment.employee

    return {
        "id": assignment.id,
        "asset_id": assignment.asset.asset_id,
        "asset_name": assignment.asset.asset_name,
        "employee_id": employee.employee_id,
        "employee_name": (
            employee.user.get_full_name()
            or employee.user.username
        ),
        "assigned_date": (
            assignment.assigned_date.isoformat()
            if assignment.assigned_date
            else None
        ),
        "return_date": (
            assignment.return_date.isoformat()
            if assignment.return_date
            else None
        ),
        "is_active": assignment.is_active,
    }


def _serialize_recent_asset_request(request):
    employee = request.employee

    return {
        "id": request.id,
        "asset_category": request.asset_category,
        "asset_name": request.asset_name,
        "quantity": request.quantity,
        "priority": request.priority,
        "status": request.status,
        "employee": (
            employee.user.get_full_name()
            or employee.user.username
        ),
        "requested_at": (
            request.requested_at.isoformat()
            if request.requested_at
            else None
        ),
    }


def _serialize_recent_maintenance(request):
    employee = request.employee

    return {
        "id": request.id,
        "asset_id": request.asset.asset_id,
        "asset_name": request.asset.asset_name,
        "request_type": request.request_type,
        "priority": request.priority,
        "status": request.status,
        "employee": (
            employee.user.get_full_name()
            or employee.user.username
        ),
        "requested_at": (
            request.requested_at.isoformat()
            if request.requested_at
            else None
        ),
    }


def _build_asset_statistics(asset_queryset):
    return {
        "total": asset_queryset.count(),
        "available": asset_queryset.filter(
            status=Asset.Status.AVAILABLE
        ).count(),
        "assigned": asset_queryset.filter(
            status=Asset.Status.ASSIGNED
        ).count(),
        "under_maintenance": asset_queryset.filter(
            status=Asset.Status.UNDER_MAINTENANCE
        ).count(),
        "damaged": asset_queryset.filter(
            status=Asset.Status.DAMAGED
        ).count(),
        "lost": asset_queryset.filter(
            status=Asset.Status.LOST
        ).count(),
        "retired": asset_queryset.filter(
            status=Asset.Status.RETIRED
        ).count(),
        "disposed": asset_queryset.filter(
            status=Asset.Status.DISPOSED
        ).count(),
    }


def _build_license_statistics(user):
    """
    Return license statistics only to authorized roles.
    Other roles receive a privacy-safe empty structure.
    """
    empty_data = {
        "total_software_license_records": 0,
        "total_licenses": 0,
        "assigned_licenses": 0,
        "available_licenses": 0,
        "licenses_nearing_expiry": 0,
    }

    if not _can_view_license_data(user):
        return empty_data

    license_queryset = SoftwareLicense.objects.all()

    today = timezone.localdate()
    expiry_limit = today + timedelta(days=30)

    expiring_licenses = license_queryset.filter(
        expiry_date__isnull=False,
        expiry_date__gte=today,
        expiry_date__lte=expiry_limit,
    ).count()

    total_license_records = license_queryset.count()

    total_license_quantity = (
        license_queryset.aggregate(
            total=Sum("total_licenses")
        )["total"]
        or 0
    )

    assigned_license_quantity = (
        license_queryset.aggregate(
            total=Sum("assigned_licenses")
        )["total"]
        or 0
    )

    return {
        "total_software_license_records": total_license_records,
        "total_licenses": total_license_quantity,
        "assigned_licenses": assigned_license_quantity,
        "available_licenses": max(
            total_license_quantity - assigned_license_quantity,
            0,
        ),
        "licenses_nearing_expiry": expiring_licenses,
    }


def _build_purchase_statistics(user):
    """
    Return purchase statistics only to Super Admin and IT Admin.
    """
    if not _can_view_purchase_data(user):
        return {
            "monthly_purchases": {},
        }

    purchase_queryset = Purchase.objects.all()

    monthly_purchase_data = {}

    for purchase in purchase_queryset:
        if not purchase.purchase_date:
            continue

        month_key = purchase.purchase_date.strftime("%Y-%m")

        monthly_purchase_data[month_key] = (
            monthly_purchase_data.get(month_key, 0)
            + float(purchase.total_amount or 0)
        )

    return {
        "monthly_purchases": monthly_purchase_data,
    }


def _build_common_dashboard(user):
    assets = _base_asset_queryset(user)
    assignments = _base_assignment_queryset(user)
    asset_requests = _base_asset_request_queryset(user)
    maintenance_requests = _base_maintenance_queryset(user)
    employees = _base_employee_queryset(user)

    asset_category_counts = {
        item["category"]: item["total"]
        for item in assets.values("category").annotate(
            total=Count("id")
        )
    }

    asset_department_counts = {
        item["department__name"]: item["total"]
        for item in assets.values("department__name").annotate(
            total=Count("id")
        )
    }

    asset_status_counts = {
        item["status"]: item["total"]
        for item in assets.values("status").annotate(
            total=Count("id")
        )
    }

    maintenance_status_counts = {
        item["status"]: item["total"]
        for item in maintenance_requests.values("status").annotate(
            total=Count("id")
        )
    }

    license_statistics = _build_license_statistics(user)
    purchase_statistics = _build_purchase_statistics(user)

    return {
        "asset_statistics": _build_asset_statistics(assets),

        "total_employees": employees.count(),

        "active_employees": employees.filter(
            employment_status=EmployeeProfile.EmploymentStatus.ACTIVE
        ).count(),

        "total_assignments": assignments.count(),

        "active_assignments": assignments.filter(
            is_active=True
        ).count(),

        "total_asset_requests": asset_requests.count(),

        "pending_asset_requests": asset_requests.filter(
            status=AssetRequest.Status.PENDING
        ).count(),

        "total_maintenance_requests": maintenance_requests.count(),

        "pending_maintenance_requests": maintenance_requests.filter(
            status=MaintenanceRequest.Status.PENDING
        ).count(),

        **license_statistics,

        "asset_category_wise": asset_category_counts,

        "asset_department_wise": asset_department_counts,

        "asset_status_wise": asset_status_counts,

        "maintenance_status_wise": maintenance_status_counts,

        **purchase_statistics,

        "recent_assets": [
            _serialize_recent_asset(asset)
            for asset in assets.order_by("-created_at")[:5]
        ],

        "recent_assignments": [
            _serialize_recent_assignment(assignment)
            for assignment in assignments.select_related(
                "asset",
                "employee__user",
            ).order_by("-created_at")[:5]
        ],

        "recent_asset_requests": [
            _serialize_recent_asset_request(request)
            for request in asset_requests.select_related(
                "employee__user",
            ).order_by("-requested_at")[:5]
        ],

        "recent_maintenance_requests": [
            _serialize_recent_maintenance(request)
            for request in maintenance_requests.select_related(
                "asset",
                "employee__user",
            ).order_by("-requested_at")[:5]
        ],
    }


def _build_employee_dashboard(user):
    """
    Employee-specific dashboard data.

    Only the logged-in employee's own profile,
    assigned assets, requests and maintenance records
    are returned.
    """
    employee_profile = (
        EmployeeProfile.objects
        .select_related(
            "user",
            "department",
        )
        .filter(user=user)
        .first()
    )

    if not employee_profile:
        return {
            "profile": None,
            "assigned_assets": [],
            "asset_requests": [],
            "maintenance_requests": [],
        }

    assigned_assets = Asset.objects.filter(
        assignments__employee=employee_profile,
        assignments__is_active=True,
    ).distinct()

    asset_requests = AssetRequest.objects.filter(
        employee=employee_profile
    ).order_by("-requested_at")

    maintenance_requests = MaintenanceRequest.objects.filter(
        employee=employee_profile
    ).order_by("-requested_at")

    return {
        "profile": {
            "employee_id": employee_profile.employee_id,
            "name": (
                user.get_full_name()
                or user.username
            ),
            "job_title": employee_profile.job_title,
            "department": (
                employee_profile.department.name
                if employee_profile.department
                else None
            ),
            "employment_status": employee_profile.employment_status,
            "asset_return_status": employee_profile.asset_return_status,
        },

        "assigned_assets": [
            _serialize_recent_asset(asset)
            for asset in assigned_assets.order_by("asset_name")
        ],

        "asset_requests": [
            _serialize_recent_asset_request(request)
            for request in asset_requests[:10]
        ],

        "maintenance_requests": [
            _serialize_recent_maintenance(request)
            for request in maintenance_requests[:10]
        ],
    }


def _get_dashboard_data(user):
    """
    Build the complete dashboard data while preserving
    all existing RBAC and privacy restrictions.
    """
    dashboard_data = {
        "role": user.role,
        "role_display": user.get_role_display(),
        "data": _build_common_dashboard(user),
    }

    if user.role == User.Role.EMPLOYEE:
        dashboard_data["data"]["employee_dashboard"] = (
            _build_employee_dashboard(user)
        )

    return dashboard_data


@login_required
def dashboard_home(request):
    user = request.user

    if not user.is_active:
        return JsonResponse(
            {
                "detail": "Your account is inactive."
            },
            status=403,
        )

    if user.role not in User.Role.values:
        return JsonResponse(
            {
                "detail": "Invalid user role."
            },
            status=403,
        )

    dashboard_data = _get_dashboard_data(user)

    accept_header = request.headers.get(
        "Accept",
        ""
    )

    if "application/json" in accept_header:
        return JsonResponse(dashboard_data)

    return render(
        request,
        "dashboard/home.html",
    )