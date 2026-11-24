from django.urls import path

from .views import (
    admin_asset_incident_list,
    admin_asset_incident_process,
    asset_create,
    asset_delete,
    asset_detail,
    asset_dispose,
    asset_list,
    asset_retire,
    asset_update,
    employee_asset_detail,
    employee_asset_incident_create,
    employee_asset_incident_list,
)

urlpatterns = [
    path(
        "",
        asset_list,
        name="asset_list",
    ),

    path(
        "add/",
        asset_create,
        name="asset_create",
    ),

    # =========================
    # EMPLOYEE ASSET ROUTES
    # =========================

    path(
        "employee/<int:asset_id>/",
        employee_asset_detail,
        name="employee_asset_detail",
    ),

    path(
        "employee/report/",
        employee_asset_incident_create,
        name="employee_asset_incident_create",
    ),

    path(
        "employee/reports/",
        employee_asset_incident_list,
        name="employee_asset_incident_list",
    ),

    # =========================
    # ADMIN INCIDENT ROUTES
    # =========================

    path(
        "admin/incidents/",
        admin_asset_incident_list,
        name="admin_asset_incident_list",
    ),

    path(
        "admin/incidents/<int:incident_id>/process/",
        admin_asset_incident_process,
        name="admin_asset_incident_process",
    ),

    # =========================
    # ASSET MANAGEMENT ROUTES
    # =========================

    path(
        "<int:asset_id>/",
        asset_detail,
        name="asset_detail",
    ),

    path(
        "<int:asset_id>/edit/",
        asset_update,
        name="asset_update",
    ),

    path(
        "<int:asset_id>/retire/",
        asset_retire,
        name="asset_retire",
    ),

    path(
        "<int:asset_id>/dispose/",
        asset_dispose,
        name="asset_dispose",
    ),

    path(
        "<int:asset_id>/delete/",
        asset_delete,
        name="asset_delete",
    ),
]