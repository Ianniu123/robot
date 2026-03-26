import time
import tkinter as tk
from tkinter import ttk, messagebox
from lerobot.motors.feetech import FeetechMotorsBus

# --- CHECK YOUR PORT ---
PORT = "/dev/tty.usbmodem5AAF2196261" 

class RawMotor:
    def __init__(self, motor_id, model):
        self.id = motor_id
        self.model = model

MOTORS = {
    "shoulder_pan": RawMotor(1, "sts3215"),
    "shoulder_lift": RawMotor(2, "sts3215"),
    "elbow_flex": RawMotor(3, "sts3215"),
    "wrist_flex": RawMotor(4, "sts3215"),
    "wrist_roll": RawMotor(5, "sts3215"),
    "gripper": RawMotor(6, "sts3215")
}

BOUNDS = {
    "shoulder_pan": (745, 3489),
    "shoulder_lift": (830, 3117),
    "elbow_flex": (824, 3055),
    "wrist_flex": (943, 3246),
    "wrist_roll": (1024, 3072),
    "gripper": (2033, 3565)
}

class RobotControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SO-101 Full Arm Dashboard")
        self.root.geometry("550x450")
        self.root.configure(padx=20, pady=20)

        style = ttk.Style()
        style.theme_use('clam')
        
        self.bus = FeetechMotorsBus(port=PORT, motors=MOTORS)
        self.resting_positions = {}
        
        try:
            self.bus.connect()
            print("🔌 Interrogating hardware for resting positions...")
            
            for motor_name in MOTORS.keys():
                # THE FIX: Added normalize=False to the READ command
                pos = self.bus.read("Present_Position", motor_name, normalize=False)
                
                # Handle list vs integer returns
                val = int(pos[0] if isinstance(pos, (list, tuple)) else pos)
                self.resting_positions[motor_name] = val
                
            for motor_name in MOTORS.keys():
                self.bus.write("Torque_Enable", motor_name, 1, normalize=False)
                
            print("✅ Hardware Connected. Sliders synced to reality.")
            
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            messagebox.showerror("Hardware Error", f"Could not connect to arm.\n{e}")
            self.root.destroy()
            return

        ttk.Label(root, text="Joint Controller", font=("Helvetica", 18, "bold")).pack(pady=(0, 15))

        self.sliders = {}
        self.value_labels = {}

        for index, (motor_name, (min_val, max_val)) in enumerate(BOUNDS.items()):
            frame = ttk.Frame(root)
            frame.pack(fill='x', pady=5)

            ttk.Label(frame, text=motor_name.replace("_", " ").title(), width=15, font=("Helvetica", 12)).pack(side='left')

            slider = ttk.Scale(frame, from_=min_val, to=max_val, orient='horizontal', length=200)
            
            # Start the slider at the REAL position we just read
            start_val = self.resting_positions.get(motor_name, 2048)
            slider.set(start_val) 
            
            slider.configure(command=lambda val, name=motor_name, idx=index: self.update_single_motor(name, idx))
            slider.pack(side='left', padx=10)

            val_label = ttk.Label(frame, text=str(start_val), width=10, font=("Courier", 12))
            val_label.pack(side='left')

            self.sliders[index] = slider
            self.value_labels[index] = val_label

        self.relax_btn = ttk.Button(root, text="Disable Torque (Relax)", command=self.relax_arm)
        self.relax_btn.pack(pady=30)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_single_motor(self, motor_name, index):
        raw_val = int(self.sliders[index].get())
        self.value_labels[index].config(text=str(raw_val))
        try:
            self.bus.write("Goal_Position", motor_name, raw_val, normalize=False)
        except Exception as e:
            print(f"Write error: {repr(e)}")

    def relax_arm(self):
        try:
            for motor_name in MOTORS.keys():
                self.bus.write("Torque_Enable", motor_name, 0, normalize=False)
            time.sleep(0.2) 
            print("🛑 Relaxed.")
        except: pass

    def on_closing(self):
        self.relax_arm()
        self.bus.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = RobotControllerApp(root)
    root.mainloop()