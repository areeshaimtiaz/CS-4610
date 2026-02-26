# gui.py
# Updated: renders CFG as SVG (DOT -> SVG) and removes PNG/Pillow display code.
# Tkinter cannot display SVG directly, so the SVG is saved and opened in the default browser.
#
# Requirements:
#   pip install graphviz
#   macOS: brew install graphviz
#
# Run:
#   python gui.py

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import textwrap
import os
import tempfile
import graphviz
import webbrowser

from cfg_builder import build_listM, generate_cfg, build_adj_from_edges
from paths_finder import find_all_paths

# (Optional but helpful on macOS if PATH issues prevent Graphviz from being found)
os.environ["PATH"] = os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin"


def edges_to_dot(nodes, edges):
    lines = [
        "digraph CFG {",
        "  rankdir=TB;",
        "  node [shape=ellipse];",
    ]
    for n in nodes:
        lines.append(f'  "{n}";')
    for a, b in edges:
        lines.append(f'  "{a}" -> "{b}";')
    lines.append("}")
    return "\n".join(lines)


def render_dot_to_svg(dot_text: str) -> str:
    # Save SVG in current working directory
    cwd = os.getcwd()
    svg_path = os.path.join(cwd, "cfg_graph.svg")

    src = graphviz.Source(dot_text)

    # IMPORTANT:
    # When using filename, do NOT include ".svg"
    # Graphviz automatically appends the extension.
    output_path = src.render(
        filename=os.path.join(cwd, "cfg_graph"),
        format="svg",
        cleanup=True
    )

    if not os.path.exists(output_path):
        raise FileNotFoundError(f"SVG was not created at {output_path}")

    return output_path



class CFGToolGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automatic CFG Tool — Front View")
        self.geometry("1000x720")
        self.create_widgets()

        # store last produced structures
        self.last_listM = []
        self.last_nodes = []
        self.last_edges = []
        self.last_list3 = []
        self.last_counts = {}

        # store last rendered svg path (optional: for Export SVG button / reuse)
        self.last_svg_path = None

    def create_widgets(self):
        # Top frame: Title / toolbar
        top_frame = ttk.Frame(self, padding=(8, 8))
        top_frame.pack(side=tk.TOP, fill=tk.X)

        title = ttk.Label(
            top_frame,
            text="Automatic Control Flow Graph Tool",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(side=tk.LEFT)

        # Main panes: left = Paste Your Code Below; right = outputs & controls
        main_pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left pane: Paste your code below
        left_frame = ttk.Labelframe(main_pane, text="Paste Your Code Below", padding=(8, 8))
        left_frame.config(height=600, width=450)
        main_pane.add(left_frame, weight=1)

        self.code_text = scrolledtext.ScrolledText(left_frame, wrap=tk.NONE, font=("Consolas", 11))
        self.code_text.pack(fill=tk.BOTH, expand=True)

        sample = textwrap.dedent("""\
            var=int(input())
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
        """)
        self.code_text.insert("1.0", sample)

        # Right pane (SCROLLABLE)
        right_container = ttk.Frame(main_pane)
        main_pane.add(right_container, weight=1)

        canvas = tk.Canvas(right_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        right_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=right_frame, anchor="nw")

        def on_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        right_frame.bind("<Configure>", on_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Buttons frame (Create CFG, Complexity, Find Paths, Export DOT, Export SVG)
        buttons_frame = ttk.Labelframe(right_frame, text="Controls", padding=(8, 8))
        buttons_frame.pack(fill=tk.X)

        ttk.Button(buttons_frame, text="Create CFG", command=self.on_create_cfg).grid(
            row=0, column=0, padx=6, pady=6, sticky="ew"
        )
        ttk.Button(buttons_frame, text="Complexity", command=self.on_complexity).grid(
            row=0, column=1, padx=6, pady=6, sticky="ew"
        )
        ttk.Button(buttons_frame, text="Find Paths", command=self.on_find_paths).grid(
            row=0, column=2, padx=6, pady=6, sticky="ew"
        )
        ttk.Button(buttons_frame, text="Export DOT...", command=self.on_export_dot).grid(
            row=0, column=3, padx=6, pady=6, sticky="ew"
        )
        ttk.Button(buttons_frame, text="Export SVG...", command=self.on_export_svg).grid(
            row=0, column=4, padx=6, pady=6, sticky="ew"
        )

        buttons_frame.columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Output: nodes and edges (CFG)
        cfg_frame = ttk.Labelframe(right_frame, text="CFG (Nodes & Edges)", padding=(8, 8))
        cfg_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.nodes_text = scrolledtext.ScrolledText(cfg_frame, height=6, wrap=tk.NONE, font=("Consolas", 10))
        self.nodes_text.pack(fill=tk.BOTH, expand=False)

        self.edges_text = scrolledtext.ScrolledText(cfg_frame, height=8, wrap=tk.NONE, font=("Consolas", 10))
        self.edges_text.pack(fill=tk.BOTH, expand=True)

        # Graph area (SVG note)
        graph_frame = ttk.Labelframe(right_frame, text="CFG Graph (SVG)", padding=(8, 8))
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.graph_note = ttk.Label(
            graph_frame,
            text="SVG graphs open in your browser (Tkinter cannot display SVG directly).\n"
                 "Click 'Create CFG' to generate and open the SVG.",
            justify="left",
        )
        self.graph_note.pack(fill=tk.BOTH, expand=True)

        # Output: complexity and paths
        lower_frame = ttk.Frame(right_frame)
        lower_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        complexity_box = ttk.Labelframe(lower_frame, text="Complexity", padding=(8, 8))
        complexity_box.pack(fill=tk.X)

        self.complexity_var = tk.StringVar(value="Cyclomatic Complexity: —")
        self.complexity_label = ttk.Label(complexity_box, textvariable=self.complexity_var, font=("Segoe UI", 11))
        self.complexity_label.pack(anchor="w")

        paths_box = ttk.Labelframe(lower_frame, text="Paths (start → end)", padding=(8, 8))
        paths_box.pack(fill=tk.BOTH, expand=True)

        self.paths_text = scrolledtext.ScrolledText(paths_box, wrap=tk.NONE, font=("Consolas", 10))
        self.paths_text.pack(fill=tk.BOTH, expand=True)

        # bottom status / help
        bottom = ttk.Frame(self, padding=(6, 4))
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        hint = ttk.Label(
            bottom,
            text="Appearance: Create CFG  |  Complexity  |  Find Paths  |  Paste Your Code Below",
            font=("Segoe UI", 9),
        )
        hint.pack(side=tk.LEFT)

    def on_create_cfg(self):
        src = self.code_text.get("1.0", tk.END)
        if not src.strip():
            messagebox.showinfo("No code", "Paste the python program in the 'Paste Your Code Below' area first.")
            return

        try:
            listM = build_listM(src)
            nodes, edges, list3, counts = generate_cfg(listM)
        except Exception as e:
            messagebox.showerror("Error generating CFG", f"Exception: {e}")
            return

        # store
        self.last_listM = listM
        self.last_nodes = nodes
        self.last_edges = edges
        self.last_list3 = list3
        self.last_counts = counts

        # display nodes and edges
        self.nodes_text.delete("1.0", tk.END)
        self.nodes_text.insert(tk.END, "ListM (sequence):\n")
        self.nodes_text.insert(tk.END, ", ".join(listM) + "\n\n")
        self.nodes_text.insert(tk.END, "Nodes (unique):\n")
        self.nodes_text.insert(tk.END, ", ".join(nodes) + "\n")

        self.edges_text.delete("1.0", tk.END)
        self.edges_text.insert(tk.END, "Edges (List2):\n")
        for a, b in edges:
            self.edges_text.insert(tk.END, f"{a}  ->  {b}\n")

        # clear previous paths and complexity
        self.paths_text.delete("1.0", tk.END)
        self.complexity_var.set("Cyclomatic Complexity: —")

        # Render SVG and open it
        try:
            dot_text = edges_to_dot(self.last_nodes, self.last_edges)
            svg_path = render_dot_to_svg(dot_text)
            self.last_svg_path = svg_path
            print("Rendered SVG:", svg_path)
            webbrowser.open("file://" + svg_path)
        except Exception as e:
            messagebox.showerror("Graph Error", f"Could not render/open SVG graph:\n{e}")

        messagebox.showinfo("CFG Created", f"CFG created with {len(nodes)} nodes and {len(edges)} edges.")

    def on_complexity(self):
        if not self.last_nodes or not self.last_edges:
            messagebox.showinfo("Run Create CFG first", "Please click 'Create CFG' before computing complexity.")
            return

        # Cyclomatic complexity (simple version): V = E - N + 2 (P=1)
        E = len(self.last_edges)
        N = len(self.last_nodes)
        V = E - N + 2
        if V < 1:
            V = 1

        self.complexity_var.set(f"Cyclomatic Complexity: {V} (E={E}, N={N})")
        self.paths_text.insert(tk.END, f"\nComplexity computed: E={E}, N={N}, V={V}\n")

    def on_find_paths(self):
        if not self.last_edges:
            messagebox.showinfo("Run Create CFG first", "Please click 'Create CFG' before finding paths.")
            return

        adj = build_adj_from_edges(self.last_edges)

        try:
            paths = find_all_paths(adj, "start", "end")
        except RecursionError:
            messagebox.showerror("Recursion Error", "Path finding recursed too deeply (possible cycles).")
            return
        except Exception as exc:
            messagebox.showerror("Error", f"Path finding failed: {exc}")
            return

        self.paths_text.delete("1.0", tk.END)
        if not paths:
            self.paths_text.insert(tk.END, "No start → end paths found.\n")
        else:
            for idx, p in enumerate(paths, 1):
                self.paths_text.insert(tk.END, f"{idx}. " + " -> ".join([str(x) for x in p]) + "\n")

        messagebox.showinfo("Paths Found", f"Found {len(paths)} path(s) from 'start' to 'end'.")

    def on_export_dot(self):
        if not self.last_nodes or not self.last_edges:
            messagebox.showinfo("Nothing to export", "Run 'Create CFG' first.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".dot",
            filetypes=[("DOT files", "*.dot"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            dot_text = edges_to_dot(self.last_nodes, self.last_edges)
            with open(path, "w", encoding="utf8") as fh:
                fh.write(dot_text)
            messagebox.showinfo("Exported", f"DOT file saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error saving DOT", str(e))

    def on_export_svg(self):
        if not self.last_nodes or not self.last_edges:
            messagebox.showinfo("Nothing to export", "Run 'Create CFG' first.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            dot_text = edges_to_dot(self.last_nodes, self.last_edges)
            src = graphviz.Source(dot_text)

            # Graphviz will append ".svg" if missing; keep whatever it returns
            svg_path = src.render(filename=path, format="svg", cleanup=True)

            messagebox.showinfo("Exported", f"SVG saved to:\n{svg_path}")
            # Optional: open after export
            webbrowser.open("file://" + svg_path)
        except Exception as e:
            messagebox.showerror("Error saving SVG", str(e))


if __name__ == "__main__":
    app = CFGToolGUI()
    app.mainloop()
