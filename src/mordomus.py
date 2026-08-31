import queue
import socket
import threading
import time


class MordomusTransport:

    #Frame sent to the bridge right after a connection is established
    BOOT_COMMAND = bytes([0x57, 0x01, 0x64])

    def __init__(self, ip: str, port: int, inter_frame_delay: float = 0.10, reconnect_delay: float = 5.0):
        self.ip = ip
        self.port = port
        self.delay = inter_frame_delay
        self.reconnect_delay = reconnect_delay
        self.socket = None
        self.cmd_queue = queue.Queue()
        self.on_telemetry_callback = None
        self._running = False
        self._buffer = bytearray()

    def connect(self):
        """Starts the sender thread and the connection supervisor. The actual
        TCP connection is (re)established in the background for as long as
        the transport is running."""
        self._running = True
        threading.Thread(target=self._sender_loop, daemon=True).start()
        threading.Thread(target=self._connection_supervisor, daemon=True).start()

    def _connection_supervisor(self):
        """Owns the socket lifecycle: connects, receives until the connection
        is lost, then closes it and reconnects after reconnect_delay."""
        while self._running:
            try:
                print(f"[TCP] Connecting to Waveshare Bridge at {self.ip}:{self.port}...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                #no nagle to force single packet sending
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                sock.settimeout(2.0)
                sock.connect((self.ip, self.port))

                self._buffer = bytearray()  #discard any partial frame from the previous connection
                self.socket = sock
                print("[TCP] Connected successfully.")

                # Send the boot command as soon as the connection is up
                self.send_raw(self.BOOT_COMMAND, meta={"boot": True})

                self._receiver_loop()  # Blocks until this connection is lost

            except Exception as e:
                print(f"[TCP CONNECT ERROR] {e}")

            finally:
                if self.socket:
                    try:
                        self.socket.close()
                    except Exception:
                        pass
                    self.socket = None

            if self._running:
                print(f"[TCP] Reconnecting in {self.reconnect_delay:.0f}s...")
                time.sleep(self.reconnect_delay)

    def send_command(self, dev_id: int, val: int, meta: dict = None):
        """Builds 3-byte frame [0xAA, ID, VALUE] and enqueues it."""
        frame = bytes([0xAA, dev_id, val])
        self.cmd_queue.put((frame, meta))

    def send_raw(self, frame: bytes, meta: dict = None):
        """Enqueues a pre-built frame as-is, bypassing the [0xAA, ID, VALUE] wrapping."""
        self.cmd_queue.put((frame, meta))

    def _sender_loop(self):
        while self._running:
            frame, meta = self.cmd_queue.get()
            try:
                if self.socket:
                    self.socket.sendall(frame)
                    print(f"[TCP OUT] Sent: {frame.hex().upper()}")
                else:
                    print(f"[TCP SEND SKIPPED] Not connected, dropped: {frame.hex().upper()}")
            except Exception as e:
                print(f"[TCP SEND ERROR] {e}")

            time.sleep(self.delay)  # Enforce buffer overflow safety delay
            self.cmd_queue.task_done()

    def _receiver_loop(self):
        """Reads and parses frames for the current connection. Returns as soon
        as the connection is lost, so the supervisor can close it and reconnect."""
        while self._running:
            try:
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
                continue
            except Exception as e:
                print(f"[TCP RECV ERROR] {e}")
                return  #let the supervisor close the socket and reconnect