from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.forms import ConfirmAgainForm, LoginForm, PasswordResetForm, RegisterForm
from accounts.links import (
    confirm_link,
    find_user,
    issue_confirm_link,
    issue_reset_link,
    reset_link,
)
from accounts.models import ActionLink, LinkPurpose

MISMATCH = "The username or email and password do not match."
NO_ACCOUNT = "No account matches that username or email."
ALREADY_CONFIRMED = "This account is already confirmed."
LINK_EXPIRED = "This confirmation link has expired."
LINK_INVALID = "This confirmation link is not valid."
RESET_LINK_EXPIRED = "This reset link has expired."
RESET_LINK_INVALID = "This reset link is not valid."
RESET_NOTICE = "Your password is reset. Log in to continue."
CONFIRMED_NOTICE = "Your account is confirmed. Log in to continue."


def next_path(request, candidate: str | None) -> str:
    url = (candidate or "").strip()
    allowed = url.startswith("/") and not url.startswith("//")
    if allowed and url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return url
    return reverse("weather:home")


def _destination(request) -> str:
    source = request.POST if request.method == "POST" else request.GET
    return next_path(request, source.get("next"))


@require_http_methods(["GET", "POST"])
def register(request):
    nxt = _destination(request)
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            link = issue_confirm_link(user)
            return render(
                request,
                "accounts/confirm_sent.html",
                {
                    "title": "Confirm your account",
                    "heading": "Confirm your account",
                    "confirm_url": confirm_link(request, link.token, nxt),
                    "next": nxt,
                },
            )
    else:
        form = RegisterForm()
    return render(
        request,
        "accounts/register.html",
        {
            "title": "Register",
            "heading": "Register",
            "lede": "Choose a username, an email, and a password.",
            "form": form,
            "next": nxt,
        },
    )


@require_http_methods(["GET", "POST"])
def login(request):
    nxt = _destination(request)
    confirm_error = False
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = find_user(form.cleaned_data["username"])
            password = form.cleaned_data["password"]
            password_fails = (
                user is None or not user.is_active or not user.check_password(password)
            )
            if password_fails:
                form.add_error(None, MISMATCH)
            elif not user.confirmed:
                confirm_error = True
            else:
                auth_login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                from weather.views import UNIT_SESSION_KEY

                request.session[UNIT_SESSION_KEY] = user.temperature_unit
                return redirect(nxt)
    else:
        form = LoginForm()
    return render(
        request,
        "accounts/login.html",
        {
            "title": "Log in",
            "heading": "Log in",
            "form": form,
            "next": nxt,
            "confirm_error": confirm_error,
        },
    )


@require_GET
def confirm(request, token):
    nxt = _destination(request)
    link = (
        ActionLink.objects.filter(token=token, purpose=LinkPurpose.CONFIRM)
        .select_related("user")
        .first()
    )
    if link is None:
        return _invalid_confirm(request, nxt, LINK_INVALID)
    if link.expires_at <= timezone.now():
        return _invalid_confirm(request, nxt, LINK_EXPIRED)
    user = link.user
    if not user.confirmed:
        user.confirmed = True
        user.save(update_fields=["confirmed"])
    return render(
        request,
        "accounts/login.html",
        {
            "title": "Log in",
            "heading": "Log in",
            "lede": CONFIRMED_NOTICE,
            "form": LoginForm(),
            "next": nxt,
            "confirm_error": False,
        },
    )


@require_http_methods(["GET", "POST"])
def confirm_again(request):
    nxt = _destination(request)
    message = ""
    already_confirmed = False
    confirm_url = ""
    if request.method == "POST":
        form = ConfirmAgainForm(request.POST)
        if form.is_valid():
            user = find_user(form.cleaned_data["username"])
            if user is None:
                message = NO_ACCOUNT
            elif user.confirmed:
                message = ALREADY_CONFIRMED
                already_confirmed = True
            else:
                link = issue_confirm_link(user)
                confirm_url = confirm_link(request, link.token, nxt)
    else:
        form = ConfirmAgainForm()
    return render(
        request,
        "accounts/confirm_again.html",
        {
            "title": "Show that message again",
            "heading": "Show that message again",
            "lede": "Enter the username or email on the account.",
            "form": form,
            "next": nxt,
            "message": message,
            "already_confirmed": already_confirmed,
            "confirm_url": confirm_url,
        },
    )


