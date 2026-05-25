import cv2
import tasks as tsk
import models
import mediapipe as mp
from typing import List

class Handler:

    tasks : List[tsk.Task]
    model : models.Model


    def __init__(self, model_type : str):
        if model_type == "Gesture":
            self.model = models.Gesture_Mode("gesture_recognizer.task",self.handle_result)
        print("Model is loaded")
        self.tasks = []

    def attack_task(self, new_task : tsk.Task):
        self.tasks.append(new_task)

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam.")
            exit()
        print("Cam is opened")
        try:
            timestamp = 0
            while True:
                ret, frame = cap.read()
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                self.model.start_inference(mp_image,timestamp)
                cv2.waitKey(1)
                timestamp+=1
        except:
            cap.release()
            cv2.destroyAllWindows()

    def handle_result(self, result , output_image: mp.Image, timestamp_ms: int):
        for task in self.tasks:
            task.handle_result(result)




