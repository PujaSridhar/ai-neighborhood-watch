#!/usr/bin/env python3
"""
Update API Keys Script for AI Neighborhood Watch
This script helps you update your .env file with new API keys.
"""

import os
import sys

def update_api_keys():
    """Interactive script to update API keys."""
    print("🔧 API KEY UPDATE TOOL")
    print("=" * 40)
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Check if .env exists
    if not os.path.exists(env_path):
        print("❌ .env file not found!")
        print("   Run 'python setup.py' first to create it.")
        return False
    
    print(f"📁 Found .env file at: {env_path}")
    
    # Get current keys
    current_gemini = ""
    current_elevenlabs = ""
    
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                current_gemini = line.split('=', 1)[1].strip()
            elif line.startswith('ELEVENLABS_API_KEY='):
                current_elevenlabs = line.split('=', 1)[1].strip()
    
    print(f"\n🔍 CURRENT KEYS:")
    print(f"   Gemini: {current_gemini[:10]}..." if current_gemini else "   Gemini: Not set")
    print(f"   ElevenLabs: {current_elevenlabs[:10]}..." if current_elevenlabs else "   ElevenLabs: Not set")
    
    # Get new keys
    print(f"\n🔑 ENTER NEW API KEYS:")
    
    new_gemini = input("   Gemini API Key (or press Enter to keep current): ").strip()
    if not new_gemini:
        new_gemini = current_gemini
    
    new_elevenlabs = input("   ElevenLabs API Key (or press Enter to keep current): ").strip()
    if not new_elevenlabs:
        new_elevenlabs = current_elevenlabs
    
    # Update the file
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Replace the keys
    lines = content.split('\n')
    updated_lines = []
    
    for line in lines:
        if line.startswith('GEMINI_API_KEY='):
            updated_lines.append(f'GEMINI_API_KEY={new_gemini}')
        elif line.startswith('ELEVENLABS_API_KEY='):
            updated_lines.append(f'ELEVENLABS_API_KEY={new_elevenlabs}')
        else:
            updated_lines.append(line)
    
    # Write back
    with open(env_path, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    print(f"\n✅ Updated .env file!")
    print(f"   New Gemini Key: {new_gemini[:10]}...")
    print(f"   New ElevenLabs Key: {new_elevenlabs[:10]}...")
    
    return True

def main():
    """Main function."""
    try:
        success = update_api_keys()
        if success:
            print(f"\n🎉 SUCCESS!")
            print(f"   Your API keys have been updated.")
            print(f"   Run 'python test_apis.py' to test them.")
            print(f"   Run 'python app.py' to start your app.")
        else:
            print(f"\n❌ FAILED!")
            print(f"   Please check the error messages above.")
    except KeyboardInterrupt:
        print(f"\n\n👋 Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
