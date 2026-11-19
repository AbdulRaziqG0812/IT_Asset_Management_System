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
            "asset": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "request_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "issue_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "maxlength": 5000,
                    "placeholder": (
                        "Describe the problem or maintenance required."
                    ),
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
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
                Asset.objects
                .filter(
                    assignments__employee=employee_profile,
                    assignments__is_active=True,
                    status=Asset.Status.ASSIGNED,
                )
                .distinct()
                .order_by("asset_id")
            )
        else:
            self.fields["asset"].queryset = Asset.objects.none()

    def clean_asset(self):
        asset = self.cleaned_data.get("asset")

        if asset is None:
            raise forms.ValidationError(
                "Please select an asset."
            )

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
                "You can only request maintenance for an asset "
                "currently assigned to you."
            )

        if asset.status != Asset.Status.ASSIGNED:
            raise forms.ValidationError(
                "Only an asset currently marked as Assigned can receive "
                "a new maintenance request."
            )

        existing_request = (
            MaintenanceRequest.objects
            .filter(
                asset=asset,
                status__in=[
                    MaintenanceRequest.Status.PENDING,
                    MaintenanceRequest.Status.IN_PROGRESS,
                ],
            )
            .exists()
        )

        if existing_request:
            raise forms.ValidationError(
                "This asset already has an active maintenance request."
            )

        return asset

    def clean_request_type(self):
        request_type = self.cleaned_data.get("request_type")

        valid_types = {
            choice[0]
            for choice in MaintenanceRequest.RequestType.choices
        }

        if request_type not in valid_types:
            raise forms.ValidationError(
                "Invalid maintenance request type."
            )

        return request_type

    def clean_priority(self):
        priority = self.cleaned_data.get("priority")

        valid_priorities = {
            choice[0]
            for choice in MaintenanceRequest.Priority.choices
        }

        if priority not in valid_priorities:
            raise forms.ValidationError(
                "Invalid priority selected."
            )

        return priority

    def clean_issue_description(self):
        issue_description = (
            self.cleaned_data.get("issue_description", "").strip()
        )

        if not issue_description:
            raise forms.ValidationError(
                "Please describe the issue."
            )

        if len(issue_description) > 5000:
            raise forms.ValidationError(
                "Issue description cannot exceed 5000 characters."
            )

        return issue_description