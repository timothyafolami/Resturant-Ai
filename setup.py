#!/usr/bin/env python3
"""
Setup script for Restaurant CRM Chat Applications
Handles database creation and initial data population.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.db_models.database import create_tables, drop_tables
from src.utils.data_generator import populate_database
from src.utils.app_logging import setup_logger

logger = setup_logger()


def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "GROQ_API_KEY", 
        "DATABASE_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\nPlease create a .env file with these variables.")
        print("See .env.example for the required format.")
        return False
    
    return True


def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing required dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_database():
    """Create database tables"""
    print("🗄️ Setting up database tables...")
    try:
        create_tables()
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create database tables: {e}")
        return False


def populate_sample_data():
    """Populate database with sample data"""
    print("📊 Populating database with sample data...")
    try:
        populate_database()
        print("✅ Sample data populated successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to populate sample data: {e}")
        return False


def create_env_example():
    """Create example environment file"""
    env_example_content = """# Restaurant CRM Environment Configuration

# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama3-groq-70b-8192-tool-use-preview

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/restaurant_crm

# Optional: Langsmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=restaurant-crm
"""
    
    with open(".env.example", "w") as f:
        f.write(env_example_content)
    
    print("✅ Created .env.example file")


def main():
    """Main setup function"""
    print("🚀 Restaurant CRM Setup")
    print("="*50)
    
    # Create example env file
    create_env_example()
    
    # Check environment
    if not check_environment():
        print("\n⚠️ Setup incomplete. Please configure environment variables and run setup again.")
        return
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed during dependency installation.")
        return
    
    # Setup database
    if not setup_database():
        print("\n❌ Setup failed during database creation.")
        return
    
    # Populate sample data
    user_input = input("\n❓ Would you like to populate the database with sample data? (y/N): ").strip().lower()
    if user_input in ['y', 'yes']:
        if not populate_sample_data():
            print("\n❌ Setup failed during data population.")
            return
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run internal staff chat: python main_internal.py")
    print("2. Run customer chat: python main_external.py")
    print("\n💡 Make sure your PostgreSQL database is running and accessible.")


if __name__ == "__main__":
    main()
