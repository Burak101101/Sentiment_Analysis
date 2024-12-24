from datetime import datetime, timedelta
import json

from django.contrib import messages
from django.shortcuts import render
from django.http import JsonResponse

from .forms import SubredditFilterForm
from .services import get_filtered_reddit_posts, analyze_sentiment

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
            emotion = form.cleaned_data.get('emotion')  # Artık opsiyonel
            keywords = form.cleaned_data['keywords']
            sort_by = form.cleaned_data['sort_by']

            try:
                # İlk subreddit için verileri al
                posts_1 = get_filtered_reddit_posts(subreddit_1, days, post_count, sort_by, keywords)
                analysis_data_1 = []
                timestamps_1 = []
                scores_1 = []

                if emotion:  # Belirli bir duygu seçildiyse
                    # Sadece seçilen duyguya ait postları filtrele
                    for post in posts_1:
                        sentiment = analyze_sentiment(post["title"])
                        if sentiment["emotion"] == emotion:
                            analysis_data_1.append({
                                "title": post["title"],
                                "sentiment": sentiment,
                                "score": post["score"],
                                "timestamp": post["created_utc"],
                                "num_comments": post["num_comments"]
                            })
                else:  # Tüm duygular için analiz yap
                    for post in posts_1:
                        sentiment = analyze_sentiment(post["title"])
                        analysis_data_1.append({
                            "title": post["title"],
                            "sentiment": sentiment,
                            "score": post["score"],
                            "timestamp": post["created_utc"],
                            "num_comments": post["num_comments"]
                        })

                # Duygu dağılımını hesapla
                emotion_distribution_1 = calculate_emotion_distribution(posts_1)

                context = {
                    'subreddit_1': subreddit_1,
                    'analysis_data_1': analysis_data_1,
                    'emotion': emotion,
                    'days': days,
                    'form': form,
                    'emotion_distribution_1': emotion_distribution_1,
                    'satisfaction_index_1': calculate_satisfaction_index(analysis_data_1),
                }
                # İkinci subreddit varsa onun verilerini de al
                if subreddit_2:
                    posts_2 = get_filtered_reddit_posts(subreddit_2, days, post_count, sort_by, keywords)
                    analysis_data_2 = []
                    timestamps_2 = []
                    scores_2 = []

                    for post in posts_2:
                        sentiment = analyze_sentiment(post["title"])
                        if sentiment["emotion"] == emotion:
                            analysis_data_2.append({
                                "title": post["title"],
                                "sentiment": sentiment,
                                "score": post["score"],
                                "timestamp": post["created_utc"],
                                "num_comments": post["num_comments"]
                            })
                            timestamps_2.append(post["created_utc"])
                            scores_2.append(sentiment["score"])
                    emotion_distribution_2 = calculate_emotion_distribution(posts_2)
                    context.update({
                        'subreddit_2': subreddit_2,
                        'analysis_data_2': analysis_data_2,
                        'timestamps_2': json.dumps(timestamps_2),
                        'scores_2': json.dumps(scores_2),
                        'emotion_distribution_2': emotion_distribution_2,
                        'satisfaction_index_2': calculate_satisfaction_index(analysis_data_2),

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


