#!/usr/bin/env python3

from flask import Flask, send_file, request
import networkx as nx
import json

from trident.demo import TridentDemo

app = Flask(__name__)
app.trident = TridentDemo()

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
    file_list = glob.glob('dataset/sources/*.graphml')
    topo_list = sorted(map(lambda f: f.split('/')[-1].split('.')[0], file_list))
    return json.dumps(list(topo_list))

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

@app.route('/topology/<name>.json')
def load_topology(name):
    filename = 'dataset/sources/%s.graphml' % (name)
    g = nx.read_graphml(filename).to_undirected()

    pos = nx.nx_pydot.graphviz_layout(g)
    radius = {n: g.degree(n) for n in g.nodes}

    nodes = []
    nindex = {}
    for n in g.nodes():
        nindex[n] = len(nodes)
        node = {}
        node['id'] = n
        node['r'] = radius[n]
        node['x'] = pos[n][0]
        node['y'] = pos[n][1]
        node['label'] = g.nodes[n].get('label', '')
        node['proplist'], node['properties'] = cleanup(g.nodes[n], n)
        nodes += [node]

    g.nindex = nindex

    app.trident.set_topology(g)

    links = []
    for u, v, e in g.edges(data=True):
        e['proplist'], e['properties'] = cleanup(e, len(links))
        e['id'] = len(links)
        e['source'] = nindex[u]
        e['target'] = nindex[v]
        links += [e]

    data = {'nodes': nodes, 'links': links}
    return json.dumps(data)

@app.route('/query', methods=['POST'])
def query():
    expr = str(request.data)
    path = app.trident.query(expr)
    return json.dumps(path)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print(load_topology(sys.argv[2]))
    else:
        app.run(host='0.0.0.0', debug=True)
