from flask import Flask, jsonify, render_template
import socket
import logging
from datetime import datetime
import threading
import time

app = Flask(__name__)

logging.basicConfig(filename='server2.log', level=logging.DEBUG,
                    format='%(asctime)s - %(message)s')

def log_transaction(action, details):
    logging.info(f"{action} - {details}")
    print(f"[Server2] {action} - {details}")

def forward_to_receiver(data, is_file=False, filename=None, file_size=None):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect(('localhost', 5002))
            
            if is_file:
                metadata = f"FILE_TRANSFER|{filename}|{file_size}"
                s.sendall(metadata.encode())
                time.sleep(0.1)
                s.sendall(data)
            else:
                s.sendall(data.encode())
                
            return s.recv(1024).decode()
    except Exception as e:
        log_transaction("Forward Error", str(e))
        return None

def handle_client(conn, addr):
    try:
        initial_data = conn.recv(1024).decode()
        
        if initial_data == "Hello!":
            response = forward_to_receiver(initial_data)
            if response == "Ready!":
                conn.sendall(response.encode())
                log_transaction("Handshake", "Completed")
        
        elif "FILE_TRANSFER" in initial_data:
            _, filename, file_size = initial_data.split("|")
            file_size = int(file_size)
            log_transaction("File Transfer", f"Starting transfer for {filename} ({file_size} bytes)")
            
            received_data = b""
            remaining_bytes = file_size
            
            while remaining_bytes > 0:
                data = conn.recv(min(1024, remaining_bytes))
                if not data:
                    break
                received_data += data
                remaining_bytes -= len(data)
            
            response = forward_to_receiver(received_data, is_file=True, 
                                         filename=filename, file_size=file_size)
            
            if response == "FILE_RECEIVED":
                conn.sendall(response.encode())
                log_transaction("File Transfer", f"Completed for {filename}")
                
    except Exception as e:
        log_transaction("Error", str(e))
    finally:
        conn.close()

def socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', 5001))
        s.listen()
        log_transaction("Started", "Listening on port 5001")
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()

@app.route('/')
def server2_status():
    return jsonify({
        "status": "Server 2 is running",
        "port": 5001,
        "description": "Middle tier server forwarding to receiver",
        "type": "Socket/Web",
        "web_port": 8001,
        "active_threads": threading.active_count() - 1
    })

@app.route('/dashboard')
def server2_dashboard():
    return render_template('server2_dashboard.html')

if __name__ == "__main__":
    socket_thread = threading.Thread(target=socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    app.run(port=8001)