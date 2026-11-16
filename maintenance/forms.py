from django import forms

from assets.models import Asset
from .models import MaintenanceRequest


class MaintenanceRequestForm(forms.ModelForm):

    class Meta:
        model = MaintenanceRequest
        fields = [
            "asset",
            "request_type",
            "issue_description",
            "priority",
        ]

        widgets = {
            "asset": forms.Select(),
            "request_type": forms.Select(),
            "issue_description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "Describe the problem or maintenance required."
                    ),
                }
            ),
            "priority": forms.Select(),
        }

    def __init__(
        self,
        *args,
        employee_profile=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.employee_profile = employee_profile

        if employee_profile is not None:
            self.fields["asset"].queryset = (
                Asset.objects.filter(
                    assignments__employee=employee_profile,
                    assignments__is_active=True,
                ).distinct()
            )
        else:
            self.fields["asset"].queryset = Asset.objects.none()

    def clean_asset(self):
        asset = self.cleaned_data["asset"]

        if self.employee_profile is None:
            raise forms.ValidationError(
                "Employee profile is required."
            )

        assigned = asset.assignments.filter(
            employee=self.employee_profile,
            is_active=True,
        ).exists()

        if not assigned:
            raise forms.ValidationError(
                "You can only request maintenance for an asset currently assigned to you."
            )

        return asset

    def clean_issue_description(self):
        issue_description = (
            self.cleaned_data["issue_description"].strip()
        )

        if not issue_description:
            raise forms.ValidationError(
                "Please describe the issue."
            )

        return issue_description