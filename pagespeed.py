"""
pagespeed.py - Module for retrieving and analyzing PageSpeed (Lighthouse) scores

This module integrates with Google's PageSpeed Insights API to retrieve
performance metrics for URLs and generate insights based on those metrics.
"""

import requests
import time
import json
from urllib.parse import quote_plus
import os


class PageSpeedAnalyzer:
    """Analyzes pages using Google PageSpeed Insights API"""
    
    def __init__(self, api_key=None, output_dir="results", max_requests_per_day=100):
        """
        Initialize the PageSpeed analyzer.
        
        Args:
            api_key (str): Google API key for PageSpeed Insights
            output_dir (str): Directory to save raw PageSpeed results
            max_requests_per_day (int): Maximum daily API requests to allow
        """
        self.api_key = api_key
        self.output_dir = output_dir
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        
        # Create a subdirectory for raw PageSpeed data
        self.pagespeed_dir = os.path.join(output_dir, "pagespeed_raw")
        os.makedirs(self.pagespeed_dir, exist_ok=True)
        
        # Rate limiting parameters
        self.last_request_time = 0
        self.min_request_interval = 2.0  # seconds between requests (increased for safety)
        
        # Quota tracking
        self.requests_today = 0
        self.max_requests_per_day = max_requests_per_day
        self.quota_file = os.path.join(self.pagespeed_dir, "quota_tracker.json")
        self._load_quota_state()
    
    def _load_quota_state(self):
        """Load the current quota state from file if it exists."""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    quota_data = json.load(f)
                
                # Check if the data is from today
                last_date = quota_data.get('date')
                today = time.strftime("%Y-%m-%d")
                
                if last_date == today:
                    self.requests_today = quota_data.get('requests', 0)
                    print(f"  Resuming PageSpeed quota tracking: {self.requests_today}/{self.max_requests_per_day} requests used today")
            except Exception as e:
                print(f"  Error loading quota state: {e}")
    
    def _save_quota_state(self):
        """Save the current quota state to file."""
        try:
            today = time.strftime("%Y-%m-%d")
            quota_data = {
                'date': today,
                'requests': self.requests_today,
                'max': self.max_requests_per_day
            }
            
            with open(self.quota_file, 'w') as f:
                json.dump(quota_data, f)
        except Exception as e:
            print(f"  Error saving quota state: {e}")
    
    def _apply_rate_limiting(self):
        """Apply rate limiting to avoid hitting API limits."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def _get_cached_result(self, url, strategy):
        """
        Get cached PageSpeed result if available.
        
        Args:
            url (str): URL to analyze
            strategy (str): "mobile" or "desktop"
            
        Returns:
            dict: Cached result or None if not found
        """
        # Create a cache filename based on URL and strategy
        encoded_url = quote_plus(url)
        cache_filename = f"{encoded_url}_{strategy}.json"
        cache_path = os.path.join(self.pagespeed_dir, cache_filename)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  Error loading cached result: {e}")
        
        return None
    
    def _cache_result(self, url, strategy, result):
        """
        Cache PageSpeed result.
        
        Args:
            url (str): URL that was analyzed
            strategy (str): "mobile" or "desktop"
            result (dict): PageSpeed analysis result
        """
        # Create a cache filename based on URL and strategy
        encoded_url = quote_plus(url)
        cache_filename = f"{encoded_url}_{strategy}.json"
        cache_path = os.path.join(self.pagespeed_dir, cache_filename)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(result, f)
        except Exception as e:
            print(f"  Error caching result: {e}")
    
    def analyze_url(self, url, strategy="mobile", cache_results=True):
        """
        Analyze a URL using PageSpeed Insights.
        
        Args:
            url (str): URL to analyze
            strategy (str): "mobile" or "desktop"
            cache_results (bool): Whether to cache results
            
        Returns:
            dict: PageSpeed analysis results or None if failed
        """
        # Check if we've hit the quota limit
        if self.requests_today >= self.max_requests_per_day:
            print(f"  ⚠️ PageSpeed API daily quota limit reached ({self.max_requests_per_day} requests)")
            return None
        
        # Check cache first if enabled
        if cache_results:
            cached_result = self._get_cached_result(url, strategy)
            if cached_result:
                print(f"  Using cached PageSpeed results for {url} ({strategy})")
                return cached_result
        
        # Apply rate limiting
        self._apply_rate_limiting()
        
        # Prepare the API request
        params = {
            "url": url,
            "strategy": strategy
        }
        
        # Add API key if available
        if self.api_key:
            params["key"] = self.api_key
        
        try:
            print(f"  Requesting PageSpeed analysis for {url} ({strategy})...")
            response = requests.get(self.base_url, params=params, timeout=60)
            
            # Increment request counter and save state
            self.requests_today += 1
            self._save_quota_state()
            
            if response.status_code == 200:
                result = response.json()
                
                # Cache the result if enabled
                if cache_results:
                    self._cache_result(url, strategy, result)
                
                return result
            elif response.status_code == 429:  # Quota exceeded
                print(f"  ⚠️ PageSpeed API quota exceeded. Try again tomorrow or use a different API key.")
                # Mark that we've reached the quota limit
                self.requests_today = self.max_requests_per_day
                self._save_quota_state()
                return None
            else:
                print(f"  PageSpeed API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"  Error analyzing {url} with PageSpeed: {e}")
            return None
    
    def analyze_multiple_urls(self, urls, strategies=None, max_urls=None):
        """
        Analyze multiple URLs and return consolidated results.
        
        Args:
            urls (list): List of URLs to analyze
            strategies (list): List of strategies ("mobile" and/or "desktop")
            max_urls (int): Maximum number of URLs to analyze
            
        Returns:
            dict: Dictionary mapping URLs to their PageSpeed results
        """
        if strategies is None:
            strategies = ["mobile", "desktop"]
        
        # Limit the number of URLs if specified
        if max_urls and max_urls < len(urls):
            print(f"  Limiting PageSpeed analysis to {max_urls} URLs (out of {len(urls)})")
            urls_to_analyze = urls[:max_urls]
        else:
            urls_to_analyze = urls
            
        results = {}
        
        # Check if we still have quota available
        remaining_quota = self.max_requests_per_day - self.requests_today
        max_possible = remaining_quota // len(strategies)
        
        if max_possible <= 0:
            print(f"  ⚠️ No PageSpeed API quota remaining for today. Try again tomorrow.")
            return results
        
        if max_possible < len(urls_to_analyze):
            print(f"  ⚠️ Only enough quota for {max_possible} URLs (analyzing {len(strategies)} strategies per URL)")
            urls_to_analyze = urls_to_analyze[:max_possible]
        
        for url in urls_to_analyze:
            results[url] = {}
            
            for strategy in strategies:
                # Get PageSpeed results for this URL and strategy
                result = self.analyze_url(url, strategy)
                
                if result:
                    # Extract and process the key metrics
                    metrics = self._extract_metrics(result)
                    results[url][strategy] = metrics
                else:
                    results[url][strategy] = None
                
                # If we've hit the quota limit, stop processing
                if self.requests_today >= self.max_requests_per_day:
                    print(f"  ⚠️ PageSpeed API daily quota limit reached, stopping further analysis")
                    return results
        
        return results
        
    def _extract_metrics(self, result):
        """
        Extract key metrics from a PageSpeed result.
        
        Args:
            result (dict): The raw PageSpeed result
            
        Returns:
            dict: Dictionary of extracted metrics
        """
        metrics = {}
        
        # Check if the result contains lighthouse data
        if not result or not isinstance(result, dict) or not result.get("lighthouseResult"):
            return metrics
        
        lighthouse_result = result["lighthouseResult"]
        
        # Extract categories and scores
        if "categories" in lighthouse_result:
            categories = lighthouse_result["categories"]
            metrics["categories"] = {}
            
            for category_key, category in categories.items():
                if "score" in category:
                    metrics["categories"][category_key] = {
                        "title": category.get("title", category_key),
                        "score": float(category["score"]) * 100  # Convert from 0-1 to 0-100
                    }
        
        # Extract audits for performance metrics
        if "audits" in lighthouse_result:
            audits = lighthouse_result["audits"]
            metrics["audits"] = {}
            
            # Extract key performance metrics
            key_metrics = [
                "first-contentful-paint",
                "largest-contentful-paint",
                "interactive",
                "speed-index",
                "total-blocking-time",
                "cumulative-layout-shift"
            ]
            
            for metric_key in key_metrics:
                if metric_key in audits:
                    audit = audits[metric_key]
                    
                    metrics["audits"][metric_key] = {
                        "title": audit.get("title", metric_key),
                        "description": audit.get("description", ""),
                        "score": float(audit.get("score", 0)) * 100,
                        "display_value": audit.get("displayValue", "")
                    }
                    
                    # Extract numeric value if available
                    if "numericValue" in audit:
                        metrics["audits"][metric_key]["numeric_value"] = audit["numericValue"]
        
        return metrics
    
    def _get_score_text(self, score):
        """Convert a score to a text description."""
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "average"
        else:
            return "poor"
    
    def get_insights(self, pagespeed_data):
        """
        Generate insights from PageSpeed data.
        
        Args:
            pagespeed_data (dict): PageSpeed data for a URL
            
        Returns:
            list: List of insights
        """
        insights = []
        
        if not pagespeed_data:
            return insights
        
        # Process mobile data first (if available)
        if "mobile" in pagespeed_data and pagespeed_data["mobile"]:
            mobile_data = pagespeed_data["mobile"]
            
            # Add overall performance score insight
            if "categories" in mobile_data and "performance" in mobile_data["categories"]:
                performance = mobile_data["categories"]["performance"]
                
                score = performance.get("score", 0)
                score_text = self._get_score_text(score)
                
                insights.append({
                    "type": "pagespeed",
                    "metric": "mobile_performance",
                    "finding": f"Mobile performance score is {score:.0f}/100 ({score_text})"
                })
            
            # Add insights for key metrics
            if "audits" in mobile_data:
                audits = mobile_data["audits"]
                
                # First Contentful Paint (FCP)
                if "first-contentful-paint" in audits:
                    fcp = audits["first-contentful-paint"]
                    score = fcp.get("score", 0)
                    display_value = fcp.get("display_value", "N/A")
                    
                    if score < 50:
                        insights.append({
                            "type": "pagespeed",
                            "metric": "mobile_fcp",
                            "finding": f"First Contentful Paint is slow at {display_value} - consider optimizing server response times and reducing render-blocking resources"
                        })
                
                # Largest Contentful Paint (LCP)
                if "largest-contentful-paint" in audits:
                    lcp = audits["largest-contentful-paint"]
                    score = lcp.get("score", 0)
                    display_value = lcp.get("display_value", "N/A")
                    
                    if score < 50:
                        insights.append({
                            "type": "pagespeed",
                            "metric": "mobile_lcp",
                            "finding": f"Largest Contentful Paint is slow at {display_value} - consider optimizing images, reducing JavaScript, and server response times"
                        })
                
                # Cumulative Layout Shift (CLS)
                if "cumulative-layout-shift" in audits:
                    cls = audits["cumulative-layout-shift"]
                    score = cls.get("score", 0)
                    display_value = cls.get("display_value", "N/A")
                    
                    if score < 50:
                        insights.append({
                            "type": "pagespeed",
                            "metric": "mobile_cls",
                            "finding": f"Cumulative Layout Shift is high at {display_value} - fix by explicitly setting size attributes for images and videos"
                        })
                
                # Total Blocking Time (TBT)
                if "total-blocking-time" in audits:
                    tbt = audits["total-blocking-time"]
                    score = tbt.get("score", 0)
                    display_value = tbt.get("display_value", "N/A")
                    
                    if score < 50:
                        insights.append({
                            "type": "pagespeed",
                            "metric": "mobile_tbt",
                            "finding": f"Total Blocking Time is high at {display_value} - consider code splitting, deferring non-critical JavaScript, or reducing JS execution time"
                        })
        
        # Process desktop data if available
        if "desktop" in pagespeed_data and pagespeed_data["desktop"]:
            desktop_data = pagespeed_data["desktop"]
            
            # Add overall performance score insight for desktop
            if "categories" in desktop_data and "performance" in desktop_data["categories"]:
                performance = desktop_data["categories"]["performance"]
                
                score = performance.get("score", 0)
                score_text = self._get_score_text(score)
                
                insights.append({
                    "type": "pagespeed",
                    "metric": "desktop_performance",
                    "finding": f"Desktop performance score is {score:.0f}/100 ({score_text})"
                })
        
        # Compare mobile and desktop scores if both are available
        if ("mobile" in pagespeed_data and pagespeed_data["mobile"] and
            "desktop" in pagespeed_data and pagespeed_data["desktop"]):
            
            mobile_score = pagespeed_data["mobile"].get("categories", {}).get("performance", {}).get("score", 0)
            desktop_score = pagespeed_data["desktop"].get("categories", {}).get("performance", {}).get("score", 0)
            
            if mobile_score > 0 and desktop_score > 0:
                diff = desktop_score - mobile_score
                
                if abs(diff) >= 10:  # Only highlight significant differences
                    worse_platform = "mobile" if diff > 0 else "desktop"
                    insights.append({
                        "type": "pagespeed",
                        "metric": "platform_comparison",
                        "finding": f"Performance is significantly worse on {worse_platform} devices, focus optimization efforts there first"
                    })
        
        return insights