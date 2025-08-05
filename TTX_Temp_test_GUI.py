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
        self.root.geometry("600x600")
        
        # Initialize variables
        self.cycling_thread = None
        self.stop_cycling = False
        self.rm = None
        self.ics_4899a = None
        self.decimal = 0
        self.is_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.gpib_timeout = 5000  # 5 second timeout
        self.retry_count = 3
        self.temp_read_timeout = 10000  # Longer timeout for temperature reads
        self.cycle_count = 0  # Track total cycles completed
        
        # Transition timing variables
        self.transition_start_time = None
        self.transition_start_temp = None
        self.heating_times = []  # List to store heating transition times
        self.cooling_times = []  # List to store cooling transition times
        self.current_transition_type = None  # 'heating' or 'cooling'
        
        # Hold time configuration (default 5 minutes = 300 seconds)
        self.hold_time_seconds = 300
        
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
        
        ttk.Label(temp_frame, text="Hold Time (minutes):").grid(row=2, column=0, sticky=tk.W)
        self.hold_time_var = tk.StringVar(value="5")
        ttk.Entry(temp_frame, textvariable=self.hold_time_var, width=10).grid(row=2, column=1, padx=(5, 0))
        
        # Timeout settings frame
        timeout_frame = ttk.LabelFrame(main_frame, text="Communication Settings", padding="10")
        timeout_frame.grid(row=2, column=2, sticky=(tk.W, tk.E), pady=(0, 10), padx=(10, 0))
        
        ttk.Label(timeout_frame, text="GPIB Timeout (ms):").grid(row=0, column=0, sticky=tk.W)
        self.timeout_var = tk.StringVar(value="5000")
        timeout_entry = ttk.Entry(timeout_frame, textvariable=self.timeout_var, width=8)
        timeout_entry.grid(row=0, column=1, padx=(5, 0))
        
        ttk.Button(timeout_frame, text="Apply", command=self.update_timeout).grid(row=1, column=0, columnspan=2, pady=(5, 0))
        
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
        
        ttk.Label(status_frame, text="Hold Timer:").grid(row=3, column=0, sticky=tk.W)
        self.timer_label = ttk.Label(status_frame, text="--:--")
        self.timer_label.grid(row=3, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(status_frame, text="Cycle Count:").grid(row=4, column=0, sticky=tk.W)
        self.cycle_count_label = ttk.Label(status_frame, text="0")
        self.cycle_count_label.grid(row=4, column=1, sticky=tk.W, padx=(5, 0))
        
        # Transition timing frame
        timing_frame = ttk.LabelFrame(main_frame, text="Transition Timing", padding="10")
        timing_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(timing_frame, text="Current Phase:").grid(row=0, column=0, sticky=tk.W)
        self.current_phase_label = ttk.Label(timing_frame, text="--")
        self.current_phase_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(timing_frame, text="Transition Timer:").grid(row=1, column=0, sticky=tk.W)
        self.transition_timer_label = ttk.Label(timing_frame, text="--:--")
        self.transition_timer_label.grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(timing_frame, text="Last Heating Time:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.last_heating_time_label = ttk.Label(timing_frame, text="--:--")
        self.last_heating_time_label.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(timing_frame, text="Last Cooling Time:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0))
        self.last_cooling_time_label = ttk.Label(timing_frame, text="--:--")
        self.last_cooling_time_label.grid(row=1, column=3, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(timing_frame, text="Avg Heating Time:").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        self.avg_heating_time_label = ttk.Label(timing_frame, text="--:--")
        self.avg_heating_time_label.grid(row=0, column=5, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(timing_frame, text="Avg Cooling Time:").grid(row=1, column=4, sticky=tk.W, padx=(20, 0))
        self.avg_cooling_time_label = ttk.Label(timing_frame, text="--:--")
        self.avg_cooling_time_label.grid(row=1, column=5, sticky=tk.W, padx=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        
        self.start_button = ttk.Button(button_frame, text="Start Cycling", 
                                      command=self.start_cycling, state="disabled")
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Cycling", 
                                     command=self.stop_cycling_func, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.reset_counter_button = ttk.Button(button_frame, text="Reset Counter", 
                                              command=self.reset_cycle_counter)
        self.reset_counter_button.grid(row=0, column=2, padx=(0, 10))
        
        self.reset_timing_button = ttk.Button(button_frame, text="Reset Timing", 
                                             command=self.reset_timing_data)
        self.reset_timing_button.grid(row=0, column=3)
        
        # Log display
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, full_message)
        self.log_text.see(tk.END)
        print(message)  # Also print to console
        
    def update_timeout(self):
        """Update GPIB timeout setting"""
        try:
            new_timeout = int(self.timeout_var.get())
            if new_timeout < 1000:
                new_timeout = 1000  # Minimum 1 second
            self.gpib_timeout = new_timeout
            self.temp_read_timeout = max(new_timeout * 2, 10000)  # Double timeout for temp reads
            if self.ics_4899a:
                self.ics_4899a.timeout = new_timeout
            self.log_message(f"GPIB timeout updated to {new_timeout}ms (temp reads: {self.temp_read_timeout}ms)")
        except ValueError:
            self.log_message("Invalid timeout value. Using default 5000ms")
            self.timeout_var.set("5000")
            self.gpib_timeout = 5000
            self.temp_read_timeout = 10000
        
    def update_hold_time(self):
        """Update hold time from GUI input"""
        try:
            hold_time_minutes = float(self.hold_time_var.get())
            if hold_time_minutes <= 0:
                hold_time_minutes = 5  # Default to 5 minutes if invalid
                self.hold_time_var.set("5")
            self.hold_time_seconds = int(hold_time_minutes * 60)
            self.log_message(f"Hold time updated to {hold_time_minutes} minutes ({self.hold_time_seconds} seconds)")
        except ValueError:
            self.log_message("Invalid hold time value. Using default 5 minutes")
            self.hold_time_var.set("5")
            self.hold_time_seconds = 300

    def format_time(self, seconds):
        """Format seconds into minutes:seconds format"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def update_timer_display(self, elapsed_time, total_time):
        """Update the timer display in the GUI"""
        remaining_time = total_time - elapsed_time
        timer_text = f"{self.format_time(elapsed_time)}/{self.format_time(total_time)}"
        self.timer_label.config(text=timer_text)

    def reconnect_device(self):
        """Attempt to reconnect to the GPIB device"""
        self.log_message("Attempting to reconnect to GPIB device...")
        try:
            # Close existing connections
            if self.ics_4899a:
                try:
                    self.ics_4899a.close()
                except:
                    pass
            
            if self.rm:
                try:
                    self.rm.close()
                except:
                    pass
            
            # Wait before reconnecting
            time.sleep(2)
            
            # Reinitialize connection
            self.rm = pyvisa.ResourceManager()
            self.ics_4899a = self.rm.open_resource("GPIB0::4::INSTR")
            
            # Configure timeout and other settings
            self.ics_4899a.timeout = self.gpib_timeout
            self.ics_4899a.read_termination = '\n'
            self.ics_4899a.write_termination = '\n'
            
            # Test connection with retries
            for attempt in range(3):
                try:
                    test_response = self.ics_4899a.query("*IDN?")
                    if test_response and test_response.strip():
                        # Read decimal configuration
                        decimal_response = self.gpib_rd_with_retry("R? 606, 1")
                        if decimal_response:
                            self.decimal = int(decimal_response)
                            self.is_connected = True
                            self.connection_label.config(text="Status: Reconnected", foreground="green")
                            self.log_message("Successfully reconnected to GPIB device")
                            return True
                    time.sleep(1)  # Wait between attempts
                except:
                    continue
            
            raise Exception("Failed to establish stable connection after retries")
                
        except Exception as e:
            self.is_connected = False
            self.connection_label.config(text="Status: Connection Failed", foreground="red")
            self.log_message(f"Reconnection failed: {e}")
            return False
        
    def connect_to_device(self):
        try:
            self.rm = pyvisa.ResourceManager()
            self.ics_4899a = self.rm.open_resource("GPIB0::4::INSTR")
            
            # Configure GPIB settings
            self.ics_4899a.timeout = self.gpib_timeout
            self.ics_4899a.read_termination = '\n'
            self.ics_4899a.write_termination = '\n'
            
            # Read decimal point configuration with validation
            decimal_response = self.gpib_rd_with_retry("R? 606, 1")
            if decimal_response and decimal_response.strip():
                self.decimal = int(decimal_response)
            else:
                raise Exception("Could not read decimal configuration")
            
            # Test connection
            device_id = self.gpib_rd_with_retry("*IDN?")
            if not device_id or not device_id.strip():
                raise Exception("Could not read device ID")
                
            current_temp = self.read_temp_with_retry(100)
            if current_temp is None:
                raise Exception("Could not read temperature")
            
            self.is_connected = True
            self.connection_label.config(text="Status: Connected", foreground="green")
            self.start_button.config(state="normal")
            self.log_message(f"Connected to: {device_id.strip()}")
            self.log_message(f"Current chamber temperature: {current_temp}°F")
            
            # Start temperature monitoring
            self.monitor_temperature()
            
        except Exception as e:
            self.log_message(f"Connection failed: {e}")
            self.connection_label.config(text="Status: Connection Failed", foreground="red")
    
    def gpib_rd_with_retry(self, cmd, retries=None, extended_timeout=False):
        """GPIB read with retry logic"""
        if retries is None:
            retries = self.retry_count
            
        # Save original timeout
        original_timeout = self.ics_4899a.timeout if self.ics_4899a else self.gpib_timeout
        
        try:
            # Use extended timeout for temperature reads during stabilization
            if extended_timeout and self.ics_4899a:
                self.ics_4899a.timeout = self.temp_read_timeout
            
            for attempt in range(retries):
                try:
                    time.sleep(0.3)  # Slightly longer delay
                    ret = self.ics_4899a.query(cmd)
                    if ret is not None and ret.strip() != "":
                        return ret.strip()
                    else:
                        if attempt < retries - 1:
                            self.log_message(f"Empty response for '{cmd}', retry {attempt + 1}/{retries}")
                            time.sleep(1)  # Longer wait between retries
                            continue
                except (pyvisa.errors.VisaIOError, pyvisa.errors.InvalidSession) as e:
                    error_msg = str(e)
                    if "TMO" in error_msg or "timeout" in error_msg.lower():
                        self.log_message(f"Timeout for '{cmd}', retry {attempt + 1}/{retries}")
                    elif "I/O" in error_msg:
                        self.log_message(f"I/O error for '{cmd}', retry {attempt + 1}/{retries}")
                        # For I/O errors, wait longer and try to reset connection
                        if attempt == 1:  # On second attempt, try to reset
                            time.sleep(2)
                            try:
                                self.ics_4899a.clear()  # Clear any pending operations
                            except:
                                pass
                    else:
                        self.log_message(f"GPIB error for '{cmd}', retry {attempt + 1}/{retries}: {e}")
                    
                    if attempt < retries - 1:
                        time.sleep(2)  # Longer wait between error retries
                        continue
                    else:
                        self.log_message(f"GPIB Query failed after {retries} attempts: {e}")
                        self.is_connected = False
                        
        finally:
            # Restore original timeout
            if self.ics_4899a:
                self.ics_4899a.timeout = original_timeout
                    
        return ""

    def gpib_wrt_with_retry(self, cmd, retries=None):
        """GPIB write with retry logic"""
        if retries is None:
            retries = self.retry_count
            
        for attempt in range(retries):
            try:
                time.sleep(0.3)
                self.ics_4899a.write(cmd)
                return True
            except (pyvisa.errors.VisaIOError, pyvisa.errors.InvalidSession) as e:
                error_msg = str(e)
                if "I/O" in error_msg and attempt == 1:  # On second attempt for I/O errors
                    try:
                        self.ics_4899a.clear()  # Clear any pending operations
                        time.sleep(1)
                    except:
                        pass
                        
                if attempt < retries - 1:
                    self.log_message(f"GPIB write error for '{cmd}', retry {attempt + 1}/{retries}: {e}")
                    time.sleep(2)
                    continue
                else:
                    self.log_message(f"GPIB Write failed after {retries} attempts: {e}")
                    self.is_connected = False
                    
        return False

    def gpib_rd(self, cmd):
        return self.gpib_rd_with_retry(cmd, 1)  # Single attempt for backward compatibility

    def gpib_wrt(self, cmd):
        return self.gpib_wrt_with_retry(cmd, 1)  # Single attempt for backward compatibility

    def read_temp_with_retry(self, addr, extended_timeout=False):
        """Read temperature with retry logic"""
        for attempt in range(self.retry_count):
            try:
                response = self.gpib_rd_with_retry("R? " + str(addr) + ", 1", extended_timeout=extended_timeout)
                if not response or response == "":
                    if attempt < self.retry_count - 1:
                        self.log_message(f"Empty temperature response, retry {attempt + 1}/{self.retry_count}")
                        time.sleep(1)
                        continue
                    return None
                temp_raw = int(response)
                return float(temp_raw / (10 ** self.decimal))
            except (ValueError, TypeError) as e:
                if attempt < self.retry_count - 1:
                    self.log_message(f"Temperature conversion error, retry {attempt + 1}: {e}")
                    time.sleep(1)
                    continue
                else:
                    self.log_message(f"Temperature conversion error after {self.retry_count} attempts: {e}")
                    return None
            except Exception as e:
                if attempt < self.retry_count - 1:
                    self.log_message(f"Temperature read error, retry {attempt + 1}: {e}")
                    time.sleep(1)
                    continue
                else:
                    self.log_message(f"Temperature read error after {self.retry_count} attempts: {e}")
                    return None
        return None

    def read_temp(self, addr, extended_timeout=False):
        return self.read_temp_with_retry(addr, extended_timeout)

    def write_temp(self, addr, value):
        set_cmd = "W " + str(addr) + ", " + str(int(value * (10 ** self.decimal)))
        return self.gpib_wrt_with_retry(set_cmd)
        
    def monitor_temperature(self):
        if self.is_connected:
            current_temp = self.read_temp(100)
            if current_temp is not None:
                self.current_temp_label.config(text=f"{current_temp}°F")
            else:
                self.current_temp_label.config(text="--°F")
                # Try to reconnect if we lost connection
                if not self.is_connected:
                    self.log_message("Lost connection during monitoring. Attempting reconnection...")
                    self.reconnect_device()
                
        # Schedule next update
        self.root.after(3000, self.monitor_temperature)  # Increased to 3 seconds to reduce load
        
    def wait_for_temp_stabilization(self, target_temp, tolerance=2.5, stabilization_time=None):
        # Use configured hold time if not specified
        if stabilization_time is None:
            self.update_hold_time()  # Update from GUI
            stabilization_time = self.hold_time_seconds
            
        temp_stabilized = False
        stabilization_start = None
        consecutive_failures = 0
        max_failures = 5  # Increased tolerance for failures during stabilization
        last_gui_update = time.time()
        last_transition_update = time.time()
        temp_read_interval = 3  # Read temperature every 3 seconds during stabilization
        transition_started = False
        
        while not temp_stabilized and not self.stop_cycling:
            # Use extended timeout for temperature reads during stabilization
            current_temp = self.read_temp(100, extended_timeout=True)
            
            if current_temp is None:
                consecutive_failures += 1
                self.log_message(f"Temperature read failure {consecutive_failures}/{max_failures}")
                
                if consecutive_failures >= max_failures:
                    self.log_message("Too many consecutive temperature read failures. Attempting reconnection...")
                    if self.reconnect_device():
                        consecutive_failures = 0
                        time.sleep(3)  # Wait after reconnection
                        continue
                    else:
                        self.log_message("Reconnection failed. Stopping temperature cycling.")
                        return False
                        
                # Wait longer between failed attempts during stabilization
                time.sleep(5)
                continue
            else:
                consecutive_failures = 0
                
            # Start transition timing if not started yet
            if not transition_started and self.transition_start_time is None:
                self.start_transition_timing(current_temp, target_temp)
                transition_started = True
                
            # Update transition timer every 5 seconds
            if time.time() - last_transition_update >= 5:
                self.update_transition_timer()
                last_transition_update = time.time()
                
            if abs(current_temp - target_temp) <= tolerance:
                # Complete transition timing when we first reach target
                if self.transition_start_time is not None:
                    self.complete_transition_timing(current_temp)
                    
                if stabilization_start is None:
                    stabilization_start = time.time()
                    self.log_message(f"Temperature within range at {current_temp}°F. Starting {stabilization_time/60:.1f} minute hold timer.")
                    self.timer_label.config(text=f"00:00/{self.format_time(stabilization_time)}")
                else:
                    elapsed_time = time.time() - stabilization_start
                    
                    # Update GUI timer every 10 seconds during stabilization
                    if time.time() - last_gui_update >= 10:
                        self.update_timer_display(elapsed_time, stabilization_time)
                        self.log_message(f"Stabilizing at {current_temp}°F - {self.format_time(elapsed_time)}/{self.format_time(stabilization_time)}")
                        last_gui_update = time.time()
                    
                    if elapsed_time >= stabilization_time:
                        temp_stabilized = True
                        self.log_message(f"Temperature stabilized at {current_temp}°F for {stabilization_time/60:.1f} minutes. ✓")
                        self.timer_label.config(text="Complete")
            else:
                stabilization_start = None
                self.timer_label.config(text="--:--")
                self.log_message(f"Waiting for temperature to stabilize... Current: {current_temp}°F, Target: {target_temp}°F")
                last_gui_update = time.time()
            
            # Check for stop signal more frequently but read temp less frequently
            for _ in range(temp_read_interval * 10):  # Check stop signal every 0.1 seconds
                if self.stop_cycling:
                    return False
                time.sleep(0.1)
                
        return temp_stabilized
        
    def reset_cycle_counter(self):
        """Reset the cycle counter to zero"""
        self.cycle_count = 0
        self.cycle_count_label.config(text="0")
        self.log_message("Cycle counter reset to 0")

    def reset_timing_data(self):
        """Reset all transition timing data"""
        self.heating_times = []
        self.cooling_times = []
        self.transition_start_time = None
        self.transition_start_temp = None
        self.current_transition_type = None
        
        # Reset GUI displays
        self.current_phase_label.config(text="--")
        self.transition_timer_label.config(text="--:--")
        self.last_heating_time_label.config(text="--:--")
        self.last_cooling_time_label.config(text="--:--")
        self.avg_heating_time_label.config(text="--:--")
        self.avg_cooling_time_label.config(text="--:--")
        
        self.log_message("Transition timing data reset")
        
    def start_transition_timing(self, current_temp, target_temp):
        """Start timing a temperature transition"""
        self.transition_start_time = time.time()
        self.transition_start_temp = current_temp
        
        # Determine transition type
        if target_temp > current_temp:
            self.current_transition_type = "heating"
            self.current_phase_label.config(text="Heating")
        else:
            self.current_transition_type = "cooling"
            self.current_phase_label.config(text="Cooling")
            
        self.transition_timer_label.config(text="00:00")
        self.log_message(f"Started {self.current_transition_type} from {current_temp:.1f}°F to {target_temp:.1f}°F")
        
    def update_transition_timer(self):
        """Update the transition timer display"""
        if self.transition_start_time:
            elapsed_time = time.time() - self.transition_start_time
            self.transition_timer_label.config(text=self.format_time(elapsed_time))
            
    def complete_transition_timing(self, final_temp):
        """Complete timing a temperature transition and record the time"""
        if self.transition_start_time and self.current_transition_type:
            elapsed_time = time.time() - self.transition_start_time
            elapsed_minutes = elapsed_time / 60
            
            # Record the time
            if self.current_transition_type == "heating":
                self.heating_times.append(elapsed_time)
                self.last_heating_time_label.config(text=self.format_time(elapsed_time))
                # Update average
                if self.heating_times:
                    avg_time = sum(self.heating_times) / len(self.heating_times)
                    self.avg_heating_time_label.config(text=self.format_time(avg_time))
            else:  # cooling
                self.cooling_times.append(elapsed_time)
                self.last_cooling_time_label.config(text=self.format_time(elapsed_time))
                # Update average
                if self.cooling_times:
                    avg_time = sum(self.cooling_times) / len(self.cooling_times)
                    self.avg_cooling_time_label.config(text=self.format_time(avg_time))
            
            self.log_message(f"Completed {self.current_transition_type} in {elapsed_minutes:.1f} minutes "
                           f"(from {self.transition_start_temp:.1f}°F to {final_temp:.1f}°F)")
            
            # Reset transition tracking
            self.transition_start_time = None
            self.transition_start_temp = None
            self.current_transition_type = None
            self.current_phase_label.config(text="Stabilizing")
            self.transition_timer_label.config(text="--:--")

    def increment_cycle_counter(self):
        """Increment the cycle counter and update display"""
        self.cycle_count += 1
        self.cycle_count_label.config(text=str(self.cycle_count))
        self.log_message(f"Completed cycle #{self.cycle_count}")
        
    def cycling_worker(self):
        try:
            low_temp = float(self.low_temp_var.get())
            high_temp = float(self.high_temp_var.get())
            
            self.log_message(f"Starting temperature cycling between {low_temp}°F and {high_temp}°F")
            
            # Turn chamber on with error checking and retries
            if not self.gpib_wrt_with_retry("W 2000, 1"):
                self.log_message("Failed to turn chamber on. Stopping...")
                return
            time.sleep(2)  # Longer delay after turning on
            
            while not self.stop_cycling:
                cycle_temps = [low_temp, high_temp]
                for i, temp in enumerate(cycle_temps):
                    if self.stop_cycling:
                        break
                        
                    self.log_message(f"Setting Temperature to: {temp}°F")
                    self.target_temp_label.config(text=f"{temp}°F")
                    self.timer_label.config(text="--:--")
                    
                    # Write temperature with error checking and retries
                    if not self.write_temp(300, temp):
                        self.log_message("Failed to set temperature. Attempting reconnection...")
                        if not self.reconnect_device():
                            self.log_message("Cannot reconnect. Stopping cycling.")
                            break
                        # Retry temperature setting after reconnection
                        if not self.write_temp(300, temp):
                            self.log_message("Failed to set temperature after reconnection. Stopping cycling.")
                            break
                    
                    # Wait for temperature stabilization
                    if not self.wait_for_temp_stabilization(temp):
                        break  # Stop cycling was requested or error occurred
                        
                    if not self.stop_cycling:
                        self.log_message(f"Temperature cycle at {temp}°F completed. Moving to next temperature...")
                        
                        # Increment cycle counter after completing high temperature (end of full cycle)
                        if i == 1:  # High temperature is second in the cycle
                            self.increment_cycle_counter()
                        
        except Exception as e:
            self.log_message(f"An error occurred: {e}")
        finally:
            # Turn chamber off with retries
            if self.is_connected:
                if self.gpib_wrt_with_retry("W 2000, 0"):
                    self.log_message("Chamber turned off.")
                else:
                    self.log_message("Warning: Could not confirm chamber was turned off.")
            
            # Reset UI state
            self.cycling_status_label.config(text="Stopped")
            self.target_temp_label.config(text="--°F")
            self.timer_label.config(text="--:--")
            self.current_phase_label.config(text="--")
            self.transition_timer_label.config(text="--:--")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.stop_cycling = False

    def start_cycling(self):
        if not self.is_connected:
            self.log_message("Error: Not connected to device. Attempting reconnection...")
            if not self.reconnect_device():
                self.log_message("Cannot start cycling - no device connection")
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
                
        if self.ics_4899a:
            try:
                self.ics_4899a.close()
            except:
                pass
                
        if self.rm:
            try:
                self.rm.close()
            except:
                pass
            
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TempCycleGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
