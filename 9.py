import time
import sys
from pubsub import pub
from meshtastic.serial_interface import SerialInterface
import serial.tools.list_ports
import threading
from colorama import init, Fore, Back, Style
init(autoreset=True)


def list_com_ports():
    # List available COM ports
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No devices found.")
        sys.exit(1)

    print("Available COM ports:")
    for i, port in enumerate(ports):
        print(f"{i + 1}: {port.device}")
    return ports

def select_com_port(ports):
    # Get user's choice of COM port
    selection = input("Enter the number of the device to use: ")
    try:
        selected_device = ports[int(selection) - 1].device
    except (IndexError, ValueError):
        print("Invalid selection.")
        sys.exit(1)
    return selected_device

def get_node_info(serial_port):
    print("Initializing SerialInterface to get node info...")
    local = SerialInterface(serial_port)
    node_info = local.nodes
    local.close()
    print("Node info retrieved.")
    return node_info

def parse_node_info(node_info):
    print("Parsing node info...")
    nodes = []
    for node_id, node in node_info.items():
        nodes.append({
            'num': node_id,
            'user': {
                'shortName': node.get('user', {}).get('shortName', 'Unknown')
            }
        })
    print("Node info parsed.")
    return nodes

def log_incoming_message(shortname, message):
    """
    Logs the incoming message to a log file.
    This will be run in the background.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("message_log.txt", "a") as log_file:
        log_file.write(f"{timestamp} - {shortname}: {message}\n")

def log_sent_message(message):
    """
    Logs the sent message to a log file.
    This will be run in the background.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("message_log.txt", "a") as log_file:
        log_file.write(f"{timestamp} - Sent: {message}\n")

def on_receive(packet, interface, node_list):
    try:
        if packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message = packet['decoded']['payload'].decode('utf-8')
            fromnum = packet['fromId']
            shortname = next((node['user']['shortName'] for node in node_list if node['num'] == fromnum), 'Unknown')

            # Display the received message in yellow
            
            print(f"{Fore.YELLOW}{Style.BRIGHT}{shortname}: {message}{Style.RESET_ALL}")

            # Log incoming message in the background
            threading.Thread(target=log_incoming_message, args=(shortname, message)).start()
    except KeyError:
        pass  # Ignore KeyError silently
    except UnicodeDecodeError:
        pass  # Ignore UnicodeDecodeError silently



def send_message(interface, message):
    """
    Send a text message to the Meshtastic network.
    Always sends to all nodes (broadcast).
    Logs the sent message in the background.
    """
    try:
        interface.sendText(message)  # Sends to all nodes by default

        # Display the sent message in light green
        print(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}You: {message}{Style.RESET_ALL}")

        # Log sent message in the background
        threading.Thread(target=log_sent_message, args=(message,)).start()
    except Exception as e:
        print(f"{Fore.RED}Error sending message: {e}{Style.RESET_ALL}")



def show_node_list(node_list):
    """
    Show the list of nodes with their ID, short names, and long names.
    """
    print("\nNode List:")
    if not node_list:
        print("No nodes available.")
    else:
        for node in node_list:
            short_name = node['user']['shortName']
            long_name = node['user'].get('longName', 'Unknown')
            print(f"Node ID: {node['num']}, Short Name: {short_name}, Long Name: {long_name}")

def main():
    # List and select a serial port
    ports = list_com_ports()
    serial_port = select_com_port(ports)
    print(f"Using serial port: {serial_port}")

    # Retrieve and parse node information
    node_info = get_node_info(serial_port)
    node_list = parse_node_info(node_info)

    # Print node list for debugging
    show_node_list(node_list)

    # Subscribe the callback function to message reception
    def on_receive_wrapper(packet, interface):
        on_receive(packet, interface, node_list)

    pub.subscribe(on_receive_wrapper, "meshtastic.receive")
    print("Subscribed to meshtastic.receive")

    # Set up the SerialInterface for message listening
    local = SerialInterface(serial_port)
    print("SerialInterface setup for listening.")

    # Prompt user to send a message or show the node list
    while True:
        try:
            user_message = input("\nEnter a message to send (or 'exit' to quit, 'list' to show node list): ")

            if user_message.lower() == 'exit':
                print("Exiting...")
                break
            elif user_message.lower() == 'list':
                show_node_list(node_list)
            else:
                # Send the message to all nodes (no need for 'to_node' input)
                send_message(local, user_message)

        except KeyboardInterrupt:
            print("\nScript terminated by user.")
            break

    # Close the interface when done
    local.close()

if __name__ == "__main__":
    main()
