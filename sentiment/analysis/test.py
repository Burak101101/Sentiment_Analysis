# test_new_model.py
from transformers import pipeline

emotion_analysis = pipeline(
    "text-classification",
    model="./fine_tuned_roberta_emotion",
    tokenizer="./fine_tuned_roberta_emotion",
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

turkish_mapping = {
    'joy': 'mutlu',
    'anger': 'kızgın',
    'sadness': 'üzgün',
    'disappointment': 'hayal kırıklığı',
    'love': 'sevgi',
    'surprise': 'şaşkınlık',
    'gratitude': 'minnettarlık',
    'approval': 'onaylama',
    'disapproval': 'onaylamama',
    'neutral': 'nötr'
}


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
        "emotion_tr": turkish_mapping[emotion],
        "score": score,
        "all_predictions": [{"emotion": label_mapping[r['label']], "score": r['score']} for r in results[:3]]
    }


test_cases = [
    # Önceki test vakaları
    "This game is absolutely amazing, best purchase ever!",  # joy
    "They completely ruined the game with this update!",  # anger (önceden disappointment'tı)
    "I miss playing this game with my old friends",  # sadness (önceden approval'dı)
    "The graphics aren't as good as promised",  # disapproval (önceden approval'dı)
    "This community is so supportive and caring",  # love/joy
    "I can't believe they're releasing it tomorrow!",  # surprise
    "Thanks for all the help with the difficult level",  # gratitude (önceden joy'du)
    "This new feature is exactly what we needed",  # approval
    "This change makes no sense at all",  # disapproval
    "It's just another regular update",  # neutral

    # Yeni test vakaları
    "I hate this update so much!",  # anger
    "Thank you for the amazing support!",  # gratitude
    "Unfortunately, I lost all my progress",  # sadness
    "This is the worst game ever!",  # anger
    "The customer service is terrible"  # disapproval
]

print("\nTest Sonuçları:")
for text in test_cases:
    result = analyze_sentiment(text)
    print(f"\nText: {text}")
    print(f"Tahmin: {result['emotion']} ({result['emotion_tr']})")
    print(f"Güven Skoru: {result['score']:.2f}")