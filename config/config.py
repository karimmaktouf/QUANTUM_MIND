# Configuration globale de l'application
import os
from datetime import timedelta

class Config:
    """Configuration de base"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', True)
    
    # Google API
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    GOOGLE_GENAI_USE_VERTEXAI = os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'FALSE')
    
    # Base de données
    DB_PATH = os.getenv('DATABASE_PATH', os.path.join(os.path.dirname(__file__), '..', 'data', 'quantum_mind.db'))
    
    # Agent QUANTUM MIND
    AGENT_NAME = 'quantum_mind'
    AGENT_MODEL = os.getenv('DEFAULT_MODEL', 'gemini-2.5-flash')
    AGENT_DESCRIPTION = 'Assistant spécialisé en recherche IA (GitHub, Hugging Face, arXiv, benchmarks).'
    AGENT_INSTRUCTION = 'Tu es QUANTUM MIND, un assistant IA focalisé sur la veille et l’analyse des tendances IA.'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # True en production HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # API
    API_HOST = '127.0.0.1'
    API_PORT = 5000
    API_DEBUG = True
    
    # Limites
    MAX_MESSAGE_LENGTH = 5000
    MAX_CONVERSATION_MESSAGES = 1000
    
    # Modèles disponibles
    AVAILABLE_MODELS = [
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
        'gemini-2.0-flash-exp',
        'gemini-pro',
    ]
    
    # Paramètres par défaut
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TOP_K = 40
    DEFAULT_TOP_P = 0.95

class DevelopmentConfig(Config):
    """Configuration de développement"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuration de production"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    DB_PATH = ':memory:'  # Base de données en mémoire pour les tests

# Sélectionner la configuration
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig
