from python_graphs import control_flow
from python_graphs import control_flow_graphviz

src = """
# IF-1
x = 5
if x > 0:
    y = 1
z = 2

"""

graph = control_flow.get_control_flow_graph(src)

# Create a Graphviz object (DOT graph)
g = control_flow_graphviz.to_graphviz(graph, include_src=src)

# Write an image (requires graphviz + pygraphviz working)
g.draw("cfg.svg", prog="dot")