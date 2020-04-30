import itertools
from lark import Lark, Visitor, Tree

class RqlSession(object):

    def __init__(self, session):
        self.variables = {}
        self.costs = {}
        self.node_properties = {}
        self.link_properties = {}
        self.port_properties = {}
        self.views = {}

    def load(self, path, var):
        # self.variables[var] = load_graphml(path)
        pass

    def define(self, definition):
        pass

    def set_value(self, key_val, selection):
        pass

    def select(self, expr, topo, watch=False, constraints=[], opt=None):
        pass

class LoadCommand():
    def __init__(self, toponame, varname):
        self.toponame = toponame
        self.varname = varname

    def __str__(self):
        return 'LOAD %s AS %s' % (self.toponame, self.varname)

class DefineCommand():
    def __init__(self, data_type, data_spec, selection):
        self.data_type = data_type
        self.data_spec = data_spec
        self.selection = selection

    def __str__(self):
        return 'DEF %s %s %s' % (self.data_type, self.data_spec, self.selection)

class SetCommand():
    def __init__(self, data_type, varname, value, selection):
        self.data_type = data_type
        self.varname = varname
        self.value = value
        self.selection = selection

    def __str__(self):
        return 'SET %s %s = %s %s' % (self.data_type, self.varname,
                                          self.value, self.selection)

class DataSpec():
    def __init__(self, varname, vartype, default_value):
        self.varname = varname
        self.vartype = vartype
        self.default_value = default_value

    def __str__(self):
        return '(%s : %s = %s)' % (self.varname, self.vartype, self.default_value)

class ElementSelection():
    def __init__(self, toponame, element_type, constraints):
        self.toponame = toponame
        self.element_type = element_type
        self.constraints = constraints

    def __str__(self):
        s = 'FOR EACH %s IN %s' % (self.element_type, self.toponame)
        if self.constraints is not None:
            s += ' THAT %s' % (self.constraints)
        return s

class PropertyRef():
    def __init__(self, waypoint, path):
        self.waypoint = waypoint
        self.path = path

    def __str__(self):
        s = ''
        if self.waypoint is not None:
            s += '%s::' % (self.waypoint)
        return '%s%s' % (s, '.'.join(self.path))

class BasicConstraint():
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    def __str__(self):
        return '(%s %s %s)' % (self.lhs, self.op, self.rhs)

class CompoundConstraint():
    def __init__(self, lhs, op, rhs = None):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    def __str__(self):
        if self.rhs is None:
            return '(%s %s)' % (self.op, self.lhs)
        else:
            return '(%s %s %s)' % (self.lhs, self.op, self.rhs)

class RouteAlgebraExpr():
    def __init__(self, waypoints, patterns):
        self.waypoints = waypoints
        self.patterns = patterns

    def __str__(self):
        res = list(itertools.chain(*zip(self.waypoints, self.patterns)))
        return ' '.join(res)

class SelectCommand():
    def __init__(self, ra_expr, toponame, varname, reactive, constraints, opt_obj):
        self.ra_expr = ra_expr
        self.toponame = toponame
        self.varname = varname
        self.reactive = reactive
        self.constraints = constraints
        self.opt_obj = opt_obj

    def __str__(self):
        s = ""
        if self.opt_obj is not None:
            s += "OPT %s WHEN " % (self.opt_obj)
        if self.reactive:
            s += "WATCH"
        else:
            s += "SELECT"
        s += " %s IN %s" % (self.ra_expr, self.toponame)
        if self.constraints is not None:
            s += " WHERE %s" % self.constraints
        if self.varname is not None:
            s += " AS %s" % self.varname
        return s

