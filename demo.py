#!/usr/bin/env python3

from flask import Flask, send_file, request
import networkx as nx
import json

from trident.demo import TridentDemo

app = Flask(__name__)

@app.route('/demo.html')
def demo():
    filename = 'demo.html'
    return send_file(filename)

@app.route('/assets/<dir_name>/<name>')
def assets(dir_name, name):
    filename = 'assets/%s/%s' % (dir_name, name)
    print(filename)
    return send_file(filename)

@app.route('/topologylist.json')
def get_topology_list():
    import glob
    file_list = glob.glob('%s/*.graphml' % topo_dir)
    topo_list = sorted(map(lambda f: f.split('/')[-1].split('.')[0], file_list))
    return json.dumps(list(topo_list))

@app.route('/topology/<name>.json')
def load_topology(name):
    app.trident.query('LOAD %s AS %s' % (name, name))
    retval = app.trident.query('SHOW %s' % (name))
    print(retval)
    return json.dumps(retval)

@app.route('/query', methods=['POST'])
def query():
    data = request.data
    expr = str(data, 'UTF-8')
    retval = app.trident.query(expr)
    return json.dumps(retval)


if __name__ == '__main__':
    import sys
    topo_dir, larkfile = sys.argv[1:]
    app.trident = TridentDemo(topo_dir, larkfile)
    app.run(host='0.0.0.0', debug=True)
