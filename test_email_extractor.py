#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test suite for Email Metadata Extractor

This script contains unit tests for the EmailMetadataExtractor class.
"""

import unittest
import os
import tempfile
from email.message import EmailMessage
from email_metadata_extractor import EmailMetadataExtractor


class TestEmailMetadataExtractor(unittest.TestCase):
    """Test cases for EmailMetadataExtractor class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample email for testing
        self.email_content = self._create_sample_email()
        
        # Create a temporary file with the email content
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.eml')
        self.temp_file.write(self.email_content)
        self.temp_file.close()
        
        # Initialize the extractor with the temporary file
        self.extractor = EmailMetadataExtractor(email_path=self.temp_file.name)

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def _create_sample_email(self):
        """Create a sample email for testing."""
        msg = EmailMessage()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'recipient@example.com, another@example.com'
        msg['Cc'] = 'cc@example.com'
        msg['Subject'] = 'Test Email'
        msg['Date'] = 'Mon, 01 Jan 2023 12:00:00 +0000'
        msg['Message-ID'] = '<12345@example.com>'
        msg['Return-Path'] = '<sender@example.com>'
        msg['X-Mailer'] = 'Test Mailer'
        msg['X-Priority'] = '3'
        msg['Received'] = 'from mail.example.com (mail.example.com [192.168.1.1]) by server.example.com with SMTP id 12345; Mon, 01 Jan 2023 12:00:00 +0000'
        msg.set_content('This is a test email.')
        
        return msg.as_bytes()

    def test_load_email(self):
        """Test loading an email from a file."""
        msg = self.extractor.load_email()
        self.assertIsNotNone(msg)
        self.assertEqual(msg['From'], 'sender@example.com')
        self.assertEqual(msg['Subject'], 'Test Email')

    def test_extract_metadata(self):
        """Test extracting metadata from an email."""
        metadata = self.extractor.extract_metadata()
        
        # Check basic headers
        self.assertEqual(metadata['from'], 'sender@example.com')
        self.assertEqual(metadata['subject'], 'Test Email')
        
        # Check extracted email addresses
        self.assertEqual(metadata['from_email'], 'sender@example.com')
        self.assertIn('recipient@example.com', metadata['to_emails'])
        self.assertIn('another@example.com', metadata['to_emails'])
        self.assertIn('cc@example.com', metadata['cc_emails'])
        
        # Check X-headers
        self.assertIn('X-Mailer', metadata['x_headers'])
        self.assertEqual(metadata['x_headers']['X-Mailer'], 'Test Mailer')
        
        # Check domains
        self.assertIn('example.com', metadata['domains'])
        
        # Check IP addresses
        self.assertIn('192.168.1.1', metadata['ip_addresses'])

    def test_extract_email_addresses(self):
        """Test extracting email addresses from header values."""
        header_value = 'Name <email@example.com>, Another <another@example.com>'
        emails = self.extractor._extract_email_addresses(header_value)
        
        self.assertEqual(len(emails), 2)
        self.assertIn('email@example.com', emails)
        self.assertIn('another@example.com', emails)

    def test_extract_domains(self):
        """Test extracting domains from email addresses."""
        # Set up metadata with email addresses
        self.extractor.metadata = {
            'from_email': 'sender@example.com',
            'to_emails': ['recipient@example.org', 'another@example.net'],
            'cc_emails': ['cc@example.com'],
            'bcc_emails': []
        }
        
        domains = self.extractor._extract_domains()
        
        self.assertEqual(len(domains), 3)
        self.assertIn('example.com', domains)
        self.assertIn('example.org', domains)
        self.assertIn('example.net', domains)

    def test_discover_alternate_emails(self):
        """Test discovering alternate email addresses."""
        # Extract metadata first
        self.extractor.extract_metadata()
        
        # Discover alternate emails
        alternates = self.extractor.discover_alternate_emails()
        
        # Check that we have some alternate emails
        self.assertTrue(len(alternates) > 0)
        
        # Check for common variations
        sender_name = 'sender'
        common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
        
        found_variation = False
        for domain in common_domains:
            if f"{sender_name}@{domain}" in alternates:
                found_variation = True
                break
        
        self.assertTrue(found_variation, "No common email variations found")

    def test_to_json(self):
        """Test converting metadata to JSON."""
        # Extract metadata first
        self.extractor.extract_metadata()
        
        # Convert to JSON
        json_str = self.extractor.to_json()
        
        # Check that it's a valid JSON string
        self.assertIsInstance(json_str, str)
        self.assertTrue(json_str.startswith('{'))
        self.assertTrue(json_str.endswith('}')


if __name__ == '__main__':
    unittest.main()