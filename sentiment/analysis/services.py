import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import praw
import requests
from dotenv import load_dotenv
from transformers import pipeline
from decouple import config
import google.generativeai as genai
from googleapiclient.discovery import build
from gnews import GNews
import markdown2  # Markdown -> HTML dönüşümü için


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

MODEL_PATH = os.path.join(BASE_DIR, 'analysis/fine_tuned_roberta_emotion')

emotion_analysis = pipeline(
    "text-classification",
    model=MODEL_PATH,
    tokenizer=MODEL_PATH
)

# Etiket mapping'i
label_mapping = {
    'LABEL_0': 'joy',
    'LABEL_1': 'anger',
    'LABEL_2': 'sadness',
    'LABEL_3': 'disappointment',
    'LABEL_4': 'love',
    'LABEL_5': 'surprise',
    'LABEL_6': 'gratitude',
    'LABEL_7': 'approval',
    'LABEL_8': 'disapproval',
    'LABEL_9': 'neutral'
}


# services.py
def get_filtered_reddit_posts(subreddit_name, days=30, post_count=50, sort_by='score', keywords=None):
    reddit = praw.Reddit(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        user_agent=os.getenv('USER_AGENT')
    )

    subreddit = reddit.subreddit(subreddit_name)
    posts = []

    # Time filter için timestamp hesapla
    time_filter = datetime.now() - timedelta(days=int(days))

    # Daha fazla post al
    post_limit = post_count * 4  # İstenen sayının 4 katı kadar post al

    # Farklı sıralama metodlarını dene
    for post in subreddit.hot(limit=post_limit):
        post_time = datetime.fromtimestamp(post.created_utc)

        # Zaman kontrolü
        if post_time < time_filter:
            continue

        # Keyword kontrolü
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(',')]
            if not any(keyword.lower() in post.title.lower() or
                       (hasattr(post, 'selftext') and keyword.lower() in post.selftext.lower())
                       for keyword in keyword_list):
                continue

        # Post nesnesini dictionary'e çevir
        post_dict = {
            "title": post.title,
            "score": post.score,
            "created_utc": datetime.fromtimestamp(post.created_utc).isoformat(),
            "num_comments": post.num_comments,
            "text": post.selftext if hasattr(post, 'selftext') else ""
        }
        posts.append(post_dict)

    # Sıralama
    posts.sort(key=lambda x: x[sort_by], reverse=True)

    # İstenilen sayıda post döndür
    return posts[:post_count]


def analyze_sentiment(text):
    # Çoklu tahmin al
    results = emotion_analysis(text, top_k=3)

    primary_result = results[0]
    emotion = label_mapping[primary_result['label']]
    score = primary_result['score']

    text = text.lower()

    # Genişletilmiş anahtar kelime setleri
    anger_words = {
        'ruined', 'terrible', 'awful', 'hate', 'worst', 'garbage', 'trash',
        'pathetic', 'useless', 'horrible'
    }

    sadness_words = {
        'miss', 'sad', 'unfortunately', 'lost', 'disappointing', 'sorry',
        'regret', 'gone', 'never', 'anymore'
    }

    gratitude_words = {
        'thanks', 'thank', 'grateful', 'appreciate', 'thankful', 'blessed',
        'appreciated', 'recognition'
    }

    disapproval_words = {
        "aren't", 'not good', 'bad', 'poor', 'terrible', 'waste', 'broken',
        'missing', 'failed', 'fails', 'wrong'
    }

    surprise_words = {
        'wow', 'omg', 'unexpected', 'surprised', 'shocking', 'unbelievable',
        'cant believe', "can't believe", 'amazing', 'incredible'
    }

    love_words = {
        'love', 'awesome', 'fantastic', 'wonderful', 'great', 'supportive',
        'caring', 'helpful', 'best'
    }

    # Güven skoru eşiklerini ayarla
    if score < 0.90:  # Orta güven skoru için kural tabanlı düzeltmeler
        # Negatif duygular için kontrol
        if any(word in text for word in anger_words):
            emotion = 'anger'
        elif any(word in text for word in sadness_words):
            emotion = 'sadness'
        elif any(word in text for word in disapproval_words):
            emotion = 'disapproval'

        # Pozitif duygular için kontrol
        elif any(word in text for word in gratitude_words):
            emotion = 'gratitude'
        elif any(word in text for word in love_words):
            emotion = 'love'
        elif any(word in text for word in surprise_words):
            emotion = 'surprise'

        # İkinci tahmin kontrolü
        elif len(results) > 1:
            second_score = results[1]['score']
            second_emotion = label_mapping[results[1]['label']]
            score_diff = score - second_score

            if score_diff < 0.15:  # Tahminler çok yakınsa
                # Belirli durum kontrolleri
                if emotion == 'approval' and second_emotion in ['disappointment', 'disapproval']:
                    emotion = second_emotion
                elif emotion == 'joy' and second_emotion == 'gratitude' and any(
                        word in text for word in gratitude_words):
                    emotion = second_emotion
                elif emotion == 'sadness' and second_emotion == 'anger' and any(word in text for word in anger_words):
                    emotion = second_emotion

    # Özel durumlar için son kontroller
    if 'hate' in text and emotion not in ['anger', 'disapproval']:
        emotion = 'anger'
    if 'worst' in text and emotion not in ['anger', 'disapproval']:
        emotion = 'anger'
    if 'thank' in text and emotion not in ['gratitude']:
        emotion = 'gratitude'

    return {
        "emotion": emotion,
        "score": score,
        "all_predictions": [{"emotion": label_mapping[r['label']], "score": r['score']} for r in results[:3]]
    }


