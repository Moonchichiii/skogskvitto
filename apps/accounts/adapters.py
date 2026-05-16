from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from django.utils.text import slugify


class AccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user) -> None:
        if getattr(user, "username", ""):
            return

        email = getattr(user, "email", "") or ""
        base_username = slugify(email.split("@")[0])[:24] or "user"
        candidate = base_username
        counter = 1

        UserModel = get_user_model()

        while UserModel.objects.filter(username=candidate).exists():
            counter += 1
            candidate = f"{base_username}-{counter}"[:30]

        user.username = candidate
