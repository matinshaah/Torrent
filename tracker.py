import pathlib
import socket
import threading
import time
from datetime import datetime
import json

has_started = False

buffer_size = 1500
files_data: dict[str: list[str]] = {}  # {'file.txt': ['peer1', 'peer2']}
peers: dict[str: tuple[str, list]] = {}


def start_tracker(address, port):
    check_thread = threading.Thread(target=check_peer)
    check_thread.start()
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((address, port))
    while True:
        data, addr = udp_socket.recvfrom(buffer_size)
        message = data.decode()

        args = message.split()
        if args[0] == 'get':
            file_peers = get_file_data(args)
            sending_data = []
            if len(file_peers) == 0:
                # sending_data = 'file not found!\n'
                pass
            else:
                sending_data = file_peers
            sending_data = json.dumps(sending_data)
            udp_socket.sendto(sending_data.encode(), addr)
            listening_addr = args[2]
            log('get', file_name=args[1], peer=listening_addr)
            print('data send')
        elif args[0] == 'share':
            if len(args) == 1:
                continue
            listening_addr = args[2]
            add_file_data(file_name=args[1], peer_addr=listening_addr)
            log('share', args[1], peer=listening_addr)
            udp_socket.sendto('Thanks for sharing'.encode(), addr)
        elif args[0] == 'ping':
            update_ping(peer_addr=args[1])
        if args[0] != 'ping':
            print(f'peers:{peers}\nfiles:{files_data}')


def log(state: str, file_name: str, peer):
    path = f'./file_logs/{file_name}'
    if state == 'share':
        with open(path, 'w') as file:
            log_message = f'Peer {peer} shared {file_name}'

            file.write(log_message + '\n')
        file.close()
    elif state == 'get':
        with open(path, 'w') as file:
            log_message = f'Peer {peer} asked for {file_name}'
            file.write(log_message + '\n')
        file.close()
    path = 'request_logs.txt'
    with open(path, 'a') as file:
        file.write(log_message + ', peers having this file: {files_data[file_name]}\n')
    file.close()


def check_peer():
    while True:
        try:
            for peer, data in peers.items():
                last_ping_time = data[0]
                if (datetime.now() - last_ping_time).total_seconds() > 60:
                    remove_peer(peer)
            time.sleep(10)
        except RuntimeError:
            pass


def remove_peer(peer: str):
    print(f'peer {peer} disconnected.')
    data = peers[peer]
    peers.pop(peer)
    file_list = data[1]
    for file in file_list:
        file_peers: list = files_data[file]
        file_peers.remove(peer)


def update_ping(peer_addr):
    if peer_addr not in peers.keys():
        peers[peer_addr] = datetime.now(), []
    else:
        files = peers[peer_addr][1]
        peers[peer_addr] = datetime.now(), files


def get_file_data(args):
    file_name = args[1]
    for file, data in files_data.items():
        if file == file_name:
            return data
    return []


def add_file_data(file_name, peer_addr):
    if peer_addr not in peers.keys():
        peers[peer_addr] = datetime.now(), [file_name]
        print(f'peer {peer_addr} connected')
    else:
        files = peers[peer_addr][1]
        if file_name not in files:
            files.append(file_name)
        peers[peer_addr] = datetime.now(), files
    if file_name not in files_data:
        files_data.update({file_name: [peer_addr]})
    elif peer_addr not in files_data.get(file_name):
        files_data.get(file_name).append(peer_addr)



def print_file_log(file_name):
    path = f'file_logs/{file_name}'
    file = pathlib.Path(path)
    if not file.exists():
        print('file not found!')
        return
    print('current peers: ', files_data[file_name], '\n')
    with open(file, 'r') as f:
        data = f.readlines()
        for line in data:
            print(line)


def print_request_logs():
    print('files_data: ', files_data)
    path = 'request_logs.txt'
    with open(path, 'r') as file:
        data = file.readlines()
        for line in data:
            print(line)


if __name__ == '__main__':
    while True:
        command = input()
        args = command.split()
        if args[0] == 'tracker':
            address, port = args[1].split(':')
            if has_started:
                print('Error, tracker has been already started!')
            else:
                has_started = True
                print(f'address:{address}, port:{port}')
                main_thread = threading.Thread(target=start_tracker, args=(address, int(port)))
                main_thread.start()
        elif args[0] == 'file_logs':
            if args[1] == 'all':
                for file in files_data.keys():
                    print_file_log(file)
            else:
                file_name = args[1]
                print_file_log(file_name)
        elif command == 'request logs':
            print_request_logs()
