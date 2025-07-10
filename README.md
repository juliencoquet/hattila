# GA4 Analysis Tool

This tool analyzes Google Analytics 4 data at both the property level and for individual URLs.

## Features

- **Property-Level Analysis**: Analyze overall trends, traffic sources, and key metrics
- **URL-Specific Analysis**: Drill down into analytics for individual URLs
- **Custom Metrics and Dimensions**: Configure exactly what data you want to analyze
- **Flexible Date Ranges**: Analyze data from any time period
- **Insightful Reports**: Automatically generated insights from your GA4 data

## Quick Start

1. **Set up your Google Cloud credentials** (service account key file)

2. **Basic property analysis**:
   ```bash
   python main.py --property-id 123456789 --key-file credentials/service-account-key.json
   ```

3. **URL-specific analysis**:
   ```bash
   python main.py --property-id 123456789 --urls site_urls.csv
   ```

4. **View results** in the `results` directory

## Installation

1. **Prerequisites**:
   - Python 3.8+
   - A Google Analytics 4 property
   - A Google Cloud service account with access to GA4

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Place your service account key file** in the `credentials` directory

## Command Line Options

| Argument | Description | Required |
|----------|-------------|----------|
| `--property-id` | GA4 property ID to analyze | Yes |
| `--key-file` | Path to service account key file | No (uses config file) |
| `--property-name` | Friendly name for the GA4 property | No (uses property ID) |
| `--urls` | Path to CSV file with URLs to analyze | No |
| `--config` | Path to configuration file | No (default: config.json) |
| `--output-dir` | Directory to save results | No (uses config file) |
| `--metrics` | Comma-separated list of metrics | No (uses config file) |
| `--dimensions` | Comma-separated list of dimensions | No (uses config file) |
| `--date-range` | Date range in format "start_date,end_date" | No (uses config file) |

## URL-Specific Analysis

To analyze specific URLs, create a CSV file with one URL per line:
```
https://example.com/page1
https://example.com/page2
https://example.com/blog/article1
```

Then run the analysis with the `--urls` parameter:
```bash
python main.py --property-id 123456789 --urls your_urls.csv
```

The tool will:
1. Perform a property-wide analysis first
2. Analyze each URL individually
3. Generate insights specific to each URL
4. Save both property-level and URL-level analysis

### URL Analysis Features

- Traffic trends over time for each URL
- Traffic source breakdown per URL
- Key metrics (pageviews, sessions, etc.) for each URL
- Comparison to property-wide metrics
- Automatic identification of high-performing or problematic URLs

## Example Output

The tool generates JSON files with analysis results:

**Property-level insights**:
```json
{
  "property_id": "123456789",
  "property_name": "Example Website",
  "date_range": {
    "start": "2023-01-01",
    "end": "2023-01-31"
  },
  "insights": [
    {
      "type": "trend",
      "finding": "Sessions have increased by 15.2% over the period"
    },
    {
      "type": "traffic_source",
      "finding": "The top traffic source is 'google' accounting for 63.5% of traffic"
    }
  ]
}
```

**URL-specific insights**:
```json
{
  "urls": {
    "https://example.com/products": {
      "status": "success",
      "metrics": {
        "sessions_last_30_days": 1250,
        "activeUsers_last_30_days": 980
      },
      "insights": [
        {
          "type": "trend",
          "finding": "Sessions have decreased by 12.3% for this URL over the period"
        },
        {
          "type": "traffic_source",
          "finding": "The top traffic source is 'email' accounting for 45.2% of traffic"
        }
      ]
    }
  }
}
```

## Advanced Usage

### Custom Metrics and Dimensions

```bash
python main.py --property-id 123456789 --metrics "sessions,screenPageViews,conversions" --dimensions "date,deviceCategory,country"
```

### Custom Date Range

```bash
python main.py --property-id 123456789 --date-range "90daysAgo,yesterday"
```

### Custom Output Directory

```bash
python main.py --property-id 123456789 --output-dir ./custom-analysis
```

## Troubleshooting

1. **Authentication Failed**:
   - Verify your service account key file exists and is valid
   - Ensure your service account has access to the GA4 property

2. **No Data Collected**:
   - Check if the property ID is correct
   - Verify if there is data for the specified date range
   - Confirm the service account has proper permissions

3. **URL Analysis Returns No Data**:
   - Ensure URLs match exactly what's in GA4 (including protocols and query parameters)
   - Check if the URLs have traffic in the selected date range
   - Try using just the path component of the URL (e.g., "/products" instead of "https://example.com/products")