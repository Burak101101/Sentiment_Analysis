# forms.py
from django import forms

class SubredditFilterForm(forms.Form):
    subreddit_1 = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Örn: Ubisoft'})
    )
    subreddit_2 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Örn: EA'})
    )
    days = forms.ChoiceField(
        choices=[
            (7, 'Son 7 gün'),
            (30, 'Son 30 gün'),
            (90, 'Son 90 gün'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    post_count = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    emotion = forms.ChoiceField(
        choices=[
            ('', 'Tüm Duygular'),  # Boş seçenek eklendi
            ('anger', 'Kızgın'),
            ('joy', 'Mutlu'),
            ('sadness', 'Üzgün'),
            ('disappointment', 'Hayal Kırıklığı'),
            ('love', 'Sevgi'),
            ('surprise', 'Şaşkınlık'),
            ('gratitude', 'Minnettarlık'),
            ('approval', 'Onaylama'),
            ('disapproval', 'Onaylamama'),
            ('neutral', 'Nötr'),
        ],
        required=False,  # Opsiyonel yaptık
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    keywords = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Anahtar kelimeler (virgülle ayırın)'
        })
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('score', 'En çok oy alan'),
            ('created_utc', 'En yeni'),
            ('num_comments', 'En çok yorum alan'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )