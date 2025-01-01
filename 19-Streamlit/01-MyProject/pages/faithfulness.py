from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    faithfulness,
    context_recall,
    context_precision,
)
from datasets import Dataset
import pandas as pd

# 샘플 데이터 생성
data = {
    "question": [
        "What is the capital of France?",
        "Who wrote '1984'?, Orwell?",
        "What is the boiling point of water?",
    ],
    "answer": ["Paris", "Orwell", "100°C"],
    "generated_answer": ["Paris", "Orwell", "100°C"],
    "context": [
        "Paris",
        "Orwell",
        "100°C",
    ],
    # 추가 열 생성
    "reference": [
        "Paris",
        "Orwell",
        "100°C",
    ],
    # 리스트 형태로 변경
    "retrieved_contexts": [
        ["Paris"],
        ["Orwell"],
        ["100°C"],
    ],
}

# DataFrame으로 변환
df = pd.DataFrame(data)

# 데이터셋 변환
test_dataset = Dataset.from_pandas(df)

# RAGAS 평가
result = evaluate(
    dataset=test_dataset,
    metrics=[
        context_precision,
        faithfulness,
        answer_relevancy,
        context_recall,
    ],
)

# 결과 출력
print("Evaluation Results:")
print(result)

# DataFrame 변환 및 상위 5개 출력
result_df = result.to_pandas()
print("\nTop 5 Results:")
print(result_df.head())