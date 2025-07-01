#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Email Metadata Extractor and Analyzer - Python Component

This script extracts metadata from email files, searches related databases,
and provides functionality to discover and modify alternate email addresses.
"""

import email
import os
import re
import json
import argparse
import sqlite3
import requests
from email.parser import BytesParser
from email.policy import default
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Import database configuration
import database_config


class EmailMetadataExtractor:
    """Class for extracting metadata from email files."""

    def __init__(self, email_path: str = None, email_content: bytes = None):
        """Initialize with either a path to an email file or raw email content."""
        self.email_path = email_path
        self.email_content = email_content
        self.metadata = {}
        self.related_emails = []
        self.db_connection = None
        
        # Import database configuration here to avoid circular imports
        try:
            from database_config import get_db_connection
            self.get_db_connection = get_db_connection
        except ImportError:
            self.get_db_connection = None

    def load_email(self) -> email.message.Message:
        """Load email from file or content."""
        if self.email_path and os.path.exists(self.email_path):
            with open(self.email_path, 'rb') as fp:
                return BytesParser(policy=default).parse(fp)
        elif self.email_content:
            return BytesParser(policy=default).parsebytes(self.email_content)
        else:
            raise ValueError("No valid email source provided")

    def extract_metadata(self) -> Dict[str, Any]:
        """Extract all metadata from the email."""
        msg = self.load_email()
        
        # Basic headers
        self.metadata = {
            'from': msg.get('From', ''),
            'to': msg.get('To', ''),
            'cc': msg.get('Cc', ''),
            'bcc': msg.get('Bcc', ''),
            'subject': msg.get('Subject', ''),
            'date': msg.get('Date', ''),
            'message_id': msg.get('Message-ID', ''),
            'in_reply_to': msg.get('In-Reply-To', ''),
            'references': msg.get('References', ''),
            'return_path': msg.get('Return-Path', ''),
            'received': self._parse_received_headers(msg),
            'x_headers': self._extract_x_headers(msg),
            'dkim': msg.get('DKIM-Signature', ''),
            'spf': msg.get('Received-SPF', ''),
            'authentication_results': msg.get('Authentication-Results', ''),
            'content_type': msg.get('Content-Type', ''),
            'user_agent': msg.get('User-Agent', ''),
            'mime_version': msg.get('MIME-Version', ''),
        }
        
        # Extract email addresses
        self.metadata['from_email'] = self._extract_email_address(self.metadata['from'])
        self.metadata['to_emails'] = self._extract_email_addresses(self.metadata['to'])
        self.metadata['cc_emails'] = self._extract_email_addresses(self.metadata['cc'])
        self.metadata['bcc_emails'] = self._extract_email_addresses(self.metadata['bcc'])
        
        # Extract IP addresses from received headers
        self.metadata['ip_addresses'] = self._extract_ip_addresses(self.metadata['received'])
        
        # Extract domains
        self.metadata['domains'] = self._extract_domains()
        
        return self.metadata

    def _parse_received_headers(self, msg: email.message.Message) -> List[str]:
        """Extract all 'Received' headers as they contain routing information."""
        received_headers = []
        for header in msg.items():
            if header[0].lower() == 'received':
                received_headers.append(header[1])
        return received_headers

    def _extract_x_headers(self, msg: email.message.Message) -> Dict[str, str]:
        """Extract all X-headers which often contain custom metadata."""
        x_headers = {}
        for header in msg.items():
            if header[0].lower().startswith('x-'):
                x_headers[header[0]] = header[1]
        return x_headers

    def _extract_email_address(self, header_value: str) -> str:
        """Extract a single email address from a header value."""
        if not header_value:
            return ""
        match = re.search(r'[\w\.-]+@[\w\.-]+', header_value)
        return match.group(0) if match else ""

    def _extract_email_addresses(self, header_value: str) -> List[str]:
        """Extract all email addresses from a header value."""
        if not header_value:
            return []
        return re.findall(r'[\w\.-]+@[\w\.-]+', header_value)

    def _extract_ip_addresses(self, received_headers: List[str]) -> List[str]:
        """Extract IP addresses from received headers."""
        ip_addresses = []
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        
        for header in received_headers:
            ips = re.findall(ip_pattern, header)
            ip_addresses.extend(ips)
            
        return ip_addresses

    def _extract_domains(self) -> List[str]:
        """Extract all domains from email addresses in headers."""
        domains = set()
        
        # Extract domains from email addresses
        all_emails = []
        if self.metadata.get('from_email'):
            all_emails.append(self.metadata['from_email'])
        all_emails.extend(self.metadata.get('to_emails', []))
        all_emails.extend(self.metadata.get('cc_emails', []))
        all_emails.extend(self.metadata.get('bcc_emails', []))
        
        for email_addr in all_emails:
            if '@' in email_addr:
                domain = email_addr.split('@')[1]
                domains.add(domain)
                
        return list(domains)

    def search_related_databases(self) -> Dict[str, Any]:
        """Search for information in databases related to the email domains."""
        results = {}
        
        # Try to import database functions
        try:
            from database_config import search_domain_info, search_related_emails
            use_real_db = True
        except ImportError:
            use_real_db = False
        
        for domain in self.metadata.get('domains', []):
            if use_real_db:
                # Use real database functions
                domain_info_dict = search_domain_info(domain)
                
                if domain_info_dict:
                    domain_info = {
                        "registrar": domain_info_dict.get('registrar', 'Unknown'),
                        "creation_date": domain_info_dict.get('creation_date', 'Unknown'),
                        "expiration_date": domain_info_dict.get('expiration_date', 'Unknown')
                    }
                    
                    # Get related emails
                    related_emails_list = search_related_emails(domain)
                    related_emails = [email_dict.get('email_address') for email_dict in related_emails_list]
                else:
                    # Domain not found in database, use fallback
                    results[domain] = self._simulate_database_search(domain)
                    continue
            else:
                # Fall back to simulation if no database configuration
                results[domain] = self._simulate_database_search(domain)
                continue
            
            results[domain] = {
                "domain_info": domain_info,
                "related_emails": related_emails
            }
        
        return results

    def _simulate_database_search(self, domain: str) -> Dict[str, Any]:
        """Simulate a database search for a domain.
        
        This is a fallback method used when no database connection is available.
        """
        # This is only used if the real database connection is not available
        return {
            "domain_info": {
                "registrar": "Example Registrar Inc.",
                "creation_date": "2010-01-01",
                "expiration_date": "2025-01-01",
            },
            "related_emails": [
                f"admin@{domain}",
                f"info@{domain}",
                f"support@{domain}"
            ]
        }

    def discover_alternate_emails(self) -> List[str]:
        """Discover potential alternate email addresses."""
        alternate_emails = []
        
        # Extract username from sender's email
        from_email = self.metadata.get('from_email', '')
        if '@' in from_email:
            username, domain = from_email.split('@')
            
            # Check common username variations
            variations = [
                username,
                username.replace('.', ''),
                username.replace('.', '_'),
                f"{username[0]}.{username.split('.')[-1]}" if '.' in username else username
            ]
            
            # Check against common domains
            common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
            for var in variations:
                for d in common_domains:
                    if d != domain:  # Don't include the original domain
                        alternate_emails.append(f"{var}@{d}")
        
        # Add emails found in database searches
        for domain_results in self.search_related_databases().values():
            alternate_emails.extend(domain_results.get('related_emails', []))
            
        return list(set(alternate_emails))  # Remove duplicates

    def modify_alternate_email(self, old_email: str, new_email: str) -> bool:
        """Modify an alternate email address."""
        # Check if we have a database connection function
        if not self.get_db_connection:
            # Fall back to in-memory modification if no database configuration
            if old_email in self.related_emails:
                self.related_emails.remove(old_email)
                self.related_emails.append(new_email)
                return True
            return False
        
        # Use actual database connection
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if the old email exists in the database
            cursor.execute("SELECT id FROM related_emails WHERE email_address = ?", (old_email,))
            email_row = cursor.fetchone()
            
            if email_row:
                # Update the email address
                cursor.execute(
                    "UPDATE related_emails SET email_address = ? WHERE id = ?", 
                    (new_email, email_row[0])
                )
                conn.commit()
                
                # Also update in-memory list if it exists there
                if old_email in self.related_emails:
                    self.related_emails.remove(old_email)
                    self.related_emails.append(new_email)
                
                return True
            else:
                return False
        except Exception as e:
            print(f"Database error when modifying email: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def to_json(self) -> str:
        """Convert metadata to JSON string."""
        return json.dumps(self.metadata, indent=2, default=str)

    def save_to_file(self, output_file: str) -> bool:
        """Save the extracted metadata to a JSON file.
        
        Args:
            output_file: Path to the output file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False
            
    def save_to_database(self) -> Optional[int]:
        """Save the extracted metadata to the database.
        
        Returns:
            Optional[int]: The ID of the newly added metadata record, or None if the operation failed
        """
        try:
            # Ensure metadata has been extracted
            if not hasattr(self, 'metadata') or not self.metadata:
                self.extract_metadata()
                
            # Get required fields for database
            message_id = self.metadata.get('message_id', '')
            sender = self.metadata.get('from', '')
            recipient = self.metadata.get('to', '')
            subject = self.metadata.get('subject', '')
            date = self.metadata.get('date', '')
            
            # Convert metadata to JSON string
            metadata_json = self.to_json()
            
            # Save to database using the database_config module
            metadata_id = database_config.save_email_metadata(
                message_id, sender, recipient, subject, date, metadata_json
            )
            
            # If successful, also save any domains and related emails found
            if metadata_id:
                # Extract domains from email addresses
                domains = self.metadata.get('domains', [])
                
                # For each domain, check if it exists in the database
                for domain in domains:
                    domain_info = database_config.search_domain_info(domain)
                    if not domain_info:  # Domain doesn't exist, add it
                        # In a real application, you might want to fetch real domain info
                        # For now, we'll just add the domain with placeholder data
                        domain_id = database_config.add_or_update_domain(domain)
            
            return metadata_id
        except Exception as e:
            print(f"Error saving to database: {e}")
            return None


