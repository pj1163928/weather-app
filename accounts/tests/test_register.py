from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

PASSWORD = "correct-horse-battery"


def _register(client, **overrides):
    data = {
        "username": "ada",
        "email": "ada@example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return client.post("/accounts/register/", data)


@pytest.mark.django_db
def test_registration_shows_a_confirmation_link_and_sends_no_email(client, monkeypatch):
    def fail_send(*args, **kwargs):
        raise AssertionError("email sent")

    monkeypatch.setattr("django.core.mail.send_mail", fail_send)

    response = _register(client, email="Ada@Example.com")
    body = response.content.decode()
    user = User.objects.get(username="ada")
    link = user.action_links.get()
    remaining = link.expires_at - timezone.now()

    assert response.status_code == 200
    assert "No email was sent." in body
    assert f"/accounts/confirm/{link.token}/" in body
    assert user.email == "ada@example.com"
    assert user.confirmed is False
    assert user.is_active is True
    assert user.temperature_unit == "celsius"
    assert timedelta(hours=23, minutes=59) < remaining <= timedelta(hours=24)
    assert "_auth_user_id" not in client.session

    opened = client.get(f"/accounts/confirm/{link.token}/")
    user.refresh_from_db()

    assert user.confirmed is True
    assert 'action="/accounts/login/"' in opened.content.decode()
    assert 'name="password"' in opened.content.decode()
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_registration_rejects_a_username_with_an_at_sign(client):
    response = _register(client, username="ada@lovelace")

    assert response.status_code == 200
    assert "A username cannot contain @." in response.content.decode()
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_registration_requires_the_password_twice_and_uses_django_validators(client):
    mismatch = _register(client, password2="correct-horse-batteries")
    too_short = _register(client, password1="short", password2="short")
    numeric = _register(client, password1="12345678", password2="12345678")
    common = _register(client, password1="password123", password2="password123")

    assert "The two password fields didn’t match." in mismatch.content.decode()
    assert "This password is too short." in too_short.content.decode()
    assert "This password is entirely numeric." in numeric.content.decode()
    assert "This password is too common." in common.content.decode()
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_username_and_email_are_unique(client):
    _register(client)
    duplicate_name = _register(client, email="other@example.com")
    duplicate_email = _register(client, username="grace", email="ADA@example.com")

    assert User.objects.count() == 1
    assert "already exists" in duplicate_name.content.decode()
    assert "already exists" in duplicate_email.content.decode()
