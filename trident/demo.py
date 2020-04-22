
class TridentDemo(object):
    def __init__(self):
        self.topology = {}
        self.current_query = ''
        self.selected_path = []

    def set_topology(self, g):
        self.topology = g
        self.current_query = ''
        self.selected_path = []

    def get_topology(self):
        return self.topology

    def set_attribute(self, nid, attr_name, attr_value):
        self.g.nodes[nid][attr_name] = attr_value

    def query(self, query):
        pass
