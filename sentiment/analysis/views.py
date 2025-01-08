import traceback
from datetime import datetime, timedelta
import json
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import render, redirect
from django.http import JsonResponse
from collections import defaultdict

from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from .forms import SubredditFilterForm
from .services import get_filtered_reddit_posts, analyze_sentiment, process_ai_analysis, EmotionGroups
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import AIReport, UserText
from .utils import generate_pdf_report

# views.py

@login_required
def dashboard(request):
    # Print ile debug edelim
    print("Dashboard view çalışıyor")

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Sorguları debug edelim
    reddit_analysis = AIReport.objects.filter(user=request.user)
    print(f"Reddit analizleri: {reddit_analysis.count()}")

    user_texts = UserText.objects.filter(user=request.user)
    print(f"Kullanıcı metinleri: {user_texts.count()}")

    total_analysis = reddit_analysis.count() + user_texts.count()

    today_reddit = reddit_analysis.filter(created_at__gte=today_start).count()
    today_texts = user_texts.filter(created_at__gte=today_start).count()
    today_analysis = today_reddit + today_texts

    # En çok analiz edilen subreddit'i bul
    most_analyzed = (
        AIReport.objects.filter(user=request.user)
        .exclude(subreddit_1='')
        .values('subreddit_1')
        .annotate(count=Count('subreddit_1'))
        .order_by('-count')
        .first()
    )
    print(f"En çok analiz edilen: {most_analyzed}")

    most_analyzed_subreddit = most_analyzed['subreddit_1'] if most_analyzed else "-"

    # Son analizleri al (hem Reddit hem kullanıcı metinleri)
    recent_reddit = list(reddit_analysis.order_by('-created_at')[:5])
    recent_texts = list(user_texts.order_by('-created_at')[:5])

    # Her iki tip analizi birleştir ve sırala
    recent_all = sorted(
        recent_reddit + recent_texts,
        key=lambda x: x.created_at,
        reverse=True
    )[:10]

    context = {
        'total_analysis': total_analysis,
        'today_analysis': today_analysis,
        'most_analyzed_subreddit': most_analyzed_subreddit,
        'recent_reports': recent_all,
    }

    print(f"Context: {context}")  # Debug için context'i yazdır

    return render(request, 'home.html', context)


