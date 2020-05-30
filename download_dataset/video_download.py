import os
from datetime import timedelta
import subprocess
from typing import Optional, Tuple


YOUTUBE_BASE_URL = "https://www.youtube.com/watch?v="


def get_video_audio_urls(youtube_id:str, max_height:Optional[int]=480) -> Tuple[str, str]:
    """
    Returns the urls of the video and the audio stream of a youtube video

    Args:
        youtube_id: the identifier of the youtube video in the URL after `watch?v=
        max_height: maximum video height. Defaults to 480 pixels
    
    Returns:
        the video and audio stream URLs as strings
`
    """

    quality_args = f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]"
    cmd = f'youtube-dl -f "{quality_args}" -g "{YOUTUBE_BASE_URL + youtube_id}"'

    result = subprocess.run(
        cmd,
        capture_output=True,
        shell=True,
        encoding="utf8"
    )

    if result.returncode != 0:
        raise Exception("Could not get audio and video URL! (Return code was not 0)")

    split_urls = result.stdout.rstrip("\n").split("\n")
    assert len(split_urls) == 2, "There should be two new line characteres!"
    video_url, audio_url = split_urls

    return video_url, audio_url


def download_partial_video_from_youtube(
    target_dir: str,
    file_base_name: str,
    youtube_id:str,
    start_time:float,
    duration:float,
    max_height:Optional[int]=480
) -> Tuple[str, str]:
    """
    Downloads a section of a youtube video beginning at `start_time`

    Args:
        target_dir: The target directory to save the video and audio file to.
        file_base_name: The base name that will be used for .mp4 and .aac files.
        youtube_id: the identifier of the youtube video in the URL after `watch?v=`
        start_time: start time of the desired section in seconds
        duration: length of the desired section in section
        max_height: maximum video height. Defaults to 480 pixels
    
    """
    
    file_base_path = os.path.join(target_dir, file_base_name)
    file_video = file_base_name + ".mp4"
    file_audio = file_base_name + ".aac"
    if os.path.isfile(file_video):
        raise Exception(f"{file_video} already exists!")
    if os.path.isfile(file_audio):
        raise Exception(f"{file_audio} already exists!")

    video_url, audio_url = get_video_audio_urls(youtube_id, max_height)
    
    start_time = timedelta(seconds=start_time)
    duration = timedelta(seconds=duration)
        
    download_cmd_video = (
        f'ffmpeg -ss {start_time} -i "{video_url}" -map 0:v -t {duration} -c:v libx264 {file_video}'
    )
    download_cmd_audio = (
        f'ffmpeg -ss {start_time} -i "{audio_url}" -map 0:a -t {duration} -c:a aac {file_audio}'
    )
    
    result = subprocess.run(
        download_cmd_video,
        capture_output=True,
        shell=True,
        encoding="utf8",
        timeout=10
    )
    if result.returncode != 0:
        raise Exception("Could not download Video! (Return code was not 0)")

    result = subprocess.run(
        download_cmd_audio,
        capture_output=True,
        shell=True,
        encoding="utf8",
        timeout=10
    )
    if result.returncode != 0:
        raise Exception("Could not download Video! (Return code was not 0)")
    
    return file_video, file_audio



if __name__ == "__main__":
    download_partial_video_from_youtube("./", "test", "T-lBMrjZ3_0", 180, 3.5, 480)
