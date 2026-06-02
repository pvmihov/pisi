import mediapipe as mp
from typing import Tuple, List, Dict
import math
import cv2
import numpy as np
import queue
import threading
import pytesseract
from evdev import UInput

class Checker:
    '''Checks for a certain condition'''
    def __init__(self):
        pass

    def test_result(self, result):
        pass

class GestureChecker(Checker):
    '''Checks whether a gesture is in the frame'''
    gesture : str
    
    def __init__(self, gesture : str):
        super().__init__()
        self.gesture = gesture

    def test_result(self, result):
        for gesture_list in result.gestures:
            if gesture_list[0].category_name == self.gesture:
                return True    
        return False

class GestureAppearChecker(Checker):
    '''Checks whether a gesture has just appeared in the frame'''

    gesture : str
    has_appeared : bool

    def __init__(self, gesture : str):
        super().__init__()
        self.gesture = gesture
        self.has_appeared = False

    def test_result(self, result):
        cur_appear = False
        for gesture_list in result.gestures:
            if gesture_list[0].category_name == self.gesture:
                cur_appear = True    
        if cur_appear and not self.has_appeared:
            self.has_appeared = True
            return True
        self.has_appeared = cur_appear
        return False


class RotateWristChecker(Checker):
    '''Checks for a snappy wrotation of the wrist. Either Horizontal or Vertical'''

    dir : bool #true for horizontal, false for vertical
    track_points : List[int] # the points to track
    prev_cords : Dict[str,List[List[float]]]
    frames_needed : int

    def __init__(self, direction : str):
        super().__init__()
        if direction == "Horizontal": self.dir = True
        elif direction == "Vertical": self.dir = False
        else: raise Exception("Direction must be Horizontal or Vertical")
        self.track_points = [3,4,17,18,19,20]
        self.frames_needed = 3
        prev_cords = []
        for point in self.track_points: prev_cords.append([])
        self.prev_cords = {
            'Left' : prev_cords,
            'Right' : prev_cords.copy()
        }

    def test_result(self, result):
        present_ind = {
            'Left' : -1,
            'Right' : -1
        }      
        for i in range(0,len(result.handedness)):
            hand = result.handedness[i]
            present_ind[ hand[0].category_name ] = i
        found_any = False
        for key, value in present_ind.items():
            if len(self.prev_cords[key][0]) == self.frames_needed:
                for i in range(0,len(self.track_points)):
                    self.prev_cords[key][i].reverse()
                    self.prev_cords[key][i].pop()
                    self.prev_cords[key][i].reverse()
            for i in range(0,len(self.track_points)):
                if value == -1:
                    self.prev_cords[key][i].append(0)
                elif self.dir:
                    self.prev_cords[key][i].append( result.hand_world_landmarks[value][self.track_points[i]].x )
                else:
                    self.prev_cords[key][i].append( result.hand_world_landmarks[value][self.track_points[i]].y )
            if len(self.prev_cords[key][0]) == self.frames_needed:
                all_fit = True
                for i in range(0,len(self.track_points)):
                    if not(self.prev_cords[key][i][0]*self.prev_cords[key][i][-1]<0):
                        all_fit = False
                if all_fit:
                    found_any = True
                    for i in range(0,len(self.track_points)): self.prev_cords[key][i] = []
        return found_any


