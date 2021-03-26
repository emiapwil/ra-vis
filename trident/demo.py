
import networkx as nx
import re

from trident.rql.common import SelectCommand, ShowCommand
from trident.rql.session import RqlSession
from trident.rql.compiler import RqlCompiler

class TridentDemo(object):
    def __init__(self, topo_dir, larkfile):
        self.session = RqlSession(topo_dir)
        self.compiler = RqlCompiler(larkfile)

    def query(self, query):
        try:
            print(query)
            commands = self.compiler.compile(query)
        except Exception as e:
            print(e)
            return [{'type': 'error', 'message': 'Error parsing %s' % (query)}]

        retval = []
        try:
            for cmd, result in self.session.execute(commands):
                print('cmd = ', cmd)
                print('result = ', result)
                if isinstance(cmd, SelectCommand):
                    if isinstance(result, list):
                        retval += [{
                            'type': 'path',
                            'expr': str(cmd),
                            'path': list(zip(result[:-1], result[1:]))
                        }]
                elif isinstance(cmd, ShowCommand):
                    if isinstance(result, list):
                        retval += [{
                            'type': 'path',
                            'expr': str(cmd),
                            'path': list(zip(result[:-1], result[1:]))
                        }]
                    else:
                        retval += [{
                            'type': 'topology',
                            'expr': str(cmd),
                            'topology': result.data()
                        }]
        except Exception as e:
            retval += [{'type': 'error', 'expr': str(cmd), 'message': e.message}]
        return retval
