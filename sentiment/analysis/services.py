import os
from datetime import datetime, timedelta
from pathlib import Path

import praw
from transformers import pipeline
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent


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
        client_id="l8vPsbLsj1MI4MSrtPCjxw",
        client_secret="7a_WCzJxGgVo7gKYL9_mWwsBVKQo1A",
        user_agent="sentiment analysis"
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
