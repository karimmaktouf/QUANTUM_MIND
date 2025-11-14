"""
Authentication Module for QUANTUM MIND
Handles user registration, login, and password management
"""

import hashlib
import secrets
import sqlite3

from .database import get_db_connection


def hash_password(password):
    """Hash a password with SHA256"""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${pwdhash.hex()}"


def verify_password(password, password_hash):
    """Verify a password against its hash"""
    try:
        salt, pwdhash = password_hash.split('$')
        
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        
        return new_hash.hex() == pwdhash
    except:
        return False


def create_user(username, password):
    """Create a new user account"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
        ''', (username, password_hash))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return {'success': True, 'user_id': user_id, 'username': username}
    except sqlite3.IntegrityError:
        conn.close()
        return {'success': False, 'error': 'Username already exists'}
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}


def verify_user(username, password):
    """Verify user credentials"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, password_hash FROM users WHERE username = ?
    ''', (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return None
    
    if verify_password(password, user[2]):
        return {'id': user[0], 'username': user[1]}
    
    return None


def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, created_at FROM users WHERE id = ?
    ''', (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def user_exists(username):
    """Check if user exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    
    return exists
