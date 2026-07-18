import serial
import time
import threading
import sys

# parameters
MODE = bool(int(sys.argv[1])) if len(sys.argv) > 1 else False  # true for interactive mode, false for non-interactive
PORT = str(input("Enter the COM port (empty for default): ")).strip()  #prompt user for COM port
if PORT == '':
    PORT = 'COM1'       
BAUDRATE = 14400
TIMEOUT = 1.0          #read timeout in seconds

def read_loop(ser, stop_event):
    """Background thread to continuously read incoming data from the serial port."""
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                #read all available bytes in the buffer
                data = ser.read(ser.in_waiting)
                if data:
                    print(f"\n<<< [Received Hex]: {data.hex().upper()}")
                    print(f"<<< [Received ASCII/Repr]: {repr(data)}")
                    # Reprint prompt to keep the interface clean
                    print(">>> Enter command: ", end="", flush=True)
            time.sleep(0.05)  # Yield CPU
        except Exception as e:
            # If the port is closed or an error occurs, exit the thread loop
            if not stop_event.is_set():
                print(f"\n[Reader Thread Error]: {e}")
            break

def run_serial_example():
    try:
        # Initialize the serial port with standard parameters
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT,
            xonxoff=False,     # Disable software flow control
            rtscts=False,      # Disable RTS/CTS hardware flow control
            dsrdtr=False       # Disable DSR/DTR hardware flow control
        )

        # Ensure RTS and DTR lines are explicitly low/disabled
        ser.rts = False
        ser.dtr = False

        print(f"Successfully opened {PORT} at {BAUDRATE} baud.")
        print("-" * 70)
        print("Interactive Serial Terminal Started.")
        print("  - Type 'exit' or 'quit' to close the port and exit.")
        print("  - Hex input is sent as bytes (spaces ignored, e.g., '57 01 64').")
        print("  - To force ASCII/plain-text, prefix with 't:' (e.g., 't:hello').")
        print("  - To force Hex, prefix with 'h:' (e.g., 'h:570164').")
        print("  - By default, valid hex strings are sent as hex; otherwise sent as ASCII.")
        print("-" * 70)

        # Start the background read thread
        stop_event = threading.Event()
        read_thread = threading.Thread(target=read_loop, args=(ser, stop_event), daemon=True)
        read_thread.start()

        if MODE:
            while True:
                try:
                    user_input = input(">>> Enter command: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print()
                    break

                if not user_input:
                    continue

                if user_input.lower() in ('exit', 'quit'):
                    break

                # Parse input format
                payload = None
                if user_input.lower().startswith('t:'):
                    # Force plain text ASCII
                    text_val = user_input[2:]
                    payload = text_val.encode('utf-8')
                    print(f">>> [Sending ASCII]: {payload}")
                elif user_input.lower().startswith('h:'):
                    # Force hex
                    hex_val = user_input[2:].replace(" ", "").replace("\\x", "").replace("0x", "")
                    try:
                        payload = bytes.fromhex(hex_val)
                        print(f">>> [Sending Hex]: {payload.hex().upper()}")
                    except ValueError as e:
                        print(f"Error: Invalid hex format after prefix: {e}")
                        continue
                else:
                    # automatic detection: try hex first, fallback to ASCII
                    cleaned = user_input.replace(" ", "").replace("\\x", "").replace("0x", "")
                    try:
                        payload = bytes.fromhex(cleaned)
                        print(f">>> [Sending Hex]: {payload.hex().upper()}")
                    except ValueError:
                        payload = user_input.encode('utf-8')
                        print(f">>> [Sending ASCII]: {payload}")

                if payload:
                    try:
                        ser.write(payload)
                        #give the device a brief moment before user can type again
                        time.sleep(0.05)
                    except Exception as e:
                        print(f"Error writing to serial port: {e}")

        else:
            # select from predefined commands
            ID = int(input("Enter the blind ID (0-255): ").strip())
            PERCENT = int(input("Enter the percent (0-100): ").strip())
            command = send_blinds(ID, PERCENT)
            print(f">>> [Sending Predefined Command]: {command.hex().upper()}")
            ser.write(command)
            time.sleep(0.1)  # Allow time for the command to be sent

        # Clean shutdown
        print("Stopping reader thread and closing port...")
        stop_event.set()
        read_thread.join(timeout=1.0)
        ser.close()
        print("Port closed. Exiting.")

    except serial.SerialException as e:
        print(f"Serial connection error: {e}")

def send_blinds(id,percent):
    """Send a command to the blinds controller."""

    id = hex(id) if isinstance(id, int) else id
    percent = hex(percent) if isinstance(percent, int) else percent
    # Construct the command based on id and percent
    command = b'\xAA'+bytes.fromhex(id[2:]) + bytes.fromhex(percent[2:]) #AA is the start byte, followed by id and percentage of opening
    return command

    

if __name__ == '__main__':
    run_serial_example()