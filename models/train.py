from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import pandas as pd
import joblib

def train_model(data, target_column):
    X = data.drop(columns=[target_column])
    y = data[target_column]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    return model

def save_model(model, filename):
    joblib.dump(model, filename)
    print(f"Model saved to {filename}")

if __name__ == "__main__":
    # Example usage
    data = pd.read_csv('path_to_processed_data.csv')  # Update with actual path
    model = train_model(data, target_column='churn')  # Update 'churn' with actual target column name
    save_model(model, 'churn_prediction_model.pkl')