from datasets import load_dataset, Dataset
import pandas as pd
import random


def get_emotion_dataset():
    # Veri setini yükle
    dataset = load_dataset("google-research-datasets/go_emotions", "simplified")

    # Go_emotions etiket eşleştirmesi
    emotion_id_mapping = {
        6: 'joy',
        0: 'anger',
        12: 'sadness',
        3: 'disappointment',
        7: 'love',
        14: 'surprise',
        4: 'gratitude',
        1: 'approval',
        2: 'disapproval',
        27: 'neutral'
    }

    # Veri setini filtrele
    def filter_emotions(example):
        return any(label_id in emotion_id_mapping.keys() for label_id in example['labels'])

    filtered_dataset = dataset.filter(filter_emotions)

    # Veri seti istatistikleri
    print("\nVeri seti istatistikleri:")
    emotion_counts = {emotion_id: 0 for emotion_id in emotion_id_mapping.keys()}

    for example in filtered_dataset['train']:
        for label_id in example['labels']:
            if label_id in emotion_id_mapping:
                emotion_counts[label_id] += 1

    total_samples = sum(emotion_counts.values())
    print(f"\nToplam örnek sayısı: {total_samples}")
    print("\nDuygu başına örnek sayıları:")
    for emotion_id, count in emotion_counts.items():
        emotion = emotion_id_mapping[emotion_id]
        percentage = (count / total_samples) * 100 if total_samples > 0 else 0
        print(f"{emotion}: {count} örnek ({percentage:.2f}%)")

    # Örnek metinleri göster
    print("\nHer duygudan örnek metinler:")
    examples_by_emotion = {emotion_id: [] for emotion_id in emotion_id_mapping.keys()}

    for example in filtered_dataset['train']:
        for label_id in example['labels']:
            if label_id in emotion_id_mapping and len(examples_by_emotion[label_id]) < 2:
                examples_by_emotion[label_id].append(example['text'])

    for emotion_id, examples in examples_by_emotion.items():
        emotion = emotion_id_mapping[emotion_id]
        print(f"\n{emotion.upper()} örnekleri:")
        for example in examples:
            print(f"- {example}")

    return filtered_dataset


def balance_dataset(dataset, target_size=1500):
    emotion_id_mapping = {
        6: 'joy',
        0: 'anger',
        12: 'sadness',
        3: 'disappointment',
        7: 'love',
        14: 'surprise',
        4: 'gratitude',
        1: 'approval',
        2: 'disapproval',
        27: 'neutral'
    }

    # Her duygu için örnekleri ayır
    emotion_examples = {emotion_id: [] for emotion_id in emotion_id_mapping.keys()}

    for example in dataset['train']:
        for label_id in example['labels']:
            if label_id in emotion_id_mapping:
                emotion_examples[label_id].append({
                    'text': example['text'],
                    'label': label_id
                })

    # Her duygu için örnekleri dengele
    balanced_data = []
    for emotion_id, examples in emotion_examples.items():
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
    for emotion_id in emotion_id_mapping.keys():
        count = len([x for x in balanced_data if x['label'] == emotion_id])
        emotion = emotion_id_mapping[emotion_id]
        print(f"{emotion}: {count} örnek")

    return balanced_dataset


# Orijinal veri setini yükle
dataset = get_emotion_dataset()

# Veri setini dengele
balanced_dataset = balance_dataset(dataset)

# Veri setini kaydet
balanced_dataset.to_csv("balanced_emotion_dataset.csv", index=False)
print("\nDengeleme işlemi tamamlandı.")
