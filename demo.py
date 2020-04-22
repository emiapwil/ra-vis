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
    topo_list = map(lambda f: f.split('/')[-1].split('.')[0], file_list)
    return json.dumps(list(topo_list))

@app.route('/topology/<name>.json')
def load_topology(name):
    filename = 'dataset/sources/%s.graphml' % (name)
    g = nx.read_graphml(filename)
    pos = nx.nx_pydot.graphviz_layout(g)

    margin = 10
    width = 640
    height = 480

    minx = min(map(lambda n: pos[n][0], pos))
    maxx = max(map(lambda n: pos[n][0], pos))
    miny = min(map(lambda n: pos[n][1], pos))
    maxy = max(map(lambda n: pos[n][1], pos))

    pos2 = pos.copy()
    for n in pos2:
        ox, oy = pos2[n]
        x = (ox - minx) * (width - 2 * margin) / (maxx - minx) + margin
        y = (oy - miny) * (height - 2 * margin) / (maxy - miny) + margin
        pos[n] = [x, y]

    radius = {n: g.degree(n) for n in g.nodes}
    minor = min([radius[n] for n in radius])
    maxor = max([radius[n] for n in radius])

    minr, maxr = 5, 15

    for n in radius:
        radius[n] = (radius[n] - minor) * (maxr - minr)/ (maxor - minor) + minr

    nodes = []
    nindex = {}
    for n in g.nodes():
        nindex[n] = len(nodes)
        g.nodes[n]['id'] = n
        g.nodes[n]['r'] = radius[n]
        g.nodes[n]['x'] = pos[n][0]
        g.nodes[n]['y'] = pos[n][1]
        nodes += [g.nodes[n]]

    g.nindex = nindex

    app.trident.set_topology(g)

    links = []
    for u, v, e in g.edges(data=True):
        link = e.copy()
        e['source'] = nindex[u]
        e['target'] = nindex[v]
        links += [e]

    data = {'nodes': nodes, 'links': links}
    return json.dumps(data)

@app.route('/query', methods=['POST'])
def query():
    expr = request.data
    print(expr)
    app.trident.query(expr)
    g = app.trident.get_topology()
    nodes = [g.nindex[n] for n in g.nodes()][len(expr):len(expr)*2]
    return json.dumps(nodes)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print(load_topology(sys.argv[2]))
    else:
        app.run(debug=True)