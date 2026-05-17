from django.urls import path

from apps.accounts.views import delete_account, profile

urlpatterns = [
    path("profile/", profile, name="profile"),
    path("profile/delete/", delete_account, name="account_delete"),
]