class RqlInterpreter(Visitor):
    def __init__(self):
        self.commands = []

    def start(self, ast):
        commands = []
        commands = list(filter(lambda c: isinstance(c, Tree), ast.children))
        self.commands = list(map(lambda c: c.cmd, commands))

    def statement(self, ast):
        ast.cmd = ast.children[0].cmd

    def load_statement(self, ast):
        _, toponame, _, varname = ast.children
        ast.cmd = LoadCommand(toponame, varname)

    def define_statement(self, ast):
        _, data_type, data_spec, selection = ast.children
        data_spec = data_spec.spec # TODO
        selection = selection.selection # TODO
        ast.cmd = DefineCommand(data_type, data_spec, selection)

    def property_spec(self, ast):
        varname, vartype, value = ast.children
        varname = varname.value
        vartype = vartype.value
        value = value.value
        ast.spec = DataSpec(varname, vartype, value)

    def element_selection(self, ast):
        for_each = ast.children[0]
        element_type = for_each.element_type
        toponame = for_each.toponame
        if len(ast.children) > 1:
            that = ast.children[1]
            constraints = that.constraints
            # TODO: assert data_type == constraints.data_type
        else:
            constraints = None
        ast.selection = ElementSelection(toponame, element_type, constraints)

    def for_each_clause(self, ast):
        _, _, element_type, _, toponame = ast.children
        ast.element_type = element_type.value
        ast.toponame = toponame.value

    def that_clause(self, ast):
        _, constraints = ast.children
        ast.constraints = constraints.constraints

    def set_statement(self, ast):
        if len(ast.children) == 4:
            _, data_type, varname, selection = ast.children
            value = None
        else:
            _, data_type, varname, value, selection = ast.children
        selection = selection.selection
        ast.cmd = SetCommand(data_type, varname.value, value, selection)

    def prop_constraint(self, ast):
        if len(ast.children) == 1:
            ast.constraints = ast.children[0].constraints
        else:
            c1, op, c2 = ast.children
            ast.constraints = CompoundConstraint(c1.constraints, op, c2.constraints)

    def and_prop_constraint(self, ast):
        if len(ast.children) == 1:
            ast.constraints = ast.children[0].constraints
        else:
            c1, c2 = ast.children
            ast.constraints = CompoundConstraint(c1.constraints, 'AND', c2.constraints)

    def encap_prop_constraint(self, ast):
        ast.constraints = ast.children[0].constraints

    def not_prop_constraint(self, ast):
        op, c = ast.children
        ast.constraints = CompoundConstraint(c.constraints, op)

    def basic_prop_constraint(self, ast):
        lhs, op, rhs = ast.children
        ast.constraints = BasicConstraint(lhs.value, op.value, rhs.value)

    def operand(self, ast):
        ast.value = ast.children[0].value

    def prop_ref(self, ast):
        children = ast.children
        if children[0].type == 'WAYPOINT':
            waypoint = ast.children[0].value
            children = children[1:]
        else:
            waypoint = None
        path = list(map(lambda c: c.value, children))
        ast.value = PropertyRef(waypoint, path)

    def select_statement(self, ast):
        children = ast.children.copy()
        if children[0].data == 'opt_clause':
            opt_obj = children[0].opt_obj
            children = children[1:]
        else:
            opt_obj = None

        reactive = children[0].reactive
        ra_expr = children[0].ra_expr
        toponame = children[0].toponame
        children = children[1:]

        if len(children) > 0 and children[0].data == 'where_clause':
            constraints = children[0].constraints
            children = children[1:]
        else:
            constraints = None

        if len(children) > 0 and children[0].data == 'as_clause':
            varname = children[0].varname
            children = children[1:]
        else:
            varname = None
        ast.cmd = SelectCommand(ra_expr, toponame, varname,
                                 reactive, constraints, opt_obj)

    def opt_clause(self, ast):
        _, opt_obj, _ = ast.children
        ast.opt_obj = opt_obj

    def select_clause(self, ast):
        mode, ra_expr, _, toponame = ast.children
        ast.reactive = mode == 'WATCH'
        ast.ra_expr = ra_expr.expr
        ast.toponame = toponame

    def ra_expr(self, ast):
        children = list(map(lambda c: c.value, ast.children))
        waypoints = children[::2]
        patterns = children[1::2]
        ast.expr = RouteAlgebraExpr(waypoints, patterns)

    def where_clause(self, ast):
        _, constraints = ast.children
        ast.constraints = constraints.constraints

    def as_clause(self, ast):
        ast.varname = ast.children[1]

if __name__ == '__main__':
    import sys

    larkfile = sys.argv[1]
    progfile = sys.argv[2]

    with open(larkfile) as f:
        parser = Lark(f.read())
    with open(progfile) as f:
        ast = parser.parse(f.read())
    print(ast.pretty())

    interpreter = RqlInterpreter()
    interpreter.visit(ast)
    print(interpreter.commands)
    for c in interpreter.commands:
        print(c)
