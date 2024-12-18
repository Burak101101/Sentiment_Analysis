# prepare_dataset.py
from datasets import load_dataset, Dataset
import pandas as pd
import random


def get_emotion_dataset():
    # Veri setini yükle
    dataset = load_dataset("google-research-datasets/go_emotions", "simplified")

    # Go_emotions etiket eşleştirmesi
    emotion_id_mapping = {
        'joy': 6,
        'anger': 0,
        'sadness': 12,
        'disappointment': 3,
        'love': 7,
        'surprise': 14
    }

    # Veri setini filtrele
    def filter_emotions(example):
        return any(label_id in [emotion_id_mapping[emotion] for emotion in emotion_id_mapping.keys()]
                   for label_id in example['labels'])

    filtered_dataset = dataset.filter(filter_emotions)

    # Veri seti istatistikleri
    print("\nVeri seti istatistikleri:")
    emotion_counts = {emotion: 0 for emotion in emotion_id_mapping.keys()}

    for example in filtered_dataset['train']:
        for label_id in example['labels']:
            for emotion, emotion_id in emotion_id_mapping.items():
                if label_id == emotion_id:
                    emotion_counts[emotion] += 1

    total_samples = sum(emotion_counts.values())
    print(f"\nToplam örnek sayısı: {total_samples}")
    print("\nDuygu başına örnek sayıları:")
    for emotion, count in emotion_counts.items():
        percentage = (count / total_samples) * 100 if total_samples > 0 else 0
        print(f"{emotion}: {count} örnek ({percentage:.2f}%)")

    # Örnek metinleri göster
    print("\nHer duygudan örnek metinler:")
    examples_by_emotion = {emotion: [] for emotion in emotion_id_mapping.keys()}

    for example in filtered_dataset['train']:
        for label_id in example['labels']:
            for emotion, emotion_id in emotion_id_mapping.items():
                if label_id == emotion_id and len(examples_by_emotion[emotion]) < 2:
                    examples_by_emotion[emotion].append(example['text'])

    for emotion, examples in examples_by_emotion.items():
        print(f"\n{emotion.upper()} örnekleri:")
        for example in examples:
            print(f"- {example}")

    return filtered_dataset


def balance_dataset(dataset, target_size=1500):
    emotion_id_mapping = {
        'joy': 6,
        'anger': 0,
        'sadness': 12,
        'disappointment': 3,
        'love': 7,
        'surprise': 14
    }

    # Her duygu için örnekleri ayır
    emotion_examples = {emotion: [] for emotion in emotion_id_mapping.keys()}

    for example in dataset['train']:
        for label_id in example['labels']:
            for emotion, emotion_id in emotion_id_mapping.items():
                if label_id == emotion_id:
                    emotion_examples[emotion].append({
                        'text': example['text'],
                        'label': emotion
                    })

    # Her duygu için örnekleri dengele
    balanced_data = []
    for emotion, examples in emotion_examples.items():
        if len(examples) > target_size:
            # Fazla örnekleri rastgele azalt
            balanced_data.extend(random.sample(examples, target_size))
        else:
            # Az olan örnekleri tekrarlayarak arttır (upsampling)
            while len(examples) < target_size:
                examples.extend(random.sample(examples, min(target_size - len(examples), len(examples))))
            balanced_data.extend(examples[:target_size])

    # Verileri karıştır
    random.shuffle(balanced_data)

    # DataFrame'e çevir
    df = pd.DataFrame(balanced_data)

    # Dataset'e çevir
    balanced_dataset = Dataset.from_pandas(df)

    # İstatistikleri göster
    print("\nDengelenmiş veri seti istatistikleri:")
    for emotion in emotion_id_mapping.keys():
        count = len([x for x in balanced_data if x['label'] == emotion])
        print(f"{emotion}: {count} örnek")

    return balanced_dataset


# Orijinal veri setini yükle
dataset = get_emotion_dataset()

# Veri setini dengele
balanced_dataset = balance_dataset(dataset)
