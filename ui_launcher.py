import json
import os
import queue
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Any, Callable

import cv2
import mediapipe as mp
from evdev import UInput, ecodes as e

import checkers
import commands
import handler
import tasks


APP_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_CONFIG_PATH = os.path.join(APP_DIR, "tasks.json")

GESTURE_OPTIONS = [
    "Closed_Fist",
    "Open_Palm",
    "Pointing_Up",
    "Thumb_Down",
    "Thumb_Up",
    "Victory",
    "ILoveYou",
]
FINGER_OPTIONS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
WRIST_DIRECTIONS = ["Horizontal", "Vertical"]
KEY_OPTIONS = [
    "KEY_VOLUMEUP",
    "KEY_VOLUMEDOWN",
    "KEY_LEFTALT",
    "KEY_TAB",
    "KEY_LEFTMETA",
    "KEY_D",
    "KEY_SPACE",
    "KEY_A",
    "KEY_B",
    "KEY_C",
]


@dataclass(frozen=True)
class ParamDef:
    '''Describes one configurable UI parameter for a registry entry.'''

    name: str
    label: str
    kind: str
    default: Any
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegistryItem:
    '''Declares UI metadata and object factory for a command/checker type.'''

    label: str
    kind: str
    params: tuple[ParamDef, ...]
    factory: Callable[[dict[str, Any], dict[str, Any]], Any]


def parse_keycode(key_name: str) -> int:
    '''Parses a key name into an evdev keycode, normalizing KEY_ prefix.'''

    normalized = key_name.strip().upper()
    if not normalized.startswith("KEY_"):
        normalized = f"KEY_{normalized}"
    if not hasattr(e, normalized):
        raise ValueError(f"Unknown key code: {key_name}")
    return getattr(e, normalized)


def parse_key_list(raw_keys: Any) -> list[int]:
    '''Parses a comma-separated key list (or list input) into keycodes.'''

    if isinstance(raw_keys, list):
        parts = [str(item).strip() for item in raw_keys if str(item).strip()]
    else:
        parts = [part.strip() for part in str(raw_keys).split(",") if part.strip()]
    if not parts:
        raise ValueError("At least one key is required")
    return [parse_keycode(key) for key in parts]


COMMAND_REGISTRY: dict[str, RegistryItem] = {
    "KeyChordCommand": RegistryItem(
        label="Key chord",
        kind="command",
        params=(
            ParamDef("keys", "Keys (comma separated)", "string", "KEY_LEFTALT,KEY_TAB"),
        ),
        factory=lambda p, c: commands.KeyChordCommand(c["keyboard"], parse_key_list(p["keys"])),
    ),
    "KeyHoldForTimeCommand": RegistryItem(
        label="Hold key for time",
        kind="command",
        params=(
            ParamDef("key", "Key", "key", "KEY_VOLUMEUP", tuple(KEY_OPTIONS)),
            ParamDef("hold_time", "Hold time (seconds)", "float", 0.5),
        ),
        factory=lambda p, c: commands.KeyHoldForTimeCommand(c["keyboard"], parse_keycode(p["key"]), float(p["hold_time"])),
    ),
    "KeyHoldCommand": RegistryItem(
        label="Hold key",
        kind="hold",
        params=(
            ParamDef("key", "Key", "key", "KEY_VOLUMEUP", tuple(KEY_OPTIONS)),
        ),
        factory=lambda p, c: commands.KeyHoldCommand(c["keyboard"], parse_keycode(p["key"])),
    ),
    "WriteLetterCommand": RegistryItem(
        label="Write recognised letter",
        kind="argument",
        params=(),
        factory=lambda p, c: commands.WriteLetterCommand(c["keyboard"]),
    ),
    "MouseClick": RegistryItem(
        label="Mouse left click",
        kind="command",
        params=(),
        factory=lambda p, c: commands.MouseClick(c["mouse"]),
    ),
    "MoveMouseCommand": RegistryItem(
        label="Move mouse",
        kind="argument",
        params=(),
        factory=lambda p, c: commands.MoveMouseCommand(c["mouse"]),
    ),
}

