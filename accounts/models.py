from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        IT_ADMIN = "IT_ADMIN", "IT Administrator"
        HR_MANAGER = "HR_MANAGER", "HR Manager"
        DEPARTMENT_MANAGER = "DEPARTMENT_MANAGER", "Department Manager"
        EMPLOYEE = "EMPLOYEE", "Employee"

    email = models.EmailField(
        unique=True,
        help_text="User's unique email address."
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    

class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )

    employee_id = models.CharField(
        max_length=50,
        unique=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    job_title = models.CharField(
        max_length=100,
        blank=True,
    )

    date_of_joining = models.DateField(
        null=True,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.employee_id}"