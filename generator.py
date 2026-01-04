import PIL.Image

# FIX FOR PIL ANTIALIAS ERROR
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import os
# ... rest of your imports ...

import os
import sys
import requests
import random
import asyncio
import edge_tts
import google.generativeai as genai
from moviepy.editor import *

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# Check for keys immediately
if not GOOGLE_API_KEY:
    print("❌ ERROR: GOOGLE_API_KEY is missing in Secrets.")
    sys.exit(1)
if not PEXELS_API_KEY:
    print("❌ ERROR: PEXELS_API_KEY is missing in Secrets.")
    sys.exit(1)

genai.configure(api_key=GOOGLE_API_KEY)

def get_script(topic):
    print(f"📝 Generative Script for: {topic}...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # We ask for something very safe to avoid filters
        prompt = (
            f"Write a 2 sentence fun fact about {topic}. "
            "Plain text only. No formatting. No intro."
        )
        response = model.generate_content(prompt)
        
        if not response.text:
            print("⚠️ Gemini returned empty text. Using fallback.")
            return "Did you know this topic is fascinating? There is so much to learn about it."
            
        clean_text = response.text.replace("*", "").replace("#", "").strip()
        print(f"✅ Script: {clean_text}")
        return clean_text
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return "Here is a cool fact. Science is amazing and the world is full of wonders."

async def get_voice(text):
    print("🎙️ Generating Voice...")
    try:
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save("voice.mp3")
        # Verify file exists
        if os.path.exists("voice.mp3") and os.path.getsize("voice.mp3") > 0:
            print("✅ Voice generated successfully.")
        else:
            print("❌ Voice file is empty!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        sys.exit(1)

def get_video(topic):
    print("🎬 Downloading Background Video...")
    headers = {"Authorization": PEXELS_API_KEY}
    # Broader search term to ensure results
    search_term = topic.split()[0] if " " in topic else topic
    url = f"https://api.pexels.com/videos/search?query={search_term}&per_page=5&orientation=portrait"
    
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        
        if not data.get('videos'):
            print("⚠️ No videos found. Trying 'nature' fallback.")
            # Fallback to nature if specific topic fails
            url = "https://api.pexels.com/videos/search?query=nature&per_page=3&orientation=portrait"
            r = requests.get(url, headers=headers)
            data = r.json()

        if data.get('videos'):
            video_url = random.choice(data['videos'])['video_files'][0]['link']
            with open("bg.mp4", "wb") as f:
                f.write(requests.get(video_url).content)
            print("✅ Video downloaded.")
            return True
        else:
            print("❌ No video could be found at all.")
            return False
            
    except Exception as e:
        print(f"❌ Pexels Error: {e}")
        return False

def make_short():
    print("⚡ Editing Video...")
    try:
        if not os.path.exists("voice.mp3"):
            print("❌ Missing voice.mp3")
            sys.exit(1)
            
        audio = AudioFileClip("voice.mp3")
        video = VideoFileClip("bg.mp4")

        # 1. Loop video
        if video.duration < audio.duration:
            video = video.loop(duration=audio.duration)
        else:
            video = video.subclip(0, audio.duration)
        
        # 2. Add Audio
        video = video.set_audio(audio)
        
        # 3. Resize (Safe Crop)
        # Resize height to 1920 first, keeping aspect ratio
        video = video.resize(height=1920)
        # Crop the center 1080
        video = video.crop(x1=0, y1=0, width=1080, height=1920, x_center=1080/2, y_center=1920/2)

        # 4. Write File (With explicit Codecs for GitHub compatibility)
        video.write_videofile(
            "final_video.mp4", 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True
        )
        
        if os.path.exists("final_video.mp4"):
            print("✅ SUCCESS: final_video.mp4 created!")
        else:
            print("❌ Write finished but file is missing.")
            sys.exit(1)

    except Exception as e:
        print(f"❌ MoviePy Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    topic = os.environ.get("VIDEO_TOPIC", "Nature")
    print(f"🚀 Starting Generator for: {topic}")
    
    script = get_script(topic)
    asyncio.run(get_voice(script))
    
    if get_video(topic):
        make_short()
    else:
        print("❌ Could not download video. Exiting.")
        sys.exit(1)
