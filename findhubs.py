import click
import omg
import pickle
from listacs import acsutil
from collections import defaultdict


def mapname(mapnum):
    return f"MAP{mapnum:02}"


def OP(name, *args):
    return (acsutil.pcode_index[name], *args)


PUSHNUMBER = acsutil.PCD_PUSHNUMBER
IFNOTGOTO = acsutil.PCD_IFNOTGOTO
lspec2 = OP("LSPEC2", 74)
lspec2direct = OP("LSPEC2DIRECT", 74)
setlinespecial = OP("SETLINESPECIAL")
gametype_eq_2 = [OP("GAMETYPE"), OP("PUSHNUMBER", 2), OP("EQ")]


def find_exits(linedefs, behavior):
    s = omg.mapedit.ZLinedef._fmtsize
    LD_OFFSET_ACTION = 6
    LD_OFFSET_ARG0 = 7
    ACTION_NEWLEVEL = 74
    # Grab arg0 from all linedefs with action == 74
    exits = set(
        linedefs[i + LD_OFFSET_ARG0]
        for i in range(0, len(linedefs), s)
        if linedefs[i + LD_OFFSET_ACTION] == ACTION_NEWLEVEL
    )

    acs = acsutil.Behavior(behavior)

    for script in acs.scripts:
        opcodes = [opcode for _, opcode in script.opcodes()]
        if not opcodes:
            continue

        # Check for if (Gametype() == 2) prefix
        if opcodes[0:3] == gametype_eq_2 and opcodes[3][0] == IFNOTGOTO:
            # HEXDD MAP60:
            # GAMETYPE
            # PUSHNUMBER 2
            # EQ
            # IFNOTGOTO 2376
            # LSPEC2DIRECT 74, 41, 0
            # TERMINATE
            continue

        for idx, opcode in enumerate(opcodes):
            if opcode == lspec2:
                # HEXDD MAP33:
                # idx - 2: PUSHNUMBER 34 <- arg0
                # idx - 1: PUSHNUMBER 0 <- arg1
                # idx    : LSPEC2 74
                op, arg0 = opcodes[idx - 2]
                assert op == PUSHNUMBER
                exits.add(arg0)
            elif opcode[0:2] == lspec2direct:
                # HEXDD MAP42: LSPEC2DIRECT 74, 41, 0
                exits.add(opcode[2])
            elif opcode == setlinespecial:
                # HEXEN MAP02
                # idx - 6: PUSHNUMBER 74
                # idx - 5: PUSHNUMBER 5 <- arg0
                # idx - 4: PUSHNUMBER 0 <- arg1
                # idx - 3: PUSHNUMBER 0
                # idx - 2: PUSHNUMBER 0
                # idx - 1: PUSHNUMBER 0
                # idx    : SETLINESPECIAL
                op, special = opcodes[idx - 6]
                if op != PUSHNUMBER:
                    continue
                if special != ACTION_NEWLEVEL:
                    continue
                op, arg0 = opcodes[idx - 5]
                assert op == PUSHNUMBER
                exits.add(arg0)

    return sorted(mapname(e) for e in exits)


@click.command()
@click.argument(
    "wadname",
    required=True,
    type=click.Path(exists=True, readable=True, dir_okay=False),
)
def findhubs(wadname):
    wad = omg.WAD(wadname)

    mapexits = {}

    for mapname, mapinfo in wad.maps.items():
        mapexits[mapname] = find_exits(
            mapinfo["LINEDEFS"].data, mapinfo["BEHAVIOR"].data
        )

    mapenters = defaultdict(set)

    print("Map  : Exits to")
    for mapname, exits in sorted(mapexits.items()):
        for exit in exits:
            mapenters[exit].add(mapname)
        s = ", ".join(str(i) for i in exits)
        print(f"{mapname}: {s}")

    mapenters = {k: sorted(v) for k, v in mapenters.items()}

    print("Map  : Comes from")
    for mapname, entries in sorted(mapenters.items()):
        s = ", ".join(str(i) for i in entries)
        print(f"{mapname}: {s}")

    # TODO: Convert mapexits into hub/spoke graph
    with open(f"{wadname}.pickle", "wb") as f:
        pickle.dump((mapexits, mapenters), f)

    return 0


if __name__ == "__main__":
    findhubs()
