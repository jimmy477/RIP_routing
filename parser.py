import sys
import socket


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
            #print(self.router_ids_line, self.router_id, self.input_ports, self.outputs)

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
                #checks if the parts of the ascii file have been found if not exception raised.
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
            outputs.append(output)
        return outputs

    def split_timer(self):
        pass


class Router:

    def __init__(self, router_id, input_ports, outputs):
        self.router_id = router_id
        self.input_ports = input_ports
        self.outputs = outputs

    def create_udp_sockets(self):
        """Creates a UDP socket  for each input port given, and binds one socket to each input port"""

        host = socket.gethostbyname(socket.gethostname())
        for input_port in self.input_ports:
            print(input_port)
            # TODO add  error handling
            input_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            input_socket.bind((host, input_port))


def event_loop(router):
    router.create_udp_sockets()
    while True:
        pass


if __name__ == '__main__':
    parser = ConfigParser()
    router = Router(parser.router_id, parser.input_ports, parser.outputs)
    event_loop(router)
