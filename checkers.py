import mediapipe as mp
from typing import Tuple, List, Dict

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
    prev_cords : Dict[str,List[List[int]]]
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
                #for i in range(0,len(self.track_points)): self.prev_cords[key][i] = []
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
                    if not(self.prev_cords[key][i][0]*self.prev_cords[key][i][self.frames_needed-1]<0):
                        all_fit = False
                if all_fit:
                    found_any = True
                    for i in range(0,len(self.track_points)): self.prev_cords[key][i] = []
        return found_any

# class HandMovementChecker(Checker):
#     '''Checks for moving throughout the screen'''

#     dir : Tuple[float,float] #vector for the moving
#     dist : float #how much move is required to trigger


#     def __init__(self, dir : Tuple[float,float], dist : float):
#         super().__init__()


#     def test_result(self, result):
#         if len(result.hand_landmarks)!=0:
#             print(result.hand_landmarks[0][17])
#         else:
#             print('empty')
#         return False