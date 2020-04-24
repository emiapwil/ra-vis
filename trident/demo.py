
import networkx as nx
import re

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
        pattern = 'src - dst where src.id = (\w+) and dst.id = (\w+)'
        m = re.search(pattern, query)
        if m is not None:
            src = m.group(1)
            dst = m.group(2)
            print(src, dst)
        g = self.topology
        path = nx.shortest_path(g, src, dst)
        pairs = list(zip(path[:-1], path[1:]))
        print(pairs)
        links = list(map(lambda p: g[p[0]][p[1]], pairs))
        links = list(map(lambda d: list(d.values())[0]['id'], links))
        return links
