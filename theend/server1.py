from flask import Flask, jsonify, render_template
import socket
import logging
from datetime import datetime
import threading
import time
import os

app = Flask(__name__)

logging.basicConfig(filename='server1.log', level=logging.DEBUG,
                    format='%(asctime)s - %(message)s')

def log_transaction(action, details):
    logging.info(f"{action} - {details}")
    print(f"[Server1] {action} - {details}")

def forward_to_server2(data, is_file=False, filename=None, file_size=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect(('localhost', 5001))
            
            if is_file:
                # Forward file metadata
                metadata = f"FILE_TRANSFER|{filename}|{file_size}"
                s.sendall(metadata.encode())
                time.sleep(0.1)
                
                # Forward file content
                total_sent = 0
                while total_sent < len(data):
                    sent = s.send(data[total_sent:total_sent+1024])
                    if sent == 0:
                        raise RuntimeError("Socket connection broken")
                    total_sent += sent
            else:
                s.sendall(data.encode())
                
            return s.recv(1024).decode()
    except Exception as e:
        log_transaction("Forward Error", str(e))
        return None

def handle_client(conn, addr):
    try:
        initial_data = conn.recv(1024).decode()
        
        if not initial_data:
            log_transaction("Warning", f"Empty data from {addr}")
            return
            
        if initial_data == "Hello!":
            response = forward_to_server2(initial_data)
            if response == "Ready!":
                conn.sendall(response.encode())
                log_transaction("Handshake", f"Completed with {addr}")
        
        elif "FILE_TRANSFER" in initial_data:
            try:
                parts = initial_data.split("|")
                if len(parts) != 3:
                    raise ValueError("Invalid FILE_TRANSFER format")
                    
                _, filename, file_size_str = parts
                file_size = int(file_size_str)
                
                log_transaction("File Transfer", 
                              f"Starting transfer for {filename} ({file_size} bytes) from {addr}")
                
                received_data = bytearray()
                remaining_bytes = file_size
                chunk_size = 4096
                
                while remaining_bytes > 0:
                    data = conn.recv(min(chunk_size, remaining_bytes))
                    if not data:
                        break
                    received_data.extend(data)
                    remaining_bytes -= len(data)
                
                if remaining_bytes != 0:
                    raise IOError(f"Incomplete file transfer, missing {remaining_bytes} bytes")
                
                response = forward_to_server2(bytes(received_data), 
                                           is_file=True,
                                           filename=os.path.basename(filename),
                                           file_size=file_size)
                
                if response == "FILE_RECEIVED":
                    conn.sendall(response.encode())
                    log_transaction("File Transfer", 
                                  f"Successfully forwarded {filename} ({file_size} bytes)")
                else:
                    raise RuntimeError("Forwarding failed, no confirmation from Server2")
                    
            except ValueError as e:
                log_transaction("Error", f"Invalid file metadata: {str(e)}")
                conn.sendall("ERROR|Invalid file metadata".encode())
            except Exception as e:
                log_transaction("Error", f"File transfer failed: {str(e)}")
                conn.sendall(f"ERROR|{str(e)}".encode())
                
    except ConnectionError as e:
        log_transaction("Connection Error", f"With {addr}: {str(e)}")
    except Exception as e:
        log_transaction("Unexpected Error", f"With {addr}: {str(e)}")
    finally:
        try:
            conn.close()
        except:
            pass

def socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', 5000))
        s.listen(5)
        log_transaction("Started", "Listening on port 5000")
        
        while True:
            try:
                conn, addr = s.accept()
                log_transaction("Connection", f"New connection from {addr}")
                threading.Thread(target=handle_client, args=(conn, addr)).start()
            except Exception as e:
                log_transaction("Accept Error", str(e))

@app.route('/')
def server1_status():
    return jsonify({
        "status": "Server 1 is running",
        "port": 5000,
        "description": "Entry point server forwarding to Server 2",
        "type": "Socket/Web",
        "web_port": 8000,
        "active_threads": threading.active_count() - 1
    })

@app.route('/dashboard')
def server1_dashboard():
    return render_template('server1_dashboard.html')

if __name__ == "__main__":
    threading.stack_size(128*1024)
    
    socket_thread = threading.Thread(target=socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    
    try:
        app.run(port=8000, threaded=True)
    except KeyboardInterrupt:
        log_transaction("Shutdown", "Server shutting down gracefully")
    except Exception as e:
        log_transaction("Fatal Error", str(e))