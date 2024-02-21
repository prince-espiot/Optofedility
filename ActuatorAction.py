import logging
import sys
import csv
import futils
from force_ctrl import OFForcer
import socket

try:
    from src.force_ctrl.OFForcer import OFForcer, OptomotionForcerException
except ImportError:
    from force_ctrl.OFForcer import OFForcer, OptomotionForcerException

# Define the server's IP address and port
server_ip = '127.0.0.1'  # Replace with your desired IP address
server_port = 5006  # Replace with your desired port


class ForceController:

    def __init__(self):
        self.cached_result = None
        self.current_column_index = 1  # Start index at 1 for "Press point 1"
        self.connect_success_flag = False
        logging.basicConfig(filename='ActuatorAction.log', level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s: %(message)s')

        log = logging.getLogger('force_ctrl.OptomotionForcer')
        log.addHandler(logging.StreamHandler(sys.stdout))
        log.setLevel(logging.INFO)

        # Check if the connection has already been established
        if not self.connect_success_flag:
            try:
                # Open the force control
                self.force = OFForcer(ip_address='192.168.250.254')

                # Tare force sensor
                self.force.force_tare('F1')

                # Initialize force data recording
                self.force.scope_init('F1', samplerate=250)
                self.connect_success_flag = True

                # Log connection success
                logging.info("Force control connection established.")

            except Exception as e:
                logging.error(f"Error: {e}")
                self.connect_success_flag = False

    def connect(self):
        if self.connect_success_flag:
            # Log connection status
            logging.info("Already connected to the force control.")
            return "ok"
        else:
            return "Connection failed."

    def disconnect(self):
        self.force.close()
        # print("ok")
        return "ok"

    def zero(self):
        self.force.force_tare('F1')
        # print("ok")
        return "ok"

    def move_act(self, position):
        # self.force = OFForcer()
        self.force.force_tare('F1')
        self.force.move('F1', position)
        # print("ok")
        return "ok"

    def seek_surface(self, max_position, force_value):
        # self.force.force_tare('F1')
        force.set_force_ctrl_params('F1',0)
        force_value = force_value * 102
        surf_pos = self.force.force_seek_surface('F1',
                                                 touchForce=force_value, velLimit_mms=4.0)
        self.force.move('F1', surf_pos - 2.0)
        # self.force.force_tare('F1')
        # print(surf_pos)
        # print("ok")
        return surf_pos

    def auto_seek_surface(self):
        # self.force.force_tare('F1')
        if not hasattr(self, 'cached_result'):
            self.cached_result = (
                self.force.force_seek_surface('F1', touchForce=5.0, velLimit_mms=4.0))  # pos=max_position
        self.force.move('F1', self.cached_result - 2)
        return self.cached_result

    def press_with_force(self, force_value, force_time, rise_time, fall_time):
        logging.debug("press_with_force function called!")
        self.force.scope_start()
        # self.auto_seek_surface()
        force.set_force_ctrl_params('F1',1 )
        force_value = (force_value * 102)
        self.force.force_press_advanced('F1', force_value, force_time, riseTime_ms=rise_time, fallTime_ms=fall_time)
        fdatat = self.force.scope_get_data()

        # Generate a dynamic column name
        column_name = f'Press point {self.current_column_index}'

        # Write the new data to the CSV file, using the generated column name
        with open('force_data.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([column_name])  # Write the column name
            for data in fdatat:
                writer.writerow([("%.2f" % data).replace('.', ',')])

        # Increment the current column index for the next call
        self.current_column_index += 1

        futils.plotForceToFile(fdatat, column_name, force_value, data_period=0.002, showGraph=False, minForce=-10)
        return "ok"

    def set_cntl_params(self, config_number):
        if config_number >= 0 and config_number <= 1:
            self.force.set_force_ctrl_params('F1', config_number)
            return "ok"
        else:
            return "Config number out of range"

    def get_position(self):
        logging.debug("get_position function called!")
        position = self.force.get_position('F1')
        return position

    def get_force(self):
        logging.debug("get_force function called!")
        force_value = self.force.get_force('F1')
        fdatat = self.force.scope_get_data()
        with open('force_data.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            for data in fdatat:
                writer.writerow([("%.2f" % data)])
        return force_value

    def get_errors(self):
        errors = self.force.get_errors()
        return errors


def main(force_controller):
    """

    :type force_controller: An instance of the ForceController that is passed to the main function
    from the ActuatorService file.
    """
    response = ''

    # Create a socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((server_ip, server_port))
        server_socket.listen()

        logging.info(f"Server listening on {server_ip}:{server_port}")

        while True:
            client_socket, client_address = server_socket.accept()

            with client_socket:
                logging.info(f"Connection established with {client_address}")

                command = client_socket.recv(1024).decode()
                if not command:
                    break

                logging.info(f"Received command: {command}")

                if command == 'Connect':
                    logging.info("connect called")
                    response = force_controller.connect()
                elif command == 'Disconnect':
                    response = force_controller.disconnect()
                    logging.info("disconnect")
                elif command == 'Zero':
                    response = force_controller.zero()
                    logging.info("zero")
                elif command.startswith("Move"):
                    _, position = command.split()
                    position = (float(position))
                    response = force_controller.move_act(position)  # , args.arg2
                    logging.info("move")
                elif command.startswith("SeekSurface"):
                    _, max_position, force_value = command.split()
                    max_position = (float(max_position))
                    force_value = (float(force_value))
                    response = force_controller.seek_surface(max_position, force_value)
                    logging.info(response)
                elif command.startswith("PressWithForce"):
                    _, force_value, force_time, rise_time, fall_time = command.split()
                    force_value = (float(force_value))
                    force_time = (int(force_time))
                    rise_time = (int(rise_time))
                    fall_time = (int(fall_time))
                    response = force_controller.press_with_force(force_value, force_time, rise_time, fall_time)
                    logging.info("press_with_force")
                elif command.startswith("SetForceControlParams"):
                    _, config_number = command.split()
                    config_nr = (int(config_number))
                    response = force_controller.set_cntl_params(config_nr)                   
                elif command.startswith("GetPosition"):
                    logging.info("get_position")
                    response = force_controller.get_position()
                elif command.startswith("GetForce"):
                    logging.info("get_force")
                    response = force_controller.get_force()
                elif command.startswith("GetErrors"):
                    logging.info("GetErrors")
                    response = force_controller.get_errors()
                elif command == 'exit':
                    logging.info("Received shutdown command. Closing server.")
                    response = 'ok'
                else:
                    logging.warning("Invalid function choice. Use --help for usage information.")
                    response = "Invalid command"
                # print(response)
                # For this example, we'll just echo the command back to the client
                response = f"{response}"

                client_socket.sendall(response.encode())
                logging.info(f"Sent response: {response}")

        server_socket.close()


if __name__ == '__main__':
    force_controller = ForceController()
    main(force_controller)
