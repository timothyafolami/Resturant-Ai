#!/usr/bin/env python3
"""
Main application for External Customer Chat
Provides menu information and dining assistance for restaurant customers.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agent.chat_agents import run_external_chat_async
from src.utils.app_logging import setup_logger, get_context_logger

# Load environment variables
load_dotenv()

logger = setup_logger()


def main():
    """Main external customer chat application"""
    print("🍽️ Welcome to Our Restaurant!")
    print("="*50)
    print("Hello! I'm your AI dining assistant, here to help you")
    print("explore our delicious menu and find the perfect meal!")
    print("Type 'quit', 'exit', or 'bye' to end our conversation.")
    print("="*50)
    ctx_logger = get_context_logger("external")
    # Example commands to help customers get started
    print("\n💡 Try asking me about:")
    print("• What's on the menu today?")
    print("• Do you have any vegetarian options?")
    print("• Tell me about your pasta dishes")
    print("• What would you recommend for someone who likes spicy food?")
    print("• Show me desserts under $15")
    print("• What are your chef's recommendations?")
    print("-"*50)
    
    # Use a stable thread id for conversational memory
    thread_id = "customer_session"
    
    while True:
        try:
            # Get user input
            user_input = input("\n🙋 Customer: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("\n👋 Thank you for visiting our restaurant!")
                print("We hope to serve you delicious food soon! 🍽️✨")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 Let me help you with that...")

            # Log user question
            ctx_logger.info(f"[thread={thread_id}] User: {user_input}")

            # Run external customer chat (async)
            response = asyncio.run(run_external_chat_async(user_input, thread_id))
            # Log assistant response
            ctx_logger.info(f"[thread={thread_id}] Assistant: {response}")

            print(f"\n🍽️ Restaurant Assistant:\n{response}")
            
            # thread_id is already stable; nothing to do
                
        except KeyboardInterrupt:
            print("\n\n👋 Thank you for your interest! Hope to see you soon!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"\n❌ Sorry, I encountered an issue: {str(e)}")
            print("Please try asking something else, and I'll do my best to help!")


if __name__ == "__main__":
    main()
