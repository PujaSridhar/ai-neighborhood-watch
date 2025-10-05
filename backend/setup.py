#!/usr/bin/env python3
"""
Setup script for AI Neighborhood Watch Hackathon Project
This script helps you configure the required API keys for Gemini and ElevenLabs.
"""

import os
import sys

def create_env_file():
    """Create a .env file with the required environment variables."""
    env_content = """# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/neighborhood_watch

# AI Configuration - REQUIRED FOR HACKATHON
GEMINI_API_KEY=your_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
"""
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_path):
        print(f"⚠️  .env file already exists at {env_path}")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("❌ Setup cancelled.")
            return False
    
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(f"✅ Created .env file at {env_path}")
        return True
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def print_instructions():
    """Print instructions for getting API keys."""
    print("\n" + "="*60)
    print("🚀 AI NEIGHBORHOOD WATCH - API SETUP INSTRUCTIONS")
    print("="*60)
    
    print("\n📋 REQUIRED API KEYS:")
    print("1. Gemini API Key (Google AI Studio)")
    print("2. ElevenLabs API Key")
    
    print("\n🔑 HOW TO GET YOUR API KEYS:")
    
    print("\n1️⃣ GEMINI API KEY:")
    print("   • Go to: https://aistudio.google.com/app/apikey")
    print("   • Sign in with your Google account")
    print("   • Click 'Create API Key'")
    print("   • Copy the generated key")
    
    print("\n2️⃣ ELEVENLABS API KEY:")
    print("   • Go to: https://elevenlabs.io/app/settings/api-keys")
    print("   • Sign up for a free account")
    print("   • Go to API Keys section")
    print("   • Click 'Create API Key'")
    print("   • Copy the generated key")
    
    print("\n⚙️  NEXT STEPS:")
    print("1. Edit the .env file and replace the placeholder values")
    print("2. Run: python app.py")
    print("3. Test the APIs with the provided endpoints")
    
    print("\n🧪 TESTING ENDPOINTS:")
    print("• POST /api/reports - Create a report (tests Gemini categorization)")
    print("• GET /api/podcast/today - Generate audio podcast (tests both APIs)")
    
    print("\n" + "="*60)

def main():
    """Main setup function."""
    print("🔧 Setting up AI Neighborhood Watch for Hackathon...")
    
    # Create .env file
    if create_env_file():
        print_instructions()
        print("\n✅ Setup complete! Edit your .env file with real API keys.")
    else:
        print("\n❌ Setup failed. Please try again.")

if __name__ == "__main__":
    main()
