# main_example.py
# ------------------------------------------------------------
# Example usage (matches the sample program style from the pseudocode).
# ------------------------------------------------------------

from cfg_builder import build_listM, generate_cfg, build_adj_from_edges
from paths_finder import find_all_paths


if __name__ == "__main__":
    sample_program = """var=int(input())
if(var == 200):
    print ("1 - Got a true expression value")
    print (var)
elif var == 150:
    print ("2 - Got a true expression value")
    print (var)
elif var == 100:
    print ("3 - Got a true expression value")
    print (var)
else:
    print ("4 - Got a false expression value")
    print (var)
"""

    # CFG algorithm
    listM = build_listM(sample_program)
    nodes, edges, list3, list2_counts = generate_cfg(listM)

    print("ListM:", listM)
    print("\nNodes:", nodes)
    print("\nEdges (List2):")
    for e in edges:
        print(" ", e)

    print("\nList3:", list3)
    print("\nList2 counts (freq from List3):", list2_counts)

    # Path-finding algorithm
    adj = build_adj_from_edges(edges)
    paths = find_all_paths(adj, "start", "end")

    print("\nAll paths from start to end:")
    for p in paths:
        print(" ", p)
