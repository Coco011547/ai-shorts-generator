import os
import requests
import random
import asyncio
import edge_tts
from moviepy.editor import *
from moviepy.config import change_settings

# Get secrets from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

def get_script(topic):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4-turbo",
        "messages": [{"role": "user", "content": f"Write a 30 sec viral short script about {topic}. plain text only. no scene directions."}]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

async def get_voice(text):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save("voice.mp3")

def get_video(topic):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={topic}&per_page=5&orientation=portrait"
    r = requests.get(url, headers=headers)
    video_url = random.choice(r.json()['videos'])['video_files'][0]['link']
    with open("bg.mp4", "wb") as f:
        f.write(requests.get(video_url).content)

def make_short():
    # Load assets
    audio = AudioFileClip("voice.mp3")
    video = VideoFileClip("bg.mp4")

    # Loop/Cut video to match audio
    if video.duration < audio.duration:
        video = video.loop(duration=audio.duration)
    else:
        video = video.subclip(0, audio.duration)
    
    video = video.set_audio(audio)
    
    # Resize for Shorts (9:16)
    video = video.resize(height=1920)
    video = video.crop(x1=0, y1=0, width=1080, height=1920, x_center=1080/2, y_center=1920/2)

    # Write file
    video.write_videofile("final_video.mp4", fps=24)

if __name__ == "__main__":
    topic = os.environ.get("VIDEO_TOPIC")
    print(f"Generating video for: {topic}")
    
    script = get_script(topic)
    asyncio.run(get_voice(script))
    get_video(topic)
    make_short()
