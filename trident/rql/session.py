from trident.rql.common import *

import networkx as nx
from networkx.algorithms import single_source_dijkstra as sssp
from functools import reduce

def cleanup(origin, eid):
    element = origin.copy()
    if 'x' in element:
        del element['x']
    if 'y' in element:
        del element['y']
    if 'label' in element:
        del element['label']
    element['id'] = eid
    return list(element.keys()), element


class GraphDB():
    def __init__(self, g):
        self.raw_graph = g

        self.nodes = {}
        self.edges = {}
        self.ports = {}

        for n in g.nodes():
            node = g.nodes[n]
            node['id'] = n
            self.nodes[n] = node

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

    def data(self):
        g = self.raw_graph
        pos = nx.nx_pydot.graphviz_layout(g)
        radius = {n: g.degree(n) for n in self.nodes}

        nodes = []
        nindex = {}
        for n in self.nodes:
            nindex[n] = len(nodes)
            node = {}
            node['id'] = n
            node['r'] = radius[n]
            node['x'] = pos[n][0]
            node['y'] = pos[n][1]
            node['label'] = g.nodes[n].get('label', '')
            node['proplist'], node['properties'] = cleanup(self.nodes[n], n)
            nodes += [node]

        links = []
        for eid in self.edges:
            e = self.edges[eid]
            edge = {}
            edge['id'] = len(links)
            edge['source'] = nindex[e['source']]
            edge['target'] = nindex[e['target']]
            edge['proplist'], edge['properties'] = cleanup(e, len(links))
            links += [edge]

        return {'nodes': nodes, 'links': links}

    def define_annotation(self, data_type, data_spec, selection):
        if data_type == 'COST':
            if data_spec.accum_func == 'add' or data_spec.accum_func == '+':
                data_spec.accum_func = lambda x, y: x + y
            elif data_spec.accum_func == 'min':
                data_spec.accum_func = lambda x, y: min(x, y)
                raise Exception('Accumulative Function %s is not supported'
                                % (data_spec.accum_func))
            elif data_spec.accum_func == 'max':
                data_spec.accum_func = lambda x, y: max(x, y)
                raise Exception('Accumulative Function %s is not supported'
                                % (data_spec.accum_func))
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
                raise Exception('%s is not defined as COST' % (var_ref))
        elif var_ref in self.cost_specs:
            raise Exception('%s is defined as COST' % (var_ref))
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

        self.set_prop_values(var_ref, value, selection)

    def set_prop_values(self, propname, value, selection):
        elements = self.select_element(selection.element_type,
                                       selection.constraints)
        for e in elements:
            elements[e][propname] = value.value

    def get_prop_value(self, element, element_type, props, prop):
        if isinstance(prop, VarRef):
            prop = str(prop)
            if prop in props:
                spec = props[prop]
                return element.get(prop, spec.default_value)
        elif isinstance(prop, Value):
            return prop.value
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
            lhs = constraints.lhs
            op = constraints.op
            rhs = constraints.rhs

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

    def select_path(self, ra_expr, constraints, opt_obj):
        wpc, nc, ec = self.classify_constraints(ra_expr, constraints)
        g = self.filter_graph(nc, ec)
        waypoints = self.find_waypoints(wpc)
        segments = zip(ra_expr.waypoints[:-1], ra_expr.waypoints[1:])
        segment_paths = []
        for src, dst in segments:
            sources = waypoints[src]
            targets = waypoints[dst]
            segment = self.find_path(g, sources, targets, opt_obj)
            segment_paths += [segment]
        return self.merge_segments(segment_paths)

    def classify_constraints(self, ra_expr, constraints):
        wpc, nc, ec = self.recursive_classify_constraints(constraints)
        for wp in ra_expr.waypoints:
            if wp not in wpc:
                raise Exception('Missing constraints on waypoint %s' % (wp))
            return wpc, nc, ec

    def filter_graph(self, node_constraints, edge_constraints):
        nodes = self.select_element('NODE', node_constraints)
        edges = self.select_element('LINK', edge_constraints)

        g = nx.MultiGraph()
        g.add_nodes_from(nodes)
        for e in edges:
            e = edges[e]
            u, v, d = e['source'], e['target'], e
            if u in nodes and v in nodes:
                g.add_edge(u, v, **d)

        return g

    def find_waypoints(self, waypoint_constraints):
        waypoints = {}
        for wp in waypoint_constraints:
            waypoints[wp] = self.select_element('NODE', waypoint_constraints[wp])
        return waypoints

    def find_path(self, g, sources, targets, opt_obj):
        ncosts = {}
        npaths = {}
        for src in sources:
            costs, paths = sssp(g, src, weight=opt_obj)
            ncosts[src] = { dst: costs[dst] for dst in targets }
            npaths[src] = { dst: paths[dst] for dst in targets }
        return (sources, targets, ncosts, npaths)

    def merge_segments(self, segment_paths):
        sources, _, _, _ = segment_paths[0]
        costs = {}
        paths = {}
        print(segment_paths)
        for src in sources:
            costs[src] = 0
            paths[src] = [src]
        argmin = lambda x, y: x if x[1] < y[1] else y
        for segment in segment_paths:
            s_srcs, s_dsts, s_costs, s_paths = segment
            costs2 = {}
            paths2 = {}
            for i in s_dsts:
                candidates = [(j, costs[j] + s_costs[j][i]) for j in s_srcs]
                k, costs2[i] = reduce(argmin, candidates)
                paths2[i] = paths[k] + s_paths[k][i][1:]
            costs = costs2
            paths = paths2

        opt, _ = reduce(argmin, [(n, costs[n]) for n in costs])
        return paths[opt]

    def merge_constraints(self, lhs, op, rhs):
        if lhs is None:
            return rhs
        if rhs is None:
            return lhs
        return CompoundConstraint(lhs, op, rhs)

    def get_waypoints(self, constraints):
        lhs = constraints.lhs
        rhs = constraints.rhs
        waypoints = set()
        if isinstance(lhs, VarRef) and lhs.waypoint is not None:
            waypoints |= {lhs.waypoint}
        if isinstance(rhs, VarRef) and rhs.waypoint is not None:
            waypoints |= {rhs.waypoint}
        if len(waypoints) > 1:
            raise Exception('Cross-waypoint constraint is not supported: %s'
                            % (constraints))
        if len(waypoints) == 1:
            if isinstance(lhs, VarRef) and lhs.waypoint is None:
                print(lhs)
                raise Exception('Invalid constraint: %s' % (constraints))
            if isinstance(rhs, VarRef) and rhs.waypoint is None:
                print(rhs)
                raise Exception('Invalid constraint: %s' % (constraints))
        return waypoints

    def lookup_data_spec(self, var_ref):
        ref = str(var_ref)
        if ref in self.node_prop_specs:
            return 'NODE', self.node_prop_specs[ref]
        if ref in self.edge_prop_specs:
            return 'LINK', self.edge_prop_specs[ref]
        else:
            return None, None

    def get_element_types(self, constraints):
        lhs = constraints.lhs
        rhs = constraints.rhs
        element_types = set()
        e1, s1 = self.lookup_data_spec(lhs)
        if e1 is not None:
            element_types |= {e1}
        e2, s2 = self.lookup_data_spec(rhs)
        if e2 is not None:
            element_types |= {e2}
        if len(element_types) > 1:
            raise Exception('Invalid constraint: %s' % (constraints))
        if len(element_types) == 1:
            if isinstance(lhs, VarRef):
                if str(lhs) in self.cost_specs:
                    raise Exception('COST constraint is not supported: %s' % (constraints))
            if isinstance(rhs, VarRef):
                if str(rhs) in self.cost_specs:
                    raise Exception('COST constraint is not supported: %s' % (constraints))
        return element_types

    def recursive_classify_constraints(self, constraints):
        if constraints is None:
            return {}, None, None
        lhs, op, rhs = constraints.lhs, constraints.op, constraints.rhs
        if isinstance(constraints, BasicConstraint):
            waypoints = self.get_waypoints(constraints)
            if len(waypoints) == 1:
                waypoint = list(waypoints)[0]
                if isinstance(lhs, VarRef):
                    lhs = VarRef(None, lhs.path)
                if isinstance(rhs, VarRef):
                    rhs = VarRef(None, rhs.path)
                constraints = BasicConstraint(lhs, op, rhs)
                return {waypoint: constraints}, None, None
            else:
                element_types = self.get_element_types(constraints)
                element_type = list(element_types)[0]
                if element_type == 'NODE':
                    return {}, constraints, None
                else:
                    return {}, None, constraints
        elif constraints.op == 'AND':
            wpc1, nc1, ec1 = self.recursive_classify_constraints(lhs)
            wpc2, nc2, ec2 = self.recursive_classify_constraints(rhs)
            wpc = {}
            for wp in wpc1.keys() | wpc2.keys():
                wpc[wp] = self.merge_constraints(wpc1.get(wp, None), op, wpc2.get(wp, None))
            nc = self.merge_constraints(nc1, op, nc2)
            ec = self.merge_constraints(ec1, op, ec2)
            return wpc, nc, ec
        elif constraints.op == 'OR':
            wpc1, nc1, ec1 = self.recursive_classify_constraints(lhs)
            wpc2, nc2, ec2 = self.recursive_classify_constraints(rhs)
            wpc = {}
            wpc_keys = wpc1.keys() | wpc2.keys()
            if len(wpc_keys) > 1:
                raise Exception("Invalid constraint: %s" % (constraints))
            types = 0
            if len(wpc_keys) > 0:
                types += 1
            if nc1 is not None or nc2 is not None:
                types += 1
            if ec1 is not None or ec2 is not None:
                types += 1
            if types != 1:
                raise Exception('Invalid constraint: %s' % (constraints))
            for wp in wpc_keys:
                wpc[wp] = self.merge_constraints(wpc1.get(wp, None), op, wpc2.get(wp, None))
            nc = self.merge_constraints(nc1, op, nc2)
            ec = self.merge_constraints(ec1, op, ec2)
            return wpc, nc, ec
        elif constraints.op == 'NOT':
            wpc1, nc1, ec1 = self.recursive_classify_constraints(lhs)
            wpc = {}
            for wp in wpc1:
                wpc[wp] = self.merge_constraints(wpc1[wp], op, None)
            nc = self.merge_constraints(nc1, op, None)
            ec = self.merge_constraints(ec1, op, None)
            return wpc, nc, ec

    def __str__(self):
        nps = self.node_prop_specs
        eps = self.edge_prop_specs
        nodes = self.nodes
        edges = self.edges

        s = ''
        for n in nodes:
            node = nodes[n]
            props = ', '.join(['%s=%s' % (s, node.get(s, '')) for s in nps])
            s += '%s: %s\n' % (n, props)
        for e in edges:
            edge = edges[e]
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
            yield (cmd, self.dispatch(cmd))

    def dispatch(self, cmd):
        if isinstance(cmd, LoadCommand):
            return self.load(cmd)
        elif isinstance(cmd, DropCommand):
            return self.drop(cmd)
        elif isinstance(cmd, DefineCommand):
            return self.define(cmd)
        elif isinstance(cmd, SetCommand):
            return self.set_value(cmd)
        elif isinstance(cmd, SelectCommand):
            return self.select(cmd)
        elif isinstance(cmd, ShowCommand):
            return self.show(cmd)

    def load(self, cmd):
        toponame = cmd.toponame
        varname = cmd.varname

        filename = '%s/%s.graphml' % (self.topo_dir, toponame)
        g = nx.read_graphml(filename).to_undirected()

        gdb = GraphDB(g)

        self.variables[varname] = gdb
        return 'Success'

    def drop(self, cmd):
        var_ref = str(cmd.var_ref)

        if var_ref in self.variables:
            var = self.variables[var_ref]
            if isinstance(var, DataSpec):
                pass # TODO
            del self.variables[var_ref]
        return 'Success'

    def define(self, cmd):
        var_ref = str(cmd.selection.toponame)

        if var_ref in self.variables:
            var = self.variables[var_ref]
            cmd.data_spec.varname = str(cmd.data_spec.varname)
            var.define_annotation(cmd.data_type, cmd.data_spec, cmd.selection)
        return 'Success'

    def set_value(self, cmd):
        var_ref = str(cmd.selection.toponame)
        if var_ref in self.variables:
            var = self.variables[var_ref]
            varname = str(cmd.varname)
            var.set_annotation(cmd.data_type, varname, cmd.value, cmd.selection)
        return 'Success'

    def select(self, cmd):
        topo_ref = str(cmd.toponame)
        if topo_ref in self.variables:
            topo = self.variables[topo_ref]

            if not isinstance(topo, GraphDB):
                raise Exception('%s is not a valid topology' % (var_ref))
            path = topo.select_path(cmd.ra_expr, cmd.constraints, cmd.opt_obj)

            if cmd.varname is not None:
                varname = str(cmd.varname)
                self.variables[varname] = path
                return varname
            else:
                return path
        raise Exception('%s does not exist' % (topo_ref))

    def show(self, cmd):
        var_ref = str(cmd.var_ref)
        if var_ref in self.variables:
            var = self.variables[var_ref]
            print('var[%s]: ' % var_ref, var)
            return var
        raise Exception('%s does not exist' % (var_ref))

if __name__ == '__main__':
    import sys
    from trident.rql.compiler import RqlCompiler

    larkfile, topo_dir, progfile = sys.argv[1:]

    compiler = RqlCompiler(larkfile)
    session = RqlSession(topo_dir)

    with open(progfile) as f:
        cmds = compiler.compile(f.read())

    session.execute(cmds)
