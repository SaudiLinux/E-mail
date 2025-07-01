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

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS for all routes

# Ensure the uploads directory exists
UPLOADS_DIR = os.path.join(tempfile.gettempdir(), 'email_analyzer_uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('.', 'index.html')


@app.route('/api/status', methods=['GET'])
def status():
    """API endpoint to check if the server is running."""
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/api/extract-metadata', methods=['POST'])
def extract_metadata():
    """API endpoint to extract metadata from an uploaded email file."""
    if 'email_file' not in request.files:
        return jsonify({'error': 'No email file provided'}), 400
    
    email_file = request.files['email_file']
    if email_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save the uploaded file temporarily
    temp_path = os.path.join(UPLOADS_DIR, email_file.filename)
    email_file.save(temp_path)
    
    try:
        # Extract metadata from the email file
        extractor = EmailMetadataExtractor(email_path=temp_path)
        metadata = extractor.extract_metadata()
        
        # Return the metadata as JSON
        return jsonify({
            'success': True,
            'metadata': metadata
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/api/search-databases', methods=['POST'])
def search_databases():
    """API endpoint to search related databases for information about email domains."""
    data = request.json
    if not data or 'metadata' not in data:
        return jsonify({'error': 'No metadata provided'}), 400
    
    try:
        # Create an extractor instance with the provided metadata
        extractor = EmailMetadataExtractor()
        extractor.metadata = data['metadata']
        
        # Search related databases
        results = extractor.search_related_databases()
        
        return jsonify({
            'success': True,
            'results': results
        })
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


if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)