import random
import threading
import select
import struct
import sys
import socket
import time
from datetime import datetime

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
            self.timers = self.split_timers()

    def __repr__(self):
        return f'Router id: {self.router_id}\n' \
               f'Input ports: {self.input_ports}\n' \
               f'Outputs: {self.outputs}\n' \
               f'Timers: {self.timers}'

    def read_file(self):
        """Reads an ascii config file and returns the lines: router_ids, input_ports,
           and timer, if it exists"""
        timers = None
        try:
            with open(self.config_file, 'r') as f:
                lines = f.readlines()
                router_ids = lines[0]
                input_ports = lines[1]
                outputs = lines[2]
                if len(lines) == 4:
                    timers = lines[3]
                if len(lines) > 4:
                    raise SyntaxError('too many lines in config file')
                return router_ids, input_ports, outputs, timers
        except IndexError:
            print('CONFIG_FILE ERROR: config file syntax is wrong')
            sys.exit()
        except SyntaxError as err:
            print('CONFIG_FILE ERROR: ' + str(err))
            sys.exit()
        except FileNotFoundError as err:
            print('INCORRECT FILENAME: ' + str(err))
            sys.exit()

    def split_ids(self):
        """Checks the router id line is formatted correctly and then returns the router id number"""
        router_ids_split = self.router_ids_line.split()
        try:
            if router_ids_split[0] != 'router-id':
                raise SyntaxError('router-ids not given')
            if len(router_ids_split) > 2:
                raise SyntaxError('too many router-ids given')
            return int(router_ids_split[1])
        except IndexError:
            print('CONFIG_FILE ERROR: router id not given')
            sys.exit()
        except SyntaxError as err:
            print('CONFIG_FILE ERROR: ' + str(err))
            sys.exit()
        except ValueError:
            print('CONFIG_FILE ERROR: router-id given is not an int')
            sys.exit()

    def split_input_ports(self):
        """Checks the input ports line is formatted correctly and then returns the ports as a list"""
        ports = []
        input_ports_split = self.input_ports_line.split()
        try:
            if input_ports_split[0] != 'input-ports' or len(input_ports_split) < 2:
                raise SyntaxError('input-ports not given')
            for input_port in input_ports_split[1:]:
                port = input_port.rstrip(',')
                port_number = int(port)
                if port_number < 1024 or port_number > 640000:
                    raise ValueError('port numbers not in range 1024 - 64000')
                ports.append(port_number)
            if len(ports) != len(set(ports)):
                raise ValueError('duplicate input-ports used')
        except ValueError as err:
            print('CONFIG_FILE_ERROR: ' + str(err))
            sys.exit()
        except SyntaxError as err:
            print('CONFIG_FILE_ERROR: ' + str(err))
            sys.exit()
        else:
            return ports

    def split_outputs(self):
        """Checks the outputs line is formatted correctly and then returns the outputs as a list of tuples of the format
           (input port num of peer router, metric to peer router, router id of peer router)"""
        outputs = []
        outputs_split = self.outputs_line.split()
        try:
            if outputs_split[0] != 'outputs' or len(outputs_split) < 2:
                raise SyntaxError('outputs not given')
            for input_port in outputs_split[1:]:
                output = input_port.rstrip(',')
                output = tuple(output.split('-'))
                if len(output) != 3:
                    raise SyntaxError('outputs syntax invalid')
                output = (int(output[0]), int(output[1]), int(output[2]))
                output_port, metric, neighbour_router = output
                if output_port in self.input_ports:
                    raise ValueError('a output given is the same as an input')
                if output_port < 1024 or output_port > 64000:
                    raise ValueError('output-port not in range 1024 - 64000')
                if metric not in range(1, 16):
                    raise ValueError('metric given not in range 1 - 15')
                if neighbour_router not in range(1, 64001):
                    raise ValueError('neighbouring router given not in range 1 - 64000')
                outputs.append(output)
        except ValueError as err:
            print('CONFIG_FILE ERROR: ' + str(err))
            sys.exit()
        except SyntaxError as err:
            print('CONFIG_FILE ERROR: ' + str(err))
            sys.exit()
        except IndexError:
            print('CONFIG_FILE ERROR: not enough outputs given')
        else:
            return outputs

    def split_timers(self):
        """Splits the timers into period, timeout and garbage collection variables respectively.
        Returns None if no timers given"""
        if self.timer_line is None:
            return None
        else:
            try:
                timer_split = self.timer_line.split()
                if timer_split[0] != 'timers' or len(timer_split) < 4:
                    raise SyntaxError('not enough timers given')
                period = int(timer_split[1].rstrip(','))
                timeout = int(timer_split[2].rstrip(','))
                garbage_collection = int(timer_split[3].rstrip(','))
                if timeout / period != 6:
                    raise ValueError('timeout / period ratio should be 6')
                if garbage_collection / period != 4:
                    raise ValueError('garbage_collection / period ratio should be 4')
                return period, timeout, garbage_collection
            except SyntaxError as err:
                print('CONFIG_FILE ERROR: ' + str(err))
                sys.exit()
            except ValueError as err:
                print('CONFIG_FILE ERROR: ' + str(err))
                sys.exit()