CHECKER_REGISTRY: dict[str, RegistryItem] = {
    "GestureChecker": RegistryItem(
        label="Gesture present",
        kind="checker",
        params=(
            ParamDef("gesture", "Gesture", "enum", "Thumb_Up", tuple(GESTURE_OPTIONS)),
        ),
        factory=lambda p, c: checkers.GestureChecker(str(p["gesture"])),
    ),
    "GestureAppearChecker": RegistryItem(
        label="Gesture appear",
        kind="checker",
        params=(
            ParamDef("gesture", "Gesture", "enum", "Closed_Fist", tuple(GESTURE_OPTIONS)),
        ),
        factory=lambda p, c: checkers.GestureAppearChecker(str(p["gesture"])),
    ),
    "RotateWristChecker": RegistryItem(
        label="Rotate wrist",
        kind="checker",
        params=(
            ParamDef("direction", "Direction", "enum", "Horizontal", tuple(WRIST_DIRECTIONS)),
        ),
        factory=lambda p, c: checkers.RotateWristChecker(str(p["direction"])),
    ),
    "MoveHandChecker": RegistryItem(
        label="Move hand",
        kind="checker",
        params=(
            ParamDef("direction_x", "Direction X", "float", 1.0),
            ParamDef("direction_y", "Direction Y", "float", 0.0),
            ParamDef("distance", "Distance", "float", 0.08),
        ),
        factory=lambda p, c: checkers.MoveHandChecker((float(p["direction_x"]), float(p["direction_y"])), float(p["distance"])),
    ),
    "SqueezeFingersChecker": RegistryItem(
        label="Squeeze fingers",
        kind="checker",
        params=(
            ParamDef("finger_1", "Finger 1", "enum", "Thumb", tuple(FINGER_OPTIONS)),
            ParamDef("finger_2", "Finger 2", "enum", "Index", tuple(FINGER_OPTIONS)),
        ),
        factory=lambda p, c: checkers.SqueezeFingersChecker(str(p["finger_1"]), str(p["finger_2"])),
    ),
    "LetterRecognitionChecker": RegistryItem(
        label="Recognise letter in air",
        kind="argument_checker",
        params=(),
        factory=lambda p, c: checkers.LetterRecognitionChecker(),
    ),
    "FingerPointMouseChecker": RegistryItem(
        label="Point finger to move mouse",
        kind="argument_checker",
        params=(),
        factory=lambda p, c: checkers.FingerPointMouseChecker(c["mouse"], c["screen_resolution"]),
    ),
}

DEFAULT_TASK_SPECS = [
    {
        "task_type": "HoldTask",
        "command": {"name": "KeyHoldCommand", "params": {"key": "KEY_VOLUMEUP"}},
        "checker": {"name": "GestureChecker", "params": {"gesture": "Thumb_Up"}},
    },
    {
        "task_type": "HoldTask",
        "command": {"name": "KeyHoldCommand", "params": {"key": "KEY_VOLUMEDOWN"}},
        "checker": {"name": "GestureChecker", "params": {"gesture": "Thumb_Down"}},
    },
    {
        "task_type": "Task",
        "command": {"name": "KeyChordCommand", "params": {"keys": "KEY_LEFTALT,KEY_TAB"}},
        "checker": {"name": "GestureAppearChecker", "params": {"gesture": "Closed_Fist"}},
    },
]


def infer_task_type(command_name: str, checker_name: str) -> str:
    '''Infers the concrete task wrapper type from command/checker kinds.'''

    command_kind = COMMAND_REGISTRY[command_name].kind
    checker_kind = CHECKER_REGISTRY[checker_name].kind
    if command_kind == "hold" and checker_kind == "checker":
        return "HoldTask"
    if command_kind == "argument" and checker_kind == "argument_checker":
        return "ArgumentTask"
    if command_kind == "command" and checker_kind == "checker":
        return "Task"
    raise ValueError("Selected command/checker are incompatible")


