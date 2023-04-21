import random
import socket
import threading
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# def start_peer(file_name, tracker_address, listen_address):
#     udp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     udp_socket.bind(listen_address)
#     pass


buff_size = 1500


def get_addr_tuple(addr):
    ip, p = addr.split(':')
    p = int(p)
    return ip, p


def get_random_item(peer_list: list):
    n = len(peer_list)
    i = random.randint(0, n - 1)
    return peer_list[i]


class Peer:
    def __init__(self, listen_address:str, tracker_address :str):
        self.listen_address = listen_address
        self.tracker_address = tracker_address
        ip, p = listen_address.split(':')
        p = int(p)
        self.listen_address_tuple = ip, p
        ip, p = tracker_address.split(':')
        p = int(p)
        self.tracker_address_tuple = ip, p
        self.log_path = f'./peers/{listen_address}/logs.txt'
        parent_path = f'./peers/{listen_address}'
        Path(parent_path).mkdir(exist_ok=True)

    def get_file_info(self, file_name):
        # print('in get file info')
        self.log(state='get', file_name=file_name)
        udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        udp_socket.sendto(f'get {file_name} {self.listen_address}'.encode(), self.tracker_address_tuple)
        data, addr = udp_socket.recvfrom(buff_size)
        data = data.decode()
        peer_list = json.loads(data)
        self.log(message=f'data received from server:\n"{peer_list}"\n')
        if len(peer_list) == 0:
            self.log(message='no peer found')
            return
        peer_addr = get_random_item(peer_list)

        self.get_file(file_name, peer_addr)
        self.share_file_info(file_name)

    def get_file(self, file_name, peer_addr):
        self.log(message=f'Making connection to peer "{peer_addr}" to get file {file_name}...')
        tcp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        tcp_socket.connect(get_addr_tuple(peer_addr))
        tcp_socket.send(f'get {file_name}'.encode())
        data = tcp_socket.recv(buff_size).decode()
        if data == 0:
            self.log(message=f'peer didn\'t find file: {file_name}')
            return
        file_dir = Path(f'./peers/{self.listen_address}')
        file_dir.mkdir(exist_ok=True)

        with open(f'{file_dir}/{file_name}', 'wb') as file:
            while True:
                data = tcp_socket.recv(buff_size)
                if not data:
                    break
                file.write(data)

        self.log(message=f'file {file_name} downloaded successfully, closing socket ...')
        file.close()
        tcp_socket.close()

    def share_file_info(self, file_name):
        self.log(state='share', file_name=file_name)
        udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        udp_socket.sendto(f'share {file_name} {self.listen_address}'.encode(), self.tracker_address_tuple)
        data, addr = udp_socket.recvfrom(buff_size)
        data = data.decode()
        if True:
            self.seed()

    def send_ping(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while True:
            udp_socket.sendto(f'ping {self.listen_address}'.encode(), ('localhost', 8000))
            time.sleep(1)

    def send_file(self, con, addr):
        data = con.recv(buff_size).decode()
        args = data.split()
        if args[0] == 'get':
            file_name = args[1]
            file_path = Path(f'./peers/{self.listen_address}/{file_name}')
            if not file_path.exists():
                # file not found
                # con.send(f'file "{file_name}" not found.'.encode())
                con.send('0'.encode())
            else:
                con.send('1'.encode())

            self.log(message=f'sending file {file_name} to peer {addr}')
            with open(file_path, 'rb') as file:
                while True:
                    file_data = file.readline()
                    if not file_data:
                        break
                    con.send(file_data)
            file.close()
            con.close()
            self.log(message=f'file {file_name} sent successfully')

    def seed(self):
        thread_pool = ThreadPoolExecutor(5)
        thread_pool.submit(self.send_ping)
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind(self.listen_address_tuple)
        tcp_socket.listen()
        while True:
            self.log(message='waiting for connection')
            con, addr = tcp_socket.accept()
            thread_pool.submit(self.send_file, con, addr)

    def log(self, state: str =None, file_name=None, message=None):
        path = Path(self.log_path)
        # path.mkdir(exist_ok=True)
        log_message = message
        if state == 'get':
            log_message = f'asking for file {file_name}'
        elif state == 'share':
            log_message = f'sharing file {file_name}'
        elif state == 'waiting':
            log_message = 'waiting for TCP connection'
        with open(path, 'a') as file:
            file.write(log_message+'\n')
        print(log_message)

    def print_logs(self):
        path = Path(self.log_path)
        if not path.exists():
            print('no log')
            return
        with open(path, 'r') as file:
            data = file.readlines()
            for line in data:
                print(line)


has_started = False
if __name__ == '__main__':
    p: Peer
    while True:
        command = input()
        args = command.split()
        if args[0] == 'peer':
            if has_started:
                print('Error, peer has been already started!')
            else:
                has_started = True
                file_name = args[2]
                tracker_address = args[3]
                listen_address = args[4]
                peer = Peer(tracker_address=tracker_address, listen_address=listen_address)
                p = peer
                if args[1] == 'get':
                    main_thread = threading.Thread(target=peer.get_file_info, args=(file_name,))
                    main_thread.start()
                elif args[1] == 'share':
                    main_thread = threading.Thread(target=peer.share_file_info, args=(file_name,))
                    main_thread.start()
        elif command == 'request logs':
            if not has_started:
                print('You have to run the peer first')
                continue
            p.print_logs()
