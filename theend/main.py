import subprocess
from threading import Thread
from flask import Flask, render_template
import time

app = Flask(__name__)

def run_sender():
    subprocess.run(['python', 'sender.py'])

def run_server1():
    subprocess.run(['python', 'server1.py'])

def run_server2():
    subprocess.run(['python', 'server2.py'])

def run_receiver():
    subprocess.run(['python', 'receiver.py'])

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    # Start all servers in separate threads
    Thread(target=run_sender).start()
    time.sleep(1)
    Thread(target=run_server1).start()
    time.sleep(1)
    Thread(target=run_server2).start()
    time.sleep(1)
    Thread(target=run_receiver).start()
    time.sleep(1)
    
    # Start the main web interface
    app.run(port=5005)