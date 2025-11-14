"""
QUANTUM MIND - Main Application Entry Point
Run this file to start the application
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  Warning: .env file not found. Copy .env.example to .env and configure.")

from app import create_app
from app.agent import start_mt_bench_scheduler
from app.database import init_database  # type: ignore[import]
from config import get_config  # type: ignore[import]


def main():
    """Main entry point"""
    
    # Get configuration based on environment
    env = os.getenv('FLASK_ENV', 'development')
    config = get_config()
    
    # Initialize database
    print("🔄 Initializing database...")
    init_database()
    print("✅ Database initialized")
    
    # Create Flask app
    print("🚀 Creating Flask app...")
    app = create_app(config)
    print("✅ Flask app created")
    
    # Register routes
    from app.routes import register_routes
    register_routes(app)
    print("✅ Routes registered")

    # Get server configuration early so we know runtime context
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = env == 'development'

    scheduler_thread = None
    should_start_scheduler = (not debug) or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    if should_start_scheduler:
        interval_env = os.getenv('MT_BENCH_REFRESH_INTERVAL')
        interval_value = None
        if interval_env:
            try:
                interval_value = int(interval_env)
            except ValueError:
                print("⚠️  MT_BENCH_REFRESH_INTERVAL invalide, utilisation de la valeur par défaut (14400s)")
        scheduler_thread = start_mt_bench_scheduler(interval_value)
        if scheduler_thread:
            print("⏱️  MT-Bench auto-refresh démarré")
        else:
            print("⚠️  MT-Bench auto-refresh désactivé (intervalle <= 0)")
    
    # Print startup info
    print("\n" + "="*60)
    print("🧠 QUANTUM MIND v1.0 - AI Research Assistant")
    print("="*60)
    print(f"Environment: {env}")
    print(f"Server: http://{host}:{port}")
    print(f"Debug: {debug}")
    print(f"Model: {os.getenv('DEFAULT_MODEL', 'gemini-2.5-flash')}")
    print(f"Database: {os.getenv('DATABASE_PATH', 'data/quantum_mind.db')}")
    print("="*60)
    print("\n🎯 Spécialisation: Recherche IA (6 outils + 1 unique)")
    print("🔥 Outil unique: ai_research_trends (GitHub + PWC + arXiv)")
    print("\n🌐 Opening browser at http://localhost:5000\n")
    
    # Start the Flask development server
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
