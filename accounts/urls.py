from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("delete/", views.delete_account, name="delete"),
    path("confirm/", views.confirm_again, name="confirm-again"),
    path("confirm/<str:token>/", views.confirm, name="confirm"),
    path("password-reset/", views.password_reset, name="password-reset"),
    path(
        "password-reset/<str:token>/",
        views.password_reset_confirm,
        name="password-reset-confirm",
    ),
]
