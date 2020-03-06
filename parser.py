class ConfigParser:

    def __init__(self, config_file):
        self.config_file = config_file
        router_ids, input_ports, outputs, timer = self.read_file()
        self.router_ids_line = router_ids
        self.router_id = self.split_ids()
        self.input_ports_line = input_ports
        self.outputs_line = outputs
        self.timer_line = timer

    def read_file(self):
        """Reads an ascii config file and returns the lines: router_ids, input_ports,
           and timer, if it exists"""
        timer = None
        f = open(self.config_file, 'r')
        lines = f.readlines()
        router_ids = lines[0]
        input_ports = lines[1]
        outputs = lines[2]

        # This is true if their is a timer parameter
        if len(lines) > 3:
            timer = lines[3]
        f.close()
        return router_ids, input_ports, outputs, timer

    def split_ids(self):
        try:
            return self.router_ids_line[1]
        except IndexError:
            print('CONFIG_FILE ERROR: No router-id given')

    def split_input_ports(self):
        ports = []
        input_ports_split = self.input_ports_line.split()
        for input_port in input_ports_split[1:]:
            port = input_port.rstrip(',')
            ports.append(int(port))
        print(ports)

    def split_outputs(self):
        outputs = []
        outputs_split = self.outputs_line.split()
        for input_port in outputs_split[1:]:
            output = input_port.rstrip(',')
            outputs.append(output)
        print(outputs)

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
    parser.split_input_ports()
