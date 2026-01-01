import socket
import os

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Écoute UDP sur {UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(1024)
    message = data.decode().strip()
    print(f"Reçu: {message} de {addr}")
    if message == "true":
        print("Extinction du serveur...")
        os.system("shutdown -h now")
