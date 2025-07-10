"""
collector.py - Data collection module for Google Analytics 4 Data API

This module handles data collection from the Google Analytics 4 Data API,
including building and executing queries.
"""

import time
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    OrderBy,
    OrderBy
)


class GA4Collector:
    """Collects data from Google Analytics 4 API"""
    
    def __init__(self, data_client):
        """
        Initialize the GA4 data collector.
        
        Args:
            data_client: The GA4 Data API client
        """
        self.data_client = data_client
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum time between requests in seconds
    
    def run_report(self, property_id, date_ranges, metrics, dimensions, row_limit=10000,
                  dimension_filter=None, metric_filter=None, offset=0, order_bys=None):
        """
        Run a GA4 Data API report.
        
        Args:
            property_id (str): The GA4 property ID
            date_ranges (list): List of date range dictionaries with start_date and end_date
            metrics (list): List of metric dictionaries with name
            dimensions (list): List of dimension dictionaries with name
            row_limit (int): Maximum number of rows to return
            dimension_filter (obj, optional): Dimension filter
            metric_filter (obj, optional): Metric filter
            offset (int): Result offset for pagination
            order_bys (list, optional): List of OrderBy objects
            
        Returns:
            The GA4 API report response
        """
        # Apply rate limiting
        self._handle_rate_limiting()
        
        # Convert date ranges to proper objects
        date_range_objects = []
        for date_range in date_ranges:
            date_range_objects.append(DateRange(
                start_date=date_range["start_date"],
                end_date=date_range["end_date"]
            ))
        
        # Convert metrics to proper objects
        metric_objects = []
        for metric in metrics:
            metric_objects.append(Metric(name=metric["name"]))
        
        # Convert dimensions to proper objects
        dimension_objects = []
        for dimension in dimensions:
            dimension_objects.append(Dimension(name=dimension["name"]))
        
        # Build the request
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=date_range_objects,
            metrics=metric_objects,
            dimensions=dimension_objects,
            limit=row_limit,
            offset=offset
        )
        
        # Add filters if provided
        if dimension_filter:
            request.dimension_filter = dimension_filter
        if metric_filter:
            request.metric_filter = metric_filter
        
        # Add ordering if provided
        if order_bys:
            request.order_bys = order_bys
        
        try:
            # Execute the request
            response = self.data_client.run_report(request)
            return response
        except Exception as e:
            print(f"Error running GA4 report: {e}")
            return None
    
    def collect_data_for_property(self, property_id, config):
        """
        Collect data for a specific GA4 property.
        
        Args:
            property_id (str): The GA4 property ID
            config: The configuration object
            
        Returns:
            dict: Dictionary with collected data
        """
        date_ranges = config.get_date_ranges()
        metrics = config.get_metrics()
        dimensions = config.get_dimensions()
        
        if not date_ranges or not metrics:
            print("Error: Missing date ranges or metrics in configuration")
            return None
        
        try:
            # Run the report
            report = self.run_report(
                property_id=property_id,
                date_ranges=date_ranges,
                metrics=metrics,
                dimensions=dimensions
            )
            
            if not report:
                return None
            
            # Process the response into a more usable format
            return self._process_report(report, date_ranges, metrics, dimensions)
        
        except Exception as e:
            print(f"Error collecting data for property {property_id}: {e}")
            return None
    
    def _process_report(self, report, date_ranges, metrics, dimensions):
        """
        Process a GA4 API report into a more usable format.
        
        Args:
            report: The GA4 API report response
            date_ranges: The date ranges used in the query
            metrics: The metrics used in the query
            dimensions: The dimensions used in the query
            
        Returns:
            dict: Dictionary with processed data
        """
        if not report or not hasattr(report, 'rows') or not report.rows:
            return {"data": [], "totals": [], "row_count": 0}
        
        # Extract dimension and metric headers
        dimension_headers = [header.name for header in report.dimension_headers]
        metric_headers = [header.name for header in report.metric_headers]
        
        # Process rows
        data = []
        for row in report.rows:
            row_data = {}
            
            # Add dimensions
            for i, dimension in enumerate(row.dimension_values):
                row_data[dimension_headers[i]] = dimension.value
            
            # Add metrics for each date range
            for date_range_idx, date_range in enumerate(date_ranges):
                date_range_name = date_range.get("name", f"date_range_{date_range_idx}")
                
                for i, metric in enumerate(row.metric_values):
                    metric_key = f"{metric_headers[i]}_{date_range_name}"
                    row_data[metric_key] = metric.value
            
            data.append(row_data)
        
        # Process totals
        totals = []
        for i, row in enumerate(report.totals):
            row_data = {}
            date_range_name = date_ranges[i].get("name", f"date_range_{i}")
            
            for j, metric in enumerate(row.metric_values):
                metric_key = f"{metric_headers[j]}_{date_range_name}"
                row_data[metric_key] = metric.value
            
            totals.append(row_data)
        
        return {
            "data": data,
            "totals": totals,
            "row_count": report.row_count
        }
    
    def _handle_rate_limiting(self):
        """
        Implement basic rate limiting to avoid API quota issues.
        Ensures a minimum time between requests.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


if __name__ == "__main__":
    # Example usage (requires data_client from auth module)
    from config import Config
    from auth import authenticate_with_service_account
    
    # Load configuration
    config = Config()
    
    # Authenticate
    data_client, admin_client = authenticate_with_service_account(
        config.get_service_account_path()
    )
    
    if data_client:
        # Create collector
        collector = GA4Collector(data_client)
        
        # Collect data for a property
        property_id = "your_property_id"  # Replace with actual property ID
        report_data = collector.collect_data_for_property(property_id, config)
        
        if report_data:
            print(f"Collected {report_data['row_count']} rows of data")
            
            # Print sample data (first 5 rows)
            print("\nSample data:")
            for i, row in enumerate(report_data["data"][:5]):
                print(f"Row {i+1}: {row}")
            
            # Print totals
            print("\nTotals:")
            for i, total in enumerate(report_data["totals"]):
                print(f"Date Range {i+1}: {total}")
        else:
            print("No data collected")