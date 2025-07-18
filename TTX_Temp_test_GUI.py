import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import pyvisa
import time
from datetime import datetime

class TempCycleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Temperature Cycling Control")
        self.root.geometry("600x500")
        
        # Initialize variables
        self.cycling_thread = None
        self.stop_cycling = False
        self.rm = None
        self.ics_4899a = None
        self.decimal = 0
        self.is_connected = False
        
        self.setup_gui()
        self.connect_to_device()
        
    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Temperature Cycling Control", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Connection status
        self.connection_label = ttk.Label(main_frame, text="Status: Disconnected", 
                                         foreground="red")
        self.connection_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Temperature settings frame
        temp_frame = ttk.LabelFrame(main_frame, text="Temperature Settings", padding="10")
        temp_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(temp_frame, text="Low Temperature (°F):").grid(row=0, column=0, sticky=tk.W)
        self.low_temp_var = tk.StringVar(value="32")
        ttk.Entry(temp_frame, textvariable=self.low_temp_var, width=10).grid(row=0, column=1, padx=(5, 0))
        
        ttk.Label(temp_frame, text="High Temperature (°F):").grid(row=1, column=0, sticky=tk.W)
        self.high_temp_var = tk.StringVar(value="140")
        ttk.Entry(temp_frame, textvariable=self.high_temp_var, width=10).grid(row=1, column=1, padx=(5, 0))
        
        # Current status frame
        status_frame = ttk.LabelFrame(main_frame, text="Current Status", padding="10")
        status_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(status_frame, text="Current Temperature:").grid(row=0, column=0, sticky=tk.W)
        self.current_temp_label = ttk.Label(status_frame, text="--°F")
        self.current_temp_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(status_frame, text="Target Temperature:").grid(row=1, column=0, sticky=tk.W)
        self.target_temp_label = ttk.Label(status_frame, text="--°F")
        self.target_temp_label.grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(status_frame, text="Cycling Status:").grid(row=2, column=0, sticky=tk.W)
        self.cycling_status_label = ttk.Label(status_frame, text="Stopped")
        self.cycling_status_label.grid(row=2, column=1, sticky=tk.W, padx=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        
        self.start_button = ttk.Button(button_frame, text="Start Cycling", 
                                      command=self.start_cycling, state="disabled")
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Cycling", 
                                     command=self.stop_cycling_func, state="disabled")
        self.stop_button.grid(row=0, column=1)
        
        # Log display
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, full_message)
        self.log_text.see(tk.END)
        print(message)  # Also print to console
        
    def connect_to_device(self):
        try:
            self.rm = pyvisa.ResourceManager()
            self.ics_4899a = self.rm.open_resource("GPIB0::4::INSTR")
            
            # Read decimal point configuration
            self.decimal = int(self.gpib_rd("R? 606, 1"))
            
            # Test connection
            device_id = self.gpib_rd("*IDN?")
            current_temp = self.read_temp(100)
            
            self.is_connected = True
            self.connection_label.config(text="Status: Connected", foreground="green")
            self.start_button.config(state="normal")
            self.log_message(f"Connected to: {device_id}")
            self.log_message(f"Current chamber temperature: {current_temp}°F")
            
            # Start temperature monitoring
            self.monitor_temperature()
            
        except Exception as e:
            self.log_message(f"Connection failed: {e}")
            self.connection_label.config(text="Status: Connection Failed", foreground="red")
    
    def gpib_rd(self, cmd):
        time.sleep(0.5)   
        try:
            ret = self.ics_4899a.query(cmd)
        except pyvisa.errors.VisaIOError as e: 
            self.log_message(f"Query Error: {e.args}")
            ret = ""
        return ret

    def gpib_wrt(self, cmd):
        time.sleep(0.5)  
        try:
            self.ics_4899a.write(cmd)
        except pyvisa.errors.VisaIOError as e: 
            self.log_message(f"Write Error: {e.args}")

    def read_temp(self, addr):
        return float(int(self.gpib_rd("R? " + str(addr) + ", 1")) / (10 ** self.decimal))

    def write_temp(self, addr, value):
        set_cmd = "W " + str(addr) + ", " + str(value * (10 ** self.decimal))
        self.gpib_wrt(set_cmd)
        
    def monitor_temperature(self):
        if self.is_connected:
            try:
                current_temp = self.read_temp(100)
                self.current_temp_label.config(text=f"{current_temp}°F")
            except Exception as e:
                self.log_message(f"Temperature read error: {e}")
                
        # Schedule next update
        self.root.after(2000, self.monitor_temperature)  # Update every 2 seconds
        
    def wait_for_temp_stabilization(self, target_temp, tolerance=2.5, stabilization_time=600):
        temp_stabilized = False
        stabilization_start = None
        
        while not temp_stabilized and not self.stop_cycling:
            current_temp = self.read_temp(100)
            if abs(current_temp - target_temp) <= tolerance:
                if stabilization_start is None:
                    stabilization_start = time.time()
                    self.log_message(f"Temperature within range at {current_temp}°F. Starting stabilization timer.")
                elif time.time() - stabilization_start > stabilization_time:
                    temp_stabilized = True
                    self.log_message(f"Temperature stabilized at {current_temp}°F for {stabilization_time/60:.1f} minutes.")
            else:
                stabilization_start = None
                self.log_message(f"Waiting for temperature to stabilize... Current: {current_temp}°F, Target: {target_temp}°F")
            
            # Check every second but allow for stop signal
            for _ in range(10):  # Check stop signal more frequently
                if self.stop_cycling:
                    return False
                time.sleep(0.1)
                
        return temp_stabilized
        
    def cycling_worker(self):
        try:
            low_temp = float(self.low_temp_var.get())
            high_temp = float(self.high_temp_var.get())
            
            self.log_message(f"Starting temperature cycling between {low_temp}°F and {high_temp}°F")
            
            # Turn chamber on
            self.gpib_wrt("W 2000, 1")
            time.sleep(1)
            
            while not self.stop_cycling:
                for temp in [low_temp, high_temp]:
                    if self.stop_cycling:
                        break
                        
                    self.log_message(f"Setting Temperature to: {temp}°F")
                    self.target_temp_label.config(text=f"{temp}°F")
                    self.write_temp(300, temp)
                    
                    # Wait for temperature stabilization
                    if not self.wait_for_temp_stabilization(temp):
                        break  # Stop cycling was requested
                        
                    if not self.stop_cycling:
                        self.log_message(f"Temperature cycle at {temp}°F completed. Moving to next temperature...")
                        
        except Exception as e:
            self.log_message(f"An error occurred: {e}")
        finally:
            # Turn chamber off
            if self.is_connected:
                self.gpib_wrt("W 2000, 0")
                self.log_message("Chamber turned off.")
            
            # Reset UI state
            self.cycling_status_label.config(text="Stopped")
            self.target_temp_label.config(text="--°F")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.stop_cycling = False
            
    def start_cycling(self):
        if not self.is_connected:
            self.log_message("Error: Not connected to device")
            return
            
        self.stop_cycling = False
        self.cycling_status_label.config(text="Running")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        # Start cycling in a separate thread
        self.cycling_thread = threading.Thread(target=self.cycling_worker, daemon=True)
        self.cycling_thread.start()
        
    def stop_cycling_func(self):
        self.stop_cycling = True
        self.log_message("Stop signal sent. Waiting for current operation to complete...")
        self.cycling_status_label.config(text="Stopping...")
        
    def on_closing(self):
        self.stop_cycling = True
        if self.cycling_thread and self.cycling_thread.is_alive():
            self.log_message("Waiting for cycling to stop...")
            self.cycling_thread.join(timeout=5)
            
        if self.is_connected and self.ics_4899a:
            try:
                self.gpib_wrt("W 2000, 0")  # Turn chamber off
            except:
                pass
                
        if self.rm:
            self.rm.close()
            
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TempCycleGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
