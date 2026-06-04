from evdev import UInput, ecodes as e
import time
import commands
import tasks
import checkers
import handler


ui = UInput()
time.sleep(0.5)

mouse_capabilities = {
    e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL],
    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
}

mouse = UInput(mouse_capabilities, bustype=e.BUS_USB)

volume_up_command = commands.KeyHoldCommand(ui,e.KEY_VOLUMEUP)
thumb_up_checker = checkers.GestureChecker("Thumb_Up")
volume_up_task = tasks.HoldTask(volume_up_command,thumb_up_checker)

volume_down_command = commands.KeyHoldCommand(ui,e.KEY_VOLUMEDOWN)
thumb_down_checker = checkers.GestureChecker("Thumb_Down")
volume_down_task = tasks.HoldTask(volume_down_command,thumb_down_checker)

alt_tab_command = commands.KeyChordCommand(ui,[e.KEY_LEFTALT,e.KEY_TAB])
fist_appear_checker = checkers.GestureAppearChecker("Closed_Fist")
alt_tab_task = tasks.Task(alt_tab_command,fist_appear_checker)

windows_d_command = commands.KeyChordCommand(ui,[e.KEY_LEFTMETA,e.KEY_D])
rotate_wrist_checker = checkers.RotateWristChecker("Horizontal")
windows_d_task = tasks.Task(windows_d_command,rotate_wrist_checker)

windows_space_command = commands.KeyChordCommand(ui,[e.KEY_LEFTMETA,e.KEY_SPACE])
pinch_fingers = checkers.SqueezeFingersChecker('Thumb','Index')
windows_space_task = tasks.Task(windows_space_command,pinch_fingers)

write_letter_command = commands.WriteLetterCommand(ui)
recognise_checker_command = checkers.LetterRecognitionChecker()
write_letter_task = tasks.ArgumentTask(write_letter_command,recognise_checker_command)

big_guy = handler.Handler("Gesture",num_hands=1)
big_guy.attach_task(volume_up_task)
big_guy.attach_task(volume_down_task)
big_guy.attach_task(alt_tab_task)
big_guy.attach_task(windows_d_task)
big_guy.attach_task(windows_space_task)
big_guy.attach_task(write_letter_task)
big_guy.attach_task(tasks.Task(commands.MouseClick(mouse),checkers.SqueezeFingersChecker('Thumb','Middle')))
big_guy.attach_task(tasks.ArgumentTask(commands.MoveMouseCommand(mouse),checkers.FingerPointMouseChecker(mouse,(1920,1080))))
big_guy.run()