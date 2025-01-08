from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class AIReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subreddit_1 = models.CharField(max_length=100)
    subreddit_2 = models.CharField(max_length=100, null=True, blank=True)
    content = models.TextField() # Kullanıcının girdiği metin
    days_analyzed = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    emotion_data = models.JSONField()  # Duygu analizi verilerini saklamak için
    time_series_data = models.JSONField()  # Zaman serisi verilerini saklamak için
    news_data = models.JSONField()  # Haber verilerini saklamak için

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.subreddit_2:
            return f"Analysis of r/{self.subreddit_1} and r/{self.subreddit_2} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        return f"Analysis of r/{self.subreddit_1} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class UserText(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()  # Kullanıcının girdiği metin
    sentiment_score = models.FloatField()  # Duygu analizi skoru
    created_at = models.DateTimeField(auto_now_add=True)
    emotion_data = models.JSONField(null=True, blank=True)  # Detaylı duygu analizi verileri (opsiyonel)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "User Text Analysis"
        verbose_name_plural = "User Text Analyses"

    def __str__(self):
        return f"{self.user.username}'s text - {self.created_at.strftime('%Y-%m-%d %H:%M')}"