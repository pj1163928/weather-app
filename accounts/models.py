from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


def validate_username_has_no_at_sign(value: str) -> None:
    if "@" in value:
        raise ValidationError("A username cannot contain @.")


class TemperatureUnit(models.TextChoices):
    CELSIUS = "celsius", "Celsius"
    FAHRENHEIT = "fahrenheit", "Fahrenheit"


class LinkPurpose(models.TextChoices):
    CONFIRM = "confirm", "Confirm"
    RESET = "reset", "Reset"


class User(AbstractUser):
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and ./+/-/_ only."
        ),
        validators=[UnicodeUsernameValidator(), validate_username_has_no_at_sign],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    email = models.EmailField(_("email address"), unique=True)
    temperature_unit = models.CharField(
        max_length=12,
        choices=TemperatureUnit.choices,
        default=TemperatureUnit.CELSIUS,
    )
    confirmed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(username__contains="@"),
                name="username_has_no_at_sign",
            ),
        ]


class ActionLink(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="action_links",
    )
    purpose = models.CharField(max_length=16, choices=LinkPurpose.choices)
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
