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
                    if data and self.on_telemetry_callback:
                        self.on_telemetry_callback(data)
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[TCP RECV ERROR] {e}")
                time.sleep(1)