from django import forms
from django.contrib.auth.forms import SetPasswordMixin, UserCreationForm

from accounts.models import User


class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(["username", "email", "password1", "password2"])
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "account-input")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class LoginForm(forms.Form):
    username = forms.CharField(label="Username or email")
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "class": "account-input"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "class": "account-input"}
        )


class PasswordResetForm(SetPasswordMixin, forms.Form):
    password1, password2 = SetPasswordMixin.create_password_fields(
        label1="New password",
        label2="New password confirmation",
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "account-input")

    def clean(self):
        self.validate_passwords()
        self.validate_password_for_user(self.user)
        return super().clean()

    def save(self, commit=True):
        return self.set_password_and_save(self.user, commit=commit)


class ConfirmAgainForm(forms.Form):
    username = forms.CharField(label="Username or email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "class": "account-input"}
        )