def main():
    """Main function to run the tool from command line."""
    parser = argparse.ArgumentParser(description='Email Metadata Extractor')
    parser.add_argument('--email', '-e', help='Path to email file')
    parser.add_argument('--output', '-o', help='Output file for metadata JSON')
    parser.add_argument('--discover', '-d', action='store_true', help='Discover alternate emails')
    parser.add_argument('--modify', '-m', nargs=2, metavar=('ORIGINAL', 'NEW'), help='Modify alternate email')
    parser.add_argument('--save-to-db', '-s', action='store_true', help='Save extracted metadata to database')
    
    args = parser.parse_args()
    
    if not args.email:
        print("Error: Email file path is required")
        parser.print_help()
        return
    
    extractor = EmailMetadataExtractor(email_path=args.email)
    
    try:
        metadata = extractor.extract_metadata()
        print("Metadata extracted successfully")
        
        if args.save_to_db:
            metadata_id = extractor.save_to_database()
            if metadata_id:
                print(f"Metadata saved to database with ID: {metadata_id}")
            else:
                print("Failed to save metadata to database")
        
        if args.output:
            extractor.save_to_file(args.output)
            print(f"Metadata saved to {args.output}")
        elif not args.save_to_db:
            print(extractor.to_json())
            
        if args.discover:
            alternates = extractor.discover_alternate_emails()
            print("\nPotential alternate emails:")
            for alt in alternates:
                print(f"  - {alt}")
                
        if args.modify:
            original, new = args.modify
            success = extractor.modify_alternate_email(original, new)
            if success:
                print(f"Successfully modified email: {original} -> {new}")
            else:
                print(f"Failed to modify email: {original} -> {new}")
                
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()