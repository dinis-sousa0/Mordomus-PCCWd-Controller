import queue
import socket
import threading
import time


class MordomusTransport:

    def __init__(self, ip: str, port: int, inter_frame_delay: float = 0.05):
        self.ip = ip
        self.port = port
        self.delay = inter_frame_delay
        self.socket = None
        self.cmd_queue = queue.Queue()
        self.on_telemetry_callback = None
        self._running = False
        self._buffer = bytearray()

    def connect(self):
        print(f"[TCP] Connecting to Waveshare Bridge at {self.ip}:{self.port}...")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(2.0)
        self.socket.connect((self.ip, self.port))
        self._running = True
        print("[TCP] Connected successfully.")

        # Background threads
        threading.Thread(target=self._sender_loop, daemon=True).start()
        threading.Thread(target=self._receiver_loop, daemon=True).start()

    def send_command(self, dev_id: int, val: int, meta: dict = None):
        """Builds 3-byte frame [0xAA, ID, VALUE] and enqueues it."""
        frame = bytes([0xAA, dev_id, val])
        self.cmd_queue.put((frame, meta))

    def _sender_loop(self):
        while self._running:
            frame, meta = self.cmd_queue.get()
            try:
                if self.socket:
                    self.socket.sendall(frame)
                    print(f"[TCP OUT] Sent: {frame.hex().upper()}")
            except Exception as e:
                print(f"[TCP SEND ERROR] {e}")

            time.sleep(self.delay)  # Enforce buffer overflow safety delay
            self.cmd_queue.task_done()

    def _receiver_loop(self):
        while self._running:
            try:
                if self.socket:
                    data = self.socket.recv(1024)
                    if not data:
                        raise ConnectionResetError("Gateway closed connection")

                    self._buffer.extend(data)

                    # Parser
                    while len(self._buffer) >= 3:
                        #Case Input Frame (0x49 0xAA [ID] [Click] 0x46) ---
                        if self._buffer[0] == 0x49:
                            if len(self._buffer) < 5:
                                break  # Wait for remaining bytes to arrive
                            
                            if self._buffer[1] == 0xAA and self._buffer[4] == 0x46:
                                frame = bytes(self._buffer[:5])
                                self._buffer = self._buffer[5:]
                                if self.on_telemetry_callback:
                                    self.on_telemetry_callback(frame)
                            else:
                                # Invalid sync sequence, drop 1 byte
                                self._buffer.pop(0)

                        # Unrecognized Byte
                        else:
                            self._buffer.pop(0)
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[TCP RECV ERROR] {e}")
                time.sleep(1)