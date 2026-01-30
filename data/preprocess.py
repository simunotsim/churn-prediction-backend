from sklearn.model_selection import train_test_split
import pandas as pd

def load_data(file_path):
    """Load raw customer data from a CSV file."""
    data = pd.read_csv(file_path)
    return data

def clean_data(data):
    """Clean the customer data by handling missing values and duplicates."""
    data = data.drop_duplicates()
    data = data.fillna(method='ffill')  # Forward fill for missing values
    return data

def preprocess_data(file_path):
    """Main function to load and preprocess the customer data."""
    raw_data = load_data(file_path)
    cleaned_data = clean_data(raw_data)
    return cleaned_data

def save_processed_data(data, output_path):
    """Save the processed data to a specified path."""
    data.to_csv(output_path, index=False)