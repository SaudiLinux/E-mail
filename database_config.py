#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Database Configuration for Email Metadata Extractor

This module provides configuration and utility functions for database connections.
It handles database initialization, connection, and operations for email metadata.
"""

import os
import sqlite3
from typing import Dict, List, Any, Optional, Tuple

# Database configuration
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'email_metadata.db')

def get_db_connection():
    """
    Create and return a connection to the SQLite database.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

def initialize_database():
    """
    Initialize the database with required tables if they don't exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create domains table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS domains (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain_name TEXT UNIQUE NOT NULL,
        registrar TEXT,
        creation_date TEXT,
        expiration_date TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create related_emails table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS related_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain_id INTEGER,
        email_address TEXT UNIQUE NOT NULL,
        description TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (domain_id) REFERENCES domains (id)
    )
    ''')
    
    # Create email_metadata table for storing extracted metadata
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS email_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE,
        sender TEXT,
        recipient TEXT,
        subject TEXT,
        date TEXT,
        metadata_json TEXT,
        processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create some sample data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM domains")
    if cursor.fetchone()[0] == 0:
        # Insert sample domains
        sample_domains = [
            ('gmail.com', 'Google LLC', '1995-08-13', '2030-01-01'),
            ('yahoo.com', 'Yahoo Inc.', '1994-01-18', '2029-01-01'),
            ('hotmail.com', 'Microsoft Corporation', '1996-07-04', '2028-01-01'),
            ('outlook.com', 'Microsoft Corporation', '1997-01-12', '2028-01-01'),
            ('example.com', 'IANA Reserved', '1992-01-01', '2025-01-01')
        ]
        
        for domain in sample_domains:
            cursor.execute(
                "INSERT INTO domains (domain_name, registrar, creation_date, expiration_date) VALUES (?, ?, ?, ?)",
                domain
            )
            
            # Get the domain_id for the inserted domain
            cursor.execute("SELECT id FROM domains WHERE domain_name = ?", (domain[0],))
            domain_id = cursor.fetchone()[0]
            
            # Insert related emails for this domain
            related_emails = [
                (domain_id, f"admin@{domain[0]}", "Administrator"),
                (domain_id, f"info@{domain[0]}", "Information"),
                (domain_id, f"support@{domain[0]}", "Support")
            ]
            
            for email in related_emails:
                cursor.execute(
                    "INSERT INTO related_emails (domain_id, email_address, description) VALUES (?, ?, ?)",
                    email
                )
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DATABASE_PATH}")

def save_email_metadata(message_id: str, sender: str, recipient: str, 
                      subject: str, date: str, metadata_json: str) -> Optional[int]:
    """
    Save extracted email metadata to the database.
    
    Args:
        message_id (str): The email message ID
        sender (str): The email sender
        recipient (str): The email recipient
        subject (str): The email subject
        date (str): The email date
        metadata_json (str): The full metadata as JSON string
    
    Returns:
        Optional[int]: The ID of the newly added metadata record, or None if the operation failed
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """INSERT INTO email_metadata 
               (message_id, sender, recipient, subject, date, metadata_json) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (message_id, sender, recipient, subject, date, metadata_json)
        )
        conn.commit()
        metadata_id = cursor.lastrowid
        return metadata_id
    except sqlite3.IntegrityError:
        # Metadata for this message_id already exists, update it
        cursor.execute(
            """UPDATE email_metadata 
               SET sender=?, recipient=?, subject=?, date=?, metadata_json=?, 
                   processed_date=CURRENT_TIMESTAMP 
               WHERE message_id=?""",
            (sender, recipient, subject, date, metadata_json, message_id)
        )
        conn.commit()
        cursor.execute("SELECT id FROM email_metadata WHERE message_id = ?", (message_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"Error saving email metadata: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def search_domain_info(domain: str) -> Dict[str, Any]:
    """
    Search for information about a domain in the database.
    
    Args:
        domain (str): The domain name to search for
        
    Returns:
        Dict[str, Any]: Information about the domain or empty dict if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM domains WHERE domain_name = ?", 
        (domain,)
    )
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {}


def search_related_emails(domain: str) -> List[Dict[str, Any]]:
    """
    Search for related emails for a domain in the database.
    
    Args:
        domain (str): The domain name to search for related emails
        
    Returns:
        List[Dict[str, Any]]: List of related emails or empty list if none found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT re.* FROM related_emails re 
           JOIN domains d ON re.domain_id = d.id 
           WHERE d.domain_name = ?""", 
        (domain,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def add_or_update_domain(domain: str, registrar: str = "Unknown", 
                        creation_date: str = None, expiration_date: str = None) -> Optional[int]:
    """
    Add a new domain to the database or update if it already exists.
    
    Args:
        domain (str): The domain name to add or update
        registrar (str): The domain registrar
        creation_date (str): The domain creation date
        expiration_date (str): The domain expiration date
        
    Returns:
        Optional[int]: The ID of the domain, or None if the operation failed
    """
    if creation_date is None:
        creation_date = datetime.now().strftime("%Y-%m-%d")
    
    if expiration_date is None:
        # Default expiration to 1 year from now
        expiration_date = (datetime.now().replace(year=datetime.now().year + 1)).strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if domain already exists
        cursor.execute("SELECT id FROM domains WHERE domain_name = ?", (domain,))
        row = cursor.fetchone()
        
        if row:  # Domain exists, update it
            domain_id = row[0]
            cursor.execute(
                """UPDATE domains 
                   SET registrar = ?, creation_date = ?, expiration_date = ? 
                   WHERE id = ?""",
                (registrar, creation_date, expiration_date, domain_id)
            )
        else:  # Domain doesn't exist, insert it
            cursor.execute(
                """INSERT INTO domains 
                   (domain_name, registrar, creation_date, expiration_date) 
                   VALUES (?, ?, ?, ?)""",
                (domain, registrar, creation_date, expiration_date)
            )
            domain_id = cursor.lastrowid
        
        conn.commit()
        return domain_id
    except Exception as e:
        print(f"Error adding or updating domain: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def search_email_metadata(search_term: str, search_type: str) -> List[Dict[str, Any]]:
    """
    Search for email metadata in the database based on search term and type.
    
    Args:
        search_term (str): The term to search for
        search_type (str): The type of search (sender, recipient, subject, message_id)
        
    Returns:
        List[Dict[str, Any]]: List of matching email metadata records
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Validate search_type to prevent SQL injection
    valid_search_types = ['sender', 'recipient', 'subject', 'message_id']
    if search_type not in valid_search_types:
        search_type = 'sender'  # Default to sender if invalid type
    
    # Use parameterized query with LIKE for partial matching
    cursor.execute(
        f"SELECT * FROM email_metadata WHERE {search_type} LIKE ?", 
        (f'%{search_term}%',)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# Initialize the database when this module is imported
if __name__ == "__main__":
    initialize_database()