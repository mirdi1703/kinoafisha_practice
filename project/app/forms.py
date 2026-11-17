from django.contrib.auth.forms import UserCreationForm
from .models import User, Review
from django import forms


class UserRegisterForm(UserCreationForm):
  """Форма регистрации с полями: ник, почта, пароль (без лишних подсказок)."""

  class Meta(UserCreationForm.Meta):
    model = User
    fields = ('username', 'email')

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Удаляем тексты помощи (help_text) для полей пароля, чтобы убрать подсказки
    if 'password1' in self.fields:
      self.fields['password1'].help_text = None
    if 'password2' in self.fields:
      self.fields['password2'].help_text = None

class ReviewForm(forms.ModelForm):

  class Meta:
    model = Review
    fields = ['rating', 'text']
    widgets = {
        'rating': forms.NumberInput(
            attrs={'min': 1, 'max': 10, 'class': 'input', 'placeholder': '1–10'}
        ),
        'text': forms.Textarea(
            attrs={
                'rows': 4,
                'class': 'input',
                'placeholder': 'Напишите ваши впечатления о фильме...',
            }
        ),
    }
    labels = {
        'rating': 'Ваша оценка (от 1 до 10)',
        'text': 'Текст отзыва',
    }