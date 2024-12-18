from datetime import datetime, timedelta
import json
from django.shortcuts import render
from django.http import JsonResponse
from .services import get_reddit_posts, analyze_sentiment

def index(request):
    return render(request, "analysis/index.html")

def analyze_subreddit_page(request):
    subreddit_name = request.GET.get("subreddit_name")
    posts = get_reddit_posts(subreddit_name)
    analysis_data = []

    # Gönderiler ve duygu analizi sonuçları
    for post in posts:
        sentiment = analyze_sentiment(post["title"])
        timestamp = datetime.fromisoformat(post["created_utc"])  # Düzeltilmiş
        analysis_data.append({
            "title": post["title"],
            "sentiment": sentiment,
            "timestamp": timestamp
        })

    # Zaman serisi verisi
    timestamps = [post["timestamp"].strftime("%Y-%m-%d %H:%M:%S") for post in analysis_data]
    scores = [post["sentiment"]["score"] for post in analysis_data]  # score'ı doğrudan alıyoruz

    return render(
        request,
        "analysis/results.html",
        {
            "subreddit_name": subreddit_name,
            "analysis_data": analysis_data,
            "timestamps": json.dumps(timestamps),
            "scores": json.dumps(scores),
        },
    )


def compare_subreddits_page(request):
    if request.method == "POST":
        subreddit_1 = request.POST.get("subreddit_1")
        subreddit_2 = request.POST.get("subreddit_2")

        # İki subreddit için gönderileri alalım
        posts_1 = get_reddit_posts(subreddit_1)
        posts_2 = get_reddit_posts(subreddit_2)

        # Duygu analizlerini yapalım
        analysis_1 = [analyze_sentiment(post["title"]) for post in posts_1]
        analysis_2 = [analyze_sentiment(post["title"]) for post in posts_2]

        # Ortalama skorları hesapla
        avg_score_1 = sum([a["score"] for a in analysis_1]) / len(analysis_1)
        avg_score_2 = sum([a["score"] for a in analysis_2]) / len(analysis_2)

        return render(
            request,
            "analysis/comparison.html",
            {
                "subreddit_1": subreddit_1,
                "subreddit_2": subreddit_2,
                "avg_score_1": json.dumps(avg_score_1),
                "avg_score_2": json.dumps(avg_score_2),
            },
        )
    return render(request, "analysis/compare.html")


