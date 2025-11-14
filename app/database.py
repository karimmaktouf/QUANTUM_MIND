"""
Database Management Module for QUANTUM MIND
Handles all SQLite database operations
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'quantum_mind.db')


def get_db_connection():
    """Get database connection"""
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            model TEXT DEFAULT 'gemini-2.5-flash-lite',
            temperature REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES conversations(session_id)
        )
    ''')
    
    # Create statistics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            total_messages INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            response_time_avg REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES conversations(session_id)
        )
    ''')
    
    conn.commit()
    conn.close()


def save_message(session_id, role, content, tokens_used=0):
    """Save a message to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO messages (session_id, role, content, tokens_used)
        VALUES (?, ?, ?, ?)
    ''', (session_id, role, content, tokens_used))
    
    # Update conversation timestamp
    cursor.execute('''
        UPDATE conversations SET updated_at = CURRENT_TIMESTAMP
        WHERE session_id = ?
    ''', (session_id,))
    
    conn.commit()
    conn.close()


def get_conversation_history(session_id):
    """Get all messages for a conversation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT role, content, timestamp FROM messages
        WHERE session_id = ?
        ORDER BY timestamp ASC
    ''', (session_id,))
    
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return messages


def get_all_conversations(user_id):
    """Get all conversations for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, session_id, user_name, model, temperature, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
    ''', (user_id,))
    
    conversations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return conversations


def create_conversation(user_id, user_name, session_id, model='gemini-2.5-flash', temperature=0.5):
    """Create a new conversation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO conversations (user_id, user_name, session_id, model, temperature)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, user_name, session_id, model, temperature))
    
    conn.commit()
    conn.close()


def delete_conversation(session_id):
    """Delete a conversation and all its messages"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
    cursor.execute('DELETE FROM statistics WHERE session_id = ?', (session_id,))
    cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
    
    conn.commit()
    conn.close()


def search_conversations(user_id, query):
    """Search conversations by keyword"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    search_query = f"%{query}%"
    cursor.execute('''
        SELECT DISTINCT c.id, c.session_id, c.user_name, c.model, c.created_at
        FROM conversations c
        LEFT JOIN messages m ON c.session_id = m.session_id
        WHERE c.user_id = ? AND (m.content LIKE ? OR c.user_name LIKE ?)
        ORDER BY c.updated_at DESC
    ''', (user_id, search_query, search_query))
    
    conversations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return conversations


def get_statistics(session_id):
    """Get statistics for a conversation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT role, tokens_used FROM messages WHERE session_id = ?
    ''', (session_id,))
    
    messages = cursor.fetchall()
    
    total_messages = len(messages)
    total_tokens = sum(row[1] for row in messages)
    user_messages = sum(1 for row in messages if row[0] == 'user')
    assistant_messages = sum(1 for row in messages if row[0] == 'assistant')
    
    cursor.execute('''
        SELECT response_time_avg FROM statistics WHERE session_id = ?
    ''', (session_id,))
    
    stat_row = cursor.fetchone()
    response_time = stat_row[0] if stat_row else 0.0
    
    conn.close()
    
    return {
        'total_messages': total_messages,
        'user_messages': user_messages,
        'assistant_messages': assistant_messages,
        'total_tokens': total_tokens,
        'response_time_avg': response_time
    }


def update_conversation_settings(session_id, **kwargs):
    """Update conversation settings (model, temperature)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if 'model' in kwargs:
        updates.append('model = ?')
        values.append(kwargs['model'])
    
    if 'temperature' in kwargs:
        updates.append('temperature = ?')
        values.append(kwargs['temperature'])
    
    if updates:
        updates.append('updated_at = CURRENT_TIMESTAMP')
        values.append(session_id)
        
        query = f"UPDATE conversations SET {', '.join(updates)} WHERE session_id = ?"
        cursor.execute(query, values)
        conn.commit()
    
    conn.close()


def get_conversation_by_id(session_id):
    """Get a specific conversation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM conversations WHERE session_id = ?
    ''', (session_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def toggle_tool(session_id, tool_name, enabled):
    """Toggle tool for a conversation"""
    # Note: This would require a tools table in production
    # For now, storing as metadata in conversation
    pass


def get_enabled_tools(session_id):
    """Get enabled tools for a conversation"""
    # Returns list of enabled tools
    return ['google_search']
