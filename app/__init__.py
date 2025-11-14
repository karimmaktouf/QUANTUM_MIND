"""
QUANTUM MIND Application
AI Research Assistant
"""

__version__ = '1.0.0'
__author__ = 'QUANTUM MIND Team'
__description__ = 'Advanced AI Research Assistant powered by Google Gemini'

from flask import Flask, render_template
from flask_cors import CORS

def create_app(config=None):
    """Factory function pour créer l'application Flask"""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Configuration
    if config:
        app.config.from_object(config)
    else:
        from config import get_config  # type: ignore[import]
        app.config.from_object(get_config())
    
    # Session configuration
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 604800  # 7 days
    app.config['SESSION_COOKIE_SECURE'] = False  # True only in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # CORS
    CORS(app)
    
    # Serve main page
    @app.route('/')
    def index():
        """Serve the main application page"""
        return render_template('index.html')
    
    # Enregistrer les blueprints (routes)
    # from app.routes import api_bp
    # app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
