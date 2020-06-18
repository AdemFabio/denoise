import os
from pathlib import Path
from typing import Union

import youtube_dl

from .celery_app import app
from .face_cropping import FaceCropper
from .video_download import download_partial_video_from_youtube, UnexpectedURLInfo, FailedDownload

face_cropper = FaceCropper()

@app.task
def crop_video(
        video_file: str,
        audio_file: str,
        cropped_dir: str,
):    
    return_code = face_cropper.cut_face_from_video(video_file, cropped_dir)

    if return_code == 0:
        # Single face successfully cropped out of video

        # Remove downloaded video
        os.remove(video_file)

        # Move corresponding audio file to the same folder
        os.rename(audio_file, os.path.join(cropped_dir, Path(audio_file).name))

    
@app.task
def download_video(
    download_dir: Union[str, Path],
    cropped_dir: Union[str, Path],
    youtube_id: str,
    start_time: float,
    duration: float
):
    try:
        video_file, audio_file = download_partial_video_from_youtube(
            target_dir=download_dir,
            file_base_name=youtube_id,
            youtube_id=youtube_id,
            start_time=start_time,
            duration=duration
        )

        crop_video.apply_async(
            queue='download_dataset',
            args=(
                video_file,
                audio_file,
                cropped_dir
            ),
            priority=2
        )
        
    except youtube_dl.utils.DownloadError as e:
        print(e)
        print(f"Youtube ID: {youtube_id}")
    except UnexpectedURLInfo as e:
        print(e)
    except FailedDownload as e:
        print(e)
    except FileExistsError as e:
        print(e)
