import os
import requests
import random
import asyncio
import edge_tts
import google.generativeai as genai
from moviepy.editor import *

# --- CONFIGURATION ---
# The code looks for your keys in the secure GitHub "Secrets" locker
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# Configure Google Gemini with your new key
genai.configure(api_key=GOOGLE_API_KEY)

def get_script(topic):
    """Generates script using Google Gemini"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            f"Write a script for a 30-second YouTube Short about {topic}. "
            "Do not include scene directions or camera angles. "
            "Just provide the raw text for the narrator to speak. "
            "Keep it punchy and engaging."
        )
        response = model.generate_content(prompt)
        # Clean up text (remove * or # formatting if Gemini adds it)
        clean_text = response.text.replace("*", "").replace("#", "")
        return clean_text
    except Exception as e:
        print(f"Error generating script: {e}")
        return "Did you know space is completely silent? There is no atmosphere in space, which means sound has no medium or way to travel to be heard."

async def get_voice(text):
    """Generates Voiceover"""
    if not text: return
    if len(text) > 1000: text = text[:1000]
    # Uses a high quality English voice
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save("voice.mp3")

def get_video(topic):
    """Downloads background video from Pexels"""
    if not PEXELS_API_KEY:
        print("Error: Pexels API Key is missing.")
        return False
        
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={topic}&per_page=5&orientation=portrait"
    
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        
        if not data.get('videos'):
            print("No videos found for this topic.")
            return False

        video_url = random.choice(data['videos'])['video_files'][0]['link']
        with open("bg.mp4", "wb") as f:
            f.write(requests.get(video_url).content)
        return True
    except Exception as e:
        print(f"Error fetching video: {e}")
        return False

def make_short():
    """Stitches audio and video together"""
    try:
        if not os.path.exists("voice.mp3") or not os.path.exists("bg.mp4"):
            print("Missing media files.")
            return

        audio = AudioFileClip("voice.mp3")
        video = VideoFileClip("bg.mp4")

        # Loop video to match audio length
        if video.duration < audio.duration:
            video = video.loop(duration=audio.duration)
        else:
            video = video.subclip(0, audio.duration)
        
        video = video.set_audio(audio)
        
        # Resize to Vertical 9:16
        video = video.resize(height=1920)
        video = video.crop(x1=0, y1=0, width=1080, height=1920, x_center=1080/2, y_center=1920/2)

        video.write_videofile("final_video.mp4", fps=24)
        print("SUCCESS: Video created!")
    except Exception as e:
        print(f"Error processing video: {e}")

if __name__ == "__main__":
    topic = os.environ.get("VIDEO_TOPIC")
    print(f"Generating video for: {topic}")
    
    if not GOOGLE_API_KEY:
        print("ERROR: Google API Key not found in Secrets.")
    else:
        script = get_script(topic)
        print("Script generated.")
        
        asyncio.run(get_voice(script))
        
        if get_video(topic):
            make_short()
