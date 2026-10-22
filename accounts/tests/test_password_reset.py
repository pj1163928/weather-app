import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from accounts.models import ActionLink, LinkPurpose

User = get_user_model()

OLD_PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "fresh-river-lantern"


@pytest.mark.django_db
def test_expired_reset_link_does_not_change_the_password(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
    )
    ActionLink.objects.create(
        user=user,
        purpose=LinkPurpose.RESET,
        token="expired-reset",
        expires_at=timezone.now() - timedelta(hours=1),
    )

    response = client.post(
        "/accounts/password-reset/expired-reset/",
        {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
    )
    user.refresh_from_db()

    assert response.status_code == 200
    assert "This reset link has expired." in response.content.decode()
    assert user.check_password(OLD_PASSWORD)
    assert not user.check_password(NEW_PASSWORD)


def _reset_token(body: str) -> str | None:
    match = re.search(r"/accounts/password-reset/([^/\"]+)/", body)
    return match.group(1) if match else None


@pytest.mark.django_db
def test_new_reset_request_invalidates_the_previous_link(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
    )

    first = client.post("/accounts/password-reset/", {"username": "ada"})
    second = client.post("/accounts/password-reset/", {"username": "ada"})
    first_token = _reset_token(first.content.decode())
    second_token = _reset_token(second.content.decode())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first_token is not None
    assert second_token is not None
    assert first_token != second_token

    response = client.post(
        f"/accounts/password-reset/{first_token}/",
        {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
    )
    user.refresh_from_db()

    assert response.status_code == 200
    assert user.check_password(OLD_PASSWORD)
    assert not user.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_successful_reset_stores_the_password_without_a_session(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
    )

    requested = client.post("/accounts/password-reset/", {"username": "ada"})
    token = _reset_token(requested.content.decode())
    response = client.post(
        f"/accounts/password-reset/{token}/",
        {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
    )
    user.refresh_from_db()
    body = response.content.decode()

    assert token is not None
    assert response.status_code == 200
    assert user.check_password(NEW_PASSWORD)
    assert user.confirmed is False
    assert 'action="/accounts/login/"' in body
    assert 'name="password"' in body
    assert "_auth_user_id" not in client.session


def _issue(client, username="ada"):
    response = client.post("/accounts/password-reset/", {"username": username})
    return response, _reset_token(response.content.decode())


@pytest.mark.django_db
def test_reset_page_sends_no_email(client):
    User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
    )

    response, token = _issue(client)
    body = response.content.decode()

    assert response.status_code == 200
    assert "No email was sent." in body
    assert token is not None
    assert "/accounts/confirm/" not in body
    assert mail.outbox == []


@pytest.mark.django_db
def test_unknown_person_gets_no_reset_link(client):
    response = client.post("/accounts/password-reset/", {"username": "missing"})
    body = response.content.decode()

    assert response.status_code == 200
    assert "No account matches that username or email." in body
    assert 'class="confirm-link"' not in body
    assert mail.outbox == []


@pytest.mark.django_db
def test_reset_request_accepts_an_email(client):
    User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
    )

    response, token = _issue(client, username="Ada@Example.com")

    assert response.status_code == 200
    assert token is not None


@pytest.mark.django_db
def test_reset_requires_the_password_twice_and_uses_django_validators(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
    )
    _, token = _issue(client)
    opened = client.get(f"/accounts/password-reset/{token}/")
    opened_body = opened.content.decode()

    def post(password1, password2):
        return client.post(
            f"/accounts/password-reset/{token}/",
            {"password1": password1, "password2": password2},
        )

    mismatch = post(NEW_PASSWORD, "correct-horse-batteries")
    too_short = post("short", "short")
    numeric = post("12345678", "12345678")
    common = post("password123", "password123")
    user.refresh_from_db()

    assert 'name="password1"' in opened_body
    assert 'name="password2"' in opened_body
    assert "The two password fields didn’t match." in mismatch.content.decode()
    assert "This password is too short." in too_short.content.decode()
    assert "This password is entirely numeric." in numeric.content.decode()
    assert "This password is too common." in common.content.decode()
    assert user.check_password(OLD_PASSWORD)


@pytest.mark.django_db
def test_reset_leaves_a_confirmed_account_confirmed(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
        confirmed=True,
    )
    _, token = _issue(client)
    response = client.post(
        f"/accounts/password-reset/{token}/",
        {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
    )
    user.refresh_from_db()

    assert user.confirmed is True
    assert user.check_password(NEW_PASSWORD)
    assert 'action="/accounts/login/"' in response.content.decode()

    logged_in = client.post(
        "/accounts/login/",
        {"username": "ada", "password": NEW_PASSWORD},
    )

    assert logged_in.status_code == 302
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_a_used_reset_link_does_not_change_the_password_again(client):
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=OLD_PASSWORD,
    )
    _, token = _issue(client)
    client.post(
        f"/accounts/password-reset/{token}/",
        {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD},
    )
    later = "second-river-lantern"
    response = client.post(
        f"/accounts/password-reset/{token}/",
        {"password1": later, "password2": later},
    )
    user.refresh_from_db()

    assert "This reset link is not valid." in response.content.decode()
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(later)


@pytest.mark.django_db
def test_login_page_links_to_password_reset(client):
    response = client.get("/accounts/login/?next=/")
    body = response.content.decode()

    assert 'href="/accounts/password-reset/?next=/"' in body
