# paths_finder.py
# ------------------------------------------------------------
# Converted from the provided pseudocode (finding different paths).
# ------------------------------------------------------------

from __future__ import annotations
from typing import Dict, List


def find_all_paths(d: Dict[str, List[str]], source: str, dest: str, path=None):
    """
    Pseudocode translation:

    find_all_paths (d, source, dest, path=[]):
      path = path + [source]
      if (source == dest) return [path]
      paths = []
      for node in d[source]
        if node in path
          for i in d[node]
            if(i==node) break
            elif(i=='end')
              path=path+[node]+['end']
              paths.append(path)
              break
        else
          newpaths = find_all_paths(d, node, dest, path)
          for newpath in newpaths
            paths.append(newpath)
      return paths
    """
    path = (path or []) + [source]

    if source == dest:
        return [path]

    paths = []
    for node in d.get(source, []):
        if node in path:
            for i in d.get(node, []):
                if i == node:
                    break
                elif i == "end":
                    newp = path + [node, "end"]
                    paths.append(newp)
                    break
            continue
        else:
            newpaths = find_all_paths(d, node, dest, path)
            for newpath in newpaths:
                paths.append(newpath)

    return paths
