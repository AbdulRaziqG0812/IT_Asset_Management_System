from django import forms

from accounts.models import EmployeeProfile

from .models import SoftwareLicense, SoftwareLicenseAssignment


class SoftwareLicenseForm(forms.ModelForm):
    class Meta:
        model = SoftwareLicense
        fields = [
            "software_name",
            "version",
            "license_type",
            "license_key",
            "total_licenses",
            "purchase_date",
            "expiry_date",
            "vendor_name",
            "purchase_price",
            "status",
            "notes",
        ]
        widgets = {
            "software_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter software name",
                }
            ),
            "version": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 2026, 365, v5.2",
                }
            ),
            "license_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "license_key": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter unique license key",
                }
            ),
            "total_licenses": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                }
            ),
            "purchase_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "expiry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "vendor_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter vendor name",
                }
            ),
            "purchase_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Additional notes",
                }
            ),
        }

    def clean_license_key(self):
        license_key = self.cleaned_data["license_key"].strip()

        queryset = SoftwareLicense.objects.filter(
            license_key=license_key
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(
                "A software license with this license key already exists."
            )

        return license_key


class SoftwareLicenseAssignmentForm(forms.ModelForm):
    class Meta:
        model = SoftwareLicenseAssignment
        fields = [
            "license",
            "employee",
            "assigned_date",
            "notes",
        ]
        widgets = {
            "license": forms.HiddenInput(),

            "employee": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "assigned_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional assignment notes",
                }
            ),
        }

    def __init__(self, *args, license_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.license_obj = license_obj

        # The license is determined by the URL/view.
        # It must never be selectable by the user.
        if license_obj is not None:
            self.fields["license"].initial = license_obj.pk
            self.fields["license"].disabled = True

        # Only active employees can receive software licenses.
        self.fields["employee"].queryset = (
            EmployeeProfile.objects
            .filter(
                employment_status=EmployeeProfile.EmploymentStatus.ACTIVE
            )
            .select_related(
                "user",
                "department",
            )
            .order_by(
                "user__first_name",
                "user__last_name",
                "employee_id",
            )
        )

        self.fields["employee"].label_from_instance = (
            lambda employee: (
                employee.user.get_full_name().strip()
                or employee.user.username
            )
            + f" ({employee.employee_id})"
        )

    def clean_license(self):
        """
        Always use the license supplied by the view.

        This prevents a user from changing the license through
        manipulated POST data.
        """
        if self.license_obj is None:
            raise forms.ValidationError(
                "A software license is required."
            )

        return self.license_obj

    def clean_employee(self):
        employee = self.cleaned_data["employee"]

        if self.license_obj:
            existing_assignment = (
                SoftwareLicenseAssignment.objects
                .filter(
                    license=self.license_obj,
                    employee=employee,
                    is_active=True,
                )
                .exists()
            )

            if existing_assignment:
                raise forms.ValidationError(
                    "This software license is already assigned "
                    "to this employee."
                )

        return employee