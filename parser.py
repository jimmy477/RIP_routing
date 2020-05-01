import random
import threading
import sched
import select
import struct
import sys
import socket
import time

localhost = '127.0.0.1'


class ConfigParser:
    """Class that parses a configuration file for the COSC364 RIPv2 assignment"""

    def __init__(self):
        try:
            self.config_file = sys.argv[1]
        except IndexError:
            print('ERROR: No config filename was given')
            sys.exit()
        else:
            self.router_ids_line, self.input_ports_line, self.outputs_line, self.timer_line = self.read_file()
            self.router_id = self.split_ids()
            self.input_ports = self.split_input_ports()
            self.outputs = self.split_outputs()

    def read_file(self):
        """Reads an ascii config file and returns the lines: router_ids, input_ports,
           and timer, if it exists"""
        timer = None
        router_ids = None
        input_ports = None
        outputs = None
        with open(self.config_file, 'r') as f:
            lines = f.readlines()
            for line_n in lines:
                param = line_n.split(' ')
                if param[0] == 'router-id':
                    router_ids = line_n
                if param[0] == 'input-ports':
                    input_ports = line_n
                if param[0] == 'outputs':
                    outputs = line_n
                if param[0] == 'timer':
                    timer = line_n
            if router_ids is None or input_ports is None or outputs is None:
                # checks if the parts of the ascii file have been found if not exception raised.
                print('CONFIG_FILE ERROR: wrong formatting')
                sys.exit()
            else:
                # This is true if their is a timer parameter
                f.close()
                return router_ids, input_ports, outputs, timer

    def split_ids(self):
        """Checks the router id line is formatted correctly and then returns the router id number"""
        router_ids_split = self.router_ids_line.split()
        if router_ids_split[0] != 'router-id':
            raise Exception('CONFIG_FILE ERROR: router-id not given')
        try:
            return router_ids_split[1]
        except IndexError:
            print('CONFIG_FILE ERROR: router-id not given')
            sys.exit()

    def split_input_ports(self):
        """Checks the input ports line is formatted correctly and then returns the ports as a list"""
        ports = []
        input_ports_split = self.input_ports_line.split()

        if input_ports_split[0] != 'input-ports':
            raise Exception('CONFIG_FILE ERROR: input-ports not given')
        for input_port in input_ports_split[1:]:
            port = input_port.rstrip(',')
            try:
                port_number = int(port)
            except ValueError:
                print('CONFIG_FILE_ERROR: port numbers given were not numbers')
                sys.exit()
            else:
                if port_number < 1024 or port_number > 640000:
                    raise Exception('CONFIG_FILE ERROR: port numbers not in range 1024 - 64000')
                ports.append(port_number)
        return ports

    def split_outputs(self):
        """Checks the outputs line is formatted correctly and then returns the outputs as a list of tuples of the format
           (input port num of peer router, metric to peer router, router id of peer router)"""
        outputs = []
        outputs_split = self.outputs_line.split()
        if outputs_split[0] != 'outputs':
            raise Exception('CONFIG_FILE ERROR: outputs not given')
        for input_port in outputs_split[1:]:
            output = input_port.rstrip(',')
            output = tuple(output.split('-'))
            outputs.append([int(i) for i in output])
        return outputs

    def split_timer(self):
        pass


