"""
Flask Routes and API Endpoints for QUANTUM MIND
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta, timezone
import uuid
import os

from .database import (
    init_database, create_conversation, save_message, get_conversation_history,
    get_all_conversations, delete_conversation, search_conversations, get_statistics,
    get_conversation_by_id, update_conversation_settings
)
from .auth import create_user, verify_user, get_user_by_id
from .utils import (
    export_to_markdown, export_to_json, export_to_pdf,
    format_tokens, truncate_text, validate_username, validate_password
)
from .agent import get_agent

# Create blueprint
api = Blueprint('api', __name__, url_prefix='/api')


# Initialize database on first run
init_database()


def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ==================== Authentication Routes ====================

@api.route('/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user_id': session.get('user_id'),
            'username': session.get('username')
        }), 200
    else:
        return jsonify({
            'authenticated': False
        }), 200


@api.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    # Validate inputs
    valid_user, error_msg = validate_username(data['username'])
    if not valid_user:
        return jsonify({'error': error_msg}), 400
    
    valid_pass, error_msg = validate_password(data['password'])
    if not valid_pass:
        return jsonify({'error': error_msg}), 400
    
    # Create user
    result = create_user(data['username'], data['password'])
    
    if result['success']:
        return jsonify({
            'message': 'User created successfully',
            'user_id': result['user_id']
        }), 201
    else:
        return jsonify({'error': result['error']}), 400


@api.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    user = verify_user(data['username'], data['password'])
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session.permanent = True
        
        return jsonify({
            'message': 'Logged in successfully',
            'user_id': user['id'],
            'username': user['username']
        }), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401


@api.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200


@api.route('/user', methods=['GET'])
@login_required
def get_user():
    """Get current user info"""
    user = get_user_by_id(session['user_id'])
    
    if user:
        return jsonify(user), 200
    else:
        return jsonify({'error': 'User not found'}), 404


# ==================== Conversation Routes ====================

@api.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for current user"""
    conversations = get_all_conversations(session['user_id'])
    
    return jsonify({
        'conversations': conversations,
        'count': len(conversations)
    }), 200


@api.route('/conversations', methods=['POST'])
@login_required
def new_conversation():
    """Create a new conversation"""
    data = request.get_json()
    
    session_id = str(uuid.uuid4())
    model = data.get('model', 'gemini-2.5-flash-lite')
    temperature = float(data.get('temperature', 0.5))
    
    create_conversation(
        session['user_id'],
        session['username'],
        session_id,
        model,
        temperature
    )
    
    return jsonify({
        'message': 'Conversation created',
        'session_id': session_id,
        'model': model,
        'temperature': temperature
    }), 201


@api.route('/history/<session_id>', methods=['GET'])
@login_required
def get_history(session_id):
    """Get conversation history"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    history = get_conversation_history(session_id)
    stats = get_statistics(session_id)
    
    return jsonify({
        'session_id': session_id,
        'messages': history,
        'statistics': stats,
        'model': conversation['model'],
        'temperature': conversation['temperature']
    }), 200


@api.route('/chat/<session_id>', methods=['POST'])
@login_required
def chat(session_id):
    """Send a message and get response"""
    data = request.get_json()
    
    if not data.get('message'):
        return jsonify({'error': 'Message required'}), 400
    
    # Verify conversation belongs to user
    conversation = get_conversation_by_id(session_id)
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Save user message
    user_tokens = len(data['message'].split())
    save_message(session_id, 'user', data['message'], tokens_used=user_tokens)
    
    # Generate assistant response using agent
    agent = get_agent(model=conversation['model'])
    agent.set_model(conversation['model'])
    agent.set_temperature(conversation['temperature'])
    
    history = get_conversation_history(session_id)
    response = agent.chat(history, session_id=session_id)
    
    if response.get('error') and not response.get('content'):
        return jsonify({'error': response['error']}), 500
    
    content = response.get('content', 'Je ne peux pas répondre pour le moment, veuillez réessayer plus tard.')
    tokens_used = response.get('tokens_used', len(content.split()))
    
    save_message(session_id, 'assistant', content, tokens_used=tokens_used)
    
    return jsonify({
        'message': content,
        'tokens_used': tokens_used
    }), 200


@api.route('/mt-bench/refresh', methods=['POST'])
@login_required
def refresh_mt_bench():
    """Force refresh of cached MT-Bench data."""
    agent = get_agent()
    try:
        result = agent.refresh_mt_bench_cache(force=True)
        return jsonify({
            'message': 'MT-Bench data refreshed',
            'updated_at': result.get('updated_at'),
            'count': result.get('count', 0),
        }), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({'error': f'Impossible de rafraîchir: {exc}'}), 500


@api.route('/mt-bench/local-mirror', methods=['GET'])
def mt_bench_local_mirror():
    """Expose curated MT-Bench data via HTTP to bypass DNS restrictions."""
    agent = get_agent()
    timestamp = datetime.now(timezone.utc).isoformat()
    models = []

    for entry in agent.CURATED_MT_BENCH:
        raw_link = entry.get('link') or ''
        slug = None
        if 'model=' in raw_link:
            slug = raw_link.split('model=', 1)[1]
        if not slug:
            slug = agent._normalize_for_matching(entry.get('model', 'model')).replace(' ', '-')

        models.append({
            'model': slug,
            'display_name': entry.get('model'),
            'benchmarks': {
                'mt_bench': {
                    'score': entry.get('mt_bench'),
                    'updated_at': entry.get('date'),
                },
                'mmlu': {
                    'score': entry.get('mmlu'),
                    'updated_at': entry.get('date'),
                },
            },
            'last_updated': entry.get('date'),
            'link': raw_link or None,
            'size': entry.get('size'),
        })

    return jsonify({
        'source': 'local_curated_snapshot',
        'updated_at': timestamp,
        'models': models,
    })


@api.route('/delete/<session_id>', methods=['DELETE'])
@login_required
def delete_conv(session_id):
    """Delete a conversation"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    delete_conversation(session_id)
    
    return jsonify({'message': 'Conversation deleted'}), 200


