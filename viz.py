import pickle
from graphviz import Digraph


def viz(name, exits, entries):
    for source in ("exits", "entries"):
        dot = Digraph(
            name=f"{name}-{source}",
            format="png",
            graph_attr={"overlap": "false"},
            engine="neato",
        )

        edges = set()
        g = locals()[source]
        for node, nodeedges in g.items():
            for edge in nodeedges:
                edges.add((node, edge))

        for node in g.keys():
            dot.node(node)
        for edge in edges:
            # a, b = edge
            # if (b, a) in edges:
            #    continue
            dot.edge(*edge)

        dot.render()


def main():
    for name in ("hexen", "hexdd"):
        with open(f"{name}.wad.pickle", "rb") as f:
            print(name)
            viz(name, *pickle.load(f))


if __name__ == "__main__":
    main()
