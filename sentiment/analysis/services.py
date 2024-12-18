from datetime import datetime
import praw
from transformers import pipeline
from decouple import config


sentiment_analysis = pipeline("text-classification", model="bhadresh-savani/distilbert-base-uncased-emotion")

def get_reddit_posts(subreddit_name):
    reddit = praw.Reddit(
        client_id=config("client_id"),
        client_secret=config("client_secret"),
        user_agent=config("user_agent")
    )
    subreddit = reddit.subreddit(subreddit_name)
    posts = []
    for post in subreddit.hot(limit=10):
        posts.append({"title": post.title, "score": post.score, "created_utc": datetime.utcfromtimestamp(post.created_utc).isoformat()  # Zaman bilgisi
})

    print(posts)  # Gelen veri yapısını kontrol edin
    return posts


def analyze_sentiment(text):
    result = sentiment_analysis(text)[0]

    # Duygu etiketlerini Türkçe'ye çevirelim ve istediğimiz duyguları filtreleyelim
    emotion_mapping = {
        'joy': 'mutlu',
        'anger': 'kızgın',
        'sadness': 'üzgün',
        'disappointment': 'hayal kırıklığı',
        'love': 'sevgi',
        'surprise': 'şaşkınlık'
    }

    emotion = result["label"]
    score = result["score"]

    # Eğer duygu bizim listedeyse direkt döndür, değilse en yakın duyguya eşle
    mapped_emotion = emotion_mapping.get(emotion, emotion)

    return {
        "emotion": mapped_emotion,
        "score": score
    }
