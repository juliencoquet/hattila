"""
url_analyzer.py - Advanced URL analysis for Google Analytics 4 data
with conversion rates, marketing channel attribution, and enhanced event tracking
"""

import os
import json
import re
import pandas as pd
import numpy as np
import math
from json_encoder import ImprovedJSONEncoder, clean_data_for_json
from translations import translate_insights_in_results
from pagespeed import PageSpeedAnalyzer
from datetime import datetime
from urllib.parse import urlparse
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest
)


class URLAnalyzer:
    """Analyzes GA4 data for specific URLs"""
    
    def __init__(self, data_client, config):
        """
        Initialize the URL analyzer.
        
        Args:
            data_client: The GA4 Data API client
            config: The configuration object
        """
        self.data_client = data_client
        self.config = config
        self.output_dir = config.get_output_directory()
        
        # Define standard GA4 metrics
        self.standard_metrics = [
            {"name": "sessions"},
            {"name": "activeUsers"}, 
            {"name": "screenPageViews"},
            {"name": "engagedSessions"},
            {"name": "eventCount"},
            {"name": "keyEvents"},
            {"name": "totalUsers"},
            {"name": "averageSessionDuration"}
        ]
        
        # Define conversion metrics (key events)
        self.conversion_metrics = [
            {"name": "keyEvents"},
            {"name": "ecommercePurchases"}, 
            {"name": "transactions"},
            {"name": "addToCarts"},
            {"name": "checkouts"}
        ]
        
        # Define standard dimensions
        self.standard_dimensions = [
            {"name": "date"},
            {"name": "sessionSource"},
            {"name": "sessionMedium"},
            {"name": "sessionCampaign"},
            {"name": "pagePath"},
            {"name": "deviceCategory"}
        ]
        
        # Key marketing channels to track
        self.marketing_channels = [
            "direct", "organic", "referral", "email", 
            "paid-search", "social", "affiliate", "display"
        ]

         # PageSpeed settings (with defaults)
        self.pagespeed_enabled = False
        self.pagespeed_api_key = None
        self.pagespeed_max_urls = 10
        
        self.pagespeed_analyzer = PageSpeedAnalyzer(output_dir=self.output_dir)
        # Debug mode
        self.debug = True
    
    def analyze_urls(self, property_id, property_name, urls, generate_files=True):
        """
        Analyze data for a list of URLs.
        
        Args:
            property_id (str): The GA4 property ID
            property_name (str): The GA4 property name
            urls (list): List of URLs to analyze
            
        Returns:
            dict: Dictionary with analysis results for each URL
        """
        # First, get page data with standard metrics
        print("Collecting page data for the property...")
        all_pages_data = self._collect_all_pages_data(property_id)
        
        # Debug: print available metrics and dimensions
        if self.debug and all_pages_data and all_pages_data.get("data"):
            sample_row = all_pages_data["data"][0] if all_pages_data["data"] else {}
            print("\nAvailable metrics and dimensions:")
            for key, value in sample_row.items():
                print(f"  - {key}: {type(value).__name__} (example: {value})")
            print("\n")

        if not all_pages_data or not all_pages_data.get("data") or len(all_pages_data["data"]) == 0:
            print(f"No page data available for property {property_id}")
            return {
                "property_id": property_id,
                "property_name": property_name,
                "timestamp": datetime.now().isoformat(),
                "urls_analyzed": len(urls),
                "urls": {}
            }
        
        # Next, collect conversion data
        print("Collecting conversion data for the property...")
        conversion_data = self._collect_conversion_data(property_id)
        
        # Then, collect marketing channel data
        print("Collecting marketing channel data for the property...")
        channel_data = self._collect_channel_data(property_id)
        
        # Convert to DataFrame for easier processing
        pages_df = pd.DataFrame(all_pages_data["data"])
        
        if self.debug:
            print(f"Collected data for {len(pages_df)} page paths")
            # If pagePath column exists, show some samples
            if 'pagePath' in pages_df.columns:
                print("Sample page paths:")
                sample_paths = pages_df['pagePath'].unique()[:5]
                for path in sample_paths:
                    print(f"  - {path}")
        
        # Calculate property-level metrics
        property_metrics = self._calculate_property_metrics(all_pages_data, conversion_data, channel_data)
        
        # Prepare results structure
        results = {
            "property_id": property_id,
            "property_name": property_name,
            "timestamp": datetime.now().isoformat(),
            "urls_analyzed": len(urls),
            "property_metrics": property_metrics,
            "marketing_channels": self._get_channel_distribution(channel_data),
            "conversion_metrics": self._extract_conversion_metrics(conversion_data),
            "urls": {}
        }
        
        # Create a safe filename for the analysis results
        safe_name = property_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Analyze each URL
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Analyzing URL: {url}")
            
            # Extract path from URL for filtering
            path = self._extract_path_from_url(url)
            print(f"  URL path: {path}")
            
            # Filter data for this path
            url_data = self._filter_data_for_path(all_pages_data, path)
            
            # Filter conversion data for this path
            url_conversion_data = self._filter_data_for_path(conversion_data, path) if conversion_data else None
            
            # Filter channel data for this path
            url_channel_data = self._filter_data_for_path(channel_data, path) if channel_data else None
            
            if not url_data or not url_data.get("data") or len(url_data["data"]) == 0:
                print(f"  No data available for URL: {url}")
                results["urls"][url] = {
                    "status": "no_data",
                    "metrics": {},
                    "insights": []
                }
                continue
            
            # Analyze the URL data with conversion and channel information
            analysis = self._analyze_url_data(url, url_data, url_conversion_data, url_channel_data, property_metrics)
            
            if analysis:
                print(f"  Found {len(analysis['insights'])} insights")
                results["urls"][url] = analysis
            else:
                print(f"  Analysis failed for URL: {url}")
                results["urls"][url] = {
                    "status": "failed",
                    "metrics": {},
                    "insights": []
                }
        
        # Analyze page speed if enabled
        if self.pagespeed_enabled:
            print("\nAnalyzing PageSpeed scores for URLs...")
            
            # Only analyze URLs that had successful GA4 analysis
            urls_to_analyze = [url for url, data in results["urls"].items() 
                            if data.get("status") == "success"]
            
            if urls_to_analyze:
                # Initialize the PageSpeed analyzer with API key and quota settings
                from pagespeed import PageSpeedAnalyzer
                pagespeed_analyzer = PageSpeedAnalyzer(
                    api_key=self.pagespeed_api_key, 
                    output_dir=self.output_dir,
                    max_requests_per_day=100  # Adjust based on your API key's quota
                )
                
                # Analyze PageSpeed for these URLs with a limit
                pagespeed_results = pagespeed_analyzer.analyze_multiple_urls(
                    urls_to_analyze, 
                    max_urls=self.pagespeed_max_urls
                )
                
                # Add PageSpeed results and insights to each URL
                for url, ps_data in pagespeed_results.items():
                    if url in results["urls"]:
                        # Add raw PageSpeed metrics
                        results["urls"][url]["pagespeed"] = ps_data
                        
                        # Generate insights from PageSpeed data
                        ps_insights = pagespeed_analyzer.get_insights(ps_data)
                        
                        # Add these insights to the existing ones
                        if ps_insights:
                            results["urls"][url]["insights"].extend(ps_insights)
                            print(f"  Added {len(ps_insights)} PageSpeed insights for {url}")
            else:
                print("  No successful URLs to analyze with PageSpeed")
        else:
            print("\nPageSpeed analysis is disabled (use --pagespeed to enable)")


        # Clean the data before saving
        clean_results = clean_data_for_json(results)
        # In the analyze_urls method, update the file saving section:
        clean_results = clean_data_for_json(results)

        if generate_files:
            try:
                # Ensure the output directory exists
                os.makedirs(self.output_dir, exist_ok=True)
                
                # Create a safe filename base with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_base = f"{safe_name}_{timestamp}"
                
                # Save English version (original)
                english_file = os.path.join(self.output_dir, f"{file_base}_url_analysis_en.json")
                with open(english_file, 'w', encoding='utf-8') as f:
                    json.dump(clean_results, f, indent=2, cls=ImprovedJSONEncoder)
                print(f"\nEnglish analysis saved to: {english_file}")
                
                # Generate French version
                try:
                    # Translate insights to French
                    french_results = translate_insights_in_results(clean_results, 'fr')
                    french_results["language"] = "fr"  # Mark as French version
                    
                    # Save French version
                    french_file = os.path.join(self.output_dir, f"{file_base}_url_analysis_fr.json")
                    with open(french_file, 'w', encoding='utf-8') as f:
                        json.dump(french_results, f, indent=2, cls=ImprovedJSONEncoder)
                    print(f"French analysis saved to: {french_file}")
                except Exception as e:
                    print(f"Error generating French translation: {e}")
            
            except Exception as e:
                print(f"\nError saving URL analysis to file: {e}")
                import traceback
                traceback.print_exc()

        return results
    
    def _collect_all_pages_data(self, property_id):
        """
        Collect general data for all pages in the property.
        
        Args:
            property_id (str): The GA4 property ID
            
        Returns:
            dict: Dictionary with collected data
        """
        # Get configuration
        date_ranges = self.config.get_date_ranges()
        
        # Use standard metrics that work reliably with GA4
        metrics = self.config.get_metrics() or self.standard_metrics
        
        # Ensure page path is included in dimensions
        dimensions = self.config.get_dimensions() or self.standard_dimensions
        
        # Make sure pagePath is included
        dimension_names = [d.get("name") for d in dimensions]
        if "pagePath" not in dimension_names:
            dimensions.append({"name": "pagePath"})
        
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
        
        try:
            # Build the request - to get all pages data
            request = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=date_range_objects,
                metrics=metric_objects,
                dimensions=dimension_objects,
                limit=100000  # Get a large sample
            )
            
            if self.debug:
                print("Sending general data request to GA4 API...")
                print(f"  Metrics: {[m['name'] for m in metrics]}")
                print(f"  Dimensions: {[d['name'] for d in dimensions]}")
            
            # Execute the request
            response = self.data_client.run_report(request)
            
            if self.debug:
                print(f"Received response with {len(response.rows) if hasattr(response, 'rows') else 0} rows")
            
            # Process the response
            all_data = self._process_report(response, date_ranges, metrics, dimensions)
            
            return all_data
        
        except Exception as e:
            print(f"Error collecting general data: {e}")
            return None
    
    def _collect_conversion_data(self, property_id):
        """
        Collect conversion-specific data for the property.
        
        Args:
            property_id (str): The GA4 property ID
            
        Returns:
            dict: Dictionary with collected conversion data
        """
        # Get configuration
        date_ranges = self.config.get_date_ranges()
        
        # Use conversion metrics
        metrics = self.conversion_metrics
        
        # Use essential dimensions including pagePath
        dimensions = [
            {"name": "pagePath"},
            {"name": "date"},
            {"name": "eventName"}
        ]
        
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
        
        try:
            # Build the request for conversion data
            request = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=date_range_objects,
                metrics=metric_objects,
                dimensions=dimension_objects,
                limit=50000
            )
            
            if self.debug:
                print("Sending conversion data request to GA4 API...")
                print(f"  Metrics: {[m['name'] for m in metrics]}")
                print(f"  Dimensions: {[d['name'] for d in dimensions]}")
            
            # Execute the request
            response = self.data_client.run_report(request)
            
            if self.debug:
                print(f"Received conversion data with {len(response.rows) if hasattr(response, 'rows') else 0} rows")
            
            # Process the response
            conversion_data = self._process_report(response, date_ranges, metrics, dimensions)
            
            return conversion_data
        
        except Exception as e:
            print(f"Error collecting conversion data: {e}")
            return None
    
    def _collect_channel_data(self, property_id):
        """
        Collect marketing channel data for the property.
        
        Args:
            property_id (str): The GA4 property ID
            
        Returns:
            dict: Dictionary with collected channel data
        """
        # Get configuration
        date_ranges = self.config.get_date_ranges()
        
        # Use basic metrics
        metrics = [
            {"name": "sessions"},
            {"name": "activeUsers"},
            {"name": "keyEvents"}
        ]
        
        # Use channel-related dimensions
        dimensions = [
            {"name": "pagePath"},
            {"name": "sessionSource"},
            {"name": "sessionMedium"},
            {"name": "sessionCampaignId"}
        ]
        
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
        
        try:
            # Build the request for channel data
            request = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=date_range_objects,
                metrics=metric_objects,
                dimensions=dimension_objects,
                limit=50000
            )
            
            if self.debug:
                print("Sending channel data request to GA4 API...")
                print(f"  Metrics: {[m['name'] for m in metrics]}")
                print(f"  Dimensions: {[d['name'] for d in dimensions]}")
            
            # Execute the request
            response = self.data_client.run_report(request)
            
            if self.debug:
                print(f"Received channel data with {len(response.rows) if hasattr(response, 'rows') else 0} rows")
            
            # Process the response
            channel_data = self._process_report(response, date_ranges, metrics, dimensions)
            
            return channel_data
        
        except Exception as e:
            print(f"Error collecting channel data: {e}")
            return None
    
    def _extract_path_from_url(self, url):
        """
        Extract the path component from a URL, compatible with GA4 path format.
        
        Args:
            url (str): The URL to process
            
        Returns:
            str: The path component of the URL
        """
        try:
            # Use urlparse for more reliable parsing
            parsed_url = urlparse(url)
            
            # GA4 typically stores paths starting with the first slash
            path = parsed_url.path
            
            # If path is empty, use "/"
            if not path:
                path = "/"
                
            if self.debug:
                print(f"  Extracted path '{path}' from URL '{url}'")
                
            return path
        except Exception as e:
            print(f"  Error extracting path from URL {url}: {e}")
            return "/"
    
    def _filter_data_for_path(self, all_data, path):
        """
        Filter data for a specific path.
        
        Args:
            all_data (dict): All data
            path (str): The path to filter by
            
        Returns:
            dict: Filtered data
        """
        if not all_data or not all_data.get("data"):
            return None
        
        filtered_data = {
            "data": [],
            "totals": all_data["totals"],
            "row_count": 0
        }
        
        # Convert to DataFrame for easier filtering
        df = pd.DataFrame(all_data["data"])
        
        if 'pagePath' not in df.columns:
            print("  'pagePath' column not found in data")
            return None
        
        # Filter rows that contain the path
        # Try exact match first
        exact_match = df[df['pagePath'] == path]
        
        if len(exact_match) > 0:
            print(f"  Found {len(exact_match)} rows with exact path match")
            filtered_df = exact_match
        else:
            # If no exact match, try contains
            contains_match = df[df['pagePath'].str.contains(path, regex=False)]
            print(f"  Found {len(contains_match)} rows with partial path match")
            filtered_df = contains_match
        
        if len(filtered_df) == 0:
            print("  No matching paths found")
            return None
        
        # Convert back to dict format
        filtered_data["data"] = filtered_df.to_dict('records')
        filtered_data["row_count"] = len(filtered_df)
        
        return filtered_data
    
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
            
            # Add metrics
            for i, metric in enumerate(row.metric_values):
                row_data[metric_headers[i]] = metric.value
            
            data.append(row_data)
        
        # Process totals
        totals = []
        for i, row in enumerate(report.totals):
            row_data = {}
            
            for j, metric in enumerate(row.metric_values):
                metric_key = metric_headers[j]
                row_data[metric_key] = metric.value
            
            totals.append(row_data)
        
        return {
            "data": data,
            "totals": totals,
            "row_count": len(data)
        }
  
    def _calculate_property_metrics(self, all_data, conversion_data, channel_data):
        """
        Calculate comprehensive property-level metrics.
        
        Args:
            all_data (dict): General data
            conversion_data (dict): Conversion data
            channel_data (dict): Channel data
            
        Returns:
            dict: Property-level metrics
        """
        property_metrics = {}
        
        # Extract metrics from general data totals
        if all_data and all_data.get("totals") and len(all_data["totals"]) > 0:
            for total_row in all_data["totals"]:
                for key, value in total_row.items():
                    try:
                        property_metrics[key] = self._ensure_numeric(value)
                    except (ValueError, TypeError):
                        property_metrics[key] = value
        
        # Extract conversion metrics
        if conversion_data and conversion_data.get("totals") and len(conversion_data["totals"]) > 0:
            for total_row in conversion_data["totals"]:
                for key, value in total_row.items():
                    try:
                        property_metrics[key] = self._ensure_numeric(value)
                    except (ValueError, TypeError):
                        property_metrics[key] = value
        
        # Calculate derived metrics
        try:
            sessions = self._ensure_numeric(property_metrics.get("sessions"))
            if sessions > 0:
                # Calculate engagement rate
                engaged_sessions = self._ensure_numeric(property_metrics.get("engagedSessions"))
                if engaged_sessions > 0:
                    property_metrics["engagementRate"] = (engaged_sessions / sessions) * 100
                    
                # Calculate pageviews per session
                page_views = self._ensure_numeric(property_metrics.get("screenPageViews"))
                if page_views > 0:
                    property_metrics["pageviewsPerSession"] = page_views / sessions
                
                # Calculate conversion rate
                key_events = self._ensure_numeric(property_metrics.get("keyEvents"))
                if key_events > 0:
                    property_metrics["conversionRate"] = (key_events / sessions) * 100
                
                # Calculate e-commerce conversion rate
                transactions = self._ensure_numeric(property_metrics.get("transactions"))
                if transactions > 0:
                    property_metrics["ecommerceConversionRate"] = (transactions / sessions) * 100
                
                # Calculate cart abandonment rate
                add_to_carts = self._ensure_numeric(property_metrics.get("addToCarts"))
                if add_to_carts > 0 and transactions > 0:
                    property_metrics["cartAbandonmentRate"] = ((add_to_carts - transactions) / add_to_carts) * 100
        except Exception as e:
            print(f"Error calculating derived metrics: {e}")
        
        return property_metrics

    def _get_channel_distribution(self, channel_data):
        """
        Calculate the distribution of marketing channels.
        
        Args:
            channel_data (dict): Channel data
            
        Returns:
            dict: Channel distribution metrics
        """
        if not channel_data or not channel_data.get("data"):
            return {}
        
        # Convert to DataFrame
        df = pd.DataFrame(channel_data["data"])
        
        # Check if we have the necessary columns
        if "sessionSource" not in df.columns or "sessionMedium" not in df.columns or "sessions" not in df.columns:
            return {}
        
        try:
            # Convert sessions to numeric values
            df["sessions"] = pd.to_numeric(df["sessions"], errors="coerce").fillna(0)
            
            # Classify channels
            df["channel"] = df.apply(self._classify_channel, axis=1)
            
            # Aggregate by channel
            channel_df = df.groupby("channel")["sessions"].sum().reset_index()
            
            # Calculate percentages
            total_sessions = float(channel_df["sessions"].sum())
            
            channel_distribution = {}
            for _, row in channel_df.iterrows():
                channel = row["channel"]
                sessions = float(row["sessions"])
                percentage = (sessions / total_sessions) * 100 if total_sessions > 0 else 0
                
                channel_distribution[channel] = {
                    "sessions": sessions,
                    "percentage": percentage
                }
            
            return channel_distribution
            
        except Exception as e:
            print(f"Error in channel distribution analysis: {e}")
            return {}
    
    def _classify_channel(self, row):
        """
        Classify a traffic source into a marketing channel.
        
        Args:
            row: DataFrame row with sessionSource and sessionMedium
            
        Returns:
            str: Classified channel
        """
        source = str(row.get("sessionSource", "")).lower()
        medium = str(row.get("sessionMedium", "")).lower()
        
        # Direct
        if source == "(direct)" or medium == "(none)" or medium == "direct":
            return "direct"
        
        # Organic Search
        if medium == "organic":
            return "organic"
        
        # Paid Search
        if medium in ["cpc", "ppc", "paidsearch"] or "paid" in medium:
            return "paid-search"
        
        # Email
        if medium == "email" or ".mail" in source or "mail" in medium:
            return "email"
        
        # Social
        social_sites = ["facebook", "instagram", "twitter", "linkedin", "pinterest", "youtube", "tiktok"]
        if medium == "social" or any(site in source for site in social_sites):
            return "social"
        
        # Referral
        if medium == "referral":
            return "referral"
        
        # Display
        if medium in ["display", "banner", "cpm"]:
            return "display"
        
        # Affiliate
        if medium == "affiliate":
            return "affiliate"
        
        # Other
        return "other"
  

    def _extract_conversion_metrics(self, conversion_data):
        """
        Extract key conversion metrics from conversion data.
        
        Args:
            conversion_data (dict): Conversion data
            
        Returns:
            dict: Conversion metrics
        """
        if not conversion_data or not conversion_data.get("data"):
            return {}
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(conversion_data["data"])
            
            conversion_metrics = {}
            
            # Extract event-specific metrics if eventName column exists
            if "eventName" in df.columns:
                # Group by event name
                event_df = df.groupby("eventName").sum().reset_index()
                
                # Extract metrics for each event
                for _, row in event_df.iterrows():
                    event_name = row["eventName"]
                    
                    # Create an entry for each event
                    conversion_metrics[event_name] = {}
                    
                    # Add all numeric metrics
                    for col in event_df.columns:
                        if col != "eventName":
                            try:
                                conversion_metrics[event_name][col] = self._ensure_numeric(row[col])
                            except (ValueError, TypeError):
                                pass
            
            return conversion_metrics
        except Exception as e:
            print(f"Error extracting conversion metrics: {e}")
            return {}

    def _analyze_url_data(self, url, url_data, url_conversion_data, url_channel_data, property_metrics):
        """
        Perform comprehensive analysis for a specific URL.
        
        Args:
            url (str): The URL being analyzed
            url_data (dict): The general data for the URL
            url_conversion_data (dict): Conversion data for the URL
            url_channel_data (dict): Channel data for the URL
            property_metrics (dict): Property-level metrics for comparison
            
        Returns:
            dict: Dictionary with analysis results
        """
        if not url_data or not url_data.get("data") or len(url_data["data"]) == 0:
            return None
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(url_data["data"])
        
        if df.empty:
            return None
        
        # Calculate aggregated metrics for this URL
        url_metrics = {}
        for column in df.columns:
            if column not in ['date', 'sessionSource', 'sessionMedium', 'sessionCampaignId', 'pagePath', 'deviceCategory', 'eventName']:
                try:
                    # Convert to numeric and handle problematic values
                    value = float(pd.to_numeric(df[column], errors='coerce').sum())
                    
                    # Check for Infinity or NaN
                    if math.isinf(value) or math.isnan(value):
                        url_metrics[column] = 0
                    else:
                        # Format number appropriately
                        if value.is_integer():
                            url_metrics[column] = int(value)
                        else:
                            url_metrics[column] = round(value, 2)
                except:
                    pass
        
        # Add conversion metrics if available
        if url_conversion_data and url_conversion_data.get("data"):
            conv_df = pd.DataFrame(url_conversion_data["data"])
            
            # Extract event-specific metrics if available
            if "eventName" in conv_df.columns:
                url_metrics["events"] = {}
                
                # Group by event name
                event_groups = conv_df.groupby("eventName")
                
                for event_name, event_df in event_groups:
                    url_metrics["events"][event_name] = {}
                    
                    # Sum numeric columns for each event
                    for col in event_df.columns:
                        if col not in ['date', 'sessionSource', 'sessionMedium', 'sessionCampaignId', 'pagePath', 'deviceCategory', 'eventName']:
                            try:
                                url_metrics["events"][event_name][col] = float(pd.to_numeric(event_df[col], errors='coerce').sum())
                            except:
                                pass
        
        # Calculate marketing channel distribution if available
        if url_channel_data and url_channel_data.get("data"):
            try:
                channel_df = pd.DataFrame(url_channel_data["data"])
                
                if "sessionSource" in channel_df.columns and "sessionMedium" in channel_df.columns and "sessions" in channel_df.columns:
                    # Convert sessions to numeric first
                    channel_df["sessions"] = pd.to_numeric(channel_df["sessions"], errors="coerce").fillna(0)
                    
                    # Classify channels
                    channel_df["channel"] = channel_df.apply(self._classify_channel, axis=1)
                    
                    # Aggregate by channel
                    channel_groups = channel_df.groupby("channel")["sessions"].sum().reset_index()
                    
                    # Calculate percentages
                    total_sessions = float(channel_groups["sessions"].sum())
                    
                    url_metrics["channels"] = {}
                    for _, row in channel_groups.iterrows():
                        channel = row["channel"]
                        sessions = float(row["sessions"])
                        percentage = (sessions / total_sessions) * 100 if total_sessions > 0 else 0
                        
                        url_metrics["channels"][channel] = {
                            "sessions": sessions,
                            "percentage": percentage
                        }
            except Exception as e:
                print(f"  Error calculating channel distribution: {e}")
        
        # Calculate derived metrics
        try:
            sessions = self._ensure_numeric(url_metrics.get("sessions"))
            if sessions > 0:
                # Calculate engagement rate
                engaged_sessions = self._ensure_numeric(url_metrics.get("engagedSessions"))
                if engaged_sessions > 0:
                    url_metrics["engagementRate"] = (engaged_sessions / sessions) * 100
                    
                # Calculate pageviews per session
                page_views = self._ensure_numeric(url_metrics.get("screenPageViews"))
                if page_views > 0:
                    url_metrics["pageviewsPerSession"] = page_views / sessions
                
                # Calculate conversion rate
                key_events = self._ensure_numeric(url_metrics.get("keyEvents"))
                if key_events > 0:
                    url_metrics["conversionRate"] = (key_events / sessions) * 100
                
                # Calculate e-commerce conversion rate
                transactions = self._ensure_numeric(url_metrics.get("transactions"))
                if transactions > 0:
                    url_metrics["ecommerceConversionRate"] = (transactions / sessions) * 100
                else:
                    ecommerce_purchases = self._ensure_numeric(url_metrics.get("ecommercePurchases"))
                    if ecommerce_purchases > 0:
                        url_metrics["ecommerceConversionRate"] = (ecommerce_purchases / sessions) * 100
                
                # Calculate cart abandonment rate
                add_to_carts = self._ensure_numeric(url_metrics.get("addToCarts"))
                if add_to_carts > 0:
                    if transactions > 0:
                        url_metrics["cartAbandonmentRate"] = ((add_to_carts - transactions) / add_to_carts) * 100
                    else:
                        ecommerce_purchases = self._ensure_numeric(url_metrics.get("ecommercePurchases"))
                        if ecommerce_purchases > 0:
                            url_metrics["cartAbandonmentRate"] = ((add_to_carts - ecommerce_purchases) / add_to_carts) * 100
        except Exception as e:
            print(f"  Error calculating derived metrics: {e}")

        # Generate insights
        insights = []
        
        # Add basic metrics insights
        if url_metrics:
            # Add sessions insight
            if "sessions" in url_metrics and url_metrics["sessions"] > 0:
                insights.append({
                    "type": "metric",
                    "metric": "sessions",
                    "finding": f"This URL received {url_metrics['sessions']:.0f} sessions in the analyzed period"
                })
            
            # Add pageviews insight
            if "screenPageViews" in url_metrics and url_metrics["screenPageViews"] > 0:
                insights.append({
                    "type": "metric",
                    "metric": "screenPageViews",
                    "finding": f"This URL received {url_metrics['screenPageViews']:.0f} pageviews in the analyzed period"
                })
            
            # Add conversion rate insight if available
            if "conversionRate" in url_metrics:
                conv_rate = url_metrics["conversionRate"]
                property_conv_rate = property_metrics.get("conversionRate", 0)
                
                if property_conv_rate > 0:
                    diff_pct = ((conv_rate - property_conv_rate) / property_conv_rate) * 100
                    comparison = "higher" if diff_pct > 0 else "lower"
                    
                    insights.append({
                        "type": "conversion",
                        "metric": "conversionRate",
                        "finding": f"This URL has a conversion rate of {conv_rate:.2f}%, which is {abs(diff_pct):.1f}% {comparison} than the site average ({property_conv_rate:.2f}%)"
                    })
                else:
                    insights.append({
                        "type": "conversion",
                        "metric": "conversionRate",
                        "finding": f"This URL has a conversion rate of {conv_rate:.2f}%"
                    })
            
            # Add e-commerce conversion rate insight if available
            if "ecommerceConversionRate" in url_metrics:
                ecom_rate = url_metrics["ecommerceConversionRate"]
                property_ecom_rate = property_metrics.get("ecommerceConversionRate", 0)
                
                if property_ecom_rate > 0:
                    diff_pct = ((ecom_rate - property_ecom_rate) / property_ecom_rate) * 100
                    comparison = "higher" if diff_pct > 0 else "lower"
                    
                    insights.append({
                        "type": "ecommerce",
                        "metric": "ecommerceConversionRate",
                        "finding": f"This URL has an e-commerce conversion rate of {ecom_rate:.2f}%, which is {abs(diff_pct):.1f}% {comparison} than the site average ({property_ecom_rate:.2f}%)"
                    })
                else:
                    insights.append({
                        "type": "ecommerce",
                        "metric": "ecommerceConversionRate",
                        "finding": f"This URL has an e-commerce conversion rate of {ecom_rate:.2f}%"
                    })
            
            # Add cart abandonment rate insight if available
            if "cartAbandonmentRate" in url_metrics:
                cart_rate = url_metrics["cartAbandonmentRate"]
                property_cart_rate = property_metrics.get("cartAbandonmentRate", 0)
                
                if property_cart_rate > 0:
                    diff_pct = ((cart_rate - property_cart_rate) / property_cart_rate) * 100
                    comparison = "higher" if diff_pct > 0 else "lower"
                    
                    insights.append({
                        "type": "cart",
                        "metric": "cartAbandonmentRate",
                        "finding": f"This URL has a cart abandonment rate of {cart_rate:.2f}%, which is {abs(diff_pct):.1f}% {comparison} than the site average ({property_cart_rate:.2f}%)"
                    })
                else:
                    insights.append({
                        "type": "cart",
                        "metric": "cartAbandonmentRate",
                        "finding": f"This URL has a cart abandonment rate of {cart_rate:.2f}%"
                    })
        
        # Add engagement rate comparison
        if "engagementRate" in url_metrics and "engagementRate" in property_metrics:
            url_rate = url_metrics["engagementRate"]
            property_rate = property_metrics["engagementRate"]
            
            if property_rate > 0:
                diff_pct = ((url_rate - property_rate) / property_rate) * 100
                comparison = "higher" if diff_pct > 0 else "lower"
                
                if abs(diff_pct) >= 5:  # Only highlight significant differences
                    insights.append({
                        "type": "engagement",
                        "metric": "engagementRate",
                        "finding": f"The engagement rate for this URL is {url_rate:.1f}%, which is {abs(diff_pct):.1f}% {comparison} than the site average ({property_rate:.1f}%)"
                    })
        
        # Add marketing channel insights if available
        # Find the section in _analyze_url_data where channel metrics are processed
        # It should be part of the code that checks for "channels" in url_metrics
        # Replace it with this code:

        # Add marketing channel insights if available
        if "channels" in url_metrics and len(url_metrics["channels"]) > 0:
            try:
                # Find top channel
                top_channel = max(url_metrics["channels"].items(), key=lambda x: x[1]["sessions"])
                channel_name = top_channel[0]
                channel_data = top_channel[1]
                
                insights.append({
                    "type": "channel",
                    "metric": "topChannel",
                    "finding": f"The top marketing channel for this URL is '{channel_name}' bringing {channel_data['sessions']:.0f} sessions ({channel_data['percentage']:.1f}% of traffic)"
                })
                
                # Check for channel diversity
                if len(url_metrics["channels"]) < 3:
                    insights.append({
                        "type": "channel_diversity",
                        "finding": f"This URL has limited channel diversity with only {len(url_metrics['channels'])} channels, consider diversifying traffic sources"
                    })
                
                # Find high-converting channels
                if "keyEvents" in url_metrics and url_metrics["keyEvents"] > 0 and "sessions" in url_metrics and url_metrics["sessions"] > 0:
                    # Calculate overall conversion rate for the URL
                    overall_conv_rate = (url_metrics["keyEvents"] / url_metrics["sessions"]) * 100
                    
                    # Check if we have channel-specific conversion data
                    if url_channel_data and url_channel_data.get("data"):
                        channel_df = pd.DataFrame(url_channel_data["data"])
                        
                        if "keyEvents" in channel_df.columns and "sessions" in channel_df.columns:
                            # Convert to numeric
                            channel_df["keyEvents"] = pd.to_numeric(channel_df["keyEvents"], errors="coerce").fillna(0)
                            channel_df["sessions"] = pd.to_numeric(channel_df["sessions"], errors="coerce").fillna(0)
                            
                            # Classify channels
                            channel_df["channel"] = channel_df.apply(self._classify_channel, axis=1)
                            
                            # Group by channel and calculate conversion rates
                            channel_conv = channel_df.groupby("channel").agg({
                                "keyEvents": "sum",
                                "sessions": "sum"
                            }).reset_index()
                            
                            # Calculate conversion rate for each channel
                            channel_conv["conv_rate"] = (channel_conv["keyEvents"] / channel_conv["sessions"]) * 100
                            
                            # Find channels with higher than average conversion rates
                            high_conv_channels = channel_conv[channel_conv["conv_rate"] > overall_conv_rate]
                            
                            if len(high_conv_channels) > 0:
                                top_conv_channel = high_conv_channels.sort_values("conv_rate", ascending=False).iloc[0]
                                
                                insights.append({
                                    "type": "channel_conversion",
                                    "finding": f"The '{top_conv_channel['channel']}' channel has the highest conversion rate at {top_conv_channel['conv_rate']:.2f}%, consider investing more in this channel"
                                })
            except Exception as e:
                print(f"  Error in channel analysis: {e}")
        
        # Add event insights if available
        if "events" in url_metrics and len(url_metrics["events"]) > 0:
            # Count total events
            total_events = 0
            event_counts = {}
            
            for event_name, event_data in url_metrics["events"].items():
                if "eventCount" in event_data:
                    event_counts[event_name] = float(event_data["eventCount"])
                    total_events += event_counts[event_name]
            
            if total_events > 0:
                insights.append({
                    "type": "events",
                    "finding": f"This URL triggered {total_events:.0f} events across {len(url_metrics['events'])} event types"
                })
                
                # Identify top events
                if event_counts:
                    top_event = max(event_counts.items(), key=lambda x: x[1])
                    
                    insights.append({
                        "type": "top_event",
                        "finding": f"The most common event on this URL is '{top_event[0]}' which occurred {top_event[1]:.0f} times"
                    })
        
        # Time series analysis
        if 'date' in df.columns and len(df) > 1:
            try:
                # Convert to datetime for time series analysis
                df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                df = df.sort_values('date')
                
                # Identify trend metrics
                metric_cols = [col for col in df.columns if col not in ['date', 'sessionSource', 'sessionMedium', 'sessionCampaignId', 'pagePath', 'deviceCategory', 'eventName']]
                
                for metric in metric_cols:
                    if metric not in ['sessions', 'screenPageViews', 'activeUsers', 'keyEvents']:
                        continue  # Only analyze key metrics for trends
                        
                    # Aggregate by date
                    daily_data = df.groupby('date')[metric].sum().reset_index()
                    
                    if len(daily_data) >= 2:
                        # Calculate change over time
                        first_value = float(pd.to_numeric(daily_data[metric].iloc[0], errors='coerce'))
                        last_value = float(pd.to_numeric(daily_data[metric].iloc[-1], errors='coerce'))
                        
                        if pd.notna(first_value) and pd.notna(last_value) and first_value > 0:
                            change_pct = ((last_value - first_value) / first_value) * 100
                            
                            if abs(change_pct) >= 10:  # Only report significant changes
                                direction = "increased" if change_pct > 0 else "decreased"
                                insights.append({
                                    "type": "trend",
                                    "metric": metric,
                                    "finding": f"{self._format_metric_name(metric)} has {direction} by {abs(change_pct):.1f}% for this URL over the period"
                                })
            except Exception as e:
                print(f"  Error in time series analysis: {e}")
        
        # Device analysis
        if 'deviceCategory' in df.columns:
            try:
                # Use screenPageViews or sessions for device analysis
                metric_col = 'sessions' if 'sessions' in df.columns else 'screenPageViews'
                if metric_col in df.columns:
                    device_data = df.groupby('deviceCategory')[metric_col].sum().reset_index()
                    device_data = device_data.sort_values(metric_col, ascending=False)
                    
                    if len(device_data) > 0:
                        top_device = device_data.iloc[0]['deviceCategory']
                        top_device_value = float(device_data.iloc[0][metric_col])
                        top_device_pct = float((top_device_value / device_data[metric_col].sum()) * 100)
                        
                        insights.append({
                            "type": "device",
                            "finding": f"The top device category for this URL is '{top_device}' accounting for {top_device_pct:.1f}% of {self._format_metric_name(metric_col)}"
                        })
                        
                        # If mobile percentage is high, add note
                        mobile_rows = device_data[device_data['deviceCategory'] == 'mobile']
                        if not mobile_rows.empty:
                            mobile_pct = float((mobile_rows.iloc[0][metric_col] / device_data[metric_col].sum()) * 100)
                            if mobile_pct > 40:
                                insights.append({
                                    "type": "mobile",
                                    "finding": f"This URL has significant mobile traffic ({mobile_pct:.1f}%), ensuring mobile optimization is important"
                                })
            except Exception as e:
                print(f"  Error in device analysis: {e}")
        
        # Add URL-specific summary
        insights.append({
            "type": "summary",
            "finding": f"Analysis for URL {url} shows {len(df)} data points across the specified time period."
        })
        
        # Build the final analysis result
        analysis_result = {
            "status": "success",
            "metrics": url_metrics,
            "insights": insights,
            "data_points": len(df),
            "compared_to_property": self._compare_to_property_metrics(url_metrics, property_metrics)
        }
        
        return analysis_result
    
    def _compare_to_property_metrics(self, url_metrics, property_metrics):
        """
        Compare URL metrics to property-level metrics.
        
        Args:
            url_metrics (dict): Metrics for the URL
            property_metrics (dict): Property-level metrics
            
        Returns:
            dict: Dictionary with comparison results
        """
        comparisons = {}
        
        # Compare key metrics
        for key in url_metrics:
            if key in ["channels", "events"]:  # Skip nested objects
                continue
                
            if key in property_metrics and property_metrics[key] > 0:
                diff_pct = ((url_metrics[key] - property_metrics[key]) / property_metrics[key]) * 100
                comparisons[key] = {
                    "url_value": url_metrics[key],
                    "property_value": property_metrics[key],
                    "difference_pct": diff_pct,
                    "performs": "better" if self._is_better_metric(key, diff_pct) else "worse"
                }
        
        return comparisons
    
    def _is_better_metric(self, metric_name, diff_pct):
        """
        Determine if a metric difference is positive or negative.
        For some metrics like bounce rate, lower is better.
        
        Args:
            metric_name (str): The name of the metric
            diff_pct (float): The percentage difference
            
        Returns:
            bool: True if the difference is positive, False otherwise
        """
        # For these metrics, lower is better
        lower_is_better = ['bounceRate', 'cartAbandonmentRate']
        
        if metric_name in lower_is_better:
            return diff_pct < 0
        
        # For all other metrics, higher is better
        return diff_pct > 0
    
    def _format_metric_name(self, metric_name):
        """
        Format a metric name for display.
        
        Args:
            metric_name (str): The raw metric name
            
        Returns:
            str: Formatted metric name
        """
        # Dictionary of metric name mappings
        name_map = {
            'sessions': 'sessions',
            'activeUsers': 'active users',
            'screenPageViews': 'page views',
            'bounceRate': 'bounce rate',
            'engagementRate': 'engagement rate',
            'engagedSessions': 'engaged sessions',
            'keyEvents': 'key events',
            'eventCount': 'events',
            'keyEventsPerSession': 'key events per session',
            'userEngagementDuration': 'user engagement duration',
            'avgTimeOnSite': 'average time on site',
            'conversionRate': 'conversion rate',
            'ecommercePurchases': 'purchases',
            'transactions': 'transactions',
            'addToCarts': 'add-to-carts',
            'checkouts': 'checkouts',
            'ecommerceConversionRate': 'e-commerce conversion rate',
            'cartAbandonmentRate': 'cart abandonment rate',
            'pageviewsPerSession': 'pageviews per session'
        }
        
        # Return the mapped name or format the camelCase to spaces
        if metric_name in name_map:
            return name_map[metric_name]
        
        # Python version of camelCase to words conversion
        return re.sub(r'([A-Z])', r' \1', metric_name).lower().strip()
    
    def _ensure_numeric(self, value, default=0):
        """
        Ensure a value is numeric by converting strings and handling errors.
        
        Args:
            value: The value to convert
            default: The default value to return if conversion fails
            
        Returns:
            float: The numeric value
        """
        if value is None:
            return default
            
        try:
            # If it's already a number, just return it
            if isinstance(value, (int, float)):
                return float(value)
            
            # Try to convert string to number
            return float(value)
        except (ValueError, TypeError):
            return default