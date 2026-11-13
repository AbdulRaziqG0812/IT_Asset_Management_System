from .models import User


def is_super_admin(user):
    return (
        user.is_authenticated
        and user.role == User.Role.SUPER_ADMIN
    )


def is_it_admin(user):
    return (
        user.is_authenticated
        and user.role == User.Role.IT_ADMIN
    )


def is_hr_manager(user):
    return (
        user.is_authenticated
        and user.role == User.Role.HR_MANAGER
    )


def is_department_manager(user):
    return (
        user.is_authenticated
        and user.role == User.Role.DEPARTMENT_MANAGER
    )


def is_employee(user):
    return (
        user.is_authenticated
        and user.role == User.Role.EMPLOYEE
    )


def has_any_role(user, *roles):
    return (
        user.is_authenticated
        and user.role in roles
    )


def is_admin_level(user):
    return has_any_role(
        user,
        User.Role.SUPER_ADMIN,
        User.Role.IT_ADMIN,
    )