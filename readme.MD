# Core Idea

The most important module in pisi are tasks. They emulate real world structures like "If I close my fist, then press Alt+Tab", or generally "If "clause" , then "command"". That is why tasks have two objects inside of them, a checker and a command, which serve as the clause and the command. Any time a checker is satisfied, the command is performed immediteately. There are also hold tasks, which work with HoldCommands, that have a begin action and stop action. 
You can play around creating your own Tasks with different checkers and commands. 

# Current Functionalities

Current Commands include:
1. KeyChordCommand, receives a collection of keys which are pressed in that order, and immediately released in the reverse order
2. KeyHoldForTimeCommand, receives a key and a time. Holds the key for that fixed time
3. KeyHoldCommand, part of HoldCommands, receives a key, which it starts and ends pressing in the two respective functions.

Current Checkers include:
1. GestureChecker, receives the name of a gesture and it is satisfied any frame that a gesture appears.
2. GestureAppearChecker, receives the name of a gesture and it is satisfied on the first frame that it appears.
3. RotateWristChecker, receives a direction (Horizontal or Vertical) and is satisfied when the wrist is snapped in that direction.
4. MoveHandChecker, receives a 2d vector for direction and a float for distance and is satisfied when the hand moves at least that distance in terms of the vector in the span of about a second.
5. SqueezeFingersChecker, receives two names of fingers and is satisfied when the fingers are squeezed together. The 5 fingers are Thumb, Index, Middle, Ring and Pinky.

The recognised gestures are:
1. Closed fist, name: Closed_Fist
2. Open palm, name: Open_Palm
3. Pointing up, name: Pointing_Up
4. Thumbs down, name: Thumb_Down
5. Thumbs up, name: Thumb_Up
6. Victory, name: Victory
7. Rock Sign, name: ILoveYou

# Setting Up

1. Download or clone the repository
2. Create the python env. #TODO
3. Download the Model manually from , or with the following command
```bash
wget -q https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task
```

After setting, you have to run the main program with sudo
```bash
sudo $(which python) main.py
```