@login_required
@csrf_protect
def analyze_text(request):
    if request.method == 'POST':
        try:
            # AJAX isteği için
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                data = json.loads(request.body)
                text = data.get('text', '')
            else:
                # Normal form gönderimi için
                text = request.POST.get('text', '')

            if not text:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No text provided'
                }, status=400)

            # Duygu analizi yap
            analysis_result = analyze_sentiment(text)

            # Analiz sonucunu veritabanına kaydet
            UserText.objects.create(
                user=request.user,
                content=text,
                sentiment_score=analysis_result['score'],
                emotion_data={
                    'sentiment': analysis_result['score'],
                    'emotion': analysis_result['emotion'],
                    'all_predictions': analysis_result['all_predictions']
                }
            )

            return JsonResponse({
                'status': 'success',
                'result': analysis_result
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    # GET isteği için son 5 analizi getir
    recent_analyses = UserText.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    return render(request, 'analysis/analyze_text.html', {
        'recent_analyses': recent_analyses
    })

def calculate_sentiment_summary(analysis_data):
    """Pozitif, negatif ve nötr duyguların dağılımını hesaplar"""
    positive_emotions = ['joy', 'love', 'gratitude', 'approval', 'curiosity']
    negative_emotions = ['anger', 'sadness', 'disappointment', 'disapproval']

    counts = {'positive': 0, 'negative': 0, 'neutral': 0}
    total = len(analysis_data)

    for item in analysis_data:
        emotion = item['sentiment']['emotion']
        if emotion in positive_emotions:
            counts['positive'] += 1
        elif emotion in negative_emotions:
            counts['negative'] += 1
        else:
            counts['neutral'] += 1

    percentages = {
        k: (v / total * 100) if total > 0 else 0
        for k, v in counts.items()
    }

    return percentages


def calculate_emotion_distribution(posts):
    emotion_counts = {
        'joy': 0, 'anger': 0, 'sadness': 0, 'disappointment': 0,
        'love': 0, 'surprise': 0, 'gratitude': 0, 'approval': 0,
        'disapproval': 0, 'neutral': 0, 'curiosity': 0
    }

    for post in posts:
        emotion = post["sentiment"]["emotion"]
        emotion_counts[emotion] += 1

    return emotion_counts

@login_required
def filter_page(request):
    # Sadece form gösterimi ve POST işlemi için
    if request.method == 'POST':
        form = SubredditFilterForm(request.POST)
        if form.is_valid():
            # Form verilerini session'a kaydet
            request.session['filter_data'] = {
                'subreddit_1': form.cleaned_data['subreddit_1'],
                'subreddit_2': form.cleaned_data.get('subreddit_2'),
                'days': form.cleaned_data['days'],
                'post_count': form.cleaned_data['post_count'],
                'emotion': form.cleaned_data.get('emotion'),
                'keywords': form.cleaned_data['keywords'],
                'sort_by': form.cleaned_data['sort_by']
            }
            # Sonuçlar sayfasına yönlendir
            return redirect('results')
    else:
        form = SubredditFilterForm()

    return render(request, 'analysis/filter.html', {'form': form})


@login_required
def results_page(request):
    filter_data = request.session.get('filter_data')

    if not filter_data:
        messages.error(request, "Lütfen önce analiz kriterlerini seçin.")
        return redirect('analysis:filter')

    try:
        emotion = filter_data.get('emotion')
        if emotion == 'positive':
            emotions_to_filter = ['joy', 'love', 'gratitude', 'approval', 'curiosity']
        elif emotion == 'negative':
            emotions_to_filter = ['anger', 'sadness', 'disappointment', 'disapproval']
        else:
            emotions_to_filter = None

        # İlk subreddit analizi
        try:
            posts_1 = get_filtered_reddit_posts(
                filter_data['subreddit_1'],
                filter_data['days'],
                filter_data['post_count'],
                filter_data['sort_by'],
                filter_data['keywords']
            )

            analysis_data_1 = []
            for post in posts_1:
                try:
                    sentiment = post["top_comment"]["sentiment"]
                    # Metin uzunluğunu kontrol et
                    if len(post["top_comment"]["text"]) > 500:  # Token limitini aşmayacak şekilde kes
                        post["top_comment"]["text"] = post["top_comment"]["text"][:500] + "..."

                    if emotions_to_filter is None or sentiment["emotion"] in emotions_to_filter:
                        analysis_data_1.append({
                            "title": post["title"][:200],  # Başlığı da kes
                            "sentiment": sentiment,
                            "score": post["score"],
                            "timestamp": post["created_utc"],
                            "num_comments": post["num_comments"],
                            "top_comment": post["top_comment"]
                        })
                except Exception as e:
                    print(f"Error processing post: {e}")
                    continue

            emotion_distribution_1 = calculate_emotion_distribution([
                {"title": p["top_comment"]["text"], "sentiment": p["top_comment"]["sentiment"]}
                for p in posts_1 if "sentiment" in p["top_comment"]
            ])
            time_series_1 = calculate_time_series(posts_1, emotion)

            context = {
                'subreddit_1': filter_data['subreddit_1'],
                'analysis_data_1': analysis_data_1,
                'sentiment_summary_1': calculate_sentiment_summary(analysis_data_1),
                'emotion': emotion,
                'days': filter_data['days'],
                'emotion_distribution_1': emotion_distribution_1,
                'satisfaction_index_1': calculate_satisfaction_index(analysis_data_1),
                'time_series_1': json.dumps(time_series_1),
                'filter_data': filter_data
            }

            # İkinci subreddit varsa
            if filter_data.get('subreddit_2'):
                try:
                    posts_2 = get_filtered_reddit_posts(
                        filter_data['subreddit_2'],
                        filter_data['days'],
                        filter_data['post_count'],
                        filter_data['sort_by'],
                        filter_data['keywords']
                    )

                    analysis_data_2 = []
                    for post in posts_2:
                        try:
                            sentiment = post["top_comment"]["sentiment"]
                            # Metin uzunluğunu kontrol et
                            if len(post["top_comment"]["text"]) > 500:
                                post["top_comment"]["text"] = post["top_comment"]["text"][:500] + "..."

                            if emotions_to_filter is None or sentiment["emotion"] in emotions_to_filter:
                                analysis_data_2.append({
                                    "title": post["title"][:200],
                                    "sentiment": sentiment,
                                    "score": post["score"],
                                    "timestamp": post["created_utc"],
                                    "num_comments": post["num_comments"],
                                    "top_comment": post["top_comment"]
                                })
                        except Exception as e:
                            print(f"Error processing post for subreddit 2: {e}")
                            continue

                    emotion_distribution_2 = calculate_emotion_distribution([
                        {"title": p["top_comment"]["text"], "sentiment": p["top_comment"]["sentiment"]}
                        for p in posts_2 if "sentiment" in p["top_comment"]
                    ])
                    time_series_2 = calculate_time_series(posts_2, emotion)

                    context.update({
                        'subreddit_2': filter_data['subreddit_2'],
                        'analysis_data_2': analysis_data_2,
                        'sentiment_summary_2': calculate_sentiment_summary(analysis_data_2),
                        'emotion_distribution_2': emotion_distribution_2,
                        'satisfaction_index_2': calculate_satisfaction_index(analysis_data_2),
                        'time_series_2': json.dumps(time_series_2),
                    })
                except Exception as e:
                    messages.warning(request, f"İkinci subreddit analizi sırasında hata: {str(e)}")

            return render(request, 'analysis/results.html', context)

        except Exception as e:
            messages.error(request, f"Birinci subreddit analizi sırasında hata: {str(e)}")
            return redirect('analysis:filter')

    except Exception as e:
        messages.error(request, f"Genel bir hata oluştu: {str(e)}")
        return redirect('analysis:filter')


def calculate_satisfaction_index(analysis_data):
    positive_emotions = ['joy', 'love', 'gratitude', 'approval', 'curiosity']
    negative_emotions = ['anger', 'sadness', 'disappointment', 'disapproval']

    total_posts = len(analysis_data)
    if total_posts == 0:
        return 0

    # Yorum duygularını kullan
    positive_count = sum(1 for item in analysis_data
                        if item['sentiment']['emotion'] in positive_emotions)
    negative_count = sum(1 for item in analysis_data
                        if item['sentiment']['emotion'] in negative_emotions)

    satisfaction_index = ((positive_count - negative_count) / total_posts) * 100
    return round(satisfaction_index, 2)

def calculate_time_series(posts, emotion_group=None):
    time_series = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

    for post in posts:
        try:
            created_utc = post.get('created_utc')
            if not created_utc:
                continue

            # Timestamp'i tarihe çevir
            if isinstance(created_utc, str):
                try:
                    timestamp = datetime.fromisoformat(created_utc).strftime('%Y-%m-%d')
                except ValueError:
                    timestamp = datetime.fromtimestamp(float(created_utc)).strftime('%Y-%m-%d')
            else:
                timestamp = datetime.fromtimestamp(float(created_utc)).strftime('%Y-%m-%d')

            sentiment = post.get('top_comment', {}).get('sentiment', {})
            emotion = sentiment.get('emotion')

            if emotion_group == 'positive':
                if emotion in EmotionGroups.POSITIVE:
                    time_series[timestamp]["positive"] += 1
            elif emotion_group == 'negative':
                if emotion in EmotionGroups.NEGATIVE:
                    time_series[timestamp]["negative"] += 1
            else:
                if emotion in EmotionGroups.POSITIVE:
                    time_series[timestamp]["positive"] += 1
                elif emotion in EmotionGroups.NEGATIVE:
                    time_series[timestamp]["negative"] += 1
                else:
                    time_series[timestamp]["neutral"] += 1

        except Exception as e:
            print(f"Post işleme hatası: {str(e)}")
            continue

    sorted_dates = sorted(time_series.keys())
    return {
        "dates": sorted_dates,
        "positive": [time_series[date]["positive"] for date in sorted_dates],
        "negative": [time_series[date]["negative"] for date in sorted_dates],
        "neutral": [time_series[date]["neutral"] for date in sorted_dates]
    }

@login_required
def ai_analysis(request):
    try:
        # Request body'yi parse et
        data = json.loads(request.body)

        # Veri validasyonu
        if not data.get('subreddit_1'):
            raise ValueError("Primary subreddit is required")

        # AI analizi yap
        analysis_result = process_ai_analysis(data)

        # Başarılı analiz sonucunu veritabanına kaydet
        report = None
        try:
            report = AIReport.objects.create(
                user=request.user,
                subreddit_1=data['subreddit_1'],
                subreddit_2=data.get('subreddit_2', ''),
                content=analysis_result,
                days_analyzed=data['days'],
                emotion_data={
                    'subreddit_1': data.get('emotion_distribution_1', {}),
                    'subreddit_2': data.get('emotion_distribution_2', {})
                },
                time_series_data={
                    'subreddit_1': data.get('time_series_1', {}),
                    'subreddit_2': data.get('time_series_2', {})
                },
                news_data={}
            )
        except Exception as e:
            print(f"Error saving report: {str(e)}")
            # Rapor kaydedilemese bile analizi göster

        return JsonResponse({
            'status': 'success',
            'analysis': analysis_result,
            'report_id': report.id if report else None
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)

    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

    except Exception as e:
        print(f"Unexpected error in ai_analysis: {str(e)}")
        print(traceback.format_exc())  # Detaylı hata log'u
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred. Please try again later.'
        }, status=500)

@login_required
def user_reports(request):
    """Kullanıcının geçmiş raporlarını gösterir"""
    reports = AIReport.objects.filter(user=request.user)
    return render(request, 'analysis/user_reports.html', {'reports': reports})


@login_required
def download_report_pdf(request, report_id):
    """Raporu PDF olarak indirir"""
    try:
        report = AIReport.objects.get(id=report_id, user=request.user)
        pdf = generate_pdf_report(report)

        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"report_{report.id}_{report.created_at.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    except AIReport.DoesNotExist:
        return HttpResponse('Report not found', status=404)