from evdev import UInput, ecodes as e
import time
import commands
import tasks
import checkers
import handler


ui = UInput()
time.sleep(0.5)

volume_up_command = commands.KeyHoldCommand(ui,e.KEY_VOLUMEUP)
thumb_up_checker = checkers.GestureChecker("Thumb_Up")
volume_up_task = tasks.HoldTask(volume_up_command,thumb_up_checker)

volume_down_command = commands.KeyHoldCommand(ui,e.KEY_VOLUMEDOWN)
thumb_down_checker = checkers.GestureChecker("Thumb_Down")
volume_down_task = tasks.HoldTask(volume_down_command,thumb_down_checker)

alt_tab_command = commands.KeyChordCommand(ui,[e.KEY_LEFTALT,e.KEY_TAB])
victory_appear_checker = checkers.GestureAppearChecker("Closed_Fist")
alt_tab_task = tasks.Task(alt_tab_command,victory_appear_checker)


big_guy = handler.Handler("Gesture")
big_guy.attack_task(volume_up_task)
big_guy.attack_task(volume_down_task)
big_guy.attack_task(alt_tab_task)
big_guy.run()