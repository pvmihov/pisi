import mediapipe as mp

class Checker:
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