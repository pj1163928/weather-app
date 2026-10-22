import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone

from accounts.models import ActionLink, LinkPurpose, User

CONFIRM_FOR = timedelta(hours=24)


def find_user(identifier: str) -> User | None:
    value = identifier.strip()
    if not value:
        return None
    if "@" in value:
        return User.objects.filter(email__iexact=value).first()
    return User.objects.filter(username=value).first()


def issue_confirm_link(user: User) -> ActionLink:
    now = timezone.now()
    current = (
        user.action_links.filter(purpose=LinkPurpose.CONFIRM, expires_at__gt=now)
        .order_by("-pk")
        .first()
    )
    if current is not None:
        return current
    user.action_links.filter(purpose=LinkPurpose.CONFIRM).delete()
    return ActionLink.objects.create(
        user=user,
        purpose=LinkPurpose.CONFIRM,
        token=secrets.token_urlsafe(32),
        expires_at=now + CONFIRM_FOR,
    )


def issue_reset_link(user: User) -> ActionLink:
    now = timezone.now()
    user.action_links.filter(purpose=LinkPurpose.RESET).delete()
    return ActionLink.objects.create(
        user=user,
        purpose=LinkPurpose.RESET,
        token=secrets.token_urlsafe(32),
        expires_at=now + CONFIRM_FOR,
    )


def reset_link(request, token: str, next_target: str) -> str:
    path = reverse("accounts:password-reset-confirm", kwargs={"token": token})
    url = request.build_absolute_uri(path)
    if next_target:
        url = f"{url}?{urlencode({'next': next_target})}"
    return url


def confirm_link(request, token: str, next_target: str) -> str:
    path = reverse("accounts:confirm", kwargs={"token": token})
    url = request.build_absolute_uri(path)
    if next_target:
        url = f"{url}?{urlencode({'next': next_target})}"
    return url
