from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Review, User


class UserRegisterForm(UserCreationForm):
    """Форма регистрации нового пользователя с русскоязычными подсказками."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Имя",
        widget=forms.TextInput(attrs={"placeholder": "Например, Пётр"}),
        error_messages={
            "required": "Укажите ваше имя — оно будет отображаться в личном кабинете и отзывах.",
            "max_length": "Имя слишком длинное. Сократите его до 150 символов.",
        },
    )
    email = forms.EmailField(
        required=True,
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"placeholder": "name@example.ru"}),
        error_messages={
            "required": "Введите адрес электронной почты для получения электронных билетов.",
            "invalid": "Некорректный формат e-mail. Укажите адрес с символом @ и доменом, например name@mail.ru.",
        },
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name")
        error_messages = {
            "username": {
                "required": "Придумайте логин для входа на сайт.",
                "unique": "Этот логин уже занят. Добавьте цифры или выберите другое имя пользователя.",
                "invalid": "Логин может содержать только латинские буквы, цифры и символы @/./+/-/_.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "password1" in self.fields:
            self.fields["password1"].help_text = None
            self.fields["password1"].error_messages["required"] = (
                "Введите пароль (минимум 8 символов, не только цифры)."
            )
        if "password2" in self.fields:
            self.fields["password2"].help_text = None
            self.fields["password2"].error_messages["required"] = (
                "Повторите пароль ещё раз для защиты от опечатки."
            )

    def clean_first_name(self):
        first_name = (self.cleaned_data.get("first_name") or "").strip()
        if len(first_name) < 2:
            raise ValidationError(
                "Имя должно содержать минимум 2 буквы. Укажите ваше настоящее имя."
            )
        if any(ch.isdigit() for ch in first_name):
            raise ValidationError(
                "Имя не должно содержать цифр. Удалите цифры и оставьте только буквы."
            )
        return first_name

    def clean(self):
        cleaned_data = super().clean()
        username = (cleaned_data.get("username") or "").strip().lower()
        first_name = (cleaned_data.get("first_name") or "").strip().lower()
        password1 = (cleaned_data.get("password1") or "").lower()

        if password1 and username and password1 == username:
            self.add_error(
                "password1",
                "Пароль не должен совпадать с логином. Добавьте цифры или специальные символы.",
            )
        if password1 and first_name and first_name in password1:
            self.add_error(
                "password1",
                "Не используйте своё имя в пароле — выберите более надёжную комбинацию.",
            )
        return cleaned_data


class ReviewForm(forms.ModelForm):
    """Форма создания и редактирования отзыва зрителя о фильме."""

    class Meta:
        model = Review
        fields = ["rating", "text"]
        widgets = {
            "rating": forms.NumberInput(
                attrs={"min": 1, "max": 10, "class": "input", "placeholder": "1–10"}
            ),
            "text": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "input",
                    "placeholder": "Поделитесь впечатлением о фильме (от 10 символов)...",
                }
            ),
        }
        labels = {
            "rating": "Ваша оценка (от 1 до 10)",
            "text": "Текст отзыва",
        }
        error_messages = {
            "rating": {
                "required": "Поставьте фильму оценку от 1 до 10.",
                "min_value": "Оценка не может быть меньше 1. Укажите целое число от 1 до 10.",
                "max_value": "Оценка не может быть больше 10. Укажите целое число от 1 до 10.",
                "invalid": "Введите целое число от 1 до 10 без дробной части.",
            },
            "text": {
                "required": "Напишите текст отзыва, чтобы другие зрители узнали ваше мнение.",
            },
        }

    def clean_text(self):
        text = (self.cleaned_data.get("text") or "").strip()
        if len(text) < 10:
            raise ValidationError(
                f"Слишком короткий отзыв (сейчас {len(text)} симв.). "
                "Напишите хотя бы 10 символов — например, что понравилось в сюжете или игре актёров."
            )
        return text

    def clean(self):
        cleaned_data = super().clean()
        rating = cleaned_data.get("rating")
        text = (cleaned_data.get("text") or "").strip()

        if rating is not None and text and len(text) >= 10:
            if rating <= 3 and len(text) < 25:
                self.add_error(
                    "text",
                    "Для низкой оценки (1–3 балла) поясните причину подробнее — напишите от 25 символов.",
                )
        return cleaned_data