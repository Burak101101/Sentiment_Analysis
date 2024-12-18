# fine_tune.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from datasets import load_dataset, Dataset
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import random
import torch


def prepare_dataset():
    # Veri setini yükle
    dataset = load_dataset("go_emotions", "simplified")

    # İstediğimiz duyguların ID'leri
    emotion_ids = {
        6: 'joy',
        0: 'anger',
        12: 'sadness',
        3: 'disappointment',
        7: 'love',
        14: 'surprise'
    }

    # Veriyi hazırla
    texts = []
    labels = []

    for example in dataset['train']:
        # Örneğin etiketlerinden istediğimiz bir duygu var mı kontrol et
        for label in example['labels']:
            if label in emotion_ids:
                texts.append(example['text'])
                labels.append(list(emotion_ids.keys()).index(label))  # Yeni index'e çevir
                break

    # Her duygu için maksimum 1500 örnek al
    emotion_counts = {i: 0 for i in range(len(emotion_ids))}
    final_texts = []
    final_labels = []

    for text, label in zip(texts, labels):
        if emotion_counts[label] < 1500:
            final_texts.append(text)
            final_labels.append(label)
            emotion_counts[label] += 1

    # Dataset oluştur
    dataset_dict = {
        'text': final_texts,
        'labels': final_labels
    }

    # Dataset'e çevir
    dataset = Dataset.from_dict(dataset_dict)

    # Train-test split
    dataset = dataset.train_test_split(test_size=0.2)

    return dataset


def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
    acc = accuracy_score(labels, preds)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall
    }


def train_model(dataset):
    # Model ve tokenizer'ı yükle
    model_name = "bhadresh-savani/distilbert-base-uncased-emotion"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=6  # 6 duygu
    )

    # Tokenization fonksiyonu
    def tokenize_function(examples):
        return tokenizer(
            examples['text'],
            padding='max_length',
            truncation=True,
            max_length=128
        )

    # Dataset'i tokenize et
    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    # Eğitim argümanları
    training_args = TrainingArguments(
        output_dir="./results",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=3,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True
    )

    # Trainer'ı oluştur
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset['train'],
        eval_dataset=tokenized_dataset['test'],
        compute_metrics=compute_metrics
    )

    # Eğitimi başlat
    print("Eğitim başlıyor...")
    trainer.train()

    # Modeli kaydet
    print("Model kaydediliyor...")
    model.save_pretrained("./fine_tuned_emotion_model")
    tokenizer.save_pretrained("./fine_tuned_emotion_model")

    return trainer


if __name__ == "__main__":
    print("Veri seti hazırlanıyor...")
    dataset = prepare_dataset()

    print("Model eğitimi başlatılıyor...")
    trainer = train_model(dataset)