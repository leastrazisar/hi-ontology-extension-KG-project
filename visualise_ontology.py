import graphviz
import subprocess
import os
from rdflib import Graph, RDF, RDFS, OWL, BNode
from rdflib.collection import Collection

# load all files 
TTL_MAIN = os.path.expanduser('~/Downloads/Modolled_Individuals_Assigment.ttl')
TTL_BASE = os.path.expanduser('~/Downloads/hi-ontology.ttl')
OUTPUT   = os.path.expanduser('~/Downloads/HI_ontology_schema')
HI_NS    = 'https://w3id.org/hi-ontology#'

#skip concept to enable easier visualization as it is connected with everything
SKIP     = {'Concept'}

# spicify the colors
GREEN      = '#97C459'
GREEN_TEXT = '#27500A'
DBLUE      = '#378ADD'
DBLUE_TEXT = '#042C53'
LBLUE      = '#B5D4F4'
LBLUE_TEXT = '#0C447C'
EDGE_SUB   = '#5F5E5A'
EDGE_PROP  = '#BA7517'

# utility functions 

#get name from the uri for display label
def local(uri):
    s = str(uri)
    if '#' in s: return s.split('#')[1]
    return s.split('/')[-1]

#make safe names fro graphviz (no special characters, etc.)
def safe_id(name):
    return name.replace(':', '_').replace('-', '_').replace('.', '_').replace(' ', '_')

#make sure it is HI namespace
def is_hi(uri):
    return str(uri).startswith(HI_NS)

#external ontolgoies - for colourcoding
def is_external(uri):
    return any(ns in str(uri) for ns in [
        'w3.org/ns/prov', 'dev.nemo.inf.ufes.br',
        'caressesrobot.org', 'purl.oclc.org/NET/ssnx',
        'xmlns.com/foaf',
    ])

#need to extarct the prefix so can display it
def ext_prefix(uri):
    uri = str(uri)
    if 'prov' in uri:     return 'prov'
    if 'hcion' in uri:    return 'hcio'
    if 'caresses' in uri: return 'caresses'
    if 'ssnx' in uri:     return 'ssn'
    if 'foaf' in uri:     return 'foaf'
    return ''

#need this wwhen domains and range of property are unions o we wont be drawing a blank noce
def resolve_class(nodes, g):
    result = []
    for n in nodes:
        if isinstance(n, BNode):
            union = list(g.objects(n, OWL.unionOf))
            if union:
                try:
                    members = list(Collection(g, union[0]))
                    result.extend([local(m) for m in members
                                   if is_hi(m) and local(m) not in SKIP])
                except: pass
        elif is_hi(n):
            name = local(n)
            if name not in SKIP:
                result.append(name)
    return result

# base onotology to get origninal classes
print(f'Loading base ontology: {TTL_BASE}')
g_base = Graph()
g_base.parse(TTL_BASE, format='turtle')

ORIGINAL_HI = set()
for s in g_base.subjects(RDF.type, OWL.Class):
    if is_hi(s):
        ORIGINAL_HI.add(local(s))
print(f'Original HI classes: {sorted(ORIGINAL_HI)}')

# expanded ontology
print(f'\nLoading assignment ontology: {TTL_MAIN}')
g = Graph()
g.parse(TTL_MAIN, format='turtle')
print(f'Loaded {len(g)} triples')

# get all new hi classes
hi_classes = set()
for s in g.subjects(RDF.type, OWL.Class):
    if is_hi(s):
        name = local(s)
        if name not in SKIP:
            hi_classes.add(name)
print(f'Total classes: {len(hi_classes)}')

# to dinsinguisng between subclasses and properties connectins
subclass_hi  = []
subclass_ext = []
for s, o in g.subject_objects(RDFS.subClassOf):
    if not is_hi(s): continue
    child = local(s)
    if child in SKIP: continue
    if isinstance(o, BNode): continue
    parent_local = local(o)
    if parent_local in SKIP or parent_local == child: continue
    if is_hi(o):
        subclass_hi.append((child, parent_local))
    elif is_external(o):
        subclass_ext.append((child, str(o)))
print(f'hi: subclass relations: {len(subclass_hi)}')
print(f'External alignments: {len(subclass_ext)}')

# get object properties - dont need to disply others
obj_props = []
for prop in g.subjects(RDF.type, OWL.ObjectProperty):
    if not is_hi(prop): continue
    prop_name = local(prop)
    domains = resolve_class(list(g.objects(prop, RDFS.domain)), g)
    ranges  = resolve_class(list(g.objects(prop, RDFS.range)), g)
    for d in domains:
        for r in ranges:
            if d not in SKIP and r not in SKIP:
                obj_props.append((prop_name, d, r))