@api.route('/search', methods=['GET'])
@login_required
def search():
    """Search conversations"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Search query required'}), 400
    
    results = search_conversations(session['user_id'], query)
    
    return jsonify({
        'results': results,
        'count': len(results)
    }), 200


# ==================== Settings Routes ====================

@api.route('/settings/<session_id>', methods=['GET'])
@login_required
def get_settings(session_id):
    """Get conversation settings"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    return jsonify({
        'model': conversation['model'],
        'temperature': conversation['temperature']
    }), 200


@api.route('/settings/<session_id>', methods=['PUT'])
@login_required
def update_settings(session_id):
    """Update conversation settings"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    data = request.get_json()
    
    update_conversation_settings(session_id, **data)
    
    return jsonify({
        'message': 'Settings updated',
        'model': data.get('model'),
        'temperature': data.get('temperature')
    }), 200


# ==================== Statistics Routes ====================

@api.route('/statistics/<session_id>', methods=['GET'])
@login_required
def get_stats(session_id):
    """Get conversation statistics"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    stats = get_statistics(session_id)
    
    return jsonify(stats), 200


# ==================== Export Routes ====================

@api.route('/export/<session_id>/<format>', methods=['GET'])
@login_required
def export(session_id, format):
    """Export conversation"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    history = get_conversation_history(session_id)
    
    if format == 'markdown':
        content = export_to_markdown(session_id, session['username'], history)
        return content, 200, {'Content-Type': 'text/markdown'}
    
    elif format == 'json':
        content = export_to_json(session_id, session['username'], history)
        return content, 200, {'Content-Type': 'application/json'}
    
    elif format == 'pdf':
        content = export_to_pdf(session_id, session['username'], history)
        if content:
            return content.getvalue(), 200, {'Content-Type': 'application/pdf'}
        else:
            return jsonify({'error': 'PDF export not available'}), 400
    
    else:
        return jsonify({'error': 'Invalid format'}), 400


# ==================== Tools Routes ====================

@api.route('/tools/<session_id>', methods=['GET'])
@login_required
def get_tools(session_id):
    """Get enabled tools for conversation"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    agent = get_agent()
    tools = agent.get_tools()
    
    return jsonify({'tools': tools}), 200


@api.route('/tools/<session_id>/<tool_name>', methods=['PUT'])
@login_required
def update_tool(session_id, tool_name):
    """Enable/disable a tool"""
    conversation = get_conversation_by_id(session_id)
    
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({'error': 'Conversation not found'}), 404
    
    data = request.get_json()
    enabled = data.get('enabled', False)
    
    agent = get_agent()
    agent.toggle_tool(tool_name, enabled)
    
    return jsonify({
        'message': f'Tool {tool_name} updated',
        'enabled': enabled
    }), 200


def register_routes(app):
    """Register all routes with Flask app"""
    app.register_blueprint(api)
