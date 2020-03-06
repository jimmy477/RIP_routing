class ConfigParser:
    """Class that parses a configuration file for the COSC364 RIPv2 assignment"""

    def __init__(self, config_file):
        self.config_file = config_file
        self.router_ids_line, self.input_ports_line, self.outputs_line, self.timer_line = self.read_file()
        self.router_id = self.split_ids()
        self.input_ports = self.split_input_ports()
        self.outputs = self.split_outputs()

    def read_file(self):
        """Reads an ascii config file and returns the lines: router_ids, input_ports,
           and timer, if it exists"""

        timer = None
        with open(self.config_file, 'r') as f:
            lines = f.readlines()
            try:
                router_ids = lines[0]
                input_ports = lines[1]
                outputs = lines[2]
            except IndexError:
                print('CONFIG_FILE ERROR: wrong formatting')
            else:
                # This is true if their is a timer parameter
                if len(lines) > 3:
                    timer = lines[3]
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

    def split_input_ports(self):
        """Checks the input ports line is formatted correctly and then returns the ports as a list"""

        ports = []
        input_ports_split = self.input_ports_line.split()
        if input_ports_split[0] != 'input-ports':
            raise Exception('CONFIG_FILE ERROR: input-ports not given')
        for input_port in input_ports_split[1:]:
            port = input_port.rstrip(',')
            ports.append(int(port))
        return ports

    def split_outputs(self):
        """Checks the outputs line is formatted correctly and then returns the outputs as a list"""

        outputs = []
        outputs_split = self.outputs_line.split()
        if outputs_split[0] != 'outputs':
            raise Exception('CONFIG_FILE ERROR: outputs not given')
        for input_port in outputs_split[1:]:
            output = input_port.rstrip(',')
            outputs.append(output)
        return outputs

    def split_timer(self):
        pass

    def split_line(self, line):
        split = line.split()
        identifier = split[0]
        if identifier == 'router-id':
            return line[1]
        elif identifier == 'input-ports':
            pass
        elif identifier == 'outputs':
            pass


if __name__ == '__main__':
    parser = ConfigParser('config.ascii')
