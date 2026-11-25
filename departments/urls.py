from django.urls import path

from .views import (
    department_manager_dashboard,
    department_manager_employees,
    department_manager_assets,
    department_manager_asset_detail,
    department_manager_asset_allocation,
    department_manager_employee_detail,
    department_manager_create_asset_request,
    department_manager_asset_requests,
    department_manager_process_asset_request,

    # Super Admin Department Management
    super_admin_department_list,
    super_admin_department_create,
    super_admin_department_edit,
    super_admin_department_delete,
)


urlpatterns = [
    # =========================================================================
    # DEPARTMENT MANAGER
    # =========================================================================

    path(
        "manager/",
        department_manager_dashboard,
        name="department_manager_dashboard",
    ),

    path(
        "manager/employees/",
        department_manager_employees,
        name="department_manager_employees",
    ),

    path(
        "manager/employees/<int:employee_id>/",
        department_manager_employee_detail,
        name="department_manager_employee_detail",
    ),

    path(
        "manager/assets/",
        department_manager_assets,
        name="department_manager_assets",
    ),

    path(
        "manager/assets/<int:asset_id>/",
        department_manager_asset_detail,
        name="department_manager_asset_detail",
    ),

    path(
        "manager/assets/allocation/",
        department_manager_asset_allocation,
        name="department_manager_asset_allocation",
    ),

    path(
        "manager/asset-requests/",
        department_manager_asset_requests,
        name="department_manager_asset_requests",
    ),

    path(
        "manager/asset-requests/create/",
        department_manager_create_asset_request,
        name="department_manager_create_asset_request",
    ),

    path(
        "manager/asset-requests/<int:request_id>/process/",
        department_manager_process_asset_request,
        name="department_manager_process_asset_request",
    ),

    # =========================================================================
    # SUPER ADMIN - DEPARTMENT MANAGEMENT
    # =========================================================================

    path(
        "admin/",
        super_admin_department_list,
        name="super_admin_department_list",
    ),

    path(
        "admin/create/",
        super_admin_department_create,
        name="super_admin_department_create",
    ),

    path(
        "admin/<int:department_id>/edit/",
        super_admin_department_edit,
        name="super_admin_department_edit",
    ),

    path(
        "admin/<int:department_id>/delete/",
        super_admin_department_delete,
        name="super_admin_department_delete",
    ),
]