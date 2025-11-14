"""
Utility Functions Module for QUANTUM MIND
Handles exports, formatting, and other utilities
"""

import json
import re

try:
    import markdown
except ImportError:  # pragma: no cover - optional dependency
    markdown = None
from io import BytesIO
from datetime import datetime
from .database import get_statistics, get_conversation_history

try:
    from reportlab.lib.pagesizes import letter, A4  # type: ignore[import]
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore[import]
    from reportlab.lib.units import inch  # type: ignore[import]
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle  # type: ignore[import]
    from reportlab.lib import colors  # type: ignore[import]
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def export_to_markdown(session_id, user_name, conversation_data):
    """Export conversation to Markdown format"""
    
    stats = get_statistics(session_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md_content = f"""# Conversation - QUANTUM MIND

**Exported by:** {user_name}  
**Exported on:** {now}

## 📊 Conversation Statistics

- **Total Messages:** {stats['total_messages']}
- **User Messages:** {stats['user_messages']}
- **Agent Responses:** {stats['assistant_messages']}
- **Total Tokens Used:** {stats['total_tokens']}
- **Average Response Time:** {stats['response_time_avg']:.2f}s

---

## 💬 Conversation History

"""
    
    for message in conversation_data:
        role = "👤 **You**" if message['role'] == 'user' else "🤖 **Agent**"
        content = message['content']
        timestamp = message.get('timestamp', 'N/A')
        
        md_content += f"\n### {role}\n\n"
        md_content += f"{content}\n\n"
        md_content += f"*{timestamp}*\n\n"
        md_content += "---\n"
    
    return md_content


def export_to_json(session_id, user_name, conversation_data):
    """Export conversation to JSON format"""
    
    stats = get_statistics(session_id)
    
    export_data = {
        'metadata': {
            'session_id': session_id,
            'user_name': user_name,
            'exported_at': datetime.now().isoformat(),
            'statistics': stats
        },
        'messages': conversation_data
    }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def export_to_pdf(session_id, user_name, conversation_data):
    """Export conversation to PDF format"""
    
    if not REPORTLAB_AVAILABLE:
        return None
    
    stats = get_statistics(session_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0ea5e9'),
        spaceAfter=30
    )
    
    # Title
    story.append(Paragraph("QUANTUM MIND - Conversation Export", title_style))
    story.append(Spacer(1, 12))
    
    # Metadata
    story.append(Paragraph(f"<b>Exported by:</b> {user_name}", styles['Normal']))
    story.append(Paragraph(f"<b>Exported on:</b> {now}", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Statistics
    story.append(Paragraph("<b>Conversation Statistics</b>", styles['Heading2']))
    stats_data = [
        ['Metric', 'Value'],
        ['Total Messages', str(stats['total_messages'])],
        ['User Messages', str(stats['user_messages'])],
        ['Agent Responses', str(stats['assistant_messages'])],
        ['Total Tokens', str(stats['total_tokens'])],
        ['Avg Response Time', f"{stats['response_time_avg']:.2f}s"]
    ]
    
    stats_table = Table(stats_data)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0ea5e9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(stats_table)
    story.append(Spacer(1, 20))
    
    # Conversation
    story.append(Paragraph("<b>Conversation History</b>", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    for i, message in enumerate(conversation_data):
        role = "👤 User" if message['role'] == 'user' else "🤖 Agent"
        timestamp = message.get('timestamp', 'N/A')
        content = message['content']
        
        story.append(Paragraph(f"<b>{role}</b> - {timestamp}", styles['Normal']))
        story.append(Paragraph(content, styles['BodyText']))
        story.append(Spacer(1, 12))
        
        if (i + 1) % 5 == 0:  # Page break every 5 messages
            story.append(PageBreak())
    
    doc.build(story)
    buffer.seek(0)
    
    return buffer


def format_message_for_display(content, role='user'):
    """Format message for web display"""
    
    formatted = content
    
    # Convert markdown to HTML if needed
    if markdown and ('```' in formatted or '#' in formatted):
        try:
            formatted = markdown.markdown(formatted, extensions=['extra', 'codehilite'])
        except Exception:
            pass
    
    return {
        'content': formatted,
        'role': role,
        'timestamp': datetime.now().isoformat()
    }


def truncate_text(text, max_length=100):
    """Truncate text with ellipsis"""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def format_tokens(tokens):
    """Format token count for display"""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def validate_username(username):
    """Validate username format"""
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 50:
        return False, "Username must be at most 50 characters"
    # Allow letters, numbers, underscores, hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores and hyphens"
    return True, None


def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 100:
        return False, "Password must be at most 100 characters"
    return True, None
