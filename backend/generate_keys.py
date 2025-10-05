#!/usr/bin/env python3
"""
API Key Generation Guide for AI Neighborhood Watch Hackathon
This script provides step-by-step instructions for generating new API keys.
"""

import webbrowser
import os

def open_gemini_api():
    """Open Gemini API key generation page."""
    url = "https://aistudio.google.com/app/apikey"
    print("🔑 Opening Gemini API Key Generation...")
    print(f"   URL: {url}")
    try:
        webbrowser.open(url)
        print("   ✅ Browser opened!")
    except:
        print("   ⚠️  Could not open browser automatically")
    print("\n📋 GEMINI API KEY STEPS:")
    print("   1. Sign in with your Google account")
    print("   2. Click 'Create API Key'")
    print("   3. Choose 'Create API key in new project' (recommended)")
    print("   4. Copy the generated API key")
    print("   5. Paste it below when prompted")

def open_elevenlabs_api():
    """Open ElevenLabs API key generation page."""
    url = "https://elevenlabs.io/app/settings/api-keys"
    print("\n🔑 Opening ElevenLabs API Key Generation...")
    print(f"   URL: {url}")
    try:
        webbrowser.open(url)
        print("   ✅ Browser opened!")
    except:
        print("   ⚠️  Could not open browser automatically")
    print("\n📋 ELEVENLABS API KEY STEPS:")
    print("   1. Sign up for a free ElevenLabs account")
    print("   2. Go to Settings > API Keys")
    print("   3. Click 'Create API Key'")
    print("   4. Give it a name (e.g., 'Hackathon Project')")
    print("   5. Make sure 'Text to Speech' permission is enabled")
    print("   6. Copy the generated API key")
    print("   7. Paste it below when prompted")

def update_env_file(gemini_key, elevenlabs_key):
    """Update the .env file with new API keys."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Read current .env file
    env_content = ""
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_content = f.read()
    
    # Update the API keys
    lines = env_content.split('\n')
    updated_lines = []
    
    for line in lines:
        if line.startswith('GEMINI_API_KEY='):
            updated_lines.append(f'GEMINI_API_KEY={gemini_key}')
        elif line.startswith('ELEVENLABS_API_KEY='):
            updated_lines.append(f'ELEVENLABS_API_KEY={elevenlabs_key}')
        else:
            updated_lines.append(line)
    
    # Write updated content
    with open(env_path, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    print(f"✅ Updated .env file at {env_path}")

def main():
    """Main function to guide API key generation."""
    print("🚀 AI NEIGHBORHOOD WATCH - API KEY GENERATION")
    print("=" * 60)
    
    print("\n🎯 CURRENT STATUS:")
    print("✅ Gemini API: Working (quota reset)")
    print("❌ ElevenLabs API: Missing text_to_speech permission")
    
    print("\n🔧 SOLUTION: Generate new API keys with proper permissions")
    
    # Open API key generation pages
    open_gemini_api()
    open_elevenlabs_api()
    
    print("\n" + "=" * 60)
    print("📝 NEXT STEPS:")
    print("1. Generate both API keys using the opened browser tabs")
    print("2. Run: python update_keys.py")
    print("3. Test with: python test_apis.py")
    print("4. Start your app: python app.py")
    
    print("\n🎉 Your hackathon project will be fully functional!")

if __name__ == "__main__":
    main()
