from django.urls import path

from .views import (
    purchase_create,
    purchase_delete,
    purchase_edit,
    purchase_list,
    vendor_create,
    vendor_delete,
    vendor_edit,
    vendor_list,
)

app_name = "vendors"

urlpatterns = [
    # Vendors
    path("", vendor_list, name="vendor_list"),
    path("create/", vendor_create, name="vendor_create"),
    path("<int:vendor_id>/edit/", vendor_edit, name="vendor_edit"),
    path("<int:vendor_id>/delete/", vendor_delete, name="vendor_delete"),

    # Purchases
    path("purchases/", purchase_list, name="purchase_list"),
    path("purchases/create/", purchase_create, name="purchase_create"),
    path("purchases/<int:purchase_id>/edit/", purchase_edit, name="purchase_edit"),
    path("purchases/<int:purchase_id>/delete/", purchase_delete, name="purchase_delete"),
]