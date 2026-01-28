import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import joblib
import os

def train_model():
    # Load data
    if not os.path.exists("data/training_data.csv"):
        print("Training data not found. Run generate_training_data.py first.")
        return

    df = pd.read_csv("data/training_data.csv", on_bad_lines='skip')
    # Cleanup any NaN values if present
    df = df.dropna(subset=['text', 'label'])
    X = df["text"]
    y = df["label"]

    # Split data (though it's small, good practice)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Create pipeline: TF-IDF + Logistic Regression
    # We use char_wb analyzer to better handle nicknames and Finnish suffixes
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5))),
        ('clf', LogisticRegression(solver='lbfgs', max_iter=1000))
    ])

    # Train
    print("Training model...")
    pipeline.fit(X_train, y_train)

    # Evaluate
    score = pipeline.score(X_test, y_test)
    print(f"Model accuracy on test set: {score:.2f}")

    # Save model
    os.makedirs("models", exist_ok=True)
    joblib.dump(pipeline, "models/violation_model.joblib")
    print("Model saved to models/violation_model.joblib")

if __name__ == "__main__":
    train_model()
