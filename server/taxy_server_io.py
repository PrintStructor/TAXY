import cv2, numpy as np
import requests
from requests.exceptions import InvalidURL, ConnectionError # , HTTPError, RequestException

import os
import json
from datetime import datetime

# Size of frame to use (1280x720 for better detection accuracy)
_FRAME_WIDTH = 1280
_FRAME_HEIGHT = 720
 
class Taxy_Server_Io:
    def __init__(self, log, camera_url, save_image = False):
        self.log = log
        self.log(' *** initializing Taxy_Server_Io **** ')
        self.camera_url = camera_url
        self.save_image = save_image
        self.session = requests.Session()

        # Local storage directory for training images
        self.storage_dir = os.path.join(os.path.dirname(__file__), '..', 'collected_images')

        self.log(' *** initialized Taxy_Server_Io with camera_url = %s, save_image = %s **** ' % (str(camera_url), str(save_image)))
        

    def can_read_stream(self, printer):
        try:
            with self.session.get(self.camera_url) as _:
                return True
        except InvalidURL as _:
            raise printer.config_error("Could not read nozzle camera address, got InvalidURL error %s" % (self.camera_url))
        except ConnectionError as _:
            raise printer.config_error("Failed to establish connection with nozzle camera %s" % (self.camera_url))
        except Exception as e:
            raise printer.config_error("Nozzle camera request failed %s" % str(e))

    def open_stream(self):
        self.session = requests.Session()

    def get_single_frame(self):
        self.log(' *** calling get_single_frame **** ')
        
        if self.session is None: 
            self.log("HTTP stream for reading jpeg is not running")
            raise Exception("HTTP stream for reading jpeg is not running")

        try:
            with self.session.get(self.camera_url, stream=True) as stream:
                self.log(' stream.ok = %s ' % stream.ok)
                if stream.ok:
                    chunk_size = 1024
                    bytes_ = b''
                    for chunk in stream.iter_content(chunk_size=chunk_size):
                        bytes_ += chunk
                        a = bytes_.find(b'\xff\xd8')
                        b = bytes_.find(b'\xff\xd9')
                        if a != -1 and b != -1:
                            jpg = bytes_[a:b+2]
                            # Read the image from the byte array with OpenCV
                            image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            image = cv2.resize(image, (_FRAME_WIDTH, _FRAME_HEIGHT), interpolation=cv2.INTER_AREA)
                            # Return the image
                            return image
            return None
        except Exception as e:
            self.log("Failed to get single frame from stream %s" % str(e))
            # raise Exception("Failed to get single frame from stream %s" % str(e))

    def close_stream(self):
        if self.session is not None:
            self.session.close()
            self.session = None
            
    def save_frame_locally(self, frame, points, algorithm):
        """Save detection frame locally for custom model training"""
        try:
            self.log(' *** calling save_frame_locally **** ')

            # Create storage directory if it doesn't exist
            os.makedirs(self.storage_dir, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]  # milliseconds
            image_filename = f"{timestamp}.jpg"
            json_filename = f"{timestamp}.json"

            image_path = os.path.join(self.storage_dir, image_filename)
            json_path = os.path.join(self.storage_dir, json_filename)

            # Save image
            cv2.imwrite(image_path, frame)

            # Save metadata (detection info for annotation reference)
            metadata = {
                'timestamp': timestamp,
                'algorithm': algorithm,
                'detected_position': {
                    'x': float(points[0]) if len(points) > 0 else None,
                    'y': float(points[1]) if len(points) > 1 else None,
                    'confidence': float(points[2]) if len(points) > 2 else None
                },
                'image_file': image_filename
            }

            with open(json_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            self.log(f' *** saved frame locally to {image_path} **** ')
            return True

        except Exception as e:
            self.log("Failed to save frame locally: %s" % str(e))
            return False    
