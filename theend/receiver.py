from flask import Flask, jsonify, send_from_directory, render_template
import socket
import logging
from datetime import datetime
import threading
import os

app = Flask(__name__)
app.config['RECEIVED_FOLDER'] = 'received_files'
os.makedirs(app.config['RECEIVED_FOLDER'], exist_ok=True)

logging.basicConfig(filename='receiver.log', level=logging.DEBUG,
                    format='%(asctime)s - %(message)s')

def log_transaction(action, details):
    logging.info(f"{action} - {details}")
    print(f"[Receiver] {action} - {details}")

def handle_client(conn, addr):
    try:
        initial_data = conn.recv(1024).decode()
        
        if initial_data == "Hello!":
            conn.sendall("Ready!".encode())
            log_transaction("Handshake", "Completed")
            
        elif "FILE_TRANSFER" in initial_data:
            _, filename, file_size = initial_data.split("|")
            file_size = int(file_size)
            log_transaction("File Transfer", f"Starting receive for {filename} ({file_size} bytes)")
            
            received_data = b""
            remaining_bytes = file_size
            
            while remaining_bytes > 0:
                data = conn.recv(min(1024, remaining_bytes))
                if not data:
                    break
                received_data += data
                remaining_bytes -= len(data)
            
            filepath = os.path.join(app.config['RECEIVED_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(received_data)
            
            conn.sendall("FILE_RECEIVED".encode())
            log_transaction("File Received", f"Saved {filename} ({file_size} bytes)")
            
    except Exception as e:
        log_transaction("Error", str(e))
    finally:
        conn.close()

def socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', 5002))
        s.listen()
        log_transaction("Started", "Listening on port 5002")
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()

@app.route('/')
def receiver_status():
    return jsonify({
        "status": "Receiver is running",
        "port": 5002,
        "description": "Final destination for files",
        "received_files": os.listdir(app.config['RECEIVED_FOLDER']),
        "web_port": 8002,
        "active_threads": threading.active_count() - 1
    })

@app.route('/dashboard')
def receiver_dashboard():
    return render_template('receiver_dashboard.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['RECEIVED_FOLDER'], filename)

if __name__ == "__main__":
    socket_thread = threading.Thread(target=socket_server)
    socket_thread.daemon = True
    socket_thread.start()
    app.run(port=8002)