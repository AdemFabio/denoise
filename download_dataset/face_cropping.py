import os
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np
import skvideo.io
import torch
from facenet_pytorch import MTCNN


class FaceCropper:
    """
    Class that provides utility methods to crop a face out of a video.
    
    Attributes:
        num_detect_points: the number of intermediate
            frames for which face detection is performed.
        model (torch.Module): a face detection network
    
    """

    def __init__(
        self,
        num_detect_points: Optional[int] = 2,
        device: Optional[torch.device] = None,
    ):
        """
        Constructor of FaceCropper
        
        Arguments:
            num_detect_points: the number of intermediate frames for
                which face detection is performed.
                Has to have a minimum number of 2.
            device: torch device for the model
            
        """

        if device is None:
            device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        else:
            device = device

        if num_detect_points < 2:
            raise ValueError(
                "Face detection has to be performed for at least two frames in order to interpolate its position"
            )

        self.num_detect_points = num_detect_points
        self.model = MTCNN(keep_all=True, device=device)

    def cut_face_from_video(self,
                            path: Union[str, Path],
                            out_dir: Optional[str] = "./",
    ) -> int:
        """
        Helper method to cut a single face out of a video file
        called `filename`.
        
        Args:
            path: the path of the video out of which the face shall
                be cut out
            out_dir: directory to save the cropped videos to
        
        Returns:
            0 if a single face was found in the video and could be cropped
            out successfully
            
            1 if no or more than exactly one face was found in any of the frames
            
        """

        path = Path(path)

        # Load video
        videodata = skvideo.io.vread(path)

        frame_count = len(videodata)

        # For the intermediate 'support frames' with the following
        # indices we perform face detection.
        # For any frames in between those 'support frames' we interpolate
        # the position of the face to save time.
        face_detect_frame_idxs = np.linspace(
            0, frame_count - 1, min(self.num_detect_points, frame_count), dtype=np.int
        )

        # Detect faces in the respective 'support frames'
        boxes, _ = self.model.detect(videodata[face_detect_frame_idxs])

        # We expect exactly 1 face
        for b in boxes:
            # Make sure that there is exactly one face detected
            if b is None or len(b) != 1:
                return 1

        # Interpolate center coordinates in between two frames for
        # which face detection has been performed
        center_coords_interp = []

        for box_start, box_end, interp_start_idx, interp_end_idx in zip(
            boxes[:-1],
            boxes[1:],
            face_detect_frame_idxs[:-1],
            face_detect_frame_idxs[1:],
        ):

            # We select index 0 because we already checked
            # that there is exactly 1 face
            center_coords_start = self.get_center(box_start[0])
            center_coords_end = self.get_center(box_end[0])

            num_frames = interp_end_idx - interp_start_idx

            center_coords_interp.extend(
                self.interpolate_coords(
                    center_coords_start, center_coords_end, num_frames
                )
            )

        # Determine height and width from the face detected in the first frame
        height, width = self.get_height_width(boxes[0][0])
        cropped_frames = np.zeros((len(videodata), height, width, 3), dtype=np.int)

        _, video_height, video_width, _ = videodata.shape

        # Crop the faces out of the frames using the interpolated center coordinates
        # and the height and width determined from the first frame

        for frame_idx, (frame, center) in enumerate(
            zip(videodata, center_coords_interp)
        ):
            upper = center[0] - height // 2
            lower = upper + height
            left = center[1] - width // 2
            right = left + width

            cropped_face = self.pad_crop(frame, upper, lower, left, right,)

            cropped_frames[frame_idx, ...] = cropped_face

        skvideo.io.vwrite(
            os.path.join(out_dir, f"cropped_{path.name}"), cropped_frames
        )

        return 0

    @staticmethod
    def interpolate_coords(
        coords_start: Tuple[int], coords_end: Tuple[int], t_end: int
    ) -> List[Tuple[int]]:
        """
        Helper method that calculates linearly interpolated 2d coordinates
        between `coords_start` at t=0 and `coords_end` at t=`t_end`.
        
        If `t_end` = 5, there will be interpolated coordinates for t = 1 to 4.
        
        Args:
            coords_start: (y, x) or (row, column) of the starting coordinates
            coords_end: (y, x) or (row, column) of the end coordinates
            t_end: time step if coords_end
            
        Returns:
            A list of interpolated (y, x) coordinates.
        
        """

        t = [0, t_end]
        x = [coords_start[1], coords_end[1]]
        y = [coords_start[0], coords_end[0]]

        x_interp = np.interp(np.arange(0, t_end, 1), t, x)
        y_interp = np.interp(np.arange(0, t_end, 1), t, y)

        # (y, x) because the format is row, column
        return [(int(y), int(x)) for x, y in zip(x_interp, y_interp)]

    @staticmethod
    def pad_crop(
        frame: np.array, upper: int, lower: int, left: int, right: int
    ) -> np.array:
        """
        Helper method that crops a section out of a frame (np.array) 
        while adding padding in order to avoid out of bounds errors.
        
        Args:
            frame: frame that shall be cropped
            upper: upper row index of the crop
            lower: lower row index of the crop.
                Note that `lower` is larger than `upper`
                as the index of the uppermost pixel row is 0
            left: left column index of the crop
            right: right column index of the crop
            
        Returns:
            a cropped and padded section of the frame
        
        """

        height = lower - upper
        width = right - left

        padded_frame = np.pad(
            frame,
            ((height, height), (width, width), (0, 0)),
            "constant",
            constant_values=0,
        )

        return padded_frame[
            height + upper : height + lower, width + left : width + right, :
        ]

    @staticmethod
    def get_center(coords: np.array) -> Tuple[int, int]:
        """
        Helper method that calculates the center coordinates of a bounding box
        
        Args:
            coords: a 4-tuple containing bounding box coordinates in the format
                (left, lower, right, upper)
                
        Returns:
            A tuple containing the center coordinates (center_row, center_col)
            
        """

        if len(coords) != 4:
            raise ValueError("This should have been 4 coordinates")

        left = coords[0]
        right = coords[2]
        lower = coords[1]
        upper = coords[3]

        return int((lower + upper) // 2), int((left + right) // 2)

    @staticmethod
    def get_height_width(coords: np.array) -> Tuple[int, int]:
        """
        Helper method that calculates the height and width of
        a bounding box
        
        Args:
            coords: a 4-tuple containing bounding box coordinates in the format
                (left, lower, right, upper)
                
        Returns:
            Tuple containing the height and width of the bounding box
            
        """

        if len(coords) != 4:
            raise ValueError("This should have been 4 coordinates")

        left = coords[0]
        right = coords[2]
        lower = coords[1]
        upper = coords[3]

        return int(upper - lower), int(right - left)
