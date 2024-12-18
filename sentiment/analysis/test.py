# test_emotions.py
from services import analyze_sentiment

test_cases = [
    # Mutluluk (Joy) test cases
    {
        "text": "Just got my dream job! Can't believe it!",
        "expected": "mutlu"
    },
    {
        "text": "We won the championship! Years of hard work paid off!",
        "expected": "mutlu"
    },

    # Kızgınlık (Anger) test cases
    {
        "text": "This is absolutely unacceptable! Worst service ever!",
        "expected": "kızgın"
    },
    {
        "text": "They just removed the feature everyone was using! This is ridiculous!",
        "expected": "kızgın"
    },

    # Üzgünlük (Sadness) test cases
    {
        "text": "I miss the old days when we used to play together",
        "expected": "üzgün"
    },
    {
        "text": "My favorite character died in the series finale",
        "expected": "üzgün"
    },

    # Hayal Kırıklığı (Disappointment) test cases
    {
        "text": "After all that hype, the game was just mediocre",
        "expected": "hayal kırıklığı"
    },
    {
        "text": "They promised to fix it but nothing has changed",
        "expected": "hayal kırıklığı"
    },

    # Sevgi (Love) test cases
    {
        "text": "This community is amazing, you all make my day better!",
        "expected": "sevgi"
    },
    {
        "text": "I absolutely adore this game and its developers",
        "expected": "sevgi"
    },

    # Şaşkınlık (Surprise) test cases
    {
        "text": "OMG! They just announced a new installment!",
        "expected": "şaşkınlık"
    },
    {
        "text": "I can't believe they actually did it! No one saw this coming!",
        "expected": "şaşkınlık"
    }
]


def run_tests():
    correct = 0
    total = len(test_cases)

    print("Starting emotion analysis tests...\n")

    for i, test in enumerate(test_cases, 1):
        result = analyze_sentiment(test["text"])
        is_correct = result["emotion"] == test["expected"]

        print(f"Test {i}:")
        print(f"Text: {test['text']}")
        print(f"Expected: {test['expected']}")
        print(f"Got: {result['emotion']} (confidence: {result['score']:.2f})")
        print(f"Status: {'✓ Correct' if is_correct else '✗ Wrong'}\n")

        if is_correct:
            correct += 1

    accuracy = (correct / total) * 100
    print(f"Overall Results:")
    print(f"Total Tests: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.2f}%")


if __name__ == "__main__":
    run_tests()