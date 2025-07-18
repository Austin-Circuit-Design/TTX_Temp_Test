import pyvisa
import time

# Initialize GPIB connection
rm = pyvisa.ResourceManager()
ics_4899a = rm.open_resource("GPIB0::4::INSTR")

# Configuration variables
gpib_timeout = 5000  # 5 second timeout
retry_count = 3
cycle_count = 0  # Track total cycles completed

def configure_gpib():
    """Configure GPIB settings"""
    ics_4899a.timeout = gpib_timeout
    ics_4899a.read_termination = '\n'
    ics_4899a.write_termination = '\n'

def gpib_rd_with_retry(cmd, retries=None):
    """GPIB read with retry logic"""
    if retries is None:
        retries = retry_count
        
    for attempt in range(retries):
        try:
            time.sleep(0.2)
            ret = ics_4899a.query(cmd)
            if ret is not None and ret.strip() != "":
                return ret.strip()
            else:
                if attempt < retries - 1:
                    print(f"Empty response for '{cmd}', retry {attempt + 1}/{retries}")
                    time.sleep(0.5)
                    continue
        except (pyvisa.errors.VisaIOError, pyvisa.errors.InvalidSession) as e:
            if attempt < retries - 1:
                print(f"GPIB error for '{cmd}', retry {attempt + 1}/{retries}: {e}")
                time.sleep(1)
                continue
            else:
                print(f"GPIB Query failed after {retries} attempts: {e}")
                
    return ""

