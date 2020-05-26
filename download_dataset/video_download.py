from datetime import timedelta
import subprocess
from typing import Tuple


YOUTUBE_BASE_URL = "https://www.youtube.com/watch?v="


def get_video_audio_urls(youtube_id:str) -> Tuple[str]:
    """
    Returns the urls of the video and the audio stream of a youtube video

    Args:
        youtube_id: the identifier of the youtube video in the URL after `watch?v=
    
    Returns:
        the video and audio stream URLs as strings
`
    """
    
    result = subprocess.run(f'youtube-dl -g "{YOUTUBE_BASE_URL + youtube_id}"',
                            capture_output=True,
                            shell=True,
                            encoding="utf8")
    
    if result.returncode != 0:
        return None
    
    urls = result.stdout.split("\n")

    # 3 because there is a final "\n" after the sedond URL
    if len(urls) == 3:
        
        video_url = urls[0]
        audio_url = urls[1]
        
        return video_url, audio_url
    
    else:
        return None


def download_partial_video_from_youtube(youtube_id:str, start_time:float, duration:float):
    """
    Downloads a section of a youtube video beginning at `start_time`

    Args:
        youtube_id: the identifier of the youtube video in the URL after `watch?v=`
        start_time: start time of the desired section in seconds
        duration: length of the desired section in section
        
    """
    
    video_url, audio_url = get_video_audio_urls(youtube_id)
    
    start_time = timedelta(seconds=start_time)
    duration = timedelta(seconds=duration)
        
    #download_cmd = f'ffmpeg -ss {start_time} -i "{video_url}" -ss {start_time} -i "{audio_url}" -map 0:v -map 1:a -ss 30 -t {duration} -c:v libx264 -c:a aac test.mkv'

    download_cmd = f'ffmpeg -ss {start_time} -i "{video_url}" -ss {start_time} -i "{audio_url}" -map 0:v -map 1:a -t {duration} -c:v libx264 -c:a aac {youtube_id}.mp4'
    
    subprocess.run(download_cmd,
                   capture_output=True,
                   shell=True,
                   encoding="utf8"
                  )


if __name__ == "__main__":
    download_partial_video_from_youtube("T-lBMrjZ3_0", 180, 3.5)
