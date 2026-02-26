from staticfg import CFGBuilder

# Build CFG from file
cfg = CFGBuilder().build_from_file("example", "example.py")

# Print basic block information
for block in cfg:
    print("Block:", block.id)
    print("Statements:")
    for stmt in block.statements:
        print("   ", stmt)
    print("Exits:", [exit.target.id for exit in block.exits])
    print("-" * 40)

# Save CFG as a graph (requires graphviz)
cfg.build_visual("example_cfg", "svg")