def format_time(seconds):
    """Format seconds into minutes:seconds format"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def gpib_wrt_with_retry(cmd, retries=None):
    """GPIB write with retry logic"""
    if retries is None:
        retries = retry_count
        
    for attempt in range(retries):
        try:
            time.sleep(0.2)
            ics_4899a.write(cmd)
            return True
        except (pyvisa.errors.VisaIOError, pyvisa.errors.InvalidSession) as e:
            if attempt < retries - 1:
                print(f"GPIB write error for '{cmd}', retry {attempt + 1}/{retries}: {e}")
                time.sleep(1)
                continue
            else:
                print(f"GPIB Write failed after {retries} attempts: {e}")
                
    return False

def gpib_rd(cmd):  # Queries what the error may be
    return gpib_rd_with_retry(cmd, 1)  # Single attempt for backward compatibility

def gpib_wrt(cmd): # Writes the error if there is one
    return gpib_wrt_with_retry(cmd, 1)  # Single attempt for backward compatibility

def read_temp_with_retry(addr):
    """Read temperature with retry logic"""
    for attempt in range(retry_count):
        try:
            response = gpib_rd_with_retry("R? " + str(addr) + ", 1")
            if not response or response == "":
                if attempt < retry_count - 1:
                    print(f"Empty temperature response, retry {attempt + 1}/{retry_count}")
                    time.sleep(0.5)
                    continue
                return None
            temp_raw = int(response)
            return float(temp_raw / (10 ** decimal))
        except (ValueError, TypeError) as e:
            if attempt < retry_count - 1:
                print(f"Temperature conversion error, retry {attempt + 1}/{retry_count}: {e}")
                time.sleep(0.5)
                continue
            else:
                print(f"Temperature conversion error after {retry_count} attempts: {e}")
                return None
        except Exception as e:
            if attempt < retry_count - 1:
                print(f"Temperature read error, retry {attempt + 1}/{retry_count}: {e}")
                time.sleep(0.5)
                continue
            else:
                print(f"Temperature read error after {retry_count} attempts: {e}")
                return None
    return None

def read_temp(addr): # function to read the temperature of the oven
    return read_temp_with_retry(addr)

def write_temp(addr, value): # function to write the temperature of the oven
    global decimal
    set_cmd = "W " + str(addr) + ", " + str(int(value * (10 ** decimal)))
    return gpib_wrt_with_retry(set_cmd)

def wait_for_temp_stabilization(target_temp, tolerance=2.5, stabilization_time=600):
    """Wait for temperature to stabilize within tolerance for specified time"""
    temp_stabilized = False
    stabilization_start = None
    consecutive_failures = 0
    max_failures = 3
    last_status_time = time.time()
    
    while not temp_stabilized:
        current_temp = read_temp(100)
        
        if current_temp is None:
            consecutive_failures += 1
            print(f"Temperature read failure {consecutive_failures}/{max_failures}")
            
            if consecutive_failures >= max_failures:
                print("Too many consecutive temperature read failures. Exiting...")
                return False
            time.sleep(2)
            continue
        else:
            consecutive_failures = 0
            
        if abs(current_temp - target_temp) <= tolerance:
            if stabilization_start is None:
                stabilization_start = time.time()
                print(f"Temperature within range at {current_temp}°F. Starting stabilization timer.")
            else:
                elapsed_time = time.time() - stabilization_start
                remaining_time = stabilization_time - elapsed_time
                
                # Show progress every 30 seconds or when stabilization completes
                if time.time() - last_status_time >= 30 or elapsed_time >= stabilization_time:
                    if elapsed_time >= stabilization_time:
                        temp_stabilized = True
                        print(f"Temperature stabilized at {current_temp}°F for {stabilization_time/60:.1f} minutes. ✓")
                    else:
                        print(f"Holding at {current_temp}°F - Time: {format_time(elapsed_time)}/{format_time(stabilization_time)} (Remaining: {format_time(remaining_time)})")
                    last_status_time = time.time()
        else:
            stabilization_start = None  # Reset timer if temperature goes out of range
            print(f"Waiting for temperature to stabilize... Current: {current_temp}°F, Target: {target_temp}°F")
            last_status_time = time.time()  # Reset status timer
            
        time.sleep(2)  # Check every 2 seconds

    return temp_stabilized

def cycle_temperatures():
    """Main function to cycle between low and high temperatures"""
    global cycle_count
    low_temp = 32
    high_temp = 140
    
    print("Starting temperature cycling between 32°F and 140°F")
    print("Press Ctrl+C to stop the cycling")
    print(f"Current cycle count: {cycle_count}")
    
    try:
        # Turn chamber on with retry logic
        if not gpib_wrt_with_retry("W 2000, 1"):
            print("Failed to turn chamber on. Exiting...")
            return
        time.sleep(2)
        
        while True:
            cycle_temps = [low_temp, high_temp]
            for i, temp in enumerate(cycle_temps):
                print(f"\n--- Setting Temperature to: {temp}°F ---")
                
                # Write temperature with retry logic
                if not write_temp(300, temp):
                    print("Failed to set temperature. Exiting...")
                    return
                
                # Wait for temperature stabilization
                if not wait_for_temp_stabilization(temp):
                    print("Temperature stabilization failed. Exiting...")
                    return
                
                print(f"Temperature cycle at {temp}°F completed. Moving to next temperature...")
                
                # Increment cycle counter after completing high temperature (end of full cycle)
                if i == 1:  # High temperature is second in the cycle
                    cycle_count += 1
                    print(f"=== COMPLETED CYCLE #{cycle_count} ===")
                
    except KeyboardInterrupt:
        print(f"\nUser stop signal received. Stopping temperature cycling...")
        print(f"Total cycles completed: {cycle_count}")
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f"Total cycles completed: {cycle_count}")
    finally:
        # Turn chamber off with retry logic
        if gpib_wrt_with_retry("W 2000, 0"):
            print("Chamber turned off. Exiting...")
            print(f"Final cycle count: {cycle_count}")
        else:
            print("Warning: Could not confirm chamber was turned off.")
            print(f"Final cycle count: {cycle_count}")
        rm.close()

# Initialize and start cycling
if __name__ == "__main__":
    # Configure GPIB settings
    configure_gpib()
    
    # Read decimal point configuration with retry
    decimal_response = gpib_rd_with_retry("R? 606, 1")
    if decimal_response:
        decimal = int(decimal_response)
        print(f"Decimal configuration: {decimal}")
    else:
        print("Failed to read decimal configuration. Using default value 1")
        decimal = 1
    
    # Display current chamber info
    device_id = gpib_rd_with_retry("*IDN?")
    if device_id:
        print(f"Connected to: {device_id}")
    else:
        print("Warning: Could not read device ID")
    
    current_temp = read_temp(100)
    if current_temp is not None:
        print(f"Current chamber temperature: {current_temp}°F")
    else:
        print("Warning: Could not read current temperature")
    
    # Start cycling
    cycle_temperatures()
