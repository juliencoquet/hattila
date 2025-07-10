"""
auth.py - Authentication module for Google Analytics 4 Data API

This module handles authentication with the Google Analytics 4 Data API using either
a service account or OAuth2.
"""

import os
import json
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient
from google.oauth2 import service_account


def authenticate_with_service_account(key_file_path):
    """
    Authenticate with GA4 API using a service account key file.
    
    Args:
        key_file_path (str): Path to the service account JSON key file.
        
    Returns:
        tuple: (data_client, admin_client) - The authenticated GA4 API clients
    """
    try:
        # Verify the key file exists
        if not os.path.exists(key_file_path):
            print(f"Error: Service account key file not found: {key_file_path}")
            return None, None
        
        # Create credentials from the service account file
        credentials = service_account.Credentials.from_service_account_file(
            key_file_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        
        # Create the GA4 API clients
        data_client = BetaAnalyticsDataClient(credentials=credentials)
        admin_client = AnalyticsAdminServiceClient(credentials=credentials)
        
        print("Successfully authenticated with Google Analytics 4 API")
        return data_client, admin_client
    
    except Exception as e:
        print(f"Authentication error: {e}")
        return None, None


def get_property_ids(admin_client, filter_url=None):
    """
    Get GA4 property IDs, optionally filtered by URL.
    
    Args:
        admin_client: The GA4 Admin API client
        filter_url (str, optional): If provided, only return properties matching this URL
            
    Returns:
        dict: Dictionary mapping property names to property IDs
    """
    if not admin_client:
        print("Error: No authenticated admin client provided")
        return {}
    
    properties = {}
    
    try:
        # List all properties the account has access to
        response = admin_client.list_properties(parent="accounts/-")
        
        for property in response:
            property_id = property.name.split('/')[-1]
            property_name = property.display_name
            
            # If filter_url is provided, only include matching properties
            if filter_url:
                if hasattr(property, 'website_uri') and filter_url in property.website_uri:
                    properties[property_name] = property_id
            else:
                properties[property_name] = property_id
                
    except Exception as e:
        print(f"Error fetching GA4 properties: {e}")
    
    return properties


def get_property_for_url(admin_client, url):
    """
    Find the GA4 property associated with a specific URL.
    
    Args:
        admin_client: The GA4 Admin API client
        url (str): The URL to find a property for
            
    Returns:
        tuple: (property_id, property_name) or (None, None) if not found
    """
    properties = get_property_ids(admin_client, filter_url=url)
    
    if not properties:
        return None, None
    
    # Return the first matching property
    property_name = next(iter(properties))
    property_id = properties[property_name]
    
    return property_id, property_name


if __name__ == "__main__":
    # Example usage
    key_file = "path/to/your-service-account-key.json"
    
    # Authenticate
    data_client, admin_client = authenticate_with_service_account(key_file)
    
    if admin_client:
        # Get all GA4 properties
        all_properties = get_property_ids(admin_client)
        print(f"Found {len(all_properties)} GA4 properties:")
        for name, prop_id in all_properties.items():
            print(f"  - {name}: {prop_id}")
        
        # Find property for a specific URL
        test_url = "example.com"
        property_id, property_name = get_property_for_url(admin_client, test_url)
        
        if property_id:
            print(f"\nFound GA4 property for {test_url}:")
            print(f"  - {property_name}: {property_id}")
        else:
            print(f"\nNo GA4 property found for {test_url}")