
var tridentFrontend = function () {
  const topoListUrl = '/topologylist.json';
  const setTopologyUrl = '/topology/{0}.json';
  const queryUrl = '/query';

  var config = {
    margin: 15,
    width: 640,
    height: 640,
    radiusRange: [5, 15],
    transitionDelay: 250
  }

  function prepareTopologyList() {
    fetch(topoListUrl).then(r => r.json())
      .then(topoList => {
        topoList.forEach(topo => d3.select('select')
                         .append('option')
                         .attr('value', topo)
                         .text(topo));
      });
  }

  function transform(v, rangeV, rangeE) {
    const minV = rangeV[0], maxV = rangeV[1];
    const minE = rangeE[0], maxE = rangeE[1];
    return (v - minV) / (maxV - minV) * (maxE - minE) + minE;
  }

  function format(pattern) {
    if (arguments.length == 0) {
      return pattern;
    }
    var args = Array.prototype.slice.call(arguments, 1);
    return pattern.replace(/\{(\d+)\}/g, function(m, i){
      return args[i];
    });
  }

  function fit(data, accessor, updater, rangeE) {
    const minValue = d3.min(data, accessor);
    const maxValue = d3.max(data, accessor);
    const rangeV = [minValue, maxValue];

    data.forEach(d => {
      updater(d, transform(accessor(d), rangeV, rangeE));
    });
  }

  function scaleTopologyLayout(nodes, links) {
    const widthRange = [config.margin, config.width - config.margin];
    const heightRange = [config.margin, config.height - config.margin];
    const radiusRange = config.radiusRange;

    fit(nodes, d => d.x, function (d, x) { d.x = x; }, widthRange);
    fit(nodes, d => d.y, function (d, y) { d.y = y; }, heightRange);
    fit(nodes, d => d.r, function (d, r) { d.r = r; }, radiusRange);
  }

  var nodes = [], links = [];

  function toggleTooltips(selected, show) {
    if (show == true) {
      d3.select('#tooltip').remove();
      var direction = 'left';
      var x = selected.x + selected.r;
      if (x > config.width / 2) {
        direction = 'right';
        x = config.width - x;
      }
      var y = selected.y + selected.r - config.height;
      if (y > -config.height / 2) {
        y = y - config.height / 3;
      }

      var info = d3.select('#canvas')
          .append('div')
          .attr('id', 'tooltip')
          .style('float', direction)
          .style('position', 'relative')
          .style('width', 'auto')
          .style(direction, format('{0}px', x))
          .style('top', format('{0}px', y));

      var table = info.append('table')
          .attr('class', 'table table-striped table-dark table-sm')
          .style('text-align', 'left');

      var thead = table.append('thead').append('tr').style('font-weight', 'bold');

      thead.append('td').text('#');
      thead.append('td').text('Property');
      thead.append('td').text('Value');

      var tbody = table.append('tbody');

      var tr = tbody.append('tr');

      selected.proplist.forEach(function(prop, index) {
        var tr = tbody.append('tr');
        tr.append('td')
          .text(index + 1);
        tr.append('td')
          .attr('class', 'key')
          .text(prop);
        tr.append('td')
          .attr('class', 'value')
          .text(selected.properties[prop]);
      });
      table.append('caption').attr('class', 'bg-dark').text(selected.label);
    } else {
      d3.select('#tooltip').remove();
    }
  }

  function initializeGraph(data) {
    nodes = data.nodes;
    links = data.links;

    scaleTopologyLayout(nodes, links);

    nodes.forEach(function (node, index) {
      node.index = index;
    });
    links.forEach(function (link, index) {
      link.source = nodes[link.source];
      link.target = nodes[link.target];
      link.index = index;
      link.x = (link.source.x + link.target.x) / 2;
      link.y = (link.source.y + link.target.y) / 2;
      link.r = 0;
    });

    var svg = d3.select('svg')
        .attr('width', config.width)
        .attr('height', config.height);

    svg.selectAll('.link')
      .data([])
      .exit()
      .remove();
    svg.selectAll('.node')
      .data([])
      .exit()
      .remove();
    var link = svg.selectAll('.link')
        .data(links)
        .enter().append('line')
        .attr('class', 'link')
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)
        .attr('index', d => d.index);

    var node = svg.selectAll('.node')
        .data(nodes)
        .enter().append('circle')
        .attr('class', 'node')
        .attr('r', d => d.r)
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('index', d => d.index)
        .attr('label', d => d.label);

    d3.selectAll('.node')
      .on('mouseover', d => {
        const selector = format(indexSelector, 'node', d.index);
        toggleTooltips(d, true);
        d3.select(selector).attr('view', true);
      })
      .on('mouseout', d => {
        const selector = format(indexSelector, 'node', d.index);
        toggleTooltips(d, false);
        d3.select(selector).attr('view', false);
      });

    d3.selectAll('.link')
      .on('mouseover', d => {
        console.log(d);
        const selector = format(indexSelector, 'link', d.index);
        const src = format(indexSelector, 'node', d.source.index);
        const dst = format(indexSelector, 'node', d.target.index);

        d3.select(selector).attr('view', true);
        d3.select(src).attr('view', true);
        d3.select(dst).attr('view', true);

        toggleTooltips(d, true);
      })
      .on('mouseout', d => {
        const selector = format(indexSelector, 'link', d.index);
        const src = format(indexSelector, 'node', d.source.index);
        const dst = format(indexSelector, 'node', d.target.index);

        d3.select(selector).attr('view', false);
        d3.select(src).attr('view', false);
        d3.select(dst).attr('view', false);

        toggleTooltips(d, false);
      });
  }

  function setTopology(topo) {
    const url = format(setTopologyUrl, topo);
    console.log(url);
    fetch(url).then(r => r.json())
      .then(data => initializeGraph(data[0]));
  }

  const indexSelector = '.{0}[index="{1}"]'

  function select(selectedLinks, status, transition) {
    const svg = d3.select('svg');
    selectedLinks.forEach(function (link, index) {
      const srcIndex = format(indexSelector, 'node', link.source.index);
      const dstIndex = format(indexSelector, 'node', link.target.index);
      const linkIndex = format(indexSelector, 'link', link.index);

      transition(svg.select(srcIndex), index).attr('selected', status);
      transition(svg.select(dstIndex), index).attr('selected', status);
      transition(svg.select(linkIndex), index).attr('selected', status);
    });
  }

  function matchLink(l, src, dst) {
    return (l.source.id == src) && (l.target.id == dst);
  }

  function updatePath(expr, selected) {
    console.log(selected);
    const selectedLinks = selected.map(
      d => links.filter(l => matchLink(l, d[0], d[1]) || matchLink(l, d[1], d[0]))[0]
    )

    console.log(selectedLinks);

    select(currentQuery.selected, false, function (s, index) {
      return s.transition().delay((index + 1) * config.transitionDelay);
    });
    select(selectedLinks, true, function (s, index) {
      return s.transition().delay((index + 1) * config.transitionDelay);
    });

    currentQuery.expr = expr;
    currentQuery.selected = selectedLinks;
  }

  var currentQuery = {
    expr: '',
    selected: []
  };

  function dispatch(results) {
    results.forEach(function (result, index){
      if (result.type == 'path') {
        updatePath(result.expr, result.path);
      } else if (result.type == 'topology') {
        initializeGraph(result.topology);
      }
    });
  }

  function query(expr) {
    fetch(queryUrl, {
      body: expr,
      method: 'POST'
    }).then(r => r.json())
      .then(results => dispatch(results));
  }

  return {
    config: config,
    prepareTopologyList: prepareTopologyList,
    initializeGraph: initializeGraph,
    setTopology: setTopology,
    query: query
  };

}();

tridentFrontend.config.width = $('svg').width();
tridentFrontend.config.height = $('svg').height();
tridentFrontend.prepareTopologyList();

function submitQuery() {
  const expr = $('textarea')[0].value;
  console.log(expr);
  tridentFrontend.query(expr);
};

function selectTopology(topo) {
  tridentFrontend.query('LOAD ' + topo + ' AS ' + topo + '; SHOW ' + topo);
}
