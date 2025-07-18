import pyvisa
import time

# Initialize GPIB connection
rm = pyvisa.ResourceManager()
ics_4899a = rm.open_resource("GPIB0::4::INSTR")

def gpib_rd(cmd):  # Queries what the error may be
    time.sleep(0.5)   
    try:
        ret = ics_4899a.query(cmd)
    except pyvisa.errors.VisaIOError as e: 
        print("Query Error: ", e.args)
        ret = ""
    return ret

def gpib_wrt(cmd): # Writes the error if there is one
    time.sleep(0.5)  
    try:
        ics_4899a.write(cmd)
    except pyvisa.errors.VisaIOError as e: 
        print("Write Error: ", e.args)
    return

def read_temp(addr): # function to read the temperature of the oven
    global decimal
    return float(int(gpib_rd("R? " + str(addr) + ", 1")) / (10 ** decimal))

def write_temp(addr, value): # function to write the temperature of the oven
    global decimal
    set_cmd = "W " + str(addr) + ", " + str(value * (10 ** decimal))
    gpib_wrt(set_cmd)
    return 

def wait_for_temp_stabilization(target_temp, tolerance=2.5, stabilization_time=600):
    """Wait for temperature to stabilize within tolerance for specified time"""
    temp_stabilized = False
    stabilization_start = None
    
    while not temp_stabilized:
        current_temp = read_temp(100)
        if abs(current_temp - target_temp) <= tolerance:
            if stabilization_start is None:
                stabilization_start = time.time()
                print(f"Temperature within range at {current_temp}°F. Starting stabilization timer.")
            elif time.time() - stabilization_start > stabilization_time:
                temp_stabilized = True
                print(f"Temperature stabilized at {current_temp}°F for {stabilization_time/60:.1f} minutes.")
        else:
            stabilization_start = None  # Reset timer if temperature goes out of range
            print(f"Waiting for temperature to stabilize... Current: {current_temp}°F, Target: {target_temp}°F")
        time.sleep(1)  # Check every second

def cycle_temperatures():
    """Main function to cycle between low and high temperatures"""
    low_temp = 32
    high_temp = 140
    
    print("Starting temperature cycling between 32°F and 140°F")
    print("Press Ctrl+C to stop the cycling")
    
    try:
        # Turn chamber on
        gpib_wrt("W 2000, 1")
        time.sleep(1)
        
        while True:
            for temp in [low_temp, high_temp]:
                print(f"\n--- Setting Temperature to: {temp}°F ---")
                write_temp(300, temp)
                
                # Wait for temperature stabilization
                wait_for_temp_stabilization(temp)
                
                print(f"Temperature cycle at {temp}°F completed. Moving to next temperature...")
                
    except KeyboardInterrupt:
        print("\nUser stop signal received. Stopping temperature cycling...")
        # Turn chamber off before exiting
        gpib_wrt("W 2000, 0")
        print("Chamber turned off. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
        # Turn chamber off in case of error
        gpib_wrt("W 2000, 0")
    finally:
        rm.close()

# Initialize and start cycling
if __name__ == "__main__":
    # Read decimal point configuration
    decimal = gpib_rd("R? 606, 1")
    decimal = int(decimal)
    print(f"Decimal configuration: {decimal}")
    
    # Display current chamber info
    print(f"Connected to: {gpib_rd('*IDN?')}")
    current_temp = read_temp(100)
    print(f"Current chamber temperature: {current_temp}°F")
    
    # Start cycling
    cycle_temperatures()
