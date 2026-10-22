from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import ActionLink, LinkPurpose

User = get_user_model()


@pytest.mark.django_db
def test_expired_confirm_link_does_not_confirm(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password="correct-horse-battery",
    )
    ActionLink.objects.create(
        user=user,
        purpose=LinkPurpose.CONFIRM,
        token="expired-token",
        expires_at=timezone.now() - timedelta(hours=1),
    )

    response = client.get("/accounts/confirm/expired-token/")
    user.refresh_from_db()

    assert response.status_code == 200
    assert user.confirmed is False


@pytest.mark.django_db
def test_unknown_confirm_link_does_not_confirm(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password="correct-horse-battery",
    )

    response = client.get("/accounts/confirm/missing-token/")
    user.refresh_from_db()

    assert response.status_code == 200
    assert "This confirmation link is not valid." in response.content.decode()
    assert user.confirmed is False


@pytest.mark.django_db
def test_confirm_again_repeats_a_live_link(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password="correct-horse-battery",
    )
    ActionLink.objects.create(
        user=user,
        purpose=LinkPurpose.CONFIRM,
        token="live-token",
        expires_at=timezone.now() + timedelta(hours=5),
    )

    response = client.post("/accounts/confirm/", {"username": "Ada@Example.com"})
    body = response.content.decode()

    assert response.status_code == 200
    assert "/accounts/confirm/live-token/" in body
    assert user.action_links.count() == 1


@pytest.mark.django_db
def test_confirm_again_replaces_an_expired_link(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password="correct-horse-battery",
    )
    ActionLink.objects.create(
        user=user,
        purpose=LinkPurpose.CONFIRM,
        token="old-token",
        expires_at=timezone.now() - timedelta(hours=1),
    )

    response = client.post("/accounts/confirm/", {"username": "ada"})
    body = response.content.decode()
    link = user.action_links.get()
    user.refresh_from_db()

    assert link.token != "old-token"
    assert f"/accounts/confirm/{link.token}/" in body
    assert "/accounts/confirm/old-token/" not in body
    assert user.confirmed is False

    opened = client.get("/accounts/confirm/old-token/")
    user.refresh_from_db()

    assert opened.status_code == 200
    assert user.confirmed is False


@pytest.mark.django_db
def test_confirm_again_for_a_confirmed_account_adds_no_link(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password="correct-horse-battery",
        confirmed=True,
    )

    response = client.post("/accounts/confirm/", {"username": "ada"})
    body = response.content.decode()

    assert "This account is already confirmed." in body
    assert 'href="/accounts/login/' in body
    assert user.action_links.count() == 0


@pytest.mark.django_db
def test_confirm_again_for_an_unknown_person(client):
    response = client.post("/accounts/confirm/", {"username": "Ada"})
    body = response.content.decode()

    assert response.status_code == 200
    assert "No account matches that username or email." in body
    assert 'class="confirm-link"' not in body


@pytest.mark.django_db
def test_valid_confirm_link_confirms_without_a_session(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password="correct-horse-battery",
    )
    ActionLink.objects.create(
        user=user,
        purpose=LinkPurpose.CONFIRM,
        token="valid-token",
        expires_at=timezone.now() + timedelta(hours=23),
    )

    response = client.get("/accounts/confirm/valid-token/")
    user.refresh_from_db()
    body = response.content.decode()

    assert response.status_code == 200
    assert user.confirmed is True
    assert 'action="/accounts/login/"' in body
    assert 'name="password"' in body
    assert "_auth_user_id" not in client.session
