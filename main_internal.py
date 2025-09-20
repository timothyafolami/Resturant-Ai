#!/usr/bin/env python3
"""
Main application for Internal Restaurant Staff Chat
Provides access to employee, recipe, inventory, and menu data for restaurant staff.
"""

import os
import sys
import uuid
import asyncio
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.chat_agents import run_internal_chat_async
from src.utils.app_logging import setup_logger, get_context_logger

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
    ctx_logger = get_context_logger("internal")
    # Example commands to help staff get started
    print("\n💡 Example commands:")
    print("• Show me all employees in the kitchen department")
    print("• What recipes use chicken breast?")
    print("• Check low stock alerts")
    print("• What's on today's menu?")
    print("• Get performance stats for all employees")
    print("• Show me the recipe details for Spaghetti Carbonara")
    print("-"*50)
    
    # Use a unique thread id per CLI session; allows fresh conversation context
    base_thread_id = "internal_staff_session"
    thread_id = f"{base_thread_id}:{uuid.uuid4().hex}"
    
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

            # Log user question
            ctx_logger.info(f"[thread={thread_id}] User: {user_input}")

            # Run internal chat (async)
            response = asyncio.run(run_internal_chat_async(user_input, thread_id))
            # Log assistant response
            ctx_logger.info(f"[thread={thread_id}] Assistant: {response}")

            print(f"\n📊 System Response:\n{response}")
            
            # thread_id is already stable; nothing to do
                
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Have a great day!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"\n❌ Sorry, I encountered an error: {str(e)}")
            print("Please try again with a different question.")


if __name__ == "__main__":
    main()
