import os
import time
from pathlib import Path
from typing import Union

import pandas as pd
from celery import Celery
from kombu import Exchange, Queue

from face_cropping import FaceCropper
from video_download import download_partial_video_from_youtube

face_cropper = FaceCropper()


app = Celery("download_dataset")
celeryconfig = {}
celeryconfig['BROKER_URL'] = 'pyamqp://guest@localhost//'
celeryconfig['CELERY_QUEUES'] = (
    Queue('download_dataset', Exchange('download_dataset'), routing_key='download_dataset',
          queue_arguments={'x-max-priority': 10}),
)
celeryconfig['CELERY_ACKS_LATE'] = True
celeryconfig['CELERYD_PREFETCH_MULTIPLIER'] = 1
app.config_from_object(celeryconfig)

DURATION = 3

@app.task
def crop_video(
        video_file,
        audio_file,
        cropped_dir,
):
    assert video_file is not None and audio_file is not None
    
    return_code = face_cropper.cut_face_from_video(video_file, cropped_dir)

    if return_code == 0:
        # Single face successfully cropped out of video

        # Remove downloaded video
        os.remove(video_file)

        # Move corresponding audio file to the same folder
        os.rename(audio_file, os.path.join(cropped_dir, Path(audio_file).name))

    
@app.task
def download_video(download_dir: Union[str, Path],
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

        if video_file is not None and audio_file is not None:
            crop_video.apply_async(
                queue='download_dataset',
                args=(
                    video_file,
                    audio_file,
                    cropped_dir
                ),
                priority=2
            )
    except FileNotFoundError:
        pass
    except FileExistsError:
        pass

if __name__ == "__main__":

    df_train = pd.read_csv("./avspeech_train.csv", names=["id", "start", "end", "x_center", "y_center"], header=None).head(1000)
    df_valid = pd.read_csv("./avspeech_test.csv", names=["id", "start", "end", "x_center", "y_center"], header=None).head(1000)

    for directory, df in zip(["train", "valid"], [df_train, df_valid]):
        downloaded_dir = Path(f"./{directory}_data/downloaded")
        cropped_dir = Path(f"./{directory}_data/cropped")
        
        os.makedirs(downloaded_dir, exist_ok=True)
        os.makedirs(cropped_dir, exist_ok=True)
        

        for idx, row in df.iterrows ():
            start_time = row.start
            end_time = row.end

            # We only want to keep videos that are at least DURATION seconds long
            if end_time - start_time < DURATION:
                continue

            # We want to download the center interval of length DURATION
            start_time = (start_time + end_time) / 2 - DURATION / 2

            download_video.apply_async(
                queue='download_dataset',
                args=(
                    str(downloaded_dir),
                    str(cropped_dir),
                    row.id,
                    start_time,
                    DURATION,
                    ),
                priority=1
            )
