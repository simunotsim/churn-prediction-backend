from pathlib import Path
import pandas as pd

def load_raw_data(file_path: str) -> pd.DataFrame:
    """
    Load raw customer data from the specified CSV file.
    
    Parameters:
    - file_path: str - Path to the raw data file.
    
    Returns:
    - pd.DataFrame - DataFrame containing the loaded data.
    """
    try:
        data = pd.read_csv(file_path)
        return data
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

def load_all_raw_data(data_dir: str) -> dict:
    """
    Load all raw data files from the specified directory.
    
    Parameters:
    - data_dir: str - Directory containing raw data files.
    
    Returns:
    - dict - Dictionary with file names as keys and DataFrames as values.
    """
    data_files = Path(data_dir).glob("*.csv")
    data_dict = {}
    
    for file in data_files:
        data_dict[file.stem] = load_raw_data(file)
    
    return data_dict