print(f'Object property relations: {len(obj_props)}')

# node style
def node_attrs(name):
    if name in ORIGINAL_HI:
        fill, text = GREEN, GREEN_TEXT
    else:
        fill, text = LBLUE, LBLUE_TEXT
    return dict(style='filled,rounded', fillcolor=fill,
                fontcolor=text, color=text, fontsize='10',
                shape='box', margin='0.1,0.05', penwidth='0.5')

def ext_node_attrs():
    return dict(style='filled,rounded', fillcolor=DBLUE,
                fontcolor=DBLUE_TEXT, color=DBLUE_TEXT,
                fontsize='10', shape='box',
                margin='0.1,0.05', penwidth='0.5')

# build graph, use neato for better circular layout
dot = graphviz.Digraph('HI_Ontology', engine='neato')
dot.attr(
    overlap='false',
    sep='+8',
    splines='true',
    fontsize='10',
    bgcolor='white',
    outputorder='edgesfirst',
    label='The Hybrid Intelligence (HI) Ontology — class schema\n'
          '(green = original HI | dark blue = external ontologies | light blue = new classes)',
    labelloc='t',
    fontcolor='#2C2C2A',
    size='20,20',
)

added = set()

def add_hi(name):
    sid = safe_id(name)
    if sid not in added:
        added.add(sid)
        dot.node(sid, label=name, **node_attrs(name))
    return sid

def add_ext(uri_str):
    name = local(uri_str)
    prefix = ext_prefix(uri_str)
    label = f'{prefix}:{name}' if prefix else name
    sid = safe_id(label)
    if sid not in added:
        added.add(sid)
        dot.node(sid, label=label, **ext_node_attrs())
    return sid

# all HI classes
for name in hi_classes:
    add_hi(name)

# all sublcass conections
for child, parent in subclass_hi:
    c_id = add_hi(child)
    p_id = add_hi(parent)
    dot.edge(p_id, c_id,
             arrowhead='empty', arrowsize='0.7',
             color=EDGE_SUB, penwidth='0.6')

# all external connections
for child, parent_uri in subclass_ext:
    c_id = add_hi(child)
    p_id = add_ext(parent_uri)
    dot.edge(c_id, p_id,
             arrowhead='empty', arrowsize='0.7',
             color=DBLUE, penwidth='0.5', style='dashed')

# propertie relationships
for prop_name, d_name, r_name in obj_props:
    d_id = add_hi(d_name)
    r_id = add_hi(r_name)
    dot.edge(d_id, r_id,
             label=prop_name,
             arrowhead='vee', arrowsize='0.6',
             color=EDGE_PROP, fontcolor=EDGE_PROP,
             fontsize='7', penwidth='0.5')

# legend
with dot.subgraph(name='cluster_legend') as leg:
    leg.attr(label='Legend', fontsize='9',
             style='rounded', color='#D3D1C7', margin='8')
    leg.node('l1', 'Original HI class', **node_attrs('HITeam'))
    leg.node('l2', 'New class',         **node_attrs('LLMAgent'))
    leg.node('l3', 'External ontology', **ext_node_attrs())
    leg.edge('l1', 'l2', style='invis')
    leg.edge('l2', 'l3', style='invis')

# save 
gv_path = OUTPUT + '.gv'
# make sure no blank nodes
import re
source = dot.source
#remove blank node IDs
source = re.sub(r'\n\s*n[0-9a-f]{25,}\s*\[[^\]]*\]', '', source)
# remoce edges from blankndes
source = re.sub(r'\n\s*n[0-9a-f]{25,}\s*->', '', source)
source = re.sub(r'\n\s*\S+\s*->\s*n[0-9a-f]{25,}[^\n]*', '', source)

with open(gv_path, 'w') as f:
    f.write(source)
print(f'Source saved: {gv_path}')
print(f'\nSource saved: {gv_path}')

for fmt in ['pdf', 'png', 'svg']:
    out = f'{OUTPUT}.{fmt}'
    res = subprocess.run(
        ['neato', f'-T{fmt}', gv_path, '-o', out],
        capture_output=True, text=True
    )
    if res.returncode == 0:
        print(f'{fmt.upper()} saved: {out}')
    else:
        print(f'{fmt.upper()} failed: {res.stderr[:200]}')
