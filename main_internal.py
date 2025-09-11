#!/usr/bin/env python3
"""
Main application for Internal Restaurant Staff Chat
Provides access to employee, recipe, inventory, and menu data for restaurant staff.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.chat_agents import run_internal_chat
from src.logging_config import setup_logger

# Load environment variables
load_dotenv()

logger = setup_logger()


def main():
    """Main internal chat application"""
    print("🏪 Restaurant CRM - Internal Staff Chat")
    print("="*50)
    print("Welcome to the Restaurant Management System!")
    print("Ask questions about employees, recipes, inventory, or menu items.")
    print("Type 'quit', 'exit', or 'bye' to end the session.")
    print("="*50)
    
    # Example commands to help staff get started
    print("\n💡 Example commands:")
    print("• Show me all employees in the kitchen department")
    print("• What recipes use chicken breast?")
    print("• Check low stock alerts")
    print("• What's on today's menu?")
    print("• Get performance stats for all employees")
    print("• Show me the recipe details for Spaghetti Carbonara")
    print("-"*50)
    
    thread_id = None
    
    while True:
        try:
            # Get user input
            user_input = input("\n🧑‍💼 Staff Query: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("\n👋 Thank you for using the Restaurant CRM system!")
                print("Have a great day serving our customers!")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 Processing your request...")
            
            # Run internal chat
            response = run_internal_chat(user_input, thread_id)
            
            print(f"\n📊 System Response:\n{response}")
            
            # Set thread_id for conversation continuity
            if thread_id is None:
                thread_id = "internal_staff_session"
                
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Have a great day!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"\n❌ Sorry, I encountered an error: {str(e)}")
            print("Please try again with a different question.")


if __name__ == "__main__":
    main()
