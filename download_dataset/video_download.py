import os
from datetime import timedelta
import subprocess
from typing import Optional, Tuple

import youtube_dl


YOUTUBE_BASE_URL = "https://www.youtube.com/watch?v="


def get_video_audio_urls(
    youtube_id: str, max_height: Optional[int] = 480
) -> Tuple[str, str]:
    """
    Returns the urls of the video and the audio stream of a youtube video

    Args:
        youtube_id: the identifier of the youtube video in the URL after `watch?v=
        max_height: maximum video height. Defaults to 480 pixels
    
    Returns:
        the video and audio stream URLs as strings

    """

    ydl_opts = {
        "format": f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]",
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(
                f"{YOUTUBE_BASE_URL}{youtube_id}", download=False
            )
    except youtube_dl.utils.DownloadError as e:
        return None

    video_and_audio_info_dict = info_dict.get("requested_formats")

    if video_and_audio_info_dict is not None and len(video_and_audio_info_dict) == 2:
        video_url = video_and_audio_info_dict[0].get("url")
        audio_url = video_and_audio_info_dict[1].get("url")

        return video_url, audio_url
    else:
        return None


def download_partial_video_from_youtube(
    target_dir: str,
    file_base_name: str,
    youtube_id: str,
    start_time: float,
    duration: float,
    max_height: Optional[int] = 480,
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
    file_video = file_base_path + ".mp4"
    file_audio = file_base_path + ".aac"
    if os.path.isfile(file_video):
        raise FileExistsError(f"{file_video} already exists!")
    if os.path.isfile(file_audio):
        raise FileExistsError(f"{file_audio} already exists!")

    video_url, audio_url = get_video_audio_urls(youtube_id, max_height)

    start_time = timedelta(seconds=start_time)
    duration = timedelta(seconds=duration)

    download_cmd_video = f'ffmpeg -ss {start_time} -i "{video_url}" -map 0:v -t {duration} -c:v libx264 {file_video}'
    download_cmd_audio = f'ffmpeg -ss {start_time} -i "{audio_url}" -map 0:a -t {duration} -c:a aac {file_audio}'

    result = subprocess.run(
        download_cmd_video, capture_output=True, shell=True, encoding="utf8", timeout=10
    )
    if result.returncode != 0:
        raise FileNotFoundError("Could not download Video! (Return code was not 0)")

    result = subprocess.run(
        download_cmd_audio, capture_output=True, shell=True, encoding="utf8", timeout=10
    )
    if result.returncode != 0:
        raise FileNotFoundError("Could not download Audio! (Return code was not 0)")

    return file_video, file_audio


if __name__ == "__main__":
    download_partial_video_from_youtube("./", "test", "T-lBMrjZ3_0", 180, 3.5, 480)
