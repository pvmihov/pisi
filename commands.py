from evdev import UInput, ecodes as e
from typing import List
import time

class Command:
    '''Generic template class for commands'''
    def __init__(self):
        pass

    def do_command(self):
        '''Executes the specific command of the object'''
        pass


class KeyChordCommand(Command):
    '''Command for pressing a list of keyboard keys'''

    virtual_keyboard : UInput
    key_list : List[int]

    def __init__(self, virtual_keyboard : UInput, key_list : List[int]):
        super().__init__()
        self.virtual_keyboard = virtual_keyboard
        self.key_list = key_list

    def do_command(self):
        '''Executes the keys in key_list in the order of the array'''
        for key in self.key_list:
            self.virtual_keyboard.write(e.EV_KEY,key,1) #button up
            self.virtual_keyboard.syn()
        self.key_list.reverse()
        for key in self.key_list:
            self.virtual_keyboard.write(e.EV_KEY,key,0) #button down
            self.virtual_keyboard.syn()
        self.key_list.reverse()


class KeyHoldForTimeCommand(Command):
    '''Command for holding a key'''

    virtual_keyboard : UInput
    key : int
    hold_time : float

    def __init__(self, virtual_keyboard : UInput, key : int, hold_time : float):
        super().__init__()
        self.virtual_keyboard = virtual_keyboard
        self.key = key
        self.hold_time = hold_time

    def do_command(self):
        '''Holds the key for the required time'''
        self.virtual_keyboard.write(e.EV_KEY,self.key,1)
        self.virtual_keyboard.syn()
        time.sleep(self.hold_time)
        self.virtual_keyboard.write(e.EV_KEY,self.key,0)
        self.virtual_keyboard.syn()


class HoldCommand(Command):
    '''Command with start action and end action'''

    def __init__(self):
        super().__init__()
    
    def start_command(self):
        pass

    def end_command(self):
        pass

class KeyHoldCommand(HoldCommand):
    '''Command for holding key until end'''

    virtual_keyboard : UInput
    key : int

    def __init__(self, virtual_keyboard : UInput, key : int):
        super().__init__()
        self.virtual_keyboard = virtual_keyboard
        self.key = key

    def start_command(self):
        self.virtual_keyboard.write(e.EV_KEY,self.key,1)
        self.virtual_keyboard.syn()

    def end_command(self):
        self.virtual_keyboard.write(e.EV_KEY,self.key,0)
        self.virtual_keyboard.syn()


class ArgumentCommand(Command):
    '''Command which isn't just trigered to execute, but receives an argument supporting its action'''

    def __init__(self):
        super().__init__()

    def do_command(self, argument):
        pass

class WriteLetterCommand(ArgumentCommand):
    '''Command which receives an integer from the alphabet and presses it'''

    virtual_keyboard : UInput
    letters : list

    def __init__(self, ui : UInput):
        super().__init__()
        self.virtual_keyboard = ui
        self.letters = [e.KEY_A,e.KEY_B,e.KEY_C,e.KEY_D,e.KEY_E,e.KEY_F,e.KEY_G,e.KEY_H,e.KEY_I,e.KEY_J,e.KEY_K,e.KEY_L,e.KEY_M,e.KEY_N,e.KEY_O,e.KEY_P,
                        e.KEY_Q,e.KEY_R,e.KEY_S,e.KEY_T,e.KEY_U,e.KEY_V,e.KEY_W,e.KEY_X,e.KEY_Y,e.KEY_Z]

    def do_command(self, argument : int):
        '''Presses A + argument'''
        self.virtual_keyboard.write(e.EV_KEY,self.letters[argument],1)
        self.virtual_keyboard.syn()
        self.virtual_keyboard.write(e.EV_KEY,self.letters[argument],0)
        self.virtual_keyboard.syn()        
