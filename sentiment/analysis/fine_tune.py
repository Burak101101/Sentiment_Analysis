import pandas as pd
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
    AutoConfig
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import torch


def prepare_dataset_from_csv(csv_path):
    # CSV dosyasını oku
    df = pd.read_csv(csv_path)

    # text ve labels sütunlarını kontrol et
    if 'text' not in df.columns or 'labels' not in df.columns:
        raise ValueError("CSV dosyasında 'text' ve 'labels' sütunları bulunmalıdır.")

    # Orijinal etiketleri sıfır tabanlı sisteme dönüştürme
    original_labels = sorted(df['labels'].unique())  # Mevcut etiketleri sırala
    label_mapping = {original: new for new, original in enumerate(original_labels)}  # Haritalama
    df['labels'] = df['labels'].map(label_mapping)  # Güncelle

    print("Etiket haritalama tablosu:", label_mapping)  # Haritalama tablosunu yazdır

    # Dataset'e çevir
    dataset = Dataset.from_pandas(df)

    # Train-test split
    dataset = dataset.train_test_split(test_size=0.2)

    return dataset, label_mapping


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
    model_name = "SamLowe/roberta-base-go_emotions"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    config = AutoConfig.from_pretrained(
        model_name,
        num_labels=10,
        problem_type="single_label_classification"
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        config=config,
        ignore_mismatched_sizes=True
    )

    def tokenize_function(examples):
        tokenized_inputs = tokenizer(
            examples['text'],
            padding='max_length',
            truncation=True,
            max_length=128
        )
        tokenized_inputs['labels'] = examples['labels']
        return tokenized_inputs

    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset['train'].column_names
    )

    training_args = TrainingArguments(
        output_dir="roberta_results",
        learning_rate=1e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=4,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        logging_dir='./logs',
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        greater_is_better=True,
        push_to_hub=False
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer, padding=True)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset['train'],
        eval_dataset=tokenized_dataset['test'],
        compute_metrics=compute_metrics,
        data_collator=data_collator
    )

    print("Eğitim başlıyor...")
    trainer.train()

    print("Model kaydediliyor...")
    model.save_pretrained("./fine_tuned_roberta_emotion")
    tokenizer.save_pretrained("./fine_tuned_roberta_emotion")

    return trainer


if __name__ == "__main__":
    csv_path = "balanced_emotion_dataset.csv"
    print("CSV veri seti hazırlanıyor...")
    dataset, label_mapping = prepare_dataset_from_csv(csv_path)

    print("Model eğitimi başlatılıyor...")
    trainer = train_model(dataset)

    print("Model eğitimi tamamlandı.")
