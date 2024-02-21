import subprocess
import socket
import psutil
import logging
import time

# Define the server's IP address and port
server_ip = '127.0.0.1'  # Replace with your desired IP address
server_port = 5006  # Replace with your desired port

# Set up logging
logging.basicConfig(filename='server.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s: %(message)s')

# Initialize server_process outside the try block
server_process = None


# Function to send command to the server
def send_command_to_server(command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        retry_count = 0
        while retry_count < 3:  # Retry up to 3 times
            try:
                s.connect((server_ip, server_port))
                break  # If connection succeeds, exit the retry loop
            except ConnectionRefusedError:
                logging.warning(f"Connection refused. Port {server_port} is in use.")
                retry_count += 1
                time.sleep(1)  # Wait for a second before retrying

        if retry_count == 3:
            logging.error(f"Failed to connect after 3 attempts. Exiting.")
            return None

        try:
            s.sendall(command.encode())
            response = s.recv(1024).decode()
            return response
        except Exception as e:
            logging.error(f"Error while sending command: {e}")
            return None


def get_pid_on_port(port):
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.laddr.ip == '127.0.0.1':
            return conn.pid
    return None


def listen_for_commands():
    # Listen for commands
    while True:
        command = input()
        try:
            if command == 'exit':
                response = send_command_to_server(command)
                logging.info("Exit command sent. Waiting for response.")
                print("Response:", response)
                logging.info(f"Response: {response}")
                break  # Exit the loop if 'exit' command is sent
            else:
                response = send_command_to_server(command)
                logging.info(f"Command '{command}' sent. Waiting for response.")
                print("Response:", response)
                logging.info(f"Response: {response}")
        except Exception as e:
            logging.error(f"Error: {e}")


if __name__ == '__main__':
    try:
        # Start the server as a subprocess
        server_command = ['python', 'ActuatorAction.py']
        server_process = subprocess.Popen(server_command)
        logging.info("Server process started!:")

        listen_for_commands()
    finally:
        # Ensure that the server subprocess is terminated when the script exits
        if server_process:
            server_process.terminate()
            server_process.wait()  # Wait for the process to finish
