from flask import Flask
from src.data.loaders import load_data
from src.data.preprocess import preprocess_data
from src.features.build_features import create_features
from src.models.train import train_model
from src.models.predict import make_predictions
from src.models.evaluation import evaluate_model
from src.retention.recommendations import generate_recommendations

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Customer Churn Prediction and Retention Analytics System!"

@app.route('/run')
def run_analysis():
    # Load data
    raw_data = load_data()
    
    # Preprocess data
    processed_data = preprocess_data(raw_data)
    
    # Create features
    features = create_features(processed_data)
    
    # Train model
    model = train_model(features)
    
    # Make predictions
    predictions = make_predictions(model, features)
    
    # Evaluate model
    evaluation_results = evaluate_model(predictions, features)
    
    # Generate recommendations
    recommendations = generate_recommendations(predictions)
    
    return {
        "evaluation": evaluation_results,
        "recommendations": recommendations
    }

if __name__ == '__main__':
    app.run(debug=True)