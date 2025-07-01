#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Email Metadata Extractor Server

This script provides a Flask web server that serves as the backend for the email metadata
extractor web interface. It handles API requests from the JavaScript frontend.
"""

import os
import json
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from email_metadata_extractor import EmailMetadataExtractor
from werkzeug.utils import secure_filename

# Import database configuration
import database_config

try:
    from database_config import initialize_database
    # Initialize the database when the server starts
    initialize_database()
    print("Database initialized successfully")
except ImportError:
    print("Warning: Database configuration not found. Using simulated database.")

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS for all routes

# Ensure the uploads directory exists
UPLOADS_DIR = os.path.join(tempfile.gettempdir(), 'email_analyzer_uploads')
UPLOAD_FOLDER = UPLOADS_DIR  # Define UPLOAD_FOLDER for save_to_database route
os.makedirs(UPLOADS_DIR, exist_ok=True)


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('.', 'index.html')


@app.route('/api/search-email-metadata', methods=['POST'])
def search_email_metadata():
    """API endpoint to search for email metadata in the database."""
    data = request.json
    if not data or 'search_term' not in data:
        return jsonify({'error': 'No search term provided'}), 400
    
    search_term = data['search_term']
    search_type = data.get('search_type', 'sender')  # Default to searching by sender
    
    try:
        conn = database_config.get_db_connection()
        cursor = conn.cursor()
        
        # Build the query based on search type
        if search_type == 'sender':
            query = "SELECT * FROM email_metadata WHERE sender LIKE ?"
        elif search_type == 'recipient':
            query = "SELECT * FROM email_metadata WHERE recipient LIKE ?"
        elif search_type == 'subject':
            query = "SELECT * FROM email_metadata WHERE subject LIKE ?"
        elif search_type == 'message_id':
            query = "SELECT * FROM email_metadata WHERE message_id LIKE ?"
        else:
            return jsonify({'error': 'Invalid search type'}), 400
        
        # Execute the query
        cursor.execute(query, (f'%{search_term}%',))
        rows = cursor.fetchall()
        conn.close()
        
        # Convert rows to dictionaries
        results = [dict(row) for row in rows]
        
        return jsonify({
            'success': True,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def status():
    """API endpoint to check if the server is running."""
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/api/extract-metadata', methods=['POST'])
def extract_metadata():
    """API endpoint to extract metadata from an uploaded email file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        # Save the uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(UPLOADS_DIR, filename)
        file.save(temp_path)
        
        try:
            # Extract metadata
            extractor = EmailMetadataExtractor(temp_path)
            metadata = extractor.extract_metadata()
            
            # Save to database if save_to_db parameter is true
            save_to_db = request.form.get('save_to_db', 'false').lower() == 'true'
            metadata_id = None
            
            if save_to_db:
                metadata_id = extractor.save_to_database()
                if metadata_id:
                    metadata['database_id'] = metadata_id
                    metadata['saved_to_database'] = True
                else:
                    metadata['saved_to_database'] = False
            else:
                metadata['saved_to_database'] = False
            
            # Clean up the temporary file
            os.remove(temp_path)
            
            return jsonify(metadata)
        except Exception as e:
            # Clean up the temporary file in case of error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'error': str(e)}), 500


@app.route('/api/search-databases', methods=['POST'])
def search_databases():
    """API endpoint to search related databases for information about domains."""
    data = request.json
    if not data or 'domains' not in data:
        return jsonify({'error': 'No domains provided'}), 400
    
    domains = data['domains']
    if not domains:
        return jsonify({'error': 'Empty domains list'}), 400
    
    try:
        # Use real database search if use_real_db is true, otherwise use simulated search
        use_real_db = data.get('use_real_db', False)
        results = {}
        
        if use_real_db:
            # Use real database search
            for domain in domains:
                domain_info = database_config.search_domain_info(domain)
                related_emails = database_config.search_related_emails(domain)
                
                results[domain] = {
                    'domain_info': domain_info,
                    'related_emails': related_emails
                }
        else:
            # Use simulated search (for backward compatibility)
            extractor = EmailMetadataExtractor()
            for domain in domains:
                domain_info = extractor.search_related_databases(domain)
                results[domain] = domain_info
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save-to-database', methods=['POST'])
def save_to_database():
    """API endpoint to save extracted metadata to database."""
    if 'email_file' not in request.files:
        return jsonify({'error': 'No email file provided'}), 400
    
    email_file = request.files['email_file']
    if email_file.filename == '':
        return jsonify({'error': 'No email file selected'}), 400
    
    try:
        # Save the uploaded file
        filename = secure_filename(email_file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        email_file.save(file_path)
        
        # Extract metadata
        extractor = EmailMetadataExtractor(email_path=file_path)
        extractor.extract_metadata()
        
        # Save to database
        metadata_id = extractor.save_to_database()
        
        if metadata_id:
            return jsonify({
                'success': True,
                'message': 'Metadata saved to database successfully',
                'metadata_id': metadata_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to save metadata to database'
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/discover-alternates', methods=['POST'])
def discover_alternates():
    """API endpoint to discover potential alternate email addresses."""
    data = request.json
    if not data or 'metadata' not in data:
        return jsonify({'error': 'No metadata provided'}), 400
    
    try:
        # Create an extractor instance with the provided metadata
        extractor = EmailMetadataExtractor()
        extractor.metadata = data['metadata']
        
        # Discover alternate email addresses
        alternates = extractor.discover_alternate_emails()
        
        return jsonify({
            'success': True,
            'alternates': alternates
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/modify-email', methods=['POST'])
def modify_email():
    """API endpoint to modify an alternate email address."""
    data = request.json
    if not data or 'original_email' not in data or 'new_email' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    original_email = data['original_email']
    new_email = data['new_email']
    
    try:
        # Create an extractor instance
        extractor = EmailMetadataExtractor()
        
        # Modify the email address
        success = extractor.modify_alternate_email(original_email, new_email)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully modified email: {original_email} -> {new_email}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to modify email address'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# Note: We don't need to add a new search-email-metadata endpoint as it already exists


if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)