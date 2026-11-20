from django.contrib.auth.forms import UserCreationForm
from .models import User, Review
from django import forms


class UserRegisterForm(UserCreationForm):
    """
    Форма регистрации нового пользователя в системе.
    Наследуется от стандартного UserCreationForm Django,
    содержит поля для никнейма (username) и электронной почты (email),
    а также автоматически обрабатывает безопасное создание паролей.
    """

    first_name = forms.CharField(max_length=150,required=True,label="Имя",)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Удаляем стандартные тексты подсказок (help_text) у полей ввода пароля, 
        # чтобы интерфейс формы выглядел чище и лаконичнее.
        if 'password1' in self.fields:
            self.fields['password1'].help_text = None
        if 'password2' in self.fields:
            self.fields['password2'].help_text = None


class ReviewForm(forms.ModelForm):
    """
    Форма создания и редактирования отзыва зрителя о фильме.
    Позволяет указать оценку от 1 до 10 и написать текстовый отзыв.
    """

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