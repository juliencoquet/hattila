"""
storytelling_generator.py - Generates narrative reports from GA4 analysis data

This module takes the JSON output from url_analyzer.py and creates narrative
Google Docs reports with insights, visualizations, and recommendations.
"""

import os
import json
import datetime
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import tempfile
from config import Config
from translations import translate_text


class StorytellingGenerator:
    """Generates narrative reports from GA4 analysis data"""
    
    def __init__(self, config, language="en"):
        """
        Initialize the storytelling generator.
        
        Args:
            config: Configuration object
            language (str): Language for the reports (default: "en")
        """
        self.config = config
        self.output_dir = config.get_output_directory()
        self.language = language
        self.translated_cache = {}
        
        # Google API credentials
        self.credentials = None
        self.docs_service = None
        self.drive_service = None
        
        # Document settings
        self.header_style = {
            "font_size": 18,
            "bold": True,
            "foreground_color": {"color": {"rgb_color": {"red": 0.2, "green": 0.2, "blue": 0.6}}}
        }
        
        self.subheader_style = {
            "font_size": 14,
            "bold": True,
            "foreground_color": {"color": {"rgb_color": {"red": 0.4, "green": 0.4, "blue": 0.7}}}
        }
        
        # Initializing a template for section text formatting
        self.insight_style = {
            "font_size": 11
        }
        
        # Colors for charts
        self.colors = {
            "primary": "#4285F4",  # Google Blue
            "secondary": "#34A853",  # Google Green
            "tertiary": "#FBBC05",  # Google Yellow
            "quaternary": "#EA4335",  # Google Red
            "positive": "#34A853",  # Green for positive trends
            "negative": "#EA4335",  # Red for negative trends
            "neutral": "#9AA0A6"  # Gray for neutral items
        }
    
    def _t(self, text):
        """
        Translate text if needed.
        
        Args:
            text (str): Text to translate
            
        Returns:
            str: Translated text
        """
        if self.language == "en":
            return text
        
        # Check cache first
        if text in self.translated_cache:
            return self.translated_cache[text]
        
        # Translate
        translated = translate_text(text, self.language)
        self.translated_cache[text] = translated
        return translated
    
    def connect_to_google_apis_serviceaccount(self, credentials_path):
        """
        Connect to Google Docs and Drive APIs.
        
        Args:
            credentials_path (str): Path to service account JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
            )
            
            self.docs_service = build('docs', 'v1', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
            return True
        except Exception as e:
            print(f"Error connecting to Google APIs: {e}")
            return False

    # Change the connect_to_google_apis method
    def connect_to_google_apis_oauth(self, credentials_path=None):
        """
        Connect to Google Docs and Drive APIs using OAuth.
        
        Args:
            credentials_path (str, optional): Path to client secrets JSON file
                
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # If credentials_path is provided, update the path to client secrets
            if credentials_path and os.path.exists(credentials_path):
                import shutil
                shutil.copy(credentials_path, 'credentials.json')
            
            # Import the OAuth helper function
            from oauth_helpers import get_oauth_credentials
            
            # Get OAuth credentials
            self.credentials = get_oauth_credentials()
            
            if not self.credentials:
                print("Failed to get OAuth credentials")
                return False
            
            # Build the services with OAuth credentials
            self.docs_service = build('docs', 'v1', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
            return True
        except Exception as e:
            print(f"Error connecting to Google APIs: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_report_from_analysis(self, analysis_file, template_doc_id=None, output_folder_id=None):
        """
        Create a narrative report from an analysis JSON file.
        
        Args:
            analysis_file (str): Path to analysis JSON file
            template_doc_id (str, optional): Google Doc template ID
            output_folder_id (str, optional): Google Drive folder ID for output
            
        Returns:
            str: Google Doc ID of the created report
        """
        try:
            # Load the analysis data
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            # Create a title for the document
            property_name = analysis.get("property_name", "GA4 Analysis")
            timestamp = datetime.datetime.fromisoformat(analysis.get("timestamp", datetime.datetime.now().isoformat()))
            formatted_date = timestamp.strftime("%Y-%m-%d")
            
            doc_title = f"{property_name} - Analytics Report ({formatted_date})"
            
            # Create a new document or use template
            if template_doc_id:
                # Extract actual document ID from URL if needed
                if "docs.google.com/document/d/" in template_doc_id:
                    template_id = template_doc_id.split("docs.google.com/document/d/")[1].split("/")[0]
                else:
                    template_id = template_doc_id
                    
                print(f"Using template document: {template_id}")
                # Copy the template
                doc_id = self._copy_template(template_id, doc_title, output_folder_id)
            else:
                # Create a new document
                doc_id = self._create_new_document(doc_title, output_folder_id)
                        
            if not doc_id:
                print("Failed to create document")
                return None
            
            # Generate content for the document
            self._generate_property_overview(doc_id, analysis)
            
            # Process each URL
            if "urls" in analysis and analysis["urls"]:
                url_count = 0
                for url, url_data in analysis["urls"].items():
                    if url_data.get("status") == "success":
                        url_count += 1
                        self._generate_url_section(doc_id, url, url_data, analysis["property_metrics"])
                
                print(f"Generated content for {url_count} URLs")
            
            # Add recommendations
            self._generate_recommendations(doc_id, analysis)
            
            # Format the document (table of contents, page breaks, etc.)
            self._format_document(doc_id)

            # Share the document with the specified user
            self._share_document(doc_id, email="pro@juliencoquet.com", role="owner")
            
            return doc_id
            
        except Exception as e:
            print(f"Error creating report: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def _copy_template(self, template_id, title, folder_id=None):
        """
        Copy a template document and rename it.
        
        Args:
            template_id (str): Template document ID
            title (str): Title for the new document
            folder_id (str, optional): Folder to place the document in
            
        Returns:
            str: ID of the new document
        """
        try:
            # Create copy request
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.document'
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Copy the template
            response = self.drive_service.files().copy(
                fileId=template_id,
                body=file_metadata
            ).execute()
            
            doc_id = response.get('id')
            print(f"Created document from template: {doc_id}")
            return doc_id
        except Exception as e:
            print(f"Error copying template: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_new_document(self, title, folder_id=None):
        """
        Create a new Google Doc.
        
        Args:
            title (str): Title for the new document
            folder_id (str, optional): Folder to place the document in
            
        Returns:
            str: ID of the new document
        """
        try:
            # Create document request
            doc_metadata = {
                'title': title
            }
            
            # Create the document
            document = self.docs_service.documents().create(body=doc_metadata).execute()
            doc_id = document.get('documentId')
            
            # Move to specified folder if needed
            if folder_id and doc_id:
                file = self.drive_service.files().get(
                    fileId=doc_id, 
                    fields='parents'
                ).execute()
                
                previous_parents = ",".join(file.get('parents'))
                
                # Move file to new folder
                self.drive_service.files().update(
                    fileId=doc_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
            
            return doc_id
        except Exception as e:
            print(f"Error creating new document: {e}")
            return None
    
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
    
    def _create_channel_chart(self, channel_data, title="Channel Distribution"):
        """
        Create a pie chart for channel distribution.
        
        Args:
            channel_data (dict): Channel data with percentages
            title (str): Chart title
            
        Returns:
            str: Path to the chart image file
        """
        try:
            # Extract the data for the chart
            labels = []
            values = []
            
            # Sort by value
            sorted_channels = sorted(channel_data.items(), key=lambda x: x[1], reverse=True)
            
            for channel, value in sorted_channels:
                labels.append(channel)
                values.append(value)
            
            # If there are too many channels, group the smallest ones as "Other"
            if len(labels) > 6:
                other_value = sum(values[5:])
                labels = labels[:5] + ["Other"]
                values = values[:5] + [other_value]
            
            # Set up colors
            colors = [
                self.colors["primary"],
                self.colors["secondary"],
                self.colors["tertiary"],
                self.colors["quaternary"],
                "#5F6368",  # Google dark gray
                "#9AA0A6",  # Google light gray
            ]
            
            # Create a figure
            plt.figure(figsize=(6, 5))
            
            # Create the pie chart
            patches, texts, autotexts = plt.pie(
                values, 
                labels=None,  # We'll add our own legend
                autopct='%1.1f%%',
                startangle=90,
                colors=colors[:len(values)],
                wedgeprops={'edgecolor': 'white', 'linewidth': 1}
            )
            
            # Set font properties for the percentages
            for autotext in autotexts:
                autotext.set_fontsize(9)
                autotext.set_color('white')
            
            # Add a circle at the center to make it a donut chart
            centre_circle = plt.Circle((0, 0), 0.4, fc='white')
            plt.gcf().gca().add_artist(centre_circle)
            
            # Add a legend
            plt.legend(labels, loc="center", bbox_to_anchor=(0.5, 0.5), fontsize=9)
            
            # Equal aspect ratio ensures that pie is drawn as a circle
            plt.axis('equal')
            plt.tight_layout()
            
            # Add a title
            plt.title(title, fontsize=12, pad=20)
            
            # Save the figure to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                chart_path = tmp.name
                plt.savefig(chart_path, dpi=150, bbox_inches='tight')
                plt.close()
            
            return chart_path
            
        except Exception as e:
            print(f"Error creating channel chart: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_property_overview(self, doc_id, analysis):
        """
        Generate property overview section.
        
        Args:
            doc_id (str): Google Doc ID
            analysis (dict): Analysis data
        """
        try:
            property_name = analysis.get("property_name", "GA4 Analysis")
            property_metrics = analysis.get("property_metrics", {})
            
            # Create a batch update request
            requests = []
            
            # Add title
            requests.append({
                'insertText': {
                    'location': {
                        'index': 1
                    },
                    'text': f"{self._t('Analytics Report for')}: {property_name}\n\n"
                }
            })
            
            # Add formatted timestamp
            timestamp = datetime.datetime.fromisoformat(analysis.get("timestamp", datetime.datetime.now().isoformat()))
            formatted_date = timestamp.strftime("%Y-%m-%d")
            
            requests.append({
                'insertText': {
                    'location': {
                        'index': len(f"{self._t('Analytics Report for')}: {property_name}\n\n") + 1
                    },
                    'text': f"{self._t('Report Date')}: {formatted_date}\n\n"
                }
            })
            
            # Add table of contents placeholder
            requests.append({
                'insertText': {
                    'location': {
                        'index': len(f"{self._t('Analytics Report for')}: {property_name}\n\n{self._t('Report Date')}: {formatted_date}\n\n") + 1
                    },
                    'text': f"{self._t('Table of Contents')}\n\n"
                }
            })
            
            # Add property overview section
            current_index = len(f"{self._t('Analytics Report for')}: {property_name}\n\n{self._t('Report Date')}: {formatted_date}\n\n{self._t('Table of Contents')}\n\n") + 1
            
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': f"{self._t('Property Overview')}\n\n"
                }
            })
            
            # Add style to the section header
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(f"{self._t('Property Overview')}")
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            # Add key metrics
            current_index += len(f"{self._t('Property Overview')}\n\n")
            
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': f"{self._t('Key Metrics')}\n\n"
                }
            })
            
            # Add style to the subsection header
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(f"{self._t('Key Metrics')}")
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            # Create a table for key metrics
            current_index += len(f"{self._t('Key Metrics')}\n\n")
            
            # Prepare metrics for table
            metric_rows = []
            
            # Define key metrics to show
            key_metrics = [
                ('sessions', 'Sessions'),
                ('activeUsers', 'Active Users'),
                ('screenPageViews', 'Page Views'),
                ('engagementRate', 'Engagement Rate (%)'),
                ('conversionRate', 'Conversion Rate (%)'),
                ('averageSessionDuration', 'Avg. Session Duration (sec)')
            ]
            
            for metric_id, metric_name in key_metrics:
                if metric_id in property_metrics:
                    value = property_metrics[metric_id]
                    
                    # Format the value
                    if isinstance(value, float):
                        if metric_id in ['engagementRate', 'conversionRate']:
                            formatted_value = f"{value:.2f}%"
                        else:
                            formatted_value = f"{value:,.2f}" if value % 1 != 0 else f"{int(value):,}"
                    else:
                        formatted_value = str(value)
                    
                    metric_rows.append([self._t(metric_name), formatted_value])
            
            # Create table with 2 columns (metric name and value)
            # Only create a table if we have data
            if len(metric_rows) > 0:
                # Create table with 2 columns (metric name and value)
                table = {
                    'insertTable': {
                        'location': {
                            'index': current_index
                        },
                        'rows': len(metric_rows),
                        'columns': 2
                    }
                }
                
                requests.append(table)
            else:
                # Add a message if no metrics are available
                requests.append({
                    'insertText': {
                        'location': {
                            'index': current_index
                        },
                        'text': f"{self._t('No metrics data available.')}\n\n"
                    }
                })
            
            # Execute batch update to create the table
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            # Get the latest document to find the table
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Find the table
            table_id = None
            table_index = 0
            for element in document.get('body', {}).get('content', []):
                if 'table' in element:
                    table_id = element.get('table', {}).get('tableId')
                    break
                table_index += 1
            
            if table_id:
                # Now populate the table with data
                cell_requests = []
                
                for i, row in enumerate(metric_rows):
                    for j, cell_content in enumerate(row):
                        cell_requests.append({
                            'insertText': {
                                'location': {
                                    'tableId': table_id,
                                    'rowIndex': i,
                                    'columnIndex': j,
                                    'index': 0
                                },
                                'text': cell_content
                            }
                        })
                
                # Execute batch update to fill the table
                if cell_requests:
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': cell_requests}
                    ).execute()
            
            # Add marketing channels section
            marketing_channels = analysis.get("marketing_channels", {})
            
            if marketing_channels:
                # Create a batch update request
                requests = []
                
                # Get the document to find the end
                document = self.docs_service.documents().get(documentId=doc_id).execute()
                document_content = document.get('body', {}).get('content', [])

                # If the document is completely empty, insert at index 1
                if not document_content:
                    end_index = 1
                else:
                    # Get the last content element
                    last_element = document_content[-1]
                    end_index = last_element.get('endIndex', 0)
                    
                    # If the end index points to the beginning of the document (rare edge case),
                    # set it to position 1 (after the initial document position)
                    if end_index <= 1:
                        end_index = 1
                    
                    # If we're exactly at the end, back up one position to avoid the API error
                    if end_index > 1:
                        end_index -= 1
                                
                # Add section header
                requests.append({
                    'insertText': {
                        'location': {
                            'index': end_index
                        },
                        'text': f"\n{self._t('Marketing Channels')}\n\n"
                    }
                })
                
                # Style the header
                header_end_index = end_index + len(f"\n{self._t('Marketing Channels')}")
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': end_index + 1,  # +1 to skip the newline
                            'endIndex': header_end_index
                        },
                        'paragraphStyle': {
                            'namedStyleType': 'HEADING_2'
                        },
                        'fields': 'namedStyleType'
                    }
                })
                
                # Create a chart image for marketing channels
                if len(marketing_channels) > 0:
                    chart_path = self._create_marketing_channels_chart(marketing_channels)
                    
                    if chart_path:
                        # Upload the chart image to Drive
                        file_metadata = {
                            'name': 'marketing_channels_chart.png',
                            'mimeType': 'image/png'
                        }
                        
                        media = MediaFileUpload(chart_path, mimetype='image/png')
                                        
                file = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()

                image_id = file.get('id')

                if image_id:
                    try:
                        # Make the image accessible to anyone with the link
                        self.drive_service.permissions().create(
                            fileId=image_id,
                            body={
                                'type': 'anyone',
                                'role': 'reader'
                            }
                        ).execute()
                        
                        # Insert the image into the document
                        requests.append({
                            'insertInlineImage': {
                                'location': {
                                    'index': header_end_index + 2  # +2 to skip the newlines
                                },
                                'uri': f"https://drive.google.com/uc?id={image_id}",
                                'objectSize': {
                                    'height': {
                                        'magnitude': 300,
                                        'unit': 'PT'
                                    },
                                    'width': {
                                        'magnitude': 500,
                                        'unit': 'PT'
                                    }
                                }
                            }
                        })
                    except Exception as e:
                        print(f"Error making image public or inserting image: {e}")
                        # Continue without the image                
                # Execute the batch update
                if requests:
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute()
            
            # Add conversion metrics section if available
            conversion_metrics = analysis.get("conversion_metrics", {})
            
            if conversion_metrics:
                # Create a batch update request
                requests = []
                
                # Get the document to find the end
                document = self.docs_service.documents().get(documentId=doc_id).execute()
                end_index = document.get('body', {}).get('content', [-1])[-1].get('endIndex', 0)
                
                # Add section header
                requests.append({
                    'insertText': {
                        'location': {
                            'index': end_index
                        },
                        'text': f"\n{self._t('Conversion Metrics')}\n\n"
                    }
                })
                
                # Style the header
                header_end_index = end_index + len(f"\n{self._t('Conversion Metrics')}")
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': end_index + 1,  # +1 to skip the newline
                            'endIndex': header_end_index
                        },
                        'paragraphStyle': {
                            'namedStyleType': 'HEADING_2'
                        },
                        'fields': 'namedStyleType'
                    }
                })
                
                # Add conversion metrics text
                conversion_text = ""
                
                for event_name, event_data in conversion_metrics.items():
                    conversion_text += f"{event_name}: "
                    
                    for metric_name, metric_value in event_data.items():
                        if isinstance(metric_value, (int, float)):
                            formatted_value = f"{metric_value:,.0f}" if metric_value % 1 == 0 else f"{metric_value:,.2f}"
                            conversion_text += f"{metric_name}: {formatted_value}, "
                    
                    conversion_text = conversion_text.rstrip(", ") + "\n"
                
                if conversion_text:
                    requests.append({
                        'insertText': {
                            'location': {
                                'index': header_end_index + 2  # +2 to skip the newlines
                            },
                            'text': conversion_text
                        }
                    })
                
                # Execute the batch update
                if requests:
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute()
            
        except Exception as e:
            print(f"Error generating property overview: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_marketing_channels_chart(self, channels_data):
        """
        Create a chart image for marketing channels.
        
        Args:
            channels_data (dict): Marketing channels data
            
        Returns:
            str: Path to the chart image file
        """
        try:
            # Extract the data for the chart
            labels = []
            values = []
            
            for channel, data in channels_data.items():
                labels.append(channel)
                values.append(data.get("percentage", 0))
            
            # Sort by value
            sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)
            labels = [x[0] for x in sorted_data]
            values = [x[1] for x in sorted_data]
            
            # If there are too many channels, group the smallest ones as "Other"
            if len(labels) > 7:
                other_value = sum(values[6:])
                labels = labels[:6] + ["Other"]
                values = values[:6] + [other_value]
            
            # Set up colors
            colors = [
                self.colors["primary"],
                self.colors["secondary"],
                self.colors["tertiary"],
                self.colors["quaternary"],
                "#5F6368",  # Google dark gray
                "#9AA0A6",  # Google light gray
                "#DAD8D7"   # Google lightest gray
            ]
            
            # Create a figure
            plt.figure(figsize=(8, 6))
            
            # Create the pie chart
            patches, texts, autotexts = plt.pie(
                values, 
                labels=None,  # We'll add our own legend
                autopct='%1.1f%%',
                startangle=90,
                colors=colors[:len(values)],
                wedgeprops={'edgecolor': 'white', 'linewidth': 1}
            )
            
            # Set font properties for the percentages
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_color('white')
            
            # Add a circle at the center to make it a donut chart
            centre_circle = plt.Circle((0, 0), 0.4, fc='white')
            plt.gcf().gca().add_artist(centre_circle)
            
            # Add a legend
            plt.legend(labels, loc="center", bbox_to_anchor=(0.5, 0.5), fontsize=10)
            
            # Equal aspect ratio ensures that pie is drawn as a circle
            plt.axis('equal')
            plt.tight_layout()
            
            # Add a title
            plt.title(self._t("Marketing Channel Distribution"), fontsize=14, pad=20)
            
            # Save the figure to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                chart_path = tmp.name
                plt.savefig(chart_path, dpi=150, bbox_inches='tight')
                plt.close()
            
            return chart_path
            
        except Exception as e:
            print(f"Error creating marketing channels chart: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_url_section(self, doc_id, url, url_data, property_metrics):

        """
        Generate a section for a specific URL.
        
        Args:
            doc_id (str): Google Doc ID
            url (str): The URL
            url_data (dict): Data for the URL
            property_metrics (dict): Property-level metrics for comparison
        """
        try:
            # Get the document to find the end
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            end_index = document.get('body', {}).get('content', [-1])[-1].get('endIndex', 0)
            
            # Create a batch update request
            requests = []
            
            # Add section header with URL
            # Truncate URL if it's too long
            display_url = url
            if len(url) > 60:
                parsed_url = url.split('//')
                if len(parsed_url) > 1:
                    domain = parsed_url[1].split('/')[0]
                    path = '/' + '/'.join(parsed_url[1].split('/')[1:])
                    if len(path) > 40:
                        path = path[:37] + '...'
                    display_url = parsed_url[0] + '//' + domain + path
            
            requests.append({
                'insertText': {
                    'location': {
                        'index': end_index
                    },
                    'text': f"\n{self._t('URL Analysis')}: {display_url}\n\n"
                }
            })
            
            # Style the header
            header_end_index = end_index + len(f"\n{self._t('URL Analysis')}: {display_url}")
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': end_index + 1,  # +1 to skip the newline
                        'endIndex': header_end_index
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            # Add URL metrics
            current_index = header_end_index + 2  # +2 to skip the newlines
            
            # Add key metrics section
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': f"{self._t('Key Metrics')}\n\n"
                }
            })
            
            # Style the subheader
            subheader_end_index = current_index + len(f"{self._t('Key Metrics')}")
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': subheader_end_index
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            # Extract key metrics for this URL
            metrics = url_data.get("metrics", {})
            
            if metrics:
                # Create a table for key metrics
                current_index = subheader_end_index + 2  # +2 to skip the newlines
                
                # Prepare metrics for table
                metric_rows = []
                
                # Define key metrics to show
                key_metrics = [
                    ('sessions', 'Sessions'),
                    ('activeUsers', 'Active Users'),
                    ('screenPageViews', 'Page Views'),
                    ('engagementRate', 'Engagement Rate (%)'),
                    ('conversionRate', 'Conversion Rate (%)'),
                    ('pageviewsPerSession', 'Pageviews per Session')
                ]
                
                for metric_id, metric_name in key_metrics:
                    if metric_id in metrics:
                        value = metrics[metric_id]
                        
                        # Format the value
                        if isinstance(value, float):
                            if metric_id in ['engagementRate', 'conversionRate']:
                                formatted_value = f"{value:.2f}%"
                            else:
                                formatted_value = f"{value:,.2f}" if value % 1 != 0 else f"{int(value):,}"
                        else:
                            formatted_value = str(value)
                        
                        # Compare to property metrics
                        comparison_text = ""
                        if metric_id in property_metrics and property_metrics[metric_id] > 0:
                            prop_value = property_metrics[metric_id]
                            diff_pct = ((value - prop_value) / prop_value) * 100
                            
                            if abs(diff_pct) >= 5:  # Only show significant differences
                                comparison = self._t("higher than") if diff_pct > 0 else self._t("lower than")
                                comparison_text = f" ({abs(diff_pct):.1f}% {comparison} {self._t('property average')})"
                        
                        metric_rows.append([self._t(metric_name), formatted_value + comparison_text])
                
                # Create table with 2 columns (metric name and value)
                # Only create a table if we have data
                if len(metric_rows) > 0:
                    # Create table with 2 columns (metric name and value)
                    table = {
                        'insertTable': {
                            'location': {
                                'index': current_index
                            },
                            'rows': len(metric_rows),
                            'columns': 2
                        }
                    }
                    
                    requests.append(table)
                else:
                    # Add a message if no metrics are available
                    requests.append({
                        'insertText': {
                            'location': {
                                'index': current_index
                            },
                            'text': f"{self._t('No metrics data available.')}\n\n"
                        }
                    })
                
                # Execute batch update to create the table
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                
                # Get the latest document to find the table
                document = self.docs_service.documents().get(documentId=doc_id).execute()
                
                # Find the table
                table_id = None
                for element in document.get('body', {}).get('content', []):
                    if 'table' in element:
                        if element.get('startIndex', 0) >= current_index:
                            table_id = element.get('table', {}).get('tableId')
                            break
                
                if table_id:
                    # Now populate the table with data
                    cell_requests = []
                    
                    for i, row in enumerate(metric_rows):
                        for j, cell_content in enumerate(row):
                            cell_requests.append({
                                'insertText': {
                                    'location': {
                                        'tableId': table_id,
                                        'rowIndex': i,
                                        'columnIndex': j,
                                        'index': 0
                                    },
                                    'text': cell_content
                                }
                            })
                    
                    # Execute batch update to fill the table
                    if cell_requests:
                        self.docs_service.documents().batchUpdate(
                            documentId=doc_id,
                            body={'requests': cell_requests}
                        ).execute()
            
            # Add insights section
            # Get the document to find the end
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            end_index = document.get('body', {}).get('content', [-1])[-1].get('endIndex', 0)
            
            # Create a batch update request
            requests = []
            
            # Add insights header
            requests.append({
                'insertText': {
                    'location': {
                        'index': end_index
                    },
                    'text': f"\n{self._t('Insights')}\n\n"
                }
            })
            
            # Style the header
            insights_header_index = end_index + 1  # +1 to skip the newline
            insights_header_end = insights_header_index + len(self._t('Insights'))
            
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': insights_header_index,
                        'endIndex': insights_header_end
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            
            # Add insights content
            insights = url_data.get("insights", [])
            insights_text = ""
            
            if insights:
                # Group insights by type
                grouped_insights = {}
                for insight in insights:
                    insight_type = insight.get("type", "other")
                    if insight_type not in grouped_insights:
                        grouped_insights[insight_type] = []
                    grouped_insights[insight_type].append(insight)
                
                # Add each group of insights
                for insight_type, type_insights in grouped_insights.items():
                    # Skip summary insights as we're creating our own narrative
                    if insight_type == "summary":
                        continue
                    
                    # Format the insight type
                    formatted_type = insight_type.replace("_", " ").title()
                    insights_text += f"**{self._t(formatted_type)}**\n\n"
                    
                    # Add each insight in this group
                    for insight in type_insights:
                        finding = insight.get("finding", "")
                        if finding:
                            insights_text += f"• {self._t(finding)}\n"
                    
                    insights_text += "\n"
            else:
                insights_text = self._t("No significant insights were found for this URL.") + "\n\n"
            
            # Add the insights text
            current_index = insights_header_end + 2  # +2 to skip the newlines
            
            requests.append({
                'insertText': {
                    'location': {
                        'index': current_index
                    },
                    'text': insights_text
                }
            })
            
            # Apply formatting to bolded sections
            bold_pattern = re.compile(r'\*\*(.*?)\*\*')
            bold_matches = bold_pattern.finditer(insights_text)
            
            for match in bold_matches:
                start_pos = current_index + match.start()
                end_pos = current_index + match.end()
                
                # Remove ** marks
                requests.append({
                    'replaceText': {
                        'replaceText': match.group(1),
                        'text': match.group(),
                        'location': {'index': start_pos}
                    }
                })
                
                # Apply bold formatting
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start_pos,
                            'endIndex': start_pos + len(match.group(1))
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
            
            # Execute the batch update
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
            
            # Add PageSpeed section if available
            pagespeed_data = url_data.get("pagespeed", {})
            
            if pagespeed_data:
                # Get the document to find the end
                document = self.docs_service.documents().get(documentId=doc_id).execute()
                end_index = document.get('body', {}).get('content', [-1])[-1].get('endIndex', 0)
                
                # Create a batch update request
                requests = []
                
                # Add PageSpeed header
                requests.append({
                    'insertText': {
                        'location': {
                            'index': end_index
                        },
                        'text': f"\n{self._t('PageSpeed Analysis')}\n\n"
                    }
                })
                
                # Style the header
                pagespeed_header_index = end_index + 1  # +1 to skip the newline
                pagespeed_header_end = pagespeed_header_index + len(self._t('PageSpeed Analysis'))
                
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': pagespeed_header_index,
                            'endIndex': pagespeed_header_end
                        },
                        'paragraphStyle': {
                            'namedStyleType': 'HEADING_2'
                        },
                        'fields': 'namedStyleType'
                    }
                })
                
                # Add PageSpeed content
                pagespeed_text = ""
                
                # Process mobile and desktop scores
                for strategy in ["mobile", "desktop"]:
                    strategy_data = pagespeed_data.get(strategy, {})
                    if not strategy_data:
                        continue
                    
                    strategy_title = strategy.title()
                    pagespeed_text += f"**{self._t(strategy_title)} Performance**\n\n"
                    
                    categories = strategy_data.get("categories", {})
                    performance = categories.get("performance", {})
                    
                    if performance:
                        score = performance.get("score", 0)
                        score_text = self._get_score_text(score)
                        
                        pagespeed_text += f"{self._t('Performance Score')}: {score:.0f}/100 ({self._t(score_text)})\n\n"
                    
                    # Add metrics
                    audits = strategy_data.get("audits", {})
                    
                    if audits:
                        key_metrics = [
                            ("first-contentful-paint", "First Contentful Paint"),
                            ("largest-contentful-paint", "Largest Contentful Paint"),
                            ("speed-index", "Speed Index"),
                            ("total-blocking-time", "Total Blocking Time"),
                            ("cumulative-layout-shift", "Cumulative Layout Shift"),
                            ("interactive", "Time to Interactive")
                        ]
                        
                        for metric_id, metric_name in key_metrics:
                            metric_data = audits.get(metric_id, {})
                            if metric_data:
                                display_value = metric_data.get("display_value", "N/A")
                                score = metric_data.get("score", 0)
                                score_emoji = "✅" if score >= 90 else "⚠️" if score >= 50 else "❌"
                                
                                pagespeed_text += f"{score_emoji} {self._t(metric_name)}: {display_value}\n"
                        
                        pagespeed_text += "\n"
                
                # Add the PageSpeed text
                current_index = pagespeed_header_end + 2  # +2 to skip the newlines
                
                requests.append({
                    'insertText': {
                        'location': {
                            'index': current_index
                        },
                        'text': pagespeed_text
                    }
                })
                
                # Apply formatting to bolded sections
                bold_pattern = re.compile(r'\*\*(.*?)\*\*')
                bold_matches = bold_pattern.finditer(pagespeed_text)
                
                for match in bold_matches:
                    start_pos = current_index + match.start()
                    end_pos = current_index + match.end()
                    
                    # Remove ** marks
                    requests.append({
                        'replaceText': {
                            'replaceText': match.group(1),
                            'text': match.group(),
                            'location': {'index': start_pos}
                        }
                    })
                    
                    # Apply bold formatting
                    requests.append({
                        'updateTextStyle': {
                            'range': {
                                'startIndex': start_pos,
                                'endIndex': start_pos + len(match.group(1))
                            },
                            'textStyle': {
                                'bold': True
                            },
                            'fields': 'bold'
                        }
                    })
                
                # Execute the batch update
                if requests:
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute()
            
            # Add marketing channels section if available
            channel_data = metrics.get("channels", {})
            
            if channel_data and len(channel_data) > 0:
                # Create a chart for the channels
                channels_dict = {}
                for channel, data in channel_data.items():
                    channels_dict[channel] = data.get("percentage", 0)
                
                chart_path = self._create_channel_chart(channels_dict, f"{self._t('Traffic Sources')}: {display_url}")
                
                if chart_path:
                    # Get the document to find the end
                    document = self.docs_service.documents().get(documentId=doc_id).execute()
                    end_index = document.get('body', {}).get('content', [-1])[-1].get('endIndex', 0)
                    
                    # Create a batch update request
                    requests = []
                    
                    # Add channels header
                    requests.append({
                        'insertText': {
                            'location': {
                                'index': end_index
                            },
                            'text': f"\n{self._t('Traffic Sources')}\n\n"
                        }
                    })
                    
                    # Style the header
                    channels_header_index = end_index + 1  # +1 to skip the newline
                    channels_header_end = channels_header_index + len(self._t('Traffic Sources'))
                    
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': channels_header_index,
                                'endIndex': channels_header_end
                            },
                            'paragraphStyle': {
                                'namedStyleType': 'HEADING_2'
                            },
                            'fields': 'namedStyleType'
                        }
                    })
                    
                    # Upload the chart image to Drive
                    file_metadata = {
                        'name': f'channels_chart_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.png',
                        'mimeType': 'image/png'
                    }
                    
                    media = MediaFileUpload(chart_path, mimetype='image/png')
                    
                file = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()

                image_id = file.get('id')

                if image_id:
                    try:
                        # Make the image accessible to anyone with the link
                        self.drive_service.permissions().create(
                            fileId=image_id,
                            body={
                                'type': 'anyone',
                                'role': 'reader'
                            }
                        ).execute()
                        
                        # Insert the image into the document
                        requests.append({
                            'insertInlineImage': {
                                'location': {
                                    'index': header_end_index + 2  # +2 to skip the newlines
                                },
                                'uri': f"https://drive.google.com/uc?id={image_id}",
                                'objectSize': {
                                    'height': {
                                        'magnitude': 300,
                                        'unit': 'PT'
                                    },
                                    'width': {
                                        'magnitude': 500,
                                        'unit': 'PT'
                                    }
                                }
                            }
                        })
                    except Exception as e:
                        print(f"Error making image public or inserting image: {e}")
                        # Continue without the image
                        
                        # Execute the batch update
                        if requests:
                            self.docs_service.documents().batchUpdate(
                                documentId=doc_id,
                                body={'requests': requests}
                            ).execute()
            
            # Add a line break at the end of the URL section
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            end_index = document.get('body', {}).get('content', [-1])[-1].get('endIndex', 0)
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={
                    'requests': [
                        {
                            'insertText': {
                                'location': {
                                    'index': end_index
                                },
                                'text': "\n\n"
                            }
                        }
                    ]
                }
            ).execute()
        except Exception as e:
                print(f"Error generating URL section for {url}: {e}")
                import traceback
                traceback.print_exc()

    def _generate_recommendations(self, doc_id, analysis):
        """
        Generate recommendations based on analysis data.
        
        Args:
            doc_id (str): Google Doc ID
            analysis (dict): Analysis data
        """
        try:
            # Get the document to find the end
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            end_index = self._get_safe_insert_index(doc_id)
            
            # Create a batch update request
            requests = []
            
            # Add recommendations header
            requests.append({
                'insertText': {
                    'location': {
                        'index': end_index
                    },
                    'text': f"\n{self._t('Recommendations Based on Analysis')}\n\n"
                }
            })
            
            # Style the header
            header_index = end_index + 1  # +1 to skip the newline
            header_end = header_index + len(self._t('Recommendations Based on Analysis'))
            
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': header_index,
                        'endIndex': header_end
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1'
                    },
                    'fields': 'namedStyleType'
                    }
                })
            
            # Generate data-driven recommendations
            recommendations = []
            
            # Process property-level metrics
            property_metrics = analysis.get("property_metrics", {})
            
            # Check engagement rate from actual data
            if "engagementRate" in property_metrics:
                engagement_rate = property_metrics.get("engagementRate", 0)
                if engagement_rate < 60:
                    recommendations.append({
                        "category": "engagement",
                        "title": "Improve User Engagement",
                        "description": f"Your site's engagement rate is {engagement_rate:.1f}%, which could be improved. Consider enhancing interactive elements, adding more relevant content, and improving page load times."
                    })
                else:
                    recommendations.append({
                        "category": "engagement",
                        "title": "Maintain Strong User Engagement",
                        "description": f"Your site shows a strong engagement rate of {engagement_rate:.1f}%. Continue to monitor and maintain this level of engagement."
                    })
            
            # Extract all insights from URL analyses
            all_insights = []
            for url, url_data in analysis.get("urls", {}).items():
                if url_data.get("status") == "success":
                    insights = url_data.get("insights", [])
                    for insight in insights:
                        all_insights.append({
                            "url": url,
                            "type": insight.get("type", "unknown"),
                            "finding": insight.get("finding", "")
                        })
            
            # Group insights by type
            grouped_insights = {}
            for insight in all_insights:
                insight_type = insight.get("type")
                if insight_type not in grouped_insights:
                    grouped_insights[insight_type] = []
                grouped_insights[insight_type].append(insight)
            
            # Process PageSpeed insights
            pagespeed_issues = grouped_insights.get("pagespeed", [])
            if pagespeed_issues:
                mobile_issues = [i for i in pagespeed_issues if "mobile" in i.get("finding").lower()]
                desktop_issues = [i for i in pagespeed_issues if "desktop" in i.get("finding").lower()]
                
                if mobile_issues:
                    recommendations.append({
                        "category": "mobile",
                        "title": "Improve Mobile Performance",
                        "description": "Mobile performance issues were detected on several pages. Key findings:\n" + 
                            "\n".join([f"• {i.get('finding')} ({i.get('url')})" for i in mobile_issues[:3]])
                    })
                
                if desktop_issues:
                    recommendations.append({
                        "category": "desktop",
                        "title": "Optimize Desktop Experience",
                        "description": "Desktop performance issues were detected. Key findings:\n" + 
                            "\n".join([f"• {i.get('finding')} ({i.get('url')})" for i in desktop_issues[:3]])
                    })
            
            # Process traffic channel insights
            channel_insights = grouped_insights.get("channel", []) + grouped_insights.get("channel_diversity", [])
            if channel_insights:
                channel_recs = []
                for insight in channel_insights:
                    if "limited channel diversity" in insight.get("finding").lower():
                        channel_recs.append(f"• {insight.get('finding')} ({insight.get('url')})")
                
                if channel_recs:
                    recommendations.append({
                        "category": "traffic",
                        "title": "Diversify Traffic Sources",
                        "description": "Your traffic sources could be more diverse:\n" + "\n".join(channel_recs[:3])
                    })
            
            # Add general recommendations if we don't have enough specific ones
            if len(recommendations) < 3:
                recommendations.append({
                    "category": "general",
                    "title": "Set Up Enhanced Measurement",
                    "description": "Make sure Enhanced Measurement is enabled in your GA4 property settings to automatically collect clicks, scrolls, file downloads, and video engagement without additional coding."
                })
                
                recommendations.append({
                    "category": "general",
                    "title": "Implement Regular Analytics Reviews",
                    "description": "Schedule monthly analytics reviews to track the progress of your key metrics and identify emerging trends or issues early."
                })
            
            # Add recommendations to the document
            recommendations_text = ""
            
            for i, rec in enumerate(recommendations, 1):
                title = rec.get("title", "")
                description = rec.get("description", "")
                
                recommendations_text += f"**{i}. {self._t(title)}**\n\n"
                recommendations_text += f"{self._t(description)}\n\n"
            
            # If no recommendations were generated, add a placeholder
            if not recommendations_text:
                recommendations_text = self._t("No specific recommendations were generated based on the current data. Consider collecting more data or analyzing more URLs for detailed recommendations.") + "\n\n"
            
            # Insert text
            current_index = header_end + 2  # +2 to skip the newlines
            
            # Split text into paragraphs and insert each one separately
            paragraphs = re.sub(r'\*\*(.*?)\*\*', r'\1', recommendations_text).split("\n")
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                    
                requests.append({
                    'insertText': {
                        'location': {
                            'index': current_index
                        },
                        'text': paragraph + "\n"
                    }
                })
                
                current_index += len(paragraph) + 1
            
            # Execute the batch update
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
            
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()

    def _format_document(self, doc_id):
        """
        Format the document (page breaks, title formatting, etc.)
        
        Args:
            doc_id (str): Google Doc ID
        """
        try:
            # Get the document
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Create a batch update request
            requests = []
            
            # Add page breaks between major sections
            headings = []
            
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    style = element.get('paragraph', {}).get('paragraphStyle', {}).get('namedStyleType', '')
                    if style == 'HEADING_1':
                        headings.append({
                            'text': element.get('paragraph', {}).get('elements', [{}])[0].get('textRun', {}).get('content', '').strip(),
                            'index': element.get('endIndex', 0)
                        })
            
            # Insert page breaks before each H1 except the first one
            for i, heading in enumerate(headings):
                if i > 0:  # Skip the first heading
                    requests.append({
                        'insertPageBreak': {
                            'location': {
                                'index': heading.get('index') - 1  # Insert before the heading
                            }
                        }
                    })
            
            # Format the title
            if len(document.get('body', {}).get('content', [])) > 0:
                first_element = document.get('body', {}).get('content', [])[0]
                if 'paragraph' in first_element:
                    title_start = first_element.get('startIndex', 0)
                    title_end = first_element.get('endIndex', 0)
                    
                    # Make the title larger and colored
                    requests.append({
                        'updateTextStyle': {
                            'range': {
                                'startIndex': title_start,
                                'endIndex': title_end
                            },
                            'textStyle': {
                                'fontSize': {
                                    'magnitude': 24,
                                    'unit': 'PT'
                                },
                                'foregroundColor': {
                                    'color': {
                                        'rgbColor': {
                                            'red': 0.2,
                                            'green': 0.2,
                                            'blue': 0.6
                                        }
                                    }
                                },
                                'bold': True
                            },
                            'fields': 'fontSize,foregroundColor,bold'
                        }
                    })
            
            # Execute the batch update only if we have requests
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                
        except Exception as e:
            print(f"Error formatting document: {e}")
            import traceback
            traceback.print_exc()


    def _get_safe_insert_index(self, doc_id):
        """
        Get a safe index to insert content, avoiding segment boundary errors.
        
        Args:
            doc_id (str): Google Doc ID
            
        Returns:
            int: Safe index for insertion
        """
        try:
            # Get the document
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            document_content = document.get('body', {}).get('content', [])
            
            # If the document is completely empty, insert at index 1
            if not document_content:
                return 1
            
            # Get the end index
            last_element = document_content[-1]
            end_index = last_element.get('endIndex', 0)
            
            # If the end index is 0 or 1, use 1 as a safe starting point
            if end_index <= 1:
                return 1
            
            # Always insert a few positions before the end to avoid boundary issues
            return max(1, end_index - 2)
        
        except Exception as e:
            print(f"Error getting safe insert index: {e}")
            # Return 1 as a fallback (beginning of document)
            return 1        
        
    def _share_document(self, doc_id, email="pro@juliencoquet.com", role="writer"):
        """
        Share the document with a specific user and grant appropriate permissions.
        
        Args:
            doc_id (str): Google Doc ID
            email (str): Email address to share with
            role (str): Permission role - 'reader', 'writer', or 'owner'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create the permission
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            # For ownership transfers, we must send notification emails
            send_notification = True if role == 'owner' else False
            transfer_ownership = True if role == 'owner' else False
            
            # Share the document
            self.drive_service.permissions().create(
                fileId=doc_id,
                body=user_permission,
                sendNotificationEmail=send_notification,
                transferOwnership=transfer_ownership
            ).execute()
            
            print(f"Document shared with {email} as {role}")
            return True
        
        except Exception as e:
            print(f"Error sharing document with {email}: {e}")
            
            # If setting as owner fails, try again with writer role
            if role == 'owner':
                print("Attempting to share with 'writer' role instead")
                return self._share_document(doc_id, email, "writer")
            
            return False