class Router:

    def __init__(self, router_id, input_ports, outputs, timers):
        self.state = 'START'
        self.router_id = router_id
        self.input_ports = input_ports
        self.outputs = outputs
        self.routing_table = {}
        self.input_udp_sockets = self.create_udp_sockets()
        self.output_udp_socket = self.input_udp_sockets[0]  # This is the socket we will use to send packets
        if timers is None:
            self.period = 30
            self.timeout = 180
            self.garbage_collection = 180
        else:
            self.period = timers[0]
            self.timeout = timers[1]
            self.garbage_collection = timers[2]
        self.timers = {}  # Dictionary used to store timeout and garbage collection timer threads

    def __repr__(self):
        print('Routing Table')
        for destination in self.routing_table:
            timeout_running_time = time.time() - self.timers["Timeout " + str(destination)][1]
            print('Destination: {}, Metric: {}, Next hop: {}, Timeout: {:.2f}'
                  .format(destination, self.routing_table[destination][0], self.routing_table[destination][1], timeout_running_time))
        print()

    def create_udp_sockets(self):
        """Returns a list of UDP sockets, one for each input port and bound to each input port"""
        udp_sockets = []
        for input_port in self.input_ports:
            try:
                input_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
                self.set_timeout(destination)
                break
        rip_entries = packet[3:]  # Removes header
        num_rip_entries = len(rip_entries) // 6
        for i in range(num_rip_entries):
            start_entry = i * 6
            rip_entry = rip_entries[start_entry:start_entry + 6]
            destination = rip_entry[2]
            metric = rip_entry[5]
            next_hop = self.routing_table[sender][1]  # Next hop router_id
            total_metric = self.routing_table[sender][0] + metric
            if destination in self.routing_table:
                if total_metric < self.routing_table[destination][0]:
                    self.routing_table[destination] = (total_metric, next_hop)
                    self.set_timeout(destination)
                elif metric == 16 and self.routing_table[destination][1] == sender:
                    self.routing_table[destination] = (metric, next_hop)
                    self.set_timeout(destination)
                    self.send_packet(self.output_udp_socket, True)  # Send triggered update
            else:
                if metric == 16:  # Ignore the packet
                    return
                else:
                    self.routing_table[destination] = (total_metric, next_hop)
                    self.set_timeout(destination)

    def set_timeout(self, destination):
        """Cancels any timeouts already running for the given destination and sets the Timeout timer for the associated
        destination in the routing table and adds it to the timers dictionary of threads"""
        if 'Timeout ' + str(destination) in self.timers.keys():
            self.timers["Timeout " + str(destination)][0].cancel()
        if 'Garbage ' + str(destination) in self.timers.keys():
            self.timers["Garbage " + str(destination)][0].cancel()
        timeout_thread = threading.Timer(self.timeout, self.timeout_function, args=[destination])
        self.timers["Timeout " + str(destination)] = timeout_thread, time.time()
        timeout_thread.start()
        # print(f'started timeout at {datetime.now().time()}')

    def timeout_function(self, destination):
        """Sets the metric for the destination in the routing table to 16 as the timeout timer has exceeded
        and assumes the route to destination is broken"""
        self.routing_table[destination] = (16, self.routing_table[destination][1])
        print(f'timeout {self.routing_table}')
        garbage_thread = threading.Timer(self.garbage_collection, self.garbage_collection_function, args=[destination])
        self.timers["Garbage " + str(destination)] = garbage_thread, time.time()
        garbage_thread.start()
        self.send_packet(self.output_udp_socket, True)  # Send triggered update as is unreachable

    def garbage_collection_function(self, destination):
        """Deletes the given destination route from the routing table"""
        del self.routing_table[destination]
        print(f'garbage {self.routing_table}')

    def unpack_packet(self, socket):
        """Receives a packet from a socket and extracts the contents of a packet received on a input socket and
        returns it as a tuple of values """
        packet, _ = socket.recvfrom(1024)
        packet = bytes(packet)  # Needed in order to use struct.unpack
        format = 'BBH'  # This is the format for the header
        rip_entries = len(packet) // 20  # This gets the number of rip entries as each entry is 20 bytes
        format += 'HHIIII' * rip_entries
        extracted_packet = struct.unpack(format, packet)
        valid = self.check_packet(extracted_packet)
        if not valid:
            return
        print(f'Received packet from Router {extracted_packet[2]}')
        self.add_to_table(extracted_packet)
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
                if next_hop == output_id:  # Impliments split horizon with poisoned reverse
                    metric = 16
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
        for output_port, _, _ in self.outputs:  # Send a update packet to each connected router
            packet = self.create_packet(output_port)
            socket.sendto(packet, (localhost, int(output_port)))
        if triggered:
            print(f'Sent triggered update packets to {self.outputs}')
        else:
            print(f'Sent update packets to {self.outputs}\n')
            wait_time = random.uniform(0.8, 1.2) * self.period  # Creates a random wait time around 30secs
            time.sleep(wait_time)
            self.send_packet(socket)

    def close_threads(self):
        """Cancels all running threads"""
        for thread, _ in self.timers.values():
            thread.cancel()

    def event_loop(self):
        try:
            while True:
                readable, writable, exceptional = select.select(self.input_udp_sockets, [self.output_udp_socket],
                                                                self.input_udp_sockets)
                for socket in readable:
                    try:
                        self.unpack_packet(socket)
                        self.__repr__()
                    except ConnectionResetError as err:
                        print(f'Error receiving packet: {err}')
                for socket in writable:
                    if self.state == 'START':
                        update_thread = threading.Thread(target=self.send_packet,
                                                         args=[socket],
                                                         daemon=True)
                        update_thread.start()
                        self.state = 'NEXT'
        except KeyboardInterrupt:
            self.close_threads()



if __name__ == '__main__':
    parser = ConfigParser()
    # print(parser)
    router = Router(parser.router_id, parser.input_ports, parser.outputs, parser.timers)
    # print(router.timeout, router.garbage_collection)
    router.event_loop()
