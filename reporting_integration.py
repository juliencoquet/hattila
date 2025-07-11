"""
reporting_integration.py - Integration module for GA4 Analysis Tool reporting features

This module connects the GA4 Analysis Tool with the storytelling generator,
allowing automatic generation of Google Docs reports from analysis results.
"""

import os
import json
from storytelling_generator import StorytellingGenerator
from config import Config


def generate_google_doc_report_old(analysis_result, credentials_path, config, 
                              template_id=None, folder_id=None, language="en", custom_title=None):
    """
    Generate a Google Doc report from analysis results.
    
    Args:
        analysis_result (dict): The analysis results
        credentials_path (str): Path to OAuth client secrets file
        config (Config): Configuration object
        template_id (str, optional): Google Doc template ID
        folder_id (str, optional): Google Drive folder ID for output
        language (str): Report language code (default: "en")
        custom_title (str, optional): Custom document title
        
    Returns:
        str: Google Doc ID of the created report or None if failed
    """
    try:
        # Save analysis result to temporary file
        output_dir = config.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        temp_file = os.path.join(output_dir, "_temp_analysis.json")
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2)
        
        # Create storytelling generator with custom title
        generator = StorytellingGenerator(config, language=language, custom_title=custom_title)
        
        # Connect to Google APIs using OAuth
        if not generator.connect_to_google_apis(credentials_path):
            print("Failed to connect to Google APIs. Check credentials.")
            return None
        
        # Create the report
        doc_id = generator.create_report_from_analysis(
            temp_file,
            template_doc_id=template_id,
            output_folder_id=folder_id
        )
        
        # Delete the temporary file
        try:
            os.remove(temp_file)
        except:
            pass
        
        return doc_id
    
    except Exception as e:
        print(f"Error generating Google Doc report: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_google_doc_report(analysis_result, credentials_path, config, template_id=None, folder_id=None, language="en", custom_title=None):
    """
    Generate a Google Doc report from analysis results.
    """
    try:
        
        # Save analysis result to temporary file
        output_dir = config.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        temp_file = os.path.join(output_dir, "_temp_analysis.json")
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2)
        
        # Create storytelling generator with custom title and language
        generator = StorytellingGenerator(config, language=language, custom_title=custom_title)
        
        # Connect to Google APIs using OAuth
        if not generator.connect_to_google_apis(credentials_path):
            print("Failed to connect to Google APIs. Check credentials.")
            return None
        
        # Create the report
        doc_id = generator.create_report_from_analysis(
            temp_file,
            template_doc_id=template_id,
            output_folder_id=folder_id
        )
        
        # Delete the temporary file
        try:
            os.remove(temp_file)
        except:
            pass
        
        return doc_id
    
    except Exception as e:
        print(f"Error generating Google Doc report: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_report_from_file(analysis_file, credentials_path, config_path="config.json", template_id=None, folder_id=None, language="en"):
    """
    Generate a Google Doc report from an analysis file.
    
    Args:
        analysis_file (str): Path to analysis JSON file
        credentials_path (str): Path to Google API service account credentials
        config_path (str): Path to configuration file
        template_id (str, optional): Google Doc template ID
        folder_id (str, optional): Google Drive folder ID for output
        language (str): Report language code (default: "en")
        
    Returns:
        str: Google Doc ID of the created report or None if failed
    """
    try:
        # Load configuration
        config = Config(config_path)
        
        # Load analysis data
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Generate the report
        return generate_google_doc_report(
            analysis_data,
            credentials_path,
            config,
            template_id,
            folder_id,
            language
        )
    
    except Exception as e:
        print(f"Error generating report from file: {e}")
        import traceback
        traceback.print_exc()
        return None


# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='GA4 Analysis Report Generator')
    
    parser.add_argument('--analysis-file', required=True, help='Path to analysis JSON file')
    
    parser.add_argument('--config', default='config.json', help='Path to configuration file (default: config.json)')
    
    parser.add_argument('--credentials', required=True, help='Path to Google API service account credentials JSON file')
    
    parser.add_argument('--template', help='Google Doc template ID (optional)')
    
    parser.add_argument('--folder', help='Google Drive folder ID to save the document (optional)')
    
    parser.add_argument('--language', default='en', help='Language for the report (en, fr, etc.)')
    
    args = parser.parse_args()
    
    # Generate the report
    doc_id = generate_report_from_file(
        args.analysis_file,
        args.credentials,
        args.config,
        args.template,
        args.folder,
        args.language
    )
    
    if doc_id:
        print(f"Report created successfully: https://docs.google.com/document/d/{doc_id}/edit")
    else:
        print("Failed to create the report.")