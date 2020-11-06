from graphviz import Digraph
import pickle


def viz(name, exits, entries):
    for source in ("exits", "entries"):
        dot = Digraph(comment=f"{name}-{source}")

        edges = set()
        g = locals()[source]
        for node, nodeedges in g.items():
            for edge in nodeedges:
                edges.add((node, edge))

        for edge in edges:
            a, b = edge
            if (b, a) in edges:
                continue
            dot.edge(*edge)

        dot.render(f"{name}-{source}.gv", format="png")


def main():
    for name in ("hexen", "hexdd"):
        with open(f"{name}.wad.pickle", "rb") as f:
            print(name)
            viz(name, *pickle.load(f))


if __name__ == "__main__":
    main()
