#!/usr/bin/env python3
"""
main.py - Main script for Google Analytics 4 Analysis Tool

This is the main entry point for the GA4 Analysis Tool. It handles command-line
arguments, coordinates the authentication, data collection, and analysis processes.
"""

import os
import sys
import argparse
import csv
import json
from datetime import datetime

# Import our modules
from config import Config
from auth import authenticate_with_service_account, get_property_for_url
from collector import GA4Collector
from analyzer import GA4Analyzer
import reporting_integration


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Google Analytics 4 Analysis Tool')
    
    parser.add_argument('--config', default='config.json', help='Path to configuration file (default: config.json)')
    parser.add_argument('--key-file', help='Path to service account key file (overrides config file)')
    parser.add_argument('--property-id', required=True, help='GA4 property ID to analyze')
    parser.add_argument('--property-name', help='Friendly name for the GA4 property (default: uses property ID)')
    parser.add_argument('--urls', help='Path to CSV file with URLs to analyze (optional)')
    parser.add_argument('--output-dir', help='Directory to save results (overrides config file)')
    parser.add_argument('--metrics', help='Comma-separated list of metrics (overrides config file)')
    parser.add_argument('--dimensions', help='Comma-separated list of dimensions (overrides config file)')
    parser.add_argument('--date-range', help='Date range in format "start_date,end_date" (e.g., "30daysAgo,yesterday")')
    
    #Pagespeed
    parser.add_argument('--pagespeed', action='store_true', help='Enable PageSpeed analysis for URLs (default: disabled)')
    parser.add_argument('--pagespeed-key', help='Google API key for PageSpeed Insights')
    parser.add_argument('--pagespeed-max', type=int, default=10, help='Maximum number of URLs to analyze with PageSpeed (default: 10)')
    
    # Reporting integration
    parser.add_argument('--generate-doc', action='store_true', help='Generate a Google Doc report from the analysis')
    parser.add_argument('--google-credentials', help='Path to Google API service account credentials (for Google Docs integration)')
    parser.add_argument('--doc-template', help='Google Doc template ID to use for the report')
    parser.add_argument('--drive-folder', help='Google Drive folder ID to save the report in')
    parser.add_argument('--report-language', default='en', help='Language for the report (en, fr, etc.)')
    parser.add_argument('--doc-title', help='Custom title for the generated document')
    parser.add_argument('--doc-language', default='en', help='Language for the document content (en, fr, es, etc.)')
    
    # Parse the arguments
    return parser.parse_args()

def load_urls_from_file(file_path):
    """
    Load URLs from a CSV file.
    
    Args:
        file_path (str): Path to the file containing URLs
        
    Returns:
        list: List of URLs
    """
    urls = []
    
    if not file_path or not os.path.exists(file_path):
        return urls
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # Add non-empty cells that look like URLs
                for cell in row:
                    cell = cell.strip()
                    if cell and (cell.startswith('http') or '.' in cell):
                        urls.append(cell)
    except Exception as e:
        print(f"Error loading URLs from {file_path}: {e}")
    
    # Remove duplicates while preserving order
    unique_urls = []
    for url in urls:
        if url not in unique_urls:
            unique_urls.append(url)
    
    return unique_urls

def load_urls(file_path):
    """
    Load URLs from a CSV or JSON file.
    
    Args:
        file_path (str): Path to the file containing URLs
        
    Returns:
        list: List of URLs
    """
    urls = []
    
    if not os.path.exists(file_path):
        print(f"Error: URL file not found: {file_path}")
        return urls
    
    try:
        if file_path.endswith('.csv'):
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    # Add non-empty cells that look like URLs
                    urls.extend([cell.strip() for cell in row if cell.strip() and 
                                (cell.strip().startswith('http') or '.' in cell.strip())])
        
        elif file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            urls.append(item.strip())
                        elif isinstance(item, dict) and 'url' in item:
                            urls.append(item['url'].strip())
                
                elif isinstance(data, dict) and 'urls' in data:
                    for url in data['urls']:
                        urls.append(url.strip())
        
        else:
            print(f"Error: Unsupported file format: {file_path}")
            return []
    
    except Exception as e:
        print(f"Error loading URLs from {file_path}: {e}")
        return []
    
    # Remove duplicates while preserving order
    unique_urls = []
    for url in urls:
        if url not in unique_urls:
            unique_urls.append(url)
    
    return unique_urls


def override_config_with_args(config, args):
    """
    Override configuration with command-line arguments.
    
    Args:
        config: The configuration object
        args: The parsed command-line arguments
    """
    if args.key_file:
        config.config['service_account_key_file'] = args.key_file
    
    if args.output_dir:
        config.config['output_directory'] = args.output_dir
        os.makedirs(args.output_dir, exist_ok=True)
    
    if args.metrics:
        metrics = [{"name": metric.strip()} for metric in args.metrics.split(',')]
        config.config['metrics'] = metrics
    
    if args.dimensions:
        dimensions = [{"name": dim.strip()} for dim in args.dimensions.split(',')]
        config.config['dimensions'] = dimensions
    
    # Save the updated configuration
    config.save()


