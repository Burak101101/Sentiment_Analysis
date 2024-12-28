from datetime import datetime, timedelta
import json

from django.contrib import messages
from django.shortcuts import render
from django.http import JsonResponse
from collections import defaultdict

from django.views.decorators.http import require_http_methods

from .forms import SubredditFilterForm
from .services import get_filtered_reddit_posts, analyze_sentiment, process_ai_analysis


def index(request):
    return render(request, "analysis/index.html")

# views.py

def calculate_emotion_distribution(posts):
    emotion_counts = {
        'joy': 0, 'anger': 0, 'sadness': 0, 'disappointment': 0,
        'love': 0, 'surprise': 0, 'gratitude': 0, 'approval': 0,
        'disapproval': 0, 'neutral': 0
    }
    total_posts = len(posts)

    for post in posts:
        emotion = analyze_sentiment(post["title"])["emotion"]
        emotion_counts[emotion] += 1

    # Yüzdeleri hesapla
    emotion_percentages = {
        emotion: (count / total_posts * 100) if total_posts > 0 else 0
        for emotion, count in emotion_counts.items()
    }

    return emotion_percentages


def filtered_analysis(request):
    if request.method == 'POST':
        form = SubredditFilterForm(request.POST)
        if form.is_valid():
            subreddit_1 = form.cleaned_data['subreddit_1']
            subreddit_2 = form.cleaned_data.get('subreddit_2')
            days = form.cleaned_data['days']
            post_count = form.cleaned_data['post_count']
            emotion = form.cleaned_data.get('emotion')
            keywords = form.cleaned_data['keywords']
            sort_by = form.cleaned_data['sort_by']

            try:
                # İlk subreddit için verileri al
                posts_1 = get_filtered_reddit_posts(subreddit_1, days, post_count, sort_by, keywords)
                analysis_data_1 = []

                for post in posts_1:
                    sentiment = analyze_sentiment(post["title"])
                    # Eğer emotion seçilmişse sadece o duyguyu filtrele
                    if not emotion or sentiment["emotion"] == emotion:
                        analysis_data_1.append({
                            "title": post["title"],
                            "sentiment": sentiment,
                            "score": post["score"],
                            "timestamp": post["created_utc"],
                            "num_comments": post["num_comments"]
                        })

                emotion_distribution_1 = calculate_emotion_distribution(posts_1)
                time_series_1 = calculate_time_series(posts_1)

                context = {
                    'subreddit_1': subreddit_1,
                    'analysis_data_1': analysis_data_1,
                    'emotion': emotion,
                    'days': days,
                    'form': form,
                    'emotion_distribution_1': emotion_distribution_1,
                    'satisfaction_index_1': calculate_satisfaction_index(analysis_data_1),
                    'time_series_1': json.dumps(time_series_1),
                }

                # İkinci subreddit varsa
                if subreddit_2:
                    posts_2 = get_filtered_reddit_posts(subreddit_2, days, post_count, sort_by, keywords)
                    analysis_data_2 = []

                    for post in posts_2:
                        sentiment = analyze_sentiment(post["title"])
                        # Emotion filtresi burada da aynı şekilde uygulanmalı
                        if not emotion or sentiment["emotion"] == emotion:
                            analysis_data_2.append({
                                "title": post["title"],
                                "sentiment": sentiment,
                                "score": post["score"],
                                "timestamp": post["created_utc"],
                                "num_comments": post["num_comments"]
                            })

                    emotion_distribution_2 = calculate_emotion_distribution(posts_2)
                    time_series_2 = calculate_time_series(posts_2)

                    context.update({
                        'subreddit_2': subreddit_2,
                        'analysis_data_2': analysis_data_2,
                        'emotion_distribution_2': emotion_distribution_2,
                        'satisfaction_index_2': calculate_satisfaction_index(analysis_data_2),
                        'time_series_2': json.dumps(time_series_2),
                    })

                return render(request, 'analysis/results.html', context)

            except Exception as e:
                messages.error(request, f"Veri alınırken hata oluştu: {str(e)}")
                return render(request, 'analysis/filter.html', {'form': form})
    else:
        form = SubredditFilterForm()

    return render(request, 'analysis/filter.html', {'form': form})


def calculate_satisfaction_index(analysis_data):
    positive_emotions = ['joy', 'love', 'gratitude', 'approval']
    negative_emotions = ['anger', 'sadness', 'disappointment', 'disapproval']

    total_posts = len(analysis_data)
    if total_posts == 0:
        return 0

    positive_count = sum(1 for item in analysis_data
                         if item['sentiment']['emotion'] in positive_emotions)
    negative_count = sum(1 for item in analysis_data
                         if item['sentiment']['emotion'] in negative_emotions)

    # Memnuniyet endeksi hesapla (-100 ile 100 arası)
    if total_posts > 0:
        satisfaction_index = ((positive_count - negative_count) / total_posts) * 100
    else:
        satisfaction_index = 0

    return round(satisfaction_index, 2)


def calculate_time_series(posts):
    """
    Post'ları tarih bazında pozitif, negatif ve nötr olarak gruplandırır.
    """
    from collections import defaultdict
    time_series = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

    for post in posts:
        try:
            # created_utc'yi int'e çevir
            timestamp = datetime.fromisoformat(post['created_utc']).strftime('%Y-%m-%d')
            sentiment = analyze_sentiment(post["title"])
            emotion = sentiment["emotion"]

            if emotion in ['joy', 'love', 'gratitude', 'approval']:
                time_series[timestamp]["positive"] += 1
            elif emotion in ['anger', 'sadness', 'disappointment', 'disapproval']:
                time_series[timestamp]["negative"] += 1
            else:
                time_series[timestamp]["neutral"] += 1
        except (ValueError, TypeError) as e:
            print(f"Zaman damgası hatası: {post['created_utc']} - {e}")

    # Tarihe göre sırala
    sorted_series = sorted(time_series.items())

    # Grafik için verileri formatla
    dates = [str(date) for date, _ in sorted_series]
    positive = [data["positive"] for _, data in sorted_series]
    negative = [data["negative"] for _, data in sorted_series]
    neutral = [data["neutral"] for _, data in sorted_series]

    return {
        "dates": dates,
        "positive": positive,
        "negative": negative,
        "neutral": neutral
    }


def compare_subreddits_page(request):
    if request.method == "POST":
        subreddit_1 = request.POST.get("subreddit_1")
        subreddit_2 = request.POST.get("subreddit_2")

        # İki subreddit için gönderileri alalım
        posts_1 = get_filtered_reddit_posts(subreddit_1)
        posts_2 = get_filtered_reddit_posts(subreddit_2)

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

@require_http_methods(["POST"])
def ai_analysis(request):
    try:
        data = json.loads(request.body)
        analysis_result = process_ai_analysis(data)
        return JsonResponse(
            {'status': 'success',
             'analysis': analysis_result
             })
    except Exception as e:
        return JsonResponse(
            {'status': 'error',
             'message': str(e)
             }, status=500)


