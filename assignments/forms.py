from django import forms

from accounts.models import EmployeeProfile
from assets.models import Asset

from .models import Assignment


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            "asset",
            "employee",
            "assigned_date",
            "assignment_notes",
        ]

        widgets = {
            "asset": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
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
            "assignment_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "maxlength": 5000,
                    "placeholder": (
                        "Enter any relevant notes about this assignment."
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only assets that are currently available can appear
        # in a new assignment form.
        self.fields["asset"].queryset = (
            Asset.objects
            .filter(
                status=Asset.Status.AVAILABLE,
            )
            .order_by("asset_id")
        )

        # Only active Django users with an employee profile can
        # receive an asset assignment.
        self.fields["employee"].queryset = (
            EmployeeProfile.objects
            .filter(
                user__is_active=True,
            )
            .select_related("user", "department")
            .order_by(
                "employee_id",
            )
        )

    def clean_asset(self):
        asset = self.cleaned_data.get("asset")

        if asset is None:
            raise forms.ValidationError(
                "Please select an asset."
            )

        if asset.status != Asset.Status.AVAILABLE:
            raise forms.ValidationError(
                "Only an available asset can be assigned."
            )

        # Extra protection against an active assignment existing
        # while the asset is still being shown as available.
        if asset.assignments.filter(is_active=True).exists():
            raise forms.ValidationError(
                "This asset already has an active assignment."
            )

        return asset

    def clean_employee(self):
        employee = self.cleaned_data.get("employee")

        if employee is None:
            raise forms.ValidationError(
                "Please select an employee."
            )

        if not employee.user.is_active:
            raise forms.ValidationError(
                "An inactive employee cannot receive an asset assignment."
            )

        return employee

    def clean_assignment_notes(self):
        notes = self.cleaned_data.get(
            "assignment_notes",
            "",
        ).strip()

        if len(notes) > 5000:
            raise forms.ValidationError(
                "Assignment notes cannot exceed 5000 characters."
            )

        return notes


class AssignmentReturnForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            "return_date",
            "return_notes",
        ]

        widgets = {
            "return_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "return_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "maxlength": 5000,
                    "placeholder": (
                        "Enter any relevant notes about the asset return."
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Return form is only meaningful for an active assignment.
        if self.instance and self.instance.pk:
            if not self.instance.is_active:
                for field in self.fields.values():
                    field.disabled = True

    def clean_return_date(self):
        return_date = self.cleaned_data.get("return_date")

        if return_date is None:
            raise forms.ValidationError(
                "Please select the return date."
            )

        return return_date

    def clean_return_notes(self):
        notes = self.cleaned_data.get(
            "return_notes",
            "",
        ).strip()

        if len(notes) > 5000:
            raise forms.ValidationError(
                "Return notes cannot exceed 5000 characters."
            )

        return notes

    def clean(self):
        cleaned_data = super().clean()

        if self.instance and self.instance.pk:
            if not self.instance.is_active:
                raise forms.ValidationError(
                    "This assignment has already been returned."
                )

        return cleaned_data