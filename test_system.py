#!/usr/bin/env python3
"""
Test script for Restaurant CRM Chat Applications
Quick verification that all components are working correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.chat_agents import run_internal_chat, run_external_chat
from src.db_models.database import SessionLocal, EmployeeTable, StorageItemTable, RecipeTable, DailyMenuTable
from src.utils.logging import setup_logger

# Load environment variables
load_dotenv()

logger = setup_logger()


def test_database_connection():
    """Test database connectivity and data presence"""
    print("🗄️ Testing database connection...")
    
    try:
        db = SessionLocal()
        
        # Count records in each table
        employee_count = db.query(EmployeeTable).count()
        storage_count = db.query(StorageItemTable).count()
        recipe_count = db.query(RecipeTable).count()
        menu_count = db.query(DailyMenuTable).count()
        
        db.close()
        
        print(f"✅ Database connected successfully!")
        print(f"   📊 Records found:")
        print(f"   • Employees: {employee_count}")
        print(f"   • Storage Items: {storage_count}")
        print(f"   • Recipes: {recipe_count}")
        print(f"   • Daily Menus: {menu_count}")
        
        if all([employee_count, storage_count, recipe_count, menu_count]):
            return True
        else:
            print("⚠️ Some tables appear to be empty. Run setup.py to populate data.")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False


def test_internal_chat():
    """Test internal staff chat functionality"""
    print("\n🏪 Testing internal staff chat...")
    
    test_queries = [
        "How many employees do we have?",
        "Show me low stock alerts",
        "What recipes use chicken?"
    ]
    
    for query in test_queries:
        try:
            print(f"\n📝 Query: {query}")
            response = run_internal_chat(query, "test_internal")
            print(f"✅ Response received (length: {len(response)} chars)")
            
            # Show first 100 characters of response
            preview = response[:100] + "..." if len(response) > 100 else response
            print(f"📄 Preview: {preview}")
            
        except Exception as e:
            print(f"❌ Internal chat error: {str(e)}")
            return False
    
    return True


def test_external_chat():
    """Test external customer chat functionality"""
    print("\n🍽️ Testing customer chat...")
    
    test_queries = [
        "What's on the menu today?",
        "Do you have vegetarian options?",
        "Tell me about your desserts"
    ]
    
    for query in test_queries:
        try:
            print(f"\n📝 Query: {query}")
            response = run_external_chat(query, "test_external")
            print(f"✅ Response received (length: {len(response)} chars)")
            
            # Show first 100 characters of response
            preview = response[:100] + "..." if len(response) > 100 else response
            print(f"📄 Preview: {preview}")
            
        except Exception as e:
            print(f"❌ External chat error: {str(e)}")
            return False
    
    return True


def main():
    """Run all tests"""
    print("🧪 Restaurant CRM System Test")
    print("="*50)
    
    # Test database
    db_ok = test_database_connection()
    if not db_ok:
        print("\n❌ Database tests failed. Please run setup.py first.")
        return
    
    # Test internal chat
    internal_ok = test_internal_chat()
    
    # Test external chat
    external_ok = test_external_chat()
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    print(f"🗄️ Database: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"🏪 Internal Chat: {'✅ PASS' if internal_ok else '❌ FAIL'}")
    print(f"🍽️ Customer Chat: {'✅ PASS' if external_ok else '❌ FAIL'}")
    
    if all([db_ok, internal_ok, external_ok]):
        print("\n🎉 All tests passed! System is ready to use.")
        print("\n📋 Next steps:")
        print("• Run 'python main_internal.py' for staff chat")
        print("• Run 'python main_external.py' for customer chat")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
    
    print("="*50)


if __name__ == "__main__":
    main()
