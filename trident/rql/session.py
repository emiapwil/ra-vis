from trident.rql.common import *

import networkx as nx
from functools import reduce

class GraphDB():
    def __init__(self, g):
        self.raw_graph = g

        self.nodes = {n: g.nodes[n] for n in g.nodes()}
        self.edges = {}
        self.ports = {}

        for u, v, e in g.edges(data=True):
            e['id'] = len(self.edges)
            e['source'] = u
            e['target'] = v
            self.edges[e['id']] = e
            self.ports['%s:%s' % (u, e['id'])] = {u, e['id']}
            self.ports['%s:%s' % (v, e['id'])] = {v, e['id']}

        node_prop_names = reduce(lambda x, y: x | y,
                                 [self.nodes[n].keys() for n in self.nodes])
        self.node_prop_specs = {
            p: DataSpec(p, 'str', '') for p in node_prop_names
        }
        edge_prop_names = reduce(lambda x, y: x | y,
                                 [self.edges[e].keys() for e in self.edges])
        self.edge_prop_specs = {
            p: DataSpec(p, 'str', '') for p in edge_prop_names
        }
        self.port_prop_specs = {}

        self.cost_specs = {}

        self.views = {}

    def define_annotation(self, data_spec, selection):
        if data_spec.data_type == 'COST':
            if data_spec.accum_func == 'add' or data_spec.accum_func == '+':
                data_spec.accum_func = lambda x, y: x + y
            elif data_spec.accum_func == 'min':
                data_spec.accum_func = lambda x, y: min(x, y)
            elif data_spec.accum_func == 'max':
                data_spec.accum_func = lambda x, y: max(x, y)
            else:
                raise Exception('Accumulative Function %s is not supported'
                                % (data_spec.accum_func))
            data_spec.element_type = selection.element_type
            self.cost_specs[data_spec.varname] = data_spec
        if selection.element_type == 'NODE':
            self.node_prop_specs[data_spec.varname] = data_spec
        elif selection.element_type == 'LINK':
            self.edge_prop_specs[data_spec.varname] = data_spec
        else:
            self.port_prop_specs[data_spec.varname] = data_spec
        elements = self.select_element(selection.element_type,
                                       selection.constraints)
        for e in elements:
            elements[e][data_spec.varname] = data_spec.default_value

    def select_element(self, element_type, constraints):
        # TODO: ignore constraints for now
        if element_type == 'NODE':
            return self.nodes
        elif element_type == 'LINK':
            return self.edges
        else:
            return self.ports

    def __str__(self):
        nps = self.node_prop_specs
        eps = self.edge_prop_specs
        s = ''
        for n in self.nodes:
            node = self.nodes[n]
            props = ', '.join(['%s=%s' % (s, node.get(s, '')) for s in nps])
            s += '%s: %s\n' % (n, props)
        for e in self.edges:
            edge = self.edges[e]
            props = ', '.join(['%s=%s' % (s, edge.get(s, '')) for s in eps])
            s += '%s: %s\n' % (e, props)
        return s


class RqlSession(object):

    def __init__(self, topo_dir):
        self.topo_dir = topo_dir

        self.variables = {}
        self.views = {}

    def execute(self, commands):
        for cmd in commands:
            self.dispatch(cmd)

    def dispatch(self, cmd):
        if isinstance(cmd, LoadCommand):
            self.load(cmd)
        elif isinstance(cmd, DropCommand):
            self.drop(cmd)
        elif isinstance(cmd, DefineCommand):
            self.define(cmd)
        elif isinstance(cmd, SetCommand):
            self.set_value(cmd)
        elif isinstance(cmd, SelectCommand):
            self.select(cmd)
        elif isinstance(cmd, ShowCommand):
            self.show(cmd)

    def load(self, cmd):
        toponame = cmd.toponame
        varname = cmd.varname

        filename = '%s/%s.graphml' % (self.topo_dir, toponame)
        g = nx.read_graphml(filename).to_undirected()

        gdb = GraphDB(g)

        self.variables[varname] = gdb

    def drop(self, cmd):
        var_ref = str(cmd.var_ref)

        if var_ref in self.variables:
            var = self.variables[var_ref]
            if isinstance(var, DataSpec):
                pass # TODO
            del self.variables[var_ref]

    def define(self, cmd):
        var_ref = str(cmd.selection.toponame)

        if var_ref in self.variables:
            var = self.variables[var_ref]
            var.define_annotation(cmd.data_spec, cmd.selection)

    def set_value(self, cmd):
        pass

    def select(self, cmd):
        pass

    def show(self, cmd):
        var_ref = str(cmd.var_ref)
        if var_ref in self.variables:
            var = self.variables[var_ref]
            print(var)

if __name__ == '__main__':
    import sys
    from trident.rql.compiler import RqlCompiler

    larkfile, topo_dir, progfile = sys.argv[1:]

    compiler = RqlCompiler(larkfile)
    session = RqlSession(topo_dir)

    with open(progfile) as f:
        cmds = compiler.compile(f.read())

    session.execute(cmds)
