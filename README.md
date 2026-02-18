Windows File Packer & Remote Command Shell
A multi-component Python-based system designed to demonstrate automated payload delivery and remote system management. This project includes a Command & Control (C2) server, a multi-threaded persistent client, and a "dropper" application that bundles files into standalone Windows executables. 

🚀 Features

-Asynchronous C2 Server: A multi-threaded server capable of managing multiple client connections and issuing remote commands simultaneously.
-Persistent Reverse Shell: A client-side agent with built-in reconnection logic to maintain access across network fluctuations.
-Automated File Bundling (Dropper): A packer script that uses Base64 encoding to embed any file (PDF, Image, etc.) into a Python script and compiles it into a "stealth" .exe using PyInstaller. 
-Remote File Management: Full support for remote file uploads and downloads between the server and the target client. 
-Thread-Safe Communication: Implements Length-Prefixed Framing to ensure data integrity during socket transmissions and prevent corruption during large file transfers.

🛠️ Technical Stack

-Language: Python 3.x 
-Libraries: socket, threading, subprocess, base64, os 
-Distribution: PyInstaller (for standalone Windows binaries) 

📂 Project Structure
-server.py: The central controller used to send commands and receive file data.
-client.py: The agent that runs on the target machine, executing commands and maintaining the connection.
-packer.py: The delivery mechanism that embeds a "decoy" file and the client.exe into a single executable.

📝 How it Works

-Packing: The packer.py script takes a decoy file (e.g., manual.pdf) and encodes it. 
-Delivery: It generates an executable that, when opened, extracts and displays the decoy file to the user while silently initiating the connection to the C2 server in the background.
-Command Execution: The server uses a custom protocol to send shell commands which the client executes via the subprocess module, returning the output to the server.