def get_news_articles(subreddit, days):
    """GNews API'den ilgili haberleri çeker"""
    api_key = os.getenv('GNEWS_API_KEY')
    from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # GNews API endpoint
    url = os.getenv('GNEWS_ENDPOINT')

    params = {
        'q': subreddit,
        'apikey': api_key,
        'max': 5,  # Maksimum haber sayısı
        'lang': 'en',  # Dil
        'from': from_date,  # Başlangıç tarihi
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # HTTP hatalarını kontrol et

        data = response.json()
        articles = []

        # API'den gelen haberleri formatla
        if 'articles' in data:
            for article in data['articles']:
                articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'content': article.get('content', ''),
                    'published_date': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', ''),
                    'url': article.get('url', '')
                })

        return articles

    except Exception as e:
        print(f"GNews API Error for {subreddit}: {str(e)}")
        return []


def analyze_with_gemini(data, news_articles):
    """Gemini API kullanarak analiz yapar"""
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-pro')

    # Analiz verilerini formatlama
    prompt = f"""
    Sen bir veri analisti ve topluluk yöneticisisin. Aşağıdaki Reddit topluluğu/topluluklarının son {data['days']} günlük analiz verilerini ve ilgili haberleri inceleyerek kapsamlı bir rapor hazırlamalısın.
    
    Raporu **yalnızca HTML formatında** oluştur. Başka bir format kullanma.

    Kullanılacak HTML yapısı:
    <section>
      <h3></h3>
      <p></p>
      <ul>
        <li></li>
      </ul>
    </section>
    
    Subreddit(ler):
    - {data['subreddit_1']}
    {f"- {data['subreddit_2']}" if 'subreddit_2' in data else ""}

    Duygu Dağılımı:
    {json.dumps(data['emotion_distribution_1'], indent=2)}
    {json.dumps(data['emotion_distribution_2'], indent=2) if 'emotion_distribution_2' in data else ""}

    Zaman Serisi Verileri:
    {json.dumps(data['time_series_1'], indent=2)}
    {json.dumps(data['time_series_2'], indent=2) if 'time_series_2' in data else ""}

    İlgili Haberler:
    {json.dumps(news_articles, indent=2)}

    Lütfen şu noktaları analiz et:
    1. Öne çıkan duygusal eğilimler ve bunların olası nedenleri
    2. Zaman içindeki önemli değişimler ve bunların haberlerle olası bağlantıları
    3. Topluluk dinamikleri ve genel atmosfer
    4. Varsa dikkat çeken sorunlar veya olumlu gelişmeler
    5. Karşılaştırmalı analiz (iki subreddit varsa)

    Önemli noktalar:
    - Analizde hem duygu verilerini hem de haber içeriklerini göz önünde bulundur
    - Varsa ani duygu değişimlerini açıklamaya çalış
    - Topluluk tepkilerini haberlerle ilişkilendir
    - Belirgin trendleri vurgula

    Çıktıyı HTML formatında üret ve şu şekilde yapılandır:
    - <h3> başlıklar </h3>
    - <p> açıklamalar </p>
    - <ul> <li> maddeler </li> </ul>
    Her paragrafın altında uygun şekilde açıklamalar ekle.
    Önemli bulguları <strong> etiketi ile vurgula.
    """

    response = model.generate_content(prompt)

    # Gelen yanıtı Markdown'dan HTML'ye çevir (arada bozuk gelmesin diye)
    html_content = markdown2.markdown(response.text)


    # HTML formatını güzelleştir ve Bootstrap sınıfları ekle
    formatted_response = f"""
    <div class="ai-report">
        <div class="alert alert-info mb-4">
            <h3 class="alert-heading mb-3">AI Analiz Raporu</h3>
            <p class="mb-0"><small>Bu rapor, son {data['days']} günlük Reddit verileri ve güncel haberler analiz edilerek oluşturulmuştur.</small></p>
        </div>
        {html_content}
    </div>
    """

    return formatted_response


def process_ai_analysis(analysis_data):
    """Analiz verilerini işler ve AI raporu oluşturur"""
    try:
        # İlgili haberleri çek
        news_1 = get_news_articles(analysis_data['subreddit_1'], analysis_data['days'])
        news_2 = []
        if 'subreddit_2' in analysis_data and analysis_data['subreddit_2']:
            news_2 = get_news_articles(analysis_data['subreddit_2'], analysis_data['days'])

        all_news = {
            analysis_data['subreddit_1']: news_1,
            analysis_data.get('subreddit_2', ''): news_2
        }

        # Gemini ile analiz yap
        analysis_result = analyze_with_gemini(analysis_data, all_news)

        return analysis_result

    except Exception as e:
        print(f"AI Analysis Error: {str(e)}")
        return f"""
        <div class="alert alert-danger">
            <h4>AI Analizi Sırasında Hata Oluştu</h4>
            <p>{str(e)}</p>
            <hr>
            <p class="mb-0">Lütfen daha sonra tekrar deneyin veya sistem yöneticisi ile iletişime geçin.</p>
        </div>
        """
