"""
config.py - Configuration module for Google Analytics 4 analyzer

This module handles configuration settings and provides a simple
interface for accessing credentials and other settings.
"""

import os
import json


class Config:
    """Configuration handler for GA4 analyzer"""
    
    def __init__(self, config_file=None):
        """
        Initialize the configuration handler.
        
        Args:
            config_file (str): Path to the configuration file. If None, uses default path.
        """
        self.config_file = config_file or 'config.json'
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create a default configuration."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in configuration file: {self.config_file}")
                return self._create_default_config()
        else:
            print(f"Configuration file not found: {self.config_file}")
            return self._create_default_config()
    
    def _create_default_config(self):
        """Create and save a default configuration."""
        default_config = {
            "service_account_key_file": "credentials/service-account-key.json",
            "date_ranges": [
                {
                    "name": "last_30_days",
                    "start_date": "30daysAgo",
                    "end_date": "yesterday"
                }
            ],
            "metrics": [
                {"name": "sessions"},
                {"name": "activeUsers"},
                {"name": "screenPageViews"},
                {"name": "conversions"},
                {"name": "totalRevenue"}
            ],
            "dimensions": [
                {"name": "date"},
                {"name": "sessionSource"},
                {"name": "country"}
            ],
            "output_format": "csv",
            "output_directory": "results"
        }
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
        os.makedirs("credentials", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        # Save default configuration
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"Created default configuration file: {self.config_file}")
        return default_config
    
    def get(self, key, default=None):
        """
        Get a configuration value.
        
        Args:
            key (str): The configuration key to retrieve
            default: The default value to return if the key is not found
            
        Returns:
            The configuration value for the key, or the default value if not found
        """
        return self.config.get(key, default)
    
    def get_service_account_path(self):
        """Get the path to the service account key file."""
        key_file = self.get("service_account_key_file")
        if not key_file:
            print("Warning: service_account_key_file not found in configuration")
            return None
        
        return key_file
    
    def get_date_ranges(self):
        """Get the date ranges for GA4 queries."""
        return self.get("date_ranges", [])
    
    def set_date_range(self, start_date, end_date, name="custom_range"):
        """Set a custom date range."""
        self.config["date_ranges"] = [
            {
                "name": name,
                "start_date": start_date,
                "end_date": end_date
            }
        ]
    
    def get_metrics(self):
        """Get the metrics for GA4 queries."""
        return self.get("metrics", [])
    
    def get_dimensions(self):
        """Get the dimensions for GA4 queries."""
        return self.get("dimensions", [])
    
    def get_output_format(self):
        """Get the output format for results."""
        return self.get("output_format", "csv")
    
    def get_output_directory(self):
        """Get the output directory for results."""
        output_dir = self.get("output_directory", "results")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def save(self):
        """Save the current configuration to file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"Configuration saved to: {self.config_file}")

if __name__ == "__main__":
    # Example usage
    config = Config()
    
    print("Configuration:")
    print(f"Service Account Key File: {config.get_service_account_path()}")
    print(f"Date Ranges: {len(config.get_date_ranges())}")
    print(f"Metrics: {len(config.get_metrics())}")
    print(f"Dimensions: {len(config.get_dimensions())}")
    print(f"Output Format: {config.get_output_format()}")
    print(f"Output Directory: {config.get_output_directory()}")