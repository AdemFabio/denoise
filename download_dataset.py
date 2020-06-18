import os
import time
from pathlib import Path

import pandas as pd
from download_dataset.celery_tasks import crop_video, download_video

DURATION = 3


if __name__ == "__main__":

    df_train = pd.read_csv("./data/avspeech_train.csv", names=["id", "start", "end", "x_center", "y_center"], header=None).head(1000)
    df_valid = pd.read_csv("./data/avspeech_test.csv", names=["id", "start", "end", "x_center", "y_center"], header=None).head(1000)

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
