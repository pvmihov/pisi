import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class Model:
    '''Model for recognition template'''

    def __init__(self):
        pass


class Gesture_Mode(Model):
    '''Model Recognising Gestures'''

    def __init__(self, path_to_model : str, funct_to_call, num_hands_to_give : int):
        super().__init__()
        BaseOptions = mp.tasks.BaseOptions
        GestureRecognizer = mp.tasks.vision.GestureRecognizer
        GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
        GestureRecognizerResult = mp.tasks.vision.GestureRecognizerResult
        VisionRunningMode = mp.tasks.vision.RunningMode
        options = GestureRecognizerOptions(
            base_options=BaseOptions(model_asset_path=path_to_model),
            num_hands = num_hands_to_give,
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=funct_to_call)
        self.recognizer = GestureRecognizer.create_from_options(options)

    def start_inference(self, mp_image : mp.Image, frame_timestamp_ms):
        self.recognizer.recognize_async(mp_image, frame_timestamp_ms)

    def release(self):
        self.recognizer.close()

