"""
analyzer.py - Data analysis module for Google Analytics 4 data

This module provides functions for analyzing and deriving insights
from Google Analytics 4 data.
"""

import os
import csv
import json
import pandas as pd
import numpy as np
from datetime import datetime


class GA4Analyzer:
    """Analyzes data from Google Analytics 4"""
    
    def __init__(self, config):
        """
        Initialize the GA4 data analyzer.
        
        Args:
            config: The configuration object
        """
        self.config = config
        self.output_dir = config.get_output_directory()
    
    def analyze_property_data(self, property_id, property_name, data):
        """
        Analyze data for a specific GA4 property.
        
        Args:
            property_id (str): The GA4 property ID
            property_name (str): The GA4 property name
            data (dict): The data collected from GA4 API
            
        Returns:
            dict: Dictionary with analysis results
        """
        if not data or not data.get("data"):
            print(f"No data available for property {property_name} ({property_id})")
            return None
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(data["data"])
        
        if df.empty:
            print(f"Empty dataset for property {property_name} ({property_id})")
            return None
        
        # Basic analysis results
        results = {
            "property_id": property_id,
            "property_name": property_name,
            "row_count": data["row_count"],
            "date_range": self._get_date_range(df),
            "metrics_summary": self._calculate_metrics_summary(df),
            "insights": self._generate_insights(df, property_name)
        }
        
        # Save results
        self._save_results(property_id, property_name, results, df)
        
        return results
    
    def _get_date_range(self, df):
        """Extract the date range from the dataset."""
        if 'date' not in df.columns:
            return {"start": "unknown", "end": "unknown"}
        
        try:
            dates = pd.to_datetime(df['date'], format='%Y%m%d')
            return {
                "start": dates.min().strftime('%Y-%m-%d'),
                "end": dates.max().strftime('%Y-%m-%d'),
                "days": (dates.max() - dates.min()).days + 1
            }
        except:
            return {"start": "unknown", "end": "unknown"}
    
    def _calculate_metrics_summary(self, df):
        """Calculate summary statistics for metrics."""
        # Identify metrics columns (those that are numeric)
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_columns:
            # Try to convert string columns that might be numeric
            for col in df.columns:
                if col != 'date' and not col.startswith(('sessionSource', 'country')):
                    try:
                        df[col] = pd.to_numeric(df[col])
                        numeric_columns.append(col)
                    except:
                        pass
        
        summary = {}
        for col in numeric_columns:
            summary[col] = {
                "total": float(df[col].sum()),
                "average": float(df[col].mean()),
                "median": float(df[col].median()),
                "min": float(df[col].min()),
                "max": float(df[col].max())
            }
        
        return summary
    
    def _generate_insights(self, df, property_name):
        """Generate key insights from the data."""
        insights = []
        
        # Check if we have time series data
        if 'date' in df.columns:
            try:
                # Convert to datetime for time series analysis
                df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                df = df.sort_values('date')
                
                # Identify trend metrics
                metrics = [col for col in df.columns if col not in ['date', 'sessionSource', 'country']]
                
                for metric in metrics:
                    # Calculate change over time
                    if len(df) > 1:
                        first_value = df[metric].iloc[0]
                        last_value = df[metric].iloc[-1]
                        
                        if first_value > 0:
                            change_pct = ((last_value - first_value) / first_value) * 100
                            
                            if abs(change_pct) >= 10:  # Only report significant changes
                                direction = "increased" if change_pct > 0 else "decreased"
                                insights.append({
                                    "type": "trend",
                                    "metric": metric,
                                    "finding": f"{metric} has {direction} by {abs(change_pct):.1f}% over the period"
                                })
            except Exception as e:
                print(f"Error in trend analysis: {e}")
        
        # Traffic source analysis
        if 'sessionSource' in df.columns:
            try:
                source_counts = df.groupby('sessionSource').size().reset_index(name='count')
                source_counts = source_counts.sort_values('count', ascending=False)
                
                if len(source_counts) > 0:
                    top_source = source_counts.iloc[0]['sessionSource']
                    top_source_count = source_counts.iloc[0]['count']
                    top_source_pct = (top_source_count / source_counts['count'].sum()) * 100
                    
                    insights.append({
                        "type": "traffic_source",
                        "finding": f"The top traffic source is '{top_source}' accounting for {top_source_pct:.1f}% of traffic"
                    })
                    
                    # Diversity of traffic sources
                    if len(source_counts) > 1:
                        source_diversity = len(source_counts) / df['sessionSource'].nunique()
                        
                        if source_diversity < 0.3:
                            insights.append({
                                "type": "warning",
                                "finding": f"Traffic is heavily concentrated from a few sources, which may represent a risk"
                            })
            except Exception as e:
                print(f"Error in traffic source analysis: {e}")
        
        # Geographic analysis
        if 'country' in df.columns:
            try:
                country_counts = df.groupby('country').size().reset_index(name='count')
                country_counts = country_counts.sort_values('count', ascending=False)
                
                if len(country_counts) > 0:
                    top_country = country_counts.iloc[0]['country']
                    top_country_count = country_counts.iloc[0]['count']
                    top_country_pct = (top_country_count / country_counts['count'].sum()) * 100
                    
                    insights.append({
                        "type": "geographic",
                        "finding": f"The top country is '{top_country}' accounting for {top_country_pct:.1f}% of traffic"
                    })
                    
                    # International reach
                    if len(country_counts) > 5:
                        insights.append({
                            "type": "opportunity",
                            "finding": f"The site has visitors from {len(country_counts)} countries, suggesting good international reach"
                        })
            except Exception as e:
                print(f"Error in geographic analysis: {e}")
        
        # Conversion analysis if we have conversion metrics
        conversion_metrics = [col for col in df.columns if 'conversion' in col.lower() or 'revenue' in col.lower()]
        if conversion_metrics:
            try:
                for metric in conversion_metrics:
                    if df[metric].sum() > 0:
                        avg_value = df[metric].mean()
                        insights.append({
                            "type": "conversion",
                            "metric": metric,
                            "finding": f"Average {metric} is {avg_value:.2f}"
                        })
            except Exception as e:
                print(f"Error in conversion analysis: {e}")
        
        # Add a site-specific summary
        insights.append({
            "type": "summary",
            "finding": f"Analysis for {property_name} shows {len(insights)} key findings across traffic sources, geographic distribution, and user engagement."
        })
        
        return insights
    
    def _save_results(self, property_id, property_name, results, df):
        """Save analysis results to file."""
        # Create a safe filename from property name
        safe_name = property_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save analysis results as JSON
        results_file = os.path.join(self.output_dir, f"{safe_name}_{timestamp}_analysis.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save raw data as CSV
        raw_data_file = os.path.join(self.output_dir, f"{safe_name}_{timestamp}_raw_data.csv")
        df.to_csv(raw_data_file, index=False)
        
        print(f"Saved analysis results to {results_file}")
        print(f"Saved raw data to {raw_data_file}")


if __name__ == "__main__":
    # Example usage (requires data from collector module)
    from config import Config
    from auth import authenticate_with_service_account
    from collector import GA4Collector
    
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
        property_name = "Your Property Name"  # Replace with actual property name
        report_data = collector.collect_data_for_property(property_id, config)
        
        if report_data:
            # Create analyzer
            analyzer = GA4Analyzer(config)
            
            # Analyze data
            analysis_results = analyzer.analyze_property_data(
                property_id, property_name, report_data
            )
            
            if analysis_results:
                print("\nAnalysis Results:")
                print(f"Date Range: {analysis_results['date_range']['start']} to {analysis_results['date_range']['end']}")
                print(f"Row Count: {analysis_results['row_count']}")
                
                print("\nInsights:")
                for i, insight in enumerate(analysis_results['insights']):
                    print(f"{i+1}. {insight['finding']}")