class Router:

    def __init__(self, router_id, input_ports, outputs):
        self.state = 'START'
        self.router_id = int(router_id)
        self.input_ports = input_ports
        self.outputs = outputs
        self.output_ports = [(port, router_id) for port, _, router_id in outputs]  # Creates a list of output ports
        self.routing_table = {}
        self.input_udp_sockets = self.create_udp_sockets()
        self.output_udp_socket = self.input_udp_sockets[0]  # This is the socket we will use to send packets

    def create_udp_sockets(self):
        """Returns a list of UDP sockets, one for each input port and bound to each input port"""
        udp_sockets = []
        for input_port in self.input_ports:
            # TODO add error handling
            try:
                input_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                input_socket.setblocking(False)
            except socket.error as err:
                print(f'Error: {err}')
            try:
                input_socket.bind((localhost, input_port))
            except:
                print(f'Error: could not bind port number {input_port} to socket')
            udp_sockets.append(input_socket)
        return udp_sockets

    def add_to_table(self, packet):
        sender = packet[2]  # router_id of sender
        for _, cost, destination in self.outputs:
            if sender == destination:
                self.routing_table[destination] = (cost, sender)
            else:
                pass
        rip_entries = packet[3:]  # Removes header
        num_rip_entries = len(rip_entries) // 6
        for i in range(num_rip_entries):
            start_entry = i * 6
            rip_entry = rip_entries[start_entry:start_entry + 6]
            destination = rip_entry[2]
            metric = rip_entry[5]
            next_hop = self.routing_table[sender][1]  # Next hop router_id
            total_metric = self.routing_table[sender][0] + metric
            # TODO start timeout timer whenever the routing table is updated
            if destination in self.routing_table:
                if total_metric < self.routing_table[destination][0]:
                    self.routing_table[destination] = (total_metric, next_hop)
                elif metric == 16 and self.routing_table[destination][1] == sender:  # Next hop is the sender
                    self.routing_table[destination] = (metric, next_hop)
                    self.send_packet(self.output_udp_socket[0], True)  # Send triggered update
                    # TODO triggered update for new unreachable route
                    # TODO start garbage collection timer probably as there own threads
            else:
                self.routing_table[destination] = (total_metric, next_hop)  # TODO check if metric if 16

    def unpack_packet(self, socket):
        """Receives a packet from a socket and extracts the contents of a packet received on a input socket and
        returns it as a tuple of values """
        packet, senders_address = socket.recvfrom(1024)
        print(f'Received packet from {senders_address[1]}')
        packet = bytes(packet)  # Needed in order to use struct.unpack
        format = 'BBH'  # This is the format for the header
        rip_entries = len(packet) // 20  # This gets the number of rip entries as each entry is 20 bytes
        format += 'HHIIII' * rip_entries
        extracted_packet = struct.unpack(format, packet)
        valid = self.check_packet(extracted_packet)
        if not valid:
            return
        self.add_to_table(extracted_packet)

    def check_packet(self, packet):
        """Checks if a packet is valid, return true if it is, otherwise false"""
        header = packet[:3]
        command = header[0]
        version = header[1]
        sender = header[2]
        if version != 2 or command != 2 or sender not in range(1, 64001):  # We do not implement command = 1 (request msgs)
            print('Packet dropped: invalid header')
            return False
        rip_entries = packet[3:]  # Removes header
        num_rip_entries = len(rip_entries) // 6
        for i in range(num_rip_entries):
            start_entry = i * 6
            rip_entry = rip_entries[start_entry:start_entry + 6]
            afi = rip_entry[0]  # Address family identifier
            zero1 = rip_entry[1]
            destination = rip_entry[2]
            zero2 = rip_entry[3]
            zero3 = rip_entry[4]
            metric = rip_entry[5]
            if afi != 2 or zero1 != 0 or destination not in range(1, 64001) or zero2 != 0 or zero3 != 0 or metric < 0:
                print('Packet dropped: invalid rip entry')
                return False
        return True

    def find_id_by_port(self, output_port):
        """Returns the router_id of the given output_port number"""
        for port, _, id in self.outputs:
            if output_port == port:
                return id

    def create_packet(self, output_port):
        """Creates the RIPv2 response containing a header and the rip entries of its own routing table but omits
           any entry it its next hop is equal to the output_port given"""
        output_id = self.find_id_by_port(output_port)
        try:
            header = struct.pack(
                'BBH',  # Specifies two unsigned ints of one byte each and one unsigned int of two bytes
                2,  # Specifies the command number (response)
                2,  # Specifies the version number
                self.router_id
            )
            packet = header
            for destination, values in self.routing_table.items():
                metric, next_hop = values
                if next_hop != output_id:  # Does not send entries to router if it learnt it from this router
                    packet = packet + struct.pack(
                        'HHIIII',  # Specifies two unsigned ints of 2 bytes each and 4 unsigned ints of 4 bytes each
                        2,  # Address family identifier AF_INET
                        0,
                        int(destination),
                        0,
                        0,
                        int(metric)
                    )
        except struct.error as error:
            print(f'Error creating packet: {error}')
        return packet

    def send_packet(self, socket, triggered=False):
        """Sends an update packet to all neighbours, if triggered is true then only send once"""
        #TODO Test poisoned reversed is working.
        for output_port, _, _ in self.outputs:  # Send a update packet to each connected router
            packet = self.create_packet(output_port)
            socket.sendto(packet, (localhost, int(output_port)))
        if triggered:
            print(f'Sent triggered update packets to {self.outputs}')
        else:
            print(f'Sent update packets to {self.outputs}')
            wait_time = random.uniform(0.8, 1.2) * 30  # Creates a random wait time around 30secs
            time.sleep(wait_time)
            time.sleep(5)  # Temporary for debugging
            self.send_packet(socket)

    def event_loop(self):
        i = 1
        while True:
            # print("\nWaiting for event...")
            readable, writable, exceptional = select.select(self.input_udp_sockets, [self.output_udp_socket],
                                                            self.input_udp_sockets)
            # print_sockets("inputs: ", self.input_udp_sockets)
            # print_sockets("readable: ", readable)
            # print_sockets("writable: ", writable)
            # print_sockets("exceptional: ", exceptional)

            for socket in readable:
                try:
                    self.unpack_packet(socket)
                    print(f'Routing table: {self.routing_table}')
                except ConnectionResetError as err:
                    print(f'Error receiving packet: {err}')
            for socket in writable:
                if self.state == 'START':
                    update_thread = threading.Thread(target=self.send_packet,
                                                     args=[socket],
                                                     daemon=True)
                    update_thread.start()
                    self.state = 'NEXT'
            # time.sleep(10)
            i += 1


if __name__ == '__main__':
    parser = ConfigParser()
    router = Router(parser.router_id, parser.input_ports, parser.outputs)
    # print(router.outputs, router.output_ports)
    # print(router.outputs)
    router.event_loop()