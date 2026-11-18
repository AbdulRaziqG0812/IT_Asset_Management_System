from django.urls import path

from .views import (
    reports_home,
    asset_report,
    assignment_report,
    maintenance_report,
    asset_request_report,
    software_license_report,
    vendor_purchase_report,
    employee_report,
    department_report,
    audit_log_report,
)


app_name = "reports"


urlpatterns = [
    path("", reports_home, name="home"),

    # Asset Reports
    path("assets/", asset_report, name="asset_report"),

    # Assignment Reports
    path(
        "assignments/",
        assignment_report,
        name="assignment_report",
    ),

    # Maintenance Reports
    path(
        "maintenance/",
        maintenance_report,
        name="maintenance_report",
    ),

    # Asset Request Reports
    path(
        "asset-requests/",
        asset_request_report,
        name="asset_request_report",
    ),

    # Software License Reports
    path(
        "software-licenses/",
        software_license_report,
        name="software_license_report",
    ),

    # Vendor & Purchase Reports
    path(
        "vendors-purchases/",
        vendor_purchase_report,
        name="vendor_purchase_report",
    ),

    # Employee Reports
    path(
        "employees/",
        employee_report,
        name="employee_report",
    ),

    # Department Reports
    path(
        "departments/",
        department_report,
        name="department_report",
    ),

    # Audit Log Reports
    path(
        "audit-logs/",
        audit_log_report,
        name="audit_log_report",
    ),
]