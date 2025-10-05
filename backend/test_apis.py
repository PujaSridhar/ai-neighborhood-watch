#!/usr/bin/env python3
"""
Test script to verify Gemini and ElevenLabs API keys work correctly.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test Gemini API with the provided key."""
    print("🧪 Testing Gemini API...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No GEMINI_API_KEY found in environment")
        return False
    
    print(f"✅ Found API key: {api_key[:10]}...")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # First, let's list available models
        print("   Listing available models...")
        try:
            models = genai.list_models()
            model_list = list(models)
            print(f"   Found {len(model_list)} models")
            available_models = []
            for model in model_list:
                if 'generateContent' in model.supported_generation_methods:
                    available_models.append(model.name)
                    print(f"   ✅ Available: {model.name}")
            
            # Try the first available model
            if available_models:
                test_model = available_models[0]
                print(f"   Testing first available model: {test_model}")
                model = genai.GenerativeModel(test_model)
                response = model.generate_content("Say 'Hello' in one word")
                print(f"   ✅ {test_model} works! Response: {response.text}")
                return True
        except Exception as e:
            print(f"   Could not list models: {e}")
        
        # Try different model names
        models_to_try = ['text-bison-001', 'text-bison-002', 'gemini-pro', 'gemini-pro-vision']
        
        for model_name in models_to_try:
            try:
                print(f"   Testing model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Say 'Hello' in one word")
                print(f"   ✅ {model_name} works! Response: {response.text}")
                return True
            except Exception as e:
                print(f"   ❌ {model_name} failed: {str(e)[:100]}...")
                continue
        
        print("❌ All Gemini models failed")
        return False
        
    except Exception as e:
        print(f"❌ Gemini API setup failed: {e}")
        return False

def test_elevenlabs_api():
    """Test ElevenLabs API with the provided key."""
    print("\n🧪 Testing ElevenLabs API...")
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ No ELEVENLABS_API_KEY found in environment")
        return False
    
    print(f"✅ Found API key: {api_key[:10]}...")
    
    try:
        from elevenlabs.client import ElevenLabs
        
        client = ElevenLabs(api_key=api_key)
        
        # Test with a simple text
        print("   Testing text-to-speech generation...")
        audio = client.text_to_speech.convert(
            text="Hello, this is a test.",
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice ID
            model_id="eleven_multilingual_v2"
        )
        
        # Convert generator to bytes to check if it works
        audio_bytes = b''.join(audio)
        if audio_bytes:
            print(f"   ✅ ElevenLabs works! Generated {len(audio_bytes)} bytes of audio")
            return True
        else:
            print("   ❌ ElevenLabs returned no audio")
            return False
            
    except Exception as e:
        print(f"❌ ElevenLabs API failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔧 API Key Testing for AI Neighborhood Watch")
    print("=" * 50)
    
    gemini_works = test_gemini_api()
    elevenlabs_works = test_elevenlabs_api()
    
    print("\n" + "=" * 50)
    print("📊 RESULTS:")
    print(f"Gemini API: {'✅ Working' if gemini_works else '❌ Failed'}")
    print(f"ElevenLabs API: {'✅ Working' if elevenlabs_works else '❌ Failed'}")
    
    if gemini_works and elevenlabs_works:
        print("\n🎉 Both APIs are working! Your hackathon setup is ready!")
    else:
        print("\n⚠️  Some APIs are not working. Check your API keys.")

if __name__ == "__main__":
    main()
