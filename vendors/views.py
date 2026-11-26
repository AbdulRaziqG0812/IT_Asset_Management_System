from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User

from .forms import PurchaseForm, VendorForm
from .models import Purchase, Vendor


def is_vendor_purchase_admin(user):
    """
    Only Super Admin and IT Admin can manage vendors and purchases.
    """
    return (
        user.is_authenticated
        and user.is_active
        and user.role in {
            User.Role.SUPER_ADMIN,
            User.Role.IT_ADMIN,
        }
    )


def require_vendor_purchase_admin(user):
    """
    Deny access to unauthorized users.
    """
    if not is_vendor_purchase_admin(user):
        raise PermissionDenied(
            "You do not have permission to manage vendors and purchases."
        )


# -------------------------------------------------------------------
# Vendor Views
# -------------------------------------------------------------------

@login_required
def vendor_list(request):
    require_vendor_purchase_admin(request.user)

    search_query = request.GET.get("q", "").strip()

    vendors_queryset = (
        Vendor.objects
        .all()
        .order_by("name", "id")
    )

    if search_query:
        vendors_queryset = vendors_queryset.filter(
            Q(name__icontains=search_query)
            | Q(contact_person__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(address__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    paginator = Paginator(
        vendors_queryset,
        10,
    )

    page_number = request.GET.get(
        "page",
        1,
    )

    vendors = paginator.get_page(
        page_number,
    )

    return render(
        request,
        "vendors/vendor_list.html",
        {
            "vendors": vendors,
            "page_obj": vendors,
            "paginator": paginator,
            "search_query": search_query,
        },
    )


@login_required
def vendor_create(request):
    require_vendor_purchase_admin(request.user)

    if request.method == "POST":
        form = VendorForm(request.POST)

        if form.is_valid():
            vendor = form.save()

            messages.success(
                request,
                f"Vendor '{vendor.name}' was created successfully.",
            )

            return redirect("vendors:vendor_list")

    else:
        form = VendorForm()

    return render(
        request,
        "vendors/vendor_form.html",
        {
            "form": form,
            "page_title": "Add Vendor",
            "submit_label": "Create Vendor",
        },
    )


@login_required
def vendor_edit(request, vendor_id):
    require_vendor_purchase_admin(request.user)

    vendor = get_object_or_404(
        Vendor,
        pk=vendor_id,
    )

    if request.method == "POST":
        form = VendorForm(
            request.POST,
            instance=vendor,
        )

        if form.is_valid():
            vendor = form.save()

            messages.success(
                request,
                f"Vendor '{vendor.name}' was updated successfully.",
            )

            return redirect("vendors:vendor_list")

    else:
        form = VendorForm(
            instance=vendor,
        )

    return render(
        request,
        "vendors/vendor_form.html",
        {
            "form": form,
            "vendor": vendor,
            "page_title": "Edit Vendor",
            "submit_label": "Save Changes",
        },
    )


@login_required
def vendor_delete(request, vendor_id):
    require_vendor_purchase_admin(request.user)

    if request.method != "POST":
        raise PermissionDenied(
            "Vendors can only be deleted using POST."
        )

    vendor = get_object_or_404(
        Vendor,
        pk=vendor_id,
    )

    vendor_name = vendor.name

    try:
        vendor.delete()

    except ProtectedError:
        messages.error(
            request,
            (
                f"'{vendor_name}' could not be deleted because it is "
                "associated with existing purchase records."
            ),
        )

        return redirect("vendors:vendor_list")

    messages.success(
        request,
        f"Vendor '{vendor_name}' was deleted successfully.",
    )

    return redirect("vendors:vendor_list")


# -------------------------------------------------------------------
# Purchase Views
# -------------------------------------------------------------------

@login_required
def purchase_list(request):
    require_vendor_purchase_admin(request.user)

    purchases = (
        Purchase.objects
        .select_related("vendor")
        .all()
        .order_by("-purchase_date", "-id")
    )

    return render(
        request,
        "vendors/purchase_list.html",
        {
            "purchases": purchases,
        },
    )


@login_required
def purchase_create(request):
    require_vendor_purchase_admin(request.user)

    if request.method == "POST":
        form = PurchaseForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            purchase = form.save()

            messages.success(
                request,
                (
                    f"Purchase with invoice number "
                    f"'{purchase.invoice_number}' was created successfully."
                ),
            )

            return redirect("vendors:purchase_list")

    else:
        form = PurchaseForm()

    return render(
        request,
        "vendors/purchase_form.html",
        {
            "form": form,
            "page_title": "Add Purchase",
            "submit_label": "Create Purchase",
        },
    )


@login_required
def purchase_edit(request, purchase_id):
    require_vendor_purchase_admin(request.user)

    purchase = get_object_or_404(
        Purchase,
        pk=purchase_id,
    )

    if request.method == "POST":
        form = PurchaseForm(
            request.POST,
            request.FILES,
            instance=purchase,
        )

        if form.is_valid():
            purchase = form.save()

            messages.success(
                request,
                (
                    f"Purchase with invoice number "
                    f"'{purchase.invoice_number}' was updated successfully."
                ),
            )

            return redirect("vendors:purchase_list")

    else:
        form = PurchaseForm(
            instance=purchase,
        )

    return render(
        request,
        "vendors/purchase_form.html",
        {
            "form": form,
            "purchase": purchase,
            "page_title": "Edit Purchase",
            "submit_label": "Save Changes",
        },
    )


@login_required
def purchase_delete(request, purchase_id):
    require_vendor_purchase_admin(request.user)

    if request.method != "POST":
        raise PermissionDenied(
            "Purchases can only be deleted using POST."
        )

    purchase = get_object_or_404(
        Purchase,
        pk=purchase_id,
    )

    invoice_number = purchase.invoice_number

    purchase.delete()

    messages.success(
        request,
        (
            f"Purchase with invoice number "
            f"'{invoice_number}' was deleted successfully."
        ),
    )

    return redirect("vendors:purchase_list")