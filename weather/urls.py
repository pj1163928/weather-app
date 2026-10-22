from django.urls import path

from weather import views

app_name = "weather"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("search/suggest/", views.suggest, name="suggest"),
    path("search/city/", views.city_search, name="city-search"),
    path("search/postal/", views.postal_search, name="postal-search"),
    path("units/", views.unit, name="unit"),
    path("spotlight/", views.spotlight, name="spotlight"),
    path("here/", views.here, name="here"),
    path("favorites/add/", views.favorite_add, name="favorite-add"),
    path("favorites/<int:pk>/remove/", views.favorite_remove, name="favorite-remove"),
]