class MoveHandChecker(Checker):
    '''Checks for a slow movement of the hand in the span of about a second'''

    direction : Tuple[float,float]
    distance : float
    prev_cords : Dict[str,List[Tuple[float,float]]]
    frames_needed : int
    point_tracked : int

    def __init__(self, direction : Tuple[float,float], distance : float):
        super().__init__()
        dir_x , dir_y = direction
        distance_p = math.sqrt(dir_x*dir_x + dir_y*dir_y)
        self.direction = ( dir_x / distance_p, dir_y / distance_p )
        self.distance = distance
        self.point_tracked = 9
        self.frames_needed = 6
        self.prev_cords = {
            'Left' : [],
            'Right' : []
        }

    def test_result(self, result):
        present_ind = {
            'Left' : -1,
            'Right' : -1
        }      
        for i in range(0,len(result.handedness)):
            hand = result.handedness[i]
            present_ind[ hand[0].category_name ] = i
        found_any = False
        for key, value in present_ind.items():
            if len(self.prev_cords[key]) == self.frames_needed:
                self.prev_cords[key].reverse()
                self.prev_cords[key].pop()
                self.prev_cords[key].reverse()
            if value == -1:
                self.prev_cords[key].append(None)
            else:
                self.prev_cords[key].append( (result.hand_landmarks[value][self.point_tracked].x , result.hand_landmarks[value][self.point_tracked].y ) )
            if len(self.prev_cords[key]) == self.frames_needed:
                if self.prev_cords[key][-1] is None or self.prev_cords[key][0] is None: 
                    continue
                x_now , y_now = self.prev_cords[key][-1]
                x_then, y_then = self.prev_cords[key][0]
                change_x = x_now - x_then
                change_y = y_now - y_then
                x_des, y_des = self.direction
                scalar_mult = x_des * change_x + y_des * change_y
                if scalar_mult >= self.distance:
                    found_any = True
                    self.prev_cords[key].clear()
        return found_any
    

class SqueezeFingersChecker(Checker):
    '''Checks for squeezing of two fingers toghether'''

    found_begin : Dict[str,List[int]]
    frames_needed : int
    dist_to_start : int
    finger_1 : List[int]
    finger_2 : List[int]

    @classmethod
    def find_finger(cls, string : str) -> int:
        if string == 'Thumb':
            return [3,4]
        elif string == 'Index':
            return [7,8]
        elif string == 'Middle':
            return [11,12]
        elif string == 'Ring':
            return [15,16]
        elif string == 'Pinky':
            return [19,20]
        else:
            raise Exception(f'{str} is not a valid finger')

    def __init__(self, finger_1 : str, finger_2 : str):
        super().__init__()
        self.finger_1 = self.find_finger(finger_1)
        self.finger_2 = self.find_finger(finger_2)
        self.dist_to_start = 0.03
        self.frames_needed = 8
        self.found_begin = {
            'Right' : [-10,-10],
            'Left' : [-10,-10]
        }

    def test_result(self, result):
        present_ind = {
            'Left' : -1,
            'Right' : -1
        }      
        for i in range(0,len(result.handedness)):
            hand = result.handedness[i]
            present_ind[ hand[0].category_name ] = i
        found_any = False
        for key, value in present_ind.items():
            if value == -1: continue
            for i in range(0,2):
                fin1 = self.finger_1[i]
                fin2 = self.finger_2[i]
                x1 = result.hand_world_landmarks[value][fin1].x
                y1 = result.hand_world_landmarks[value][fin1].y
                z1 = result.hand_world_landmarks[value][fin1].z
                x2 = result.hand_world_landmarks[value][fin2].x
                y2 = result.hand_world_landmarks[value][fin2].y
                z2 = result.hand_world_landmarks[value][fin2].z
                dist = math.sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
                #print(dist,self.found_begin[key])
                if dist >= self.dist_to_start: self.found_begin[key][i] = self.frames_needed
                elif dist <= self.dist_to_start:
                    if self.found_begin[key][i] >= 0:
                        found_any = True
                        self.found_begin[key][i] = -1
        return found_any
    


class ArgumentChecker(Checker):
    '''Checker which doesn't return simply true or false, but some sort of result'''

    def __init__(self):
        super().__init__()

    def test_result(self, result):
        pass

