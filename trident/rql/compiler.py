from lark import Lark, Visitor, Tree
from trident.rql.common import *

class RqlCompiler(Visitor):
    def __init__(self, larkfile):
        with open(larkfile) as f:
            self.parser = Lark(f.read(), propagate_positions=True)
        self.commands = []

    def start(self, ast):
        commands = []
        commands = list(filter(lambda c: isinstance(c, Tree), ast.children))
        self.commands = list(map(lambda c: c.cmd, commands))

    def statement(self, ast):
        ast.cmd = ast.children[0].cmd

    def load_statement(self, ast):
        _, toponame, _, varname = ast.children
        ast.cmd = LoadCommand(toponame, varname.value)

    def define_statement(self, ast):
        _, data_type, data_spec, selection = ast.children
        data_spec = data_spec.spec
        if data_type != data_spec.data_type:
            raise Exception('Definition type mismatch at Line %s: %s, %s'
                            % (ast.meta.line, data_type, data_spec))
        selection = selection.selection
        if selection.constraints is not None:
            raise Exception('DEFINE statement MUST NOT have constraints at Line %s'
                            % (ast.meta.line))
        ast.cmd = DefineCommand(data_type, data_spec, selection)

    def property_spec(self, ast):
        varname, vartype, value = ast.children
        varname = varname.value
        vartype = vartype.value
        value = value.value
        ast.spec = DataSpec(varname, vartype, value)

    def cost_spec(self, ast):
        varname, vartype, value, accum_func = ast.children
        varname = varname.value
        vartype = vartype.value
        value = value.value
        accum_func = accum_func.value
        ast.spec = DataSpec(varname, vartype, value, accum_func)

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
        ast.cmd = SetCommand(data_type, varname.value, value.value, selection)

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

    def var_ref(self, ast):
        children = ast.children
        if children[0].type == 'WAYPOINT':
            waypoint = ast.children[0].value
            children = children[1:]
        else:
            waypoint = None
        path = list(map(lambda c: c.value, children))
        ast.value = VarRef(waypoint, path)

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

    def drop_statement(self, ast):
        ast.cmd = DropCommand(ast.children[1].value)

    def show_statement(self, ast):
        if len(ast.children) == 2:
            selection = None
        else:
            selection = ast.children[2].selection
        var_ref = ast.children[1].value
        ast.cmd = ShowCommand(var_ref, selection)

    def default(self, ast):
        ast.value = ast.children[0].value

    def value(self, ast):
        print(ast)

    def number(self, ast):
        value = ast.children[0].value
        if '.' in value:
            ast.value = float(value)
        else:
            ast.value = int(value)
        print(ast.value)

    def string(self, ast):
        value = ast.children[0].value
        ast.value = value.strip('\"')

    def compile(self, program, show_ast=False):
        self.commands = []
        ast = self.parser.parse(program)
        if show_ast:
            print(ast.pretty())
        self.visit(ast)
        return self.commands

if __name__ == '__main__':
    import sys

    larkfile = sys.argv[1]
    progfile = sys.argv[2]

    compiler = RqlCompiler(larkfile)
    with open(progfile) as f:
        commands = compiler.compile(f.read(), True)

    for c in commands:
        print(c)
