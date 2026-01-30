from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import pandas as pd

def build_features(data):
    """
    Build features for customer churn prediction from the processed data.
    
    Parameters:
    data (pd.DataFrame): The processed customer data.
    
    Returns:
    pd.DataFrame: The DataFrame with engineered features.
    """
    
    # Define numerical and categorical features
    numerical_features = ['age', 'tenure', 'monthly_spending']
    categorical_features = ['gender', 'subscription_type', 'customer_segment']

    # Create preprocessing pipelines for numerical and categorical features
    numerical_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder(handle_unknown='ignore')

    # Combine preprocessing steps
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )

    # Create a pipeline that first transforms the data and then returns it
    pipeline = Pipeline(steps=[('preprocessor', preprocessor)])

    # Fit and transform the data
    features = pipeline.fit_transform(data)

    # Convert the transformed features back to a DataFrame
    feature_names = (pipeline.named_steps['preprocessor']
                     .transformers_[0][1]
                     .get_feature_names_out(numerical_features).tolist() +
                     pipeline.named_steps['preprocessor']
                     .transformers_[1][1]
                     .get_feature_names_out(categorical_features).tolist())

    return pd.DataFrame(features, columns=feature_names)