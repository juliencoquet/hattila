"""
json_encoder.py - Specialized JSON encoder for GA4 data with proper handling of special values
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
import math


class ImprovedJSONEncoder(json.JSONEncoder):
    """
    A custom JSON encoder that properly handles:
    - NumPy types
    - Infinity and NaN values
    - Scientific notation
    - Dates and timestamps
    """
    def default(self, obj):
        # Handle NumPy numeric types
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            # Convert NumPy float to Python float
            value = float(obj)
            
            # Check for Infinity or NaN
            if math.isinf(value) or math.isnan(value):
                return 0  # Replace Infinity and NaN with 0
            
            # Handle scientific notation for large integers
            if value > 1e10 or value < -1e10:
                return 0  # Replace very large numbers with 0
                
            # Format numbers nicely
            if value.is_integer():
                return int(value)  # Convert to int if it's a whole number
            else:
                return round(value, 2)  # Round to 2 decimal places otherwise
                
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
            
        return super(ImprovedJSONEncoder, self).default(obj)


def clean_data_for_json(data):
    """
    Recursively clean data to ensure it's JSON-serializable without problems.
    
    Args:
        data: Data to clean (can be dict, list, or scalar)
        
    Returns:
        Cleaned data safe for JSON serialization
    """
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif isinstance(data, (np.integer, np.int64)):
        return int(data)
    elif isinstance(data, (np.floating, np.float64, float)):
        value = float(data)
        
        # Check for Infinity or NaN
        if math.isinf(value) or math.isnan(value):
            return 0
        
        # Handle scientific notation for large integers
        if value > 1e10 or value < -1e10:
            return 0
            
        # Format numbers nicely
        if value.is_integer():
            return int(value)
        else:
            return round(value, 2)
    elif isinstance(data, (datetime, pd.Timestamp)):
        return data.isoformat()
    else:
        return data