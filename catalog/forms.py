from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    """Форма отзыва: оценка скрытым полем (управляется звёздами), текст — textarea."""

    class Meta:
        model = Comment
        fields = ['rating', 'description']
        widgets = {
            'rating': forms.HiddenInput(attrs={'id': 'rating-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': 1000,
                'id': 'review-text',
                'placeholder': 'Поделитесь впечатлениями о товаре: посадка, комфорт, качество материалов...',
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        if not 1 <= rating <= 5:
            raise forms.ValidationError('Оценка должна быть от 1 до 5.')
        return rating

    def clean_description(self):
        text = self.cleaned_data['description'].strip()
        if len(text) < 5:
            raise forms.ValidationError('Отзыв слишком короткий (минимум 5 символов).')
        return text