def format_url(url):
    """Format a URL for consistency."""
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url


def main():
    """Main function."""
    # Parse arguments
    args = parse_arguments()
    
    # Load configuration
    config = Config(args.config)
    
    # Override configuration with command-line arguments
    if args.key_file:
        config.config['service_account_key_file'] = args.key_file
    
    if args.output_dir:
        config.config['output_directory'] = args.output_dir
        os.makedirs(args.output_dir, exist_ok=True)
    
    if args.metrics:
        metrics = [{"name": metric.strip()} for metric in args.metrics.split(',')]
        config.config['metrics'] = metrics
    
    if args.dimensions:
        dimensions = [{"name": dim.strip()} for dim in args.dimensions.split(',')]
        config.config['dimensions'] = dimensions
    
    if args.date_range:
        parts = args.date_range.split(',')
        if len(parts) == 2:
            config.config['date_ranges'] = [
                {
                    "name": "custom_range",
                    "start_date": parts[0].strip(),
                    "end_date": parts[1].strip()
                }
            ]
    
    # Save the updated configuration
    config.save()
    
    # Authenticate with GA4 API
    key_file = config.get_service_account_path()
    if not key_file:
        print("Error: Service account key file not specified in configuration")
        sys.exit(1)
    
    print(f"Authenticating with service account key: {key_file}")
    data_client, _ = authenticate_with_service_account(key_file)
    
    if not data_client:
        print("Error: Authentication failed")
        sys.exit(1)
    
    print("Authentication successful")
    
    # Get property information
    property_id = args.property_id
    property_name = args.property_name or f"Property {property_id}"
    
    # Create collector and analyzer
    collector = GA4Collector(data_client)
    analyzer = GA4Analyzer(config)
    
    # Load URLs if provided
    urls = []
    if args.urls:
        urls = load_urls_from_file(args.urls)
        print(f"Loaded {len(urls)} URLs from {args.urls}")
    
    # Collect and analyze data
    print(f"\nProcessing GA4 property: {property_name} ({property_id})")
    
    # Collect data for overall property analysis
    print("Collecting property-level data...")
    report_data = collector.collect_data_for_property(property_id, config)
    
    if not report_data:
        print(f"No data collected for property {property_id}")
        sys.exit(1)
    
    print(f"Collected {report_data['row_count']} rows of data")
    
    # Analyze property-level data
    print("Analyzing property-level data...")
    analysis = analyzer.analyze_property_data(property_id, property_name, report_data)
    
    if not analysis:
        print(f"Analysis failed for property {property_id}")
        sys.exit(1)
    
    # Display property-level insights
    print(f"\nProperty-Level Analysis Results for {property_name}:")
    print(f"Date Range: {analysis['date_range']['start']} to {analysis['date_range']['end']}")
    
    print("\nInsights:")
    for i, insight in enumerate(analysis['insights'], 1):
        print(f"{i}. {insight['finding']}")
    
    # Process URLs if provided
    if urls:
        print(f"\nPerforming URL-specific analysis for {len(urls)} URLs...")
        
        # Import the URL analyzer
        from url_analyzer import URLAnalyzer
        
        # Create URL analyzer
        url_analyzer = URLAnalyzer(data_client, config)
        
        # Set PageSpeed options based on command line arguments
        if args.pagespeed:
            url_analyzer.pagespeed_enabled = True
            if args.pagespeed_key:
                url_analyzer.pagespeed_api_key = args.pagespeed_key
            url_analyzer.pagespeed_max_urls = args.pagespeed_max

        # Analyze URLs
        url_results = url_analyzer.analyze_urls(property_id, property_name, urls, generate_files=True)
        
        # Display summary of URL analysis
        success_count = sum(1 for _, data in url_results["urls"].items() if data["status"] == "success")
        
        print(f"\nURL Analysis Complete:")
        print(f"  - Successfully analyzed: {success_count}/{len(urls)} URLs")
        
        # Display sample insights from the first few URLs
        sample_count = min(3, success_count)
        if sample_count > 0:
            print("\nSample URL Insights:")
            
            count = 0
            for url, data in url_results["urls"].items():
                if data["status"] == "success":
                    count += 1
                    print(f"\n{url}:")
                    
                    # Show up to 3 insights per URL
                    for i, insight in enumerate(data["insights"][:3], 1):
                        print(f"  {i}. {insight['finding']}")
                    
                    if count >= sample_count:
                        break
            
            print("\n(See the JSON output file for complete URL analysis)")
    
    print(f"\nResults saved to {config.get_output_directory()}")
    print("Analysis complete!")
    """Main function."""
    # Parse arguments
    args = parse_arguments()
    
    # Load configuration
    config = Config(args.config)
    
    # Override configuration with command-line arguments
    if args.key_file:
        config.config['service_account_key_file'] = args.key_file
    
    if args.output_dir:
        config.config['output_directory'] = args.output_dir
        os.makedirs(args.output_dir, exist_ok=True)
    
    if args.metrics:
        metrics = [{"name": metric.strip()} for metric in args.metrics.split(',')]
        config.config['metrics'] = metrics
    
    if args.dimensions:
        dimensions = [{"name": dim.strip()} for dim in args.dimensions.split(',')]
        config.config['dimensions'] = dimensions
    
    if args.date_range:
        parts = args.date_range.split(',')
        if len(parts) == 2:
            config.config['date_ranges'] = [
                {
                    "name": "custom_range",
                    "start_date": parts[0].strip(),
                    "end_date": parts[1].strip()
                }
            ]
    
    # Save the updated configuration
    config.save()
    
    # Authenticate with GA4 API
    key_file = config.get_service_account_path()
    if not key_file:
        print("Error: Service account key file not specified in configuration")
        sys.exit(1)
    
    print(f"Authenticating with service account key: {key_file}")
    data_client, _ = authenticate_with_service_account(key_file)
    
    if not data_client:
        print("Error: Authentication failed")
        sys.exit(1)
    
    print("Authentication successful")
    
    # Get property information
    property_id = args.property_id
    property_name = args.property_name or f"Property {property_id}"
    
    # Create collector and analyzer
    collector = GA4Collector(data_client)
    analyzer = GA4Analyzer(config)
    
    # Load URLs if provided
    urls = []
    if args.urls:
        urls = load_urls_from_file(args.urls)
        print(f"Loaded {len(urls)} URLs from {args.urls}")
    
    # Collect and analyze data
    print(f"\nProcessing GA4 property: {property_name} ({property_id})")
    
    # Collect data
    print("Collecting data...")
    report_data = collector.collect_data_for_property(property_id, config)
    
    if not report_data:
        print(f"No data collected for property {property_id}")
        sys.exit(1)
    
    print(f"Collected {report_data['row_count']} rows of data")
    
    # Analyze data
    print("Analyzing data...")
    analysis = analyzer.analyze_property_data(property_id, property_name, report_data)
    
    if not analysis:
        print(f"Analysis failed for property {property_id}")
        sys.exit(1)
    

    
    # Process URLs if provided
    if urls:
        print(f"\nPerforming URL-specific analysis for {len(urls)} URLs...")
        
        # Import the URL analyzer
        from url_analyzer import URLAnalyzer
        
        # Create URL analyzer
        url_analyzer = URLAnalyzer(data_client, config)
        
        # Set PageSpeed options based on command line arguments
        if args.pagespeed:
            url_analyzer.pagespeed_enabled = True
            if args.pagespeed_key:
                url_analyzer.pagespeed_api_key = args.pagespeed_key
            url_analyzer.pagespeed_max_urls = args.pagespeed_max

        # Analyze URLs
        url_results = url_analyzer.analyze_urls(property_id, property_name, urls, generate_files=True)
        
        # Generate Google Doc report for URL analysis if requested
        if args.generate_doc:
            print("\nGenerating Google Doc report for URL analysis...")
            url_doc_id = reporting_integration.generate_google_doc_report(
                url_results,
                args.google_credentials,
                config,
                template_id=args.doc_template,
                folder_id=args.drive_folder,
                language=args.doc_language
            )
            
            if url_doc_id:
                print(f"URL analysis Google Doc report created: https://docs.google.com/document/d/{url_doc_id}/edit")
            else:
                print("Failed to create URL analysis Google Doc report")
        
        # Display summary of URL analysis
        success_count = sum(1 for _, data in url_results["urls"].items() if data["status"] == "success")
        
        print(f"\nURL Analysis Complete:")
        print(f"  - Successfully analyzed: {success_count}/{len(urls)} URLs")
        
        # Display sample insights from the first few URLs
        sample_count = min(3, success_count)
        if sample_count > 0:
            print("\nSample URL Insights:")
            
            count = 0
            for url, data in url_results["urls"].items():
                if data["status"] == "success":
                    count += 1
                    print(f"\n{url}:")
                    
                    # Show up to 3 insights per URL
                    for i, insight in enumerate(data["insights"][:3], 1):
                        print(f"  {i}. {insight['finding']}")
                    
                    if count >= sample_count:
                        break
            
            print("\n(See the JSON output file for complete URL analysis)")

    # Display insights
    print(f"\nAnalysis Results for {property_name}:")
    print(f"Date Range: {analysis['date_range']['start']} to {analysis['date_range']['end']}")
    
    print("\nInsights:")
    for i, insight in enumerate(analysis['insights'], 1):
        print(f"{i}. {insight['finding']}")
    
    print(f"\nResults saved to {config.get_output_directory()}")
    print("Analysis complete!")


if __name__ == "__main__":
    main()