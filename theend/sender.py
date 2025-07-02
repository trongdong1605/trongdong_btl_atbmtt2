from flask import Flask, render_template, request, jsonify
import socket
import logging
from datetime import datetime
import os
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

logging.basicConfig(filename='sender.log', level=logging.DEBUG,
                    format='%(asctime)s - %(message)s')

def log_transaction(action, details):
    logging.info(f"{action} - {details}")
    print(f"[Sender] {action} - {details}")

def handshake():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(('localhost', 5000))
            s.sendall("Hello!".encode())
            response = s.recv(1024).decode()
            
            if response == "Ready!":
                log_transaction("Handshake", "Success")
                return True
    except Exception as e:
        log_transaction("Handshake Error", str(e))
    return False

def send_file(filename):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect(('localhost', 5000))
            
            # Send file metadata first
            file_size = os.path.getsize(filename)
            metadata = f"FILE_TRANSFER|{os.path.basename(filename)}|{file_size}"
            s.sendall(metadata.encode())
            time.sleep(0.1)  # Small delay
            
            # Send file content
            with open(filename, 'rb') as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    s.sendall(data)
            
            # Wait for confirmation
            response = s.recv(1024).decode()
            return response == "FILE_RECEIVED"
    except Exception as e:
        log_transaction("File Transfer Error", str(e))
        return False

@app.route('/')
def index():
    return render_template('sender.html')

@app.route('/status')
def status():
    return jsonify({
        "status": "Sender is running",
        "port": 8080,
        "description": "Web interface for sending files",
        "type": "Web/Socket",
        "upload_folder": os.listdir(app.config['UPLOAD_FOLDER'])
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file selected"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"})
    
    if file:
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        
        if not handshake():
            return jsonify({"success": False, "message": "Handshake failed"})
        
        if send_file(filename):
            return jsonify({
                "success": True,
                "message": f"File {file.filename} sent successfully",
                "filename": file.filename
            })
        else:
            return jsonify({"success": False, "message": "File transfer failed"})

if __name__ == "__main__":
    app.run(port=8080, debug=True)