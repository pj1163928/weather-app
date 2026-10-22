from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import IntegrityError, models

from weather.places import Place, place_label, place_path


def pin_key(latitude, longitude) -> str:
    quantizer = Decimal("0.0001")

    def part(value) -> str:
        number = Decimal(format(float(value), ".10f"))
        return str(number.quantize(quantizer, rounding=ROUND_HALF_UP))

    return f"{part(latitude)}:{part(longitude)}"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    name = models.CharField(max_length=200)
    region = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    pin = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "pin"],
                name="favorite_pin_once_per_user",
            )
        ]

    def as_place(self) -> Place:
        return Place(
            latitude=self.latitude,
            longitude=self.longitude,
            name=self.name,
            region=self.region,
            country=self.country,
        )

    def display_label(self) -> str:
        return place_label(self.as_place())

    def open_path(self) -> str:
        return place_path(self.as_place())


def save_favorite(user, place: Place) -> Favorite:
    key = pin_key(place.latitude, place.longitude)
    existing = Favorite.objects.filter(user=user, pin=key).first()
    if existing is not None:
        return existing
    try:
        return Favorite.objects.create(
            user=user,
            name=place.name,
            region=place.region,
            country=place.country,
            latitude=place.latitude,
            longitude=place.longitude,
            pin=key,
        )
    except IntegrityError:
        return Favorite.objects.get(user=user, pin=key)
