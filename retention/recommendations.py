from typing import List, Dict

def generate_retention_strategies(churn_predictions: List[Dict], customer_data: pd.DataFrame) -> List[str]:
    strategies = []
    
    for prediction in churn_predictions:
        customer_id = prediction['customer_id']
        risk_level = prediction['risk_level']
        
        customer_info = customer_data[customer_data['customer_id'] == customer_id]
        
        if risk_level == 'high':
            strategies.append(f"Offer a discount to customer {customer_id} to encourage retention.")
        elif risk_level == 'medium':
            strategies.append(f"Send a personalized email to customer {customer_id} highlighting new features.")
        elif risk_level == 'low':
            strategies.append(f"Engage customer {customer_id} with loyalty rewards.")
    
    return strategies

def recommend_based_on_segments(customer_segments: Dict[str, List[int]], customer_data: pd.DataFrame) -> Dict[str, List[str]]:
    segment_strategies = {}
    
    for segment, customers in customer_segments.items():
        strategies = []
        for customer_id in customers:
            customer_info = customer_data[customer_data['customer_id'] == customer_id]
            strategies.append(f"Tailor marketing campaigns for segment {segment} including customer {customer_id}.")
        
        segment_strategies[segment] = strategies
    
    return segment_strategies

# Example usage:
# churn_predictions = [{'customer_id': 1, 'risk_level': 'high'}, {'customer_id': 2, 'risk_level': 'medium'}]
# customer_data = pd.DataFrame({'customer_id': [1, 2], 'name': ['Alice', 'Bob']})
# print(generate_retention_strategies(churn_predictions, customer_data))