class LetterRecognitionChecker(ArgumentChecker):
    '''Recognises if the user is spelling a letter'''

    time_frame : int
    coordinates : Dict[str,List[Tuple[float,float]]]
    index_finger : int
    result : int
    image_queue : queue.Queue

    def __init__(self):
        super().__init__()
        #todo implement different timeframes, and different fingers
        self.time_frame = 70
        self.coordinates = {
            'Left' : [],
            'Right' : []
        }
        self.index_finger = 8
        self.result = -1
        self.image_queue = queue.Queue()
        worker_thread = threading.Thread(
            target=self.tesseract_worker, 
            args=(self.image_queue, self.parse_result), 
            daemon=True
        )
        worker_thread.start()

    def tesseract_worker(self, img_queue : queue.Queue, callback_function):
         custom_config = '--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
         while True:
            img = img_queue.get()
            try:
                text = pytesseract.image_to_string(img, config=custom_config).strip()
                if text:
                    callback_function(text)
            except Exception as e:
                print(f"OCR Error: {e}")
            img_queue.task_done()

    def parse_result(self, text : str):
        #print(text)
        if len(text) != 1:
            self.result = -1
        elif ord(text[0]) >= ord('a'):
            self.result = ord(text[0]) - ord('a')
        else:
            self.result = ord(text[0]) - ord('A')
        #print(self.result)

    def test_result(self, result) -> int | bool:
        present_ind = {
            'Left' : -1,
            'Right' : -1
        }      
        for i in range(0,len(result.handedness)):
            hand = result.handedness[i]
            present_ind[ hand[0].category_name ] = i
        found_any = False
        for key, value in present_ind.items():
            #if everything is -1,-1 to clear
            found_not_minusone = False
            for x,y in self.coordinates[key]:
                if x!=-1 or y!=-1: found_not_minusone = True
            if not found_not_minusone: self.coordinates[key].clear()
            if value == -1:
                self.coordinates[key].append( (-1,-1) )
            else:
                self.coordinates[key].append( (result.hand_landmarks[value][self.index_finger].x,result.hand_landmarks[value][self.index_finger].y) )
            if len(self.coordinates[key]) > self.time_frame:
                self.coordinates[key] = self.coordinates[key][1:]
            if len(self.coordinates[key]) == self.time_frame:

                image = self.turn_cords_to_image(self.coordinates[key])
                if image is None:
                    continue
                #cv2.imwrite("connected_lines_opencv.png", image)
                self.image_queue.put(image)
                self.coordinates[key].clear()
        if self.result == -1: return False
        old_res = self.result
        self.result = -1
        return old_res

    def turn_cords_to_image(self, coords : List[Tuple[float,float]]):
        new_cords = []
        for cord in coords:
            x,y = cord
            #print(x)
            if x==-1: continue
            new_cords.append((1-x,y))
        if len(new_cords)< self.time_frame / 2: return None
        width = 640
        height = 480
        image = np.ones((height, width, 3), dtype=np.uint8) * 255
        scaled_coords = [(int(x * width), int(y * height)) for x, y in new_cords]
        black_color = (0, 0, 0)
        thickness = 20

        for point1, point2 in zip(scaled_coords[:-1],scaled_coords[1:]):
            cv2.line(image, point1, point2, black_color, thickness)
        return image
    
class FingerPointMouseChecker(ArgumentChecker):

    finger_front : int
    mouse : UInput
    seen_mouse : bool
    start_figner : Tuple[float]
    resolution : Tuple[int,int]

    def __init__(self, mouse : UInput, resolution : Tuple[int,int]):
        super().__init__()
        self.mouse = mouse
        self.finger_front = 8
        self.seen_mouse = False
        self.start_figner = (-1,-1)
        self.resolution = resolution

    def test_result(self, result):
        if len(result.handedness)!=1:
            self.start_figner = (-1,-1)
            self.seen_mouse = False
            return False
        if not self.seen_mouse:
            self.seen_mouse = True
            self.start_figner = (result.hand_landmarks[0][self.finger_front].x,result.hand_landmarks[0][self.finger_front].y)
            return False
        else:
            x,y = self.start_figner
            assert(x!=-1)
            assert(y!=-1)
            new_x = result.hand_landmarks[0][self.finger_front].x
            new_y = result.hand_landmarks[0][self.finger_front].y
            diff_x = x-new_x
            diff_y = y-new_y
            reso_x , reso_y = self.resolution
            result_x = int(reso_x * diff_x)
            result_y = -1*int(reso_y * diff_y)
            if abs(result_x) > 15 or abs(result_y) > 15:
                self.start_figner = (new_x,new_y)
                return (result_x,result_y)
            else:
                return False