def build_task_from_spec(task_spec: dict[str, Any], context: dict[str, Any]) -> tasks.Task:
    '''Builds a runtime Task/HoldTask/ArgumentTask object from one saved task spec.'''

    command_spec = task_spec["command"]
    checker_spec = task_spec["checker"]
    command_item = COMMAND_REGISTRY[command_spec["name"]]
    checker_item = CHECKER_REGISTRY[checker_spec["name"]]
    command_obj = command_item.factory(command_spec["params"], context)
    checker_obj = checker_item.factory(checker_spec["params"], context)
    task_type = task_spec["task_type"]
    if task_type == "Task":
        return tasks.Task(command_obj, checker_obj)
    if task_type == "HoldTask":
        return tasks.HoldTask(command_obj, checker_obj)
    if task_type == "ArgumentTask":
        return tasks.ArgumentTask(command_obj, checker_obj)
    raise ValueError(f"Unknown task type: {task_type}")


def run_runtime(task_specs: list[dict[str, Any]], stop_event: threading.Event, status_queue: queue.Queue, screen_resolution: tuple[int, int]) -> None:
    '''Runs the camera + gesture loop and dispatches runtime task actions until stopped.'''

    virtual_keyboard = None
    virtual_mouse = None
    cap = None
    runtime_handler = None
    try:
        virtual_keyboard = UInput()
        time.sleep(0.3)
        mouse_capabilities = {
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL],
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE],
        }
        virtual_mouse = UInput(mouse_capabilities, bustype=e.BUS_USB)

        context = {
            "keyboard": virtual_keyboard,
            "mouse": virtual_mouse,
            "screen_resolution": screen_resolution,
        }
        runtime_handler = handler.Handler("Gesture", num_hands=1)
        for task_spec in task_specs:
            runtime_handler.attach_task(build_task_from_spec(task_spec, context))

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Could not open webcam")

        status_queue.put(("running", "Running"))
        timestamp = 0
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                continue
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            runtime_handler.model.start_inference(mp_image, timestamp)
            cv2.waitKey(1)
            timestamp += 1
    except Exception as exc:
        status_queue.put(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        if runtime_handler is not None:
            runtime_handler.model.release()
        if virtual_mouse is not None:
            virtual_mouse.close()
        if virtual_keyboard is not None:
            virtual_keyboard.close()
        status_queue.put(("stopped", "Stopped"))


class AddTaskDialog(tk.Toplevel):
    '''Modal dialog for selecting command/checker pairs and their parameters.'''

    def __init__(self, parent: tk.Misc):
        '''Initializes controls, binds dropdown changes, and prepares modal behavior.'''

        super().__init__(parent)
        self.title("Add Task")
        self.configure(bg="#10131a")
        self.resizable(False, False)
        self.result = None
        self._command_vars: dict[str, tk.StringVar] = {}
        self._checker_vars: dict[str, tk.StringVar] = {}

        self.command_name_var = tk.StringVar(value=next(iter(COMMAND_REGISTRY.keys())))
        self.checker_name_var = tk.StringVar(value=next(iter(CHECKER_REGISTRY.keys())))

        container = tk.Frame(self, bg="#10131a", padx=14, pady=12)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Command", bg="#10131a", fg="#d9e1ef").grid(row=0, column=0, sticky="w")
        self.command_combo = ttk.Combobox(
            container,
            values=list(COMMAND_REGISTRY.keys()),
            textvariable=self.command_name_var,
            state="readonly",
            width=36,
        )
        self.command_combo.grid(row=1, column=0, sticky="we", pady=(0, 8))
        self.command_combo.bind("<<ComboboxSelected>>", lambda _: self.render_fields())

        tk.Label(container, text="Checker", bg="#10131a", fg="#d9e1ef").grid(row=2, column=0, sticky="w")
        self.checker_combo = ttk.Combobox(
            container,
            values=list(CHECKER_REGISTRY.keys()),
            textvariable=self.checker_name_var,
            state="readonly",
            width=36,
        )
        self.checker_combo.grid(row=3, column=0, sticky="we", pady=(0, 8))
        self.checker_combo.bind("<<ComboboxSelected>>", lambda _: self.render_fields())

        self.command_fields_frame = tk.Frame(container, bg="#10131a")
        self.command_fields_frame.grid(row=4, column=0, sticky="we", pady=(0, 8))
        self.checker_fields_frame = tk.Frame(container, bg="#10131a")
        self.checker_fields_frame.grid(row=5, column=0, sticky="we", pady=(0, 8))

        button_row = tk.Frame(container, bg="#10131a")
        button_row.grid(row=6, column=0, sticky="e")
        tk.Button(button_row, text="Cancel", command=self.destroy, bg="#273142", fg="#d9e1ef", relief="flat").pack(side="right")
        tk.Button(button_row, text="Add", command=self.on_add, bg="#3c7dff", fg="#ffffff", relief="flat").pack(side="right", padx=(0, 8))

        self.render_fields()
        self.grab_set()
        self.transient(parent)

    def render_fields(self) -> None:
        '''Rebuilds dynamic parameter controls for selected command/checker types.'''

        for child in self.command_fields_frame.winfo_children():
            child.destroy()
        for child in self.checker_fields_frame.winfo_children():
            child.destroy()
        self._command_vars.clear()
        self._checker_vars.clear()
        self._render_registry_fields(self.command_fields_frame, COMMAND_REGISTRY[self.command_name_var.get()], self._command_vars)
        self._render_registry_fields(self.checker_fields_frame, CHECKER_REGISTRY[self.checker_name_var.get()], self._checker_vars)

    def _render_registry_fields(self, frame: tk.Frame, item: RegistryItem, target: dict[str, tk.StringVar]) -> None:
        '''Renders field widgets from registry metadata into the provided frame.'''

        if not item.params:
            tk.Label(frame, text="No extra parameters", bg="#10131a", fg="#97a5bd").grid(row=0, column=0, sticky="w")
            return
        for index, param in enumerate(item.params):
            tk.Label(frame, text=param.label, bg="#10131a", fg="#d9e1ef").grid(row=index * 2, column=0, sticky="w")
            var = tk.StringVar(value=str(param.default))
            target[param.name] = var
            if param.kind in {"enum", "key"}:
                widget = ttk.Combobox(frame, values=list(param.options), textvariable=var, width=36)
                if param.kind == "enum":
                    widget.configure(state="readonly")
            else:
                widget = tk.Entry(frame, textvariable=var, width=39, bg="#1d2431", fg="#d9e1ef", insertbackground="#d9e1ef", relief="flat")
            widget.grid(row=index * 2 + 1, column=0, sticky="we", pady=(0, 6))

    def on_add(self) -> None:
        '''Validates selections, converts values, and returns a task spec payload.'''

        command_name = self.command_name_var.get()
        checker_name = self.checker_name_var.get()
        try:
            task_type = infer_task_type(command_name, checker_name)
            command_params = self._convert_params(COMMAND_REGISTRY[command_name].params, self._command_vars)
            checker_params = self._convert_params(CHECKER_REGISTRY[checker_name].params, self._checker_vars)
        except ValueError as exc:
            messagebox.showerror("Invalid task", str(exc), parent=self)
            return
        self.result = {
            "task_type": task_type,
            "command": {"name": command_name, "params": command_params},
            "checker": {"name": checker_name, "params": checker_params},
        }
        self.destroy()

    def _convert_params(self, params: tuple[ParamDef, ...], values: dict[str, tk.StringVar]) -> dict[str, Any]:
        '''Converts string UI values to typed parameter values based on ParamDef kinds.'''

        converted = {}
        for param in params:
            raw = values[param.name].get().strip()
            if param.kind == "int":
                converted[param.name] = int(raw)
            elif param.kind == "float":
                converted[param.name] = float(raw)
            else:
                converted[param.name] = raw
        return converted


class GestureLauncherUI:
    '''Main launcher window that owns task specs, runtime state, and user actions.'''

    def __init__(self, root: tk.Tk):
        '''Builds the full UI, initializes state, and starts status polling.'''

        self.root = root
        self.task_specs = self.load_tasks()
        self.runtime_thread: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.status_queue: queue.Queue = queue.Queue()

        self.root.title("Pisi Launcher")
        self.root.geometry("760x500")
        self.root.configure(bg="#0f1219")

        title = tk.Label(root, text="Pisi Task Launcher", bg="#0f1219", fg="#e7efff", font=("Arial", 15, "bold"))
        title.pack(anchor="w", padx=16, pady=(12, 8))

        top_row = tk.Frame(root, bg="#0f1219")
        top_row.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(top_row, text="Screen width", bg="#0f1219", fg="#d9e1ef").pack(side="left")
        self.width_var = tk.StringVar(value="1920")
        tk.Entry(top_row, width=8, textvariable=self.width_var, bg="#1c2430", fg="#d9e1ef", insertbackground="#d9e1ef", relief="flat").pack(side="left", padx=(6, 12))
        tk.Label(top_row, text="Screen height", bg="#0f1219", fg="#d9e1ef").pack(side="left")
        self.height_var = tk.StringVar(value="1080")
        tk.Entry(top_row, width=8, textvariable=self.height_var, bg="#1c2430", fg="#d9e1ef", insertbackground="#d9e1ef", relief="flat").pack(side="left", padx=(6, 0))

        main_row = tk.Frame(root, bg="#0f1219")
        main_row.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        left_panel = tk.Frame(main_row, bg="#121825", bd=0, highlightthickness=1, highlightbackground="#2a3344")
        left_panel.pack(side="left", fill="both", expand=True)
        self.task_list = tk.Listbox(left_panel, bg="#121825", fg="#d9e1ef", selectbackground="#335fa8", bd=0, highlightthickness=0)
        self.task_list.pack(fill="both", expand=True, padx=8, pady=8)

        buttons_panel = tk.Frame(main_row, bg="#0f1219", padx=10)
        buttons_panel.pack(side="left", fill="y")
        tk.Button(buttons_panel, text="Add Task", command=self.add_task, width=14, bg="#273142", fg="#d9e1ef", relief="flat").pack(pady=(0, 8))
        tk.Button(buttons_panel, text="Remove Task", command=self.remove_task, width=14, bg="#273142", fg="#d9e1ef", relief="flat").pack(pady=(0, 8))
        tk.Button(buttons_panel, text="Save Tasks", command=self.save_tasks, width=14, bg="#273142", fg="#d9e1ef", relief="flat").pack()

        bottom_row = tk.Frame(root, bg="#0f1219")
        bottom_row.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(bottom_row, text="Launch", command=self.launch, width=14, bg="#3478ff", fg="#ffffff", relief="flat").pack(side="left")
        tk.Button(bottom_row, text="Stop", command=self.stop, width=14, bg="#913f4b", fg="#ffffff", relief="flat").pack(side="left", padx=(8, 0))
        self.status_var = tk.StringVar(value="Status: idle")
        tk.Label(bottom_row, textvariable=self.status_var, bg="#0f1219", fg="#b8c5db").pack(side="right")

        self.refresh_task_list()
        self.root.after(200, self.poll_status)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_tasks(self) -> list[dict[str, Any]]:
        '''Loads task specs from tasks.json, falling back to defaults on any failure.'''

        if not os.path.exists(TASKS_CONFIG_PATH):
            return list(DEFAULT_TASK_SPECS)
        try:
            with open(TASKS_CONFIG_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                raise ValueError("tasks.json must contain a list")
            return data
        except Exception:
            return list(DEFAULT_TASK_SPECS)

    def save_tasks(self) -> None:
        '''Saves current in-memory task specs to tasks.json.'''

        with open(TASKS_CONFIG_PATH, "w", encoding="utf-8") as file:
            json.dump(self.task_specs, file, indent=2)
        self.status_var.set("Status: tasks saved")

    def refresh_task_list(self) -> None:
        '''Refreshes the listbox content from current task specs.'''

        self.task_list.delete(0, tk.END)
        for index, task_spec in enumerate(self.task_specs, start=1):
            command_name = task_spec["command"]["name"]
            checker_name = task_spec["checker"]["name"]
            task_type = task_spec["task_type"]
            self.task_list.insert(tk.END, f"{index}. {task_type}: {command_name} + {checker_name}")

    def add_task(self) -> None:
        '''Opens the add-task dialog and appends the created task spec.'''

        dialog = AddTaskDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result is None:
            return
        self.task_specs.append(dialog.result)
        self.refresh_task_list()
        self.status_var.set("Status: task added")

    def remove_task(self) -> None:
        '''Removes the currently selected task spec from the list.'''

        selection = self.task_list.curselection()
        if not selection:
            self.status_var.set("Status: select a task to remove")
            return
        index = selection[0]
        self.task_specs.pop(index)
        self.refresh_task_list()
        self.status_var.set("Status: task removed")

    def _read_resolution(self) -> tuple[int, int]:
        '''Reads and validates screen resolution inputs used by mouse-point checker.'''

        width = int(self.width_var.get().strip())
        height = int(self.height_var.get().strip())
        if width <= 0 or height <= 0:
            raise ValueError("Screen resolution must be positive")
        return (width, height)

    def launch(self) -> None:
        '''Validates config and starts the runtime worker thread if not already running.'''

        if self.runtime_thread is not None and self.runtime_thread.is_alive():
            self.status_var.set("Status: already running")
            return
        if not self.task_specs:
            self.status_var.set("Status: add at least one task")
            return
        try:
            screen_resolution = self._read_resolution()
            for task_spec in self.task_specs:
                infer_task_type(task_spec["command"]["name"], task_spec["checker"]["name"])
        except Exception as exc:
            self.status_var.set(f"Status: invalid config ({exc})")
            return

        self.stop_event = threading.Event()
        self.runtime_thread = threading.Thread(
            target=run_runtime,
            args=(self.task_specs, self.stop_event, self.status_queue, screen_resolution),
            daemon=True,
        )
        self.runtime_thread.start()
        self.status_var.set("Status: launching...")

    def stop(self) -> None:
        '''Signals the runtime loop to stop through the shared event flag.'''

        if self.stop_event is None:
            self.status_var.set("Status: not running")
            return
        self.stop_event.set()
        self.status_var.set("Status: stopping...")

    def poll_status(self) -> None:
        '''Consumes runtime status messages and updates the status label continuously.'''

        try:
            while True:
                status, message = self.status_queue.get_nowait()
                if status == "running":
                    self.status_var.set(f"Status: {message}")
                elif status == "error":
                    self.status_var.set(f"Status: {message}")
                elif status == "stopped":
                    self.status_var.set(f"Status: {message}")
        except queue.Empty:
            pass
        self.root.after(200, self.poll_status)

    def on_close(self) -> None:
        '''Stops runtime if needed and closes the launcher window.'''

        if self.stop_event is not None:
            self.stop_event.set()
        self.root.destroy()


def main() -> None:
    '''Application entry point for launching the Tkinter UI.'''

    root = tk.Tk()
    GestureLauncherUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
