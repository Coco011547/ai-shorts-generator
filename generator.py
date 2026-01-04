import os
import sys
# --- FIX FOR PIL ANTIALIAS ERROR ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# -----------------------------------

import requests
import random
import asyncio
import edge_tts
import google.generativeai as genai
from moviepy.editor import *

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

if not GOOGLE_API_KEY or not PEXELS_API_KEY:
    print("❌ ERROR: API Keys are missing in Secrets.")
    sys.exit(1)

genai.configure(api_key=GOOGLE_API_KEY)

def get_script(user_prompt):
    print(f"📝 Generating Script for prompt: {user_prompt}...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # This prompt forces Gemini to follow your exact instruction
        ai_instructions = (
            f"You are a scriptwriter for YouTube Shorts. "
            f"Write a narration script based strictly on this instruction: '{user_prompt}'. "
            "Rules: "
            "1. Do NOT write scene descriptions (like [Camera pans left]). "
            "2. Do NOT write 'Narrator:' or 'Voiceover:'. "
            "3. Write ONLY the raw text to be spoken. "
            "4. Keep it under 50 words."
        )
        
        response = model.generate_content(ai_instructions)
        
        if not response.text:
            return "This is a default script because the AI returned nothing."
            
        # Clean specific formatting that breaks TTS
        clean_text = response.text.replace("*", "").replace("#", "").replace('"', '').strip()
        print(f"✅ Script: {clean_text}")
        return clean_text
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return f"I could not generate a script for {user_prompt} due to an error."

async def get_voice(text):
    print("🎙️ Generating Voice...")
    try:
        # Uses a deep male voice (Christopher)
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save("voice.mp3")
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        sys.exit(1)

def get_video(user_prompt):
    print("🎬 Finding Background Video...")
    headers = {"Authorization": PEXELS_API_KEY}
    
    # Extract a simple keyword for Pexels (search engines hate long sentences)
    # If user types "Scary story about a mirror", we try to search "mirror" or "scary"
    keywords = user_prompt.split()
    search_term = keywords[-1] if len(keywords) > 0 else "nature"
    if len(keywords) > 3:
         # Try to pick a relevant word (simplistic logic)
         search_term = keywords[2] 
    
    url = f"https://api.pexels.com/videos/search?query={search_term}&per_page=5&orientation=portrait"
    
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        
        # Fallback to nature if specific search fails
        if not data.get('videos'):
            print(f"⚠️ No videos found for '{search_term}'. Defaulting to 'Abstract'.")
            url = "https://api.pexels.com/videos/search?query=abstract&per_page=3&orientation=portrait"
            r = requests.get(url, headers=headers)
            data = r.json()

        if data.get('videos'):
            video_url = random.choice(data['videos'])['video_files'][0]['link']
            with open("bg.mp4", "wb") as f:
                f.write(requests.get(video_url).content)
            print("✅ Video downloaded.")
            return True
        else:
            print("❌ No video found.")
            return False
            
    except Exception as e:
        print(f"❌ Pexels Error: {e}")
        return False

def make_short():
    print("⚡ Editing Video...")
    try:
        audio = AudioFileClip("voice.mp3")
        video = VideoFileClip("bg.mp4")

        # Loop video
        if video.duration < audio.duration:
            video = video.loop(duration=audio.duration)
        else:
            video = video.subclip(0, audio.duration)
        
        video = video.set_audio(audio)
        
        # Resize/Crop to 9:16
        video = video.resize(height=1920)
        video = video.crop(x1=0, y1=0, width=1080, height=1920, x_center=1080/2, y_center=1920/2)

        # Write File
        video.write_videofile(
            "final_video.mp4", 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True
        )
        print("✅ SUCCESS! Video Created.")

    except Exception as e:
        print(f"❌ MoviePy Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    prompt = os.environ.get("VIDEO_TOPIC", "Nature")
    
    script = get_script(prompt)
    asyncio.run(get_voice(script))
    
    if get_video(prompt):
        make_short()

