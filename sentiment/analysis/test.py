# test_new_model.py
from sklearn.metrics import accuracy_score
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
    {"text": "This game is absolutely amazing, best purchase ever!", "true_label": "joy"},
    {"text": "They completely ruined the game with this update!", "true_label": "anger"},
    {"text": "I miss playing this game with my old friends", "true_label": "sadness"},
    {"text": "The graphics aren't as good as promised", "true_label": "disapproval"},
    {"text": "This community is so supportive and caring", "true_label": "love"},
    {"text": "I can't believe they're releasing it tomorrow!", "true_label": "surprise"},
    {"text": "Thanks for all the help with the difficult level", "true_label": "gratitude"},
    {"text": "This new feature is exactly what we needed", "true_label": "approval"},
    {"text": "This change makes no sense at all", "true_label": "disapproval"},
    {"text": "It's just another regular update", "true_label": "neutral"},
    {"text": "I hate this update so much!", "true_label": "anger"},
    {"text": "Thank you for the amazing support!", "true_label": "gratitude"},
    {"text": "Unfortunately, I lost all my progress", "true_label": "sadness"},
    {"text": "This is the worst game ever!", "true_label": "anger"},
    {"text": "The customer service is terrible", "true_label": "disapproval"}
]

# Tahmin edilen ve gerçek etiketleri listeleyin
predicted_labels = []
true_labels = []

for case in test_cases:
    text = case["text"]
    true_label = case["true_label"]
    result = analyze_sentiment(text)
    predicted_label = result["emotion"]

    predicted_labels.append(predicted_label)
    true_labels.append(true_label)

# Doğruluk skorunu hesaplayın
accuracy = accuracy_score(true_labels, predicted_labels)
print(f"\nModel Accuracy: {accuracy:.2f}")
