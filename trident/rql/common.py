from itertools import chain

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

class VarRef():
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
        res = list(chain(*zip(self.waypoints, self.patterns)))
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

class DropCommand():
    def __init__(self, var_ref):
        self.var_ref = var_ref
