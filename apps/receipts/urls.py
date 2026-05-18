from django.urls import path

from apps.receipts.views import (
    receipt_delete,
    receipt_detail,
    receipt_edit,
    receipts_list,
    tax_year_detail,
    tax_year_list,
    tax_year_lock,
    tax_year_unlock,
)

urlpatterns = [
    path("kvitton/", receipts_list, name="receipts_list"),
    path("kvitton/<int:receipt_id>/", receipt_detail, name="receipt_detail"),
    path("kvitton/<int:receipt_id>/redigera/", receipt_edit, name="receipt_edit"),
    path("kvitton/<int:receipt_id>/radera/", receipt_delete, name="receipt_delete"),
    path("inkomstar/", tax_year_list, name="tax_year_list"),
    path("inkomstar/<int:year>/", tax_year_detail, name="tax_year_detail"),
    path("inkomstar/<int:year>/las/", tax_year_lock, name="tax_year_lock"),
    path("inkomstar/<int:year>/las-upp/", tax_year_unlock, name="tax_year_unlock"),
]