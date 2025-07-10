# GA4 Analytics Storytelling Generator

This extension to the GA4 Analysis Tool creates narrative reports in Google Docs format from your analytics data, providing storytelling capabilities on top of the raw data and insights.

## Features

- Generates comprehensive Google Docs reports from GA4 analysis JSON files
- Creates visualizations of key metrics and traffic sources
- Translates reports into different languages
- Automatically formats the document with a table of contents and proper styling
- Generates actionable recommendations based on the analysis
- Integrates with the existing GA4 Analysis Tool

## Setup Instructions

### 1. Install Dependencies

In addition to the dependencies for the GA4 Analysis Tool, you'll need to install:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib matplotlib seaborn numpy pandas
```

### 2. Create Google API Credentials

To use the Google Docs and Drive APIs, you need a service account:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Docs API and Google Drive API
4. Create a Service Account under "IAM & Admin" > "Service Accounts"
5. Create a key for the service account and download it as JSON
6. Share any template Google Docs or folders with the service account email

### 3. Add Files to Your Project

Copy the following new files to your GA4 Analysis Tool directory:

- `storytelling_generator.py`
- `reporting_integration.py`

### 4. Update main.py

Update your `main.py` file with the changes from `main_update.py`:

1. Add the new import: `import reporting_integration`
2. Add the new command-line arguments to `parse_arguments()`
3. Add the report generation code after the analysis is complete

## Usage

### Basic Usage

To generate a Google Docs report from an existing analysis JSON file:

```bash
python reporting_integration.py --analysis-file results/my_analysis.json --credentials path/to/google-credentials.json
```

### Integration with GA4 Analysis Tool

To run a complete analysis and generate a Google Docs report:

```bash
python main.py --property-id YOUR_PROPERTY_ID --urls urls.csv --generate-doc --google-credentials path/to/google-credentials.json
```

### Advanced Options

```bash
python main.py --property-id YOUR_PROPERTY_ID 
               --property-name "My Website" 
               --urls urls.csv 
               --date-range "30daysAgo,yesterday" 
               --generate-doc 
               --google-credentials path/to/google-credentials.json 
               --doc-template TEMPLATE_DOC_ID
               --drive-folder FOLDER_ID
               --report-language fr
```

## Template Customization

You can create a Google Doc template to use as a starting point for your reports:

1. Create a Google Doc with your desired formatting, branding, etc.
2. Include the text "Table of Contents" where you want the TOC to appear
3. Get the document ID from the URL (`https://docs.google.com/document/d/DOCUMENT_ID/edit`)
4. Share the document with your service account email
5. Use the `--doc-template` parameter with the document ID

## Translation Support

To generate reports in different languages, use the `--report-language` parameter:

```bash
python main.py --property-id YOUR_PROPERTY_ID --generate-doc --google-credentials path/to/credentials.json --report-language fr
```

Supported languages:
- `en`: English (default)
- `fr`: French
- `es`: Spanish
- `de`: German
- More languages can be added in the `translations.py` file

## Troubleshooting

### Permission Issues

If you encounter permission errors:

1. Ensure your service account has been granted access to any template documents or folders
2. Check that both the Google Docs API and Google Drive API are enabled in your project
3. Verify the credentials file is correct and not expired

### Report Generation Failures

If the report fails to generate:

1. Check the console output for specific error messages
2. Verify the analysis JSON file is valid and contains the expected data
3. Ensure you have all required dependencies installed

## Extending the Storytelling Generator

To add new visualizations or sections to the reports:

1. Extend the `StorytellingGenerator` class in `storytelling_generator.py`
2. Add new methods for your custom sections
3. Update the `create_report_from_analysis` method to call your new methods

## License

This tool is subject to the same license as the GA4 Analysis Tool.