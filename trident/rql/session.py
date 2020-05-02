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

    def define_annotation(self, data_type, data_spec, selection):
        if data_type == 'COST':
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
            print('%s is defined as COST' % (data_spec.varname))
        if selection.element_type == 'NODE':
            self.node_prop_specs[data_spec.varname] = data_spec
        elif selection.element_type == 'LINK':
            self.edge_prop_specs[data_spec.varname] = data_spec
        else:
            self.port_prop_specs[data_spec.varname] = data_spec
        self.set_prop_values(data_spec.varname, data_spec.default_value, selection)

    def set_annotation(self, data_type, var_ref, value, selection):
        if data_type == 'COST':
            if var_ref not in self.cost_specs:
                raise Exception('%s is not defined as cost' % (var_ref))
        elif var_ref in self.cost_specs:
            raise Exception('%s is defined as cost' % (var_ref))
        element_type = selection.element_type
        if element_type == 'NODE':
            if var_ref not in self.node_prop_specs:
                raise Exception('%s is not defined for %s' % (var_ref, element_type))
            data_spec = self.node_prop_specs[var_ref]
        elif element_type == 'LINK':
            if var_ref not in self.edge_prop_specs:
                raise Exception('%s is not defined for %s' % (var_ref, element_type))
            data_spec = self.edge_prop_specs[var_ref]
        else:
            if var_ref not in self.port_prop_specs:
                raise Exception('%s is not defined for %s' % (var_ref, element_type))
            data_spec = self.port_prop_specs[var_ref]
        if data_spec.element_type != selection.element_type:
            raise Exception('Bad selection: element type mismatch')
        value = data_spec.interpret(value)

        self.set_prop_values(var_ref, value, selection)

    def set_prop_values(self, propname, value, selection):
        elements = self.select_element(selection.element_type,
                                       selection.constraints)
        for e in elements:
            elements[e][propname] = value

    def get_prop_value(self, element, element_type, props, prop):
        if prop in props:
            spec = props[prop]
            return element.get(prop, spec.default_value)
        else:
            return prop

    def run_test(self, lvalue, op, rvalue):
        if op == '>':
            return lvalue > rvalue
        elif op == '>=':
            return lvalue >= rvalue
        elif op == '<':
            return lvalue < rvalue
        elif op == '<=':
            return lvalue <= rvalue
        elif op == '=':
            return lvalue == rvalue
        elif op == '!=':
            return lvalue != rvalue
        else:
            raise Exception('%s is not defined' % (op))

    def apply_constraint(self, element, element_type, props, constraints):
        if constraints is None:
            return True
        elif isinstance(constraints, BasicConstraint):
            lhs = str(constraints.lhs)
            op = str(constraints.op)
            rhs = str(constraints.rhs)

            lhs = self.get_prop_value(element, element_type, props, lhs)
            rhs = self.get_prop_value(element, element_type, props, rhs)

            return self.run_test(lhs, op, rhs)
        elif constraints.op == 'OR':
            lhs = self.apply_constraint(element, element_type, props, constraints.lhs)
            rhs = self.apply_constraint(element, element_type, props, constraints.rhs)
            return lhs or rhs
        elif constraints.op == 'AND':
            lhs = self.apply_constraint(element, element_type, props, constraints.lhs)
            rhs = self.apply_constraint(element, element_type, props, constraints.rhs)
            return lhs and rhs
        elif constraints.op == 'NOT':
            lhs = self.apply_constraint(element, element_type, props, constraints.lhs)
            return not lhs
        else:
            return True

    def select_element(self, element_type, constraints):
        # TODO: ignore constraints for now
        if element_type == 'NODE':
            elements = self.nodes
            props = self.node_prop_specs
        elif element_type == 'LINK':
            elements = self.edges
            props = self.edge_prop_specs
        else:
            elements = self.ports
            props = self.port_prop_specs
        return {e: elements[e] for e in elements if self.apply_constraint(elements[e], element_type, props, constraints)}

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
            cmd.data_spec.varname = str(cmd.data_spec.varname)
            var.define_annotation(cmd.data_type, cmd.data_spec, cmd.selection)

    def set_value(self, cmd):
        var_ref = str(cmd.selection.toponame)
        if var_ref in self.variables:
            var = self.variables[var_ref]
            varname = str(cmd.varname)
            var.set_annotation(cmd.data_type, cmd.varname, cmd.value, cmd.selection)

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