@require_POST
def logout(request):
    from weather.views import (
        LAST_PLACE_SESSION_KEY,
        LOCATION_ACQUIRED_SESSION_KEY,
        UNIT_SESSION_KEY,
    )

    nxt = next_path(request, request.POST.get("next"))
    kept_keys = (
        UNIT_SESSION_KEY,
        LAST_PLACE_SESSION_KEY,
        LOCATION_ACQUIRED_SESSION_KEY,
    )
    kept = {key: request.session[key] for key in kept_keys if key in request.session}
    auth_logout(request)
    for key, value in kept.items():
        request.session[key] = value
    return redirect(nxt)


@require_http_methods(["GET", "POST"])
def delete_account(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.method == "POST":
        user = request.user
        auth_logout(request)
        user.delete()
        return redirect("weather:home")
    return render(
        request,
        "accounts/delete.html",
        {
            "title": "Delete account",
            "heading": "Delete your account?",
            "lede": (
                "This removes your account and your saved places. It cannot be undone."
            ),
        },
    )


@require_http_methods(["GET", "POST"])
def password_reset(request):
    nxt = _destination(request)
    message = ""
    reset_url = ""
    if request.method == "POST":
        form = ConfirmAgainForm(request.POST)
        if form.is_valid():
            user = find_user(form.cleaned_data["username"])
            if user is None:
                message = NO_ACCOUNT
            else:
                link = issue_reset_link(user)
                reset_url = reset_link(request, link.token, nxt)
    else:
        form = ConfirmAgainForm()
    return render(
        request,
        "accounts/password_reset.html",
        {
            "title": "Reset your password",
            "heading": "Reset your password",
            "lede": "Enter the username or email on the account.",
            "form": form,
            "next": nxt,
            "message": message,
            "reset_url": reset_url,
        },
    )


@require_http_methods(["GET", "POST"])
def password_reset_confirm(request, token):
    nxt = _destination(request)
    link = (
        ActionLink.objects.filter(token=token, purpose=LinkPurpose.RESET)
        .select_related("user")
        .first()
    )
    if link is None:
        return _invalid_reset(request, nxt, RESET_LINK_INVALID)
    if link.expires_at <= timezone.now():
        return _invalid_reset(request, nxt, RESET_LINK_EXPIRED)
    user = link.user
    if request.method == "POST":
        form = PasswordResetForm(user, request.POST)
        if form.is_valid():
            form.save()
            link.delete()
            return render(
                request,
                "accounts/login.html",
                {
                    "title": "Log in",
                    "heading": "Log in",
                    "lede": RESET_NOTICE,
                    "form": LoginForm(),
                    "next": nxt,
                    "confirm_error": False,
                },
            )
    else:
        form = PasswordResetForm(user)
    return render(
        request,
        "accounts/password_reset_confirm.html",
        {
            "title": "Reset your password",
            "heading": "Reset your password",
            "lede": "Enter a new password twice.",
            "form": form,
            "next": nxt,
            "token": token,
        },
    )


def _invalid_reset(request, nxt, message):
    return render(
        request,
        "accounts/password_reset_invalid.html",
        {
            "title": "Reset your password",
            "heading": "Reset your password",
            "message": message,
            "next": nxt,
        },
    )


def _invalid_confirm(request, nxt, message):
    return render(
        request,
        "accounts/confirm_invalid.html",
        {
            "title": "Confirm your account",
            "heading": "Confirm your account",
            "message": message,
            "next": nxt,
        },
    )
