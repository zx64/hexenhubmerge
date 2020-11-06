import click
import omg
import pickle
import re
import struct
from listacs import acsutil
from collections import defaultdict

# Known prefix for a deathmatch only (Gametype() == 2) script
ifdm = struct.pack(
    "<5I",
    acsutil.PCD_GAMETYPE,
    acsutil.PCD_PUSHNUMBER,
    2,
    acsutil.PCD_EQ,
    acsutil.PCD_IFNOTGOTO,
)

pushnumber = re.compile(".*: PUSHNUMBER (.*)$")
lspec2 = re.compile(".*: LSPEC2 74$")
lspec2direct = re.compile(".*: LSPEC2DIRECT 74, ([^,]*), (.*)$")
setlinespecial = re.compile(".*: SETLINESPECIAL$")

"""
Example dissassembled bytecode sequences to search for:
(HEXDD MAP33)
         396: PUSHNUMBER 34 <- arg0
         404: PUSHNUMBER 0 <- arg1
         412: LSPEC2 74

(HEXDD MAP42)
        2404: LSPEC2DIRECT 74, 41, 0

(HEXEN MAP02)
         928: PUSHNUMBER 74
         936: PUSHNUMBER 5 <- arg0
         944: PUSHNUMBER 0 <- arg1
         952: PUSHNUMBER 0
         960: PUSHNUMBER 0
         968: PUSHNUMBER 0
         976: SETLINESPECIAL

However, some exits are conditional on being deathmatch (or not):
(HEXDD MAP60)
        2336: GAMETYPE
        2340: PUSHNUMBER 2
        2348: EQ
        2352: IFNOTGOTO 2376
        2360: LSPEC2DIRECT 74, 41, 0
        2376: TERMINATE
"""


def mapname(mapnum):
    return f"MAP{mapnum:02}"


def find_exits(linedefs, behavior):
    s = omg.mapedit.ZLinedef._fmtsize
    LD_OFFSET_ACTION = 6
    LD_OFFSET_ARG0 = 7
    ACTION_NEWLEVEL = 74
    # Grab arg0 from all linedefs with action == 74
    exits = set(
        mapname(linedefs[i + LD_OFFSET_ARG0])
        for i in range(0, len(linedefs), s)
        if linedefs[i + LD_OFFSET_ACTION] == ACTION_NEWLEVEL
    )

    acs = acsutil.Behavior(behavior)

    for script in acs.scripts:
        bytecode = acs.data[script.ptr : script.end]

        # Check for if (Gametype() == 2) prefix
        if bytecode.startswith(ifdm):
            continue

        # TODO: Search for actual opcodes instead of string matching!
        listing = list(script.disassemble())
        for idx, opcode in enumerate(listing):
            if lspec2.match(opcode):
                # TODO: Assumes params are pushed in immediate prior opcodes
                # Stack could have been prepared in earlier instructions
                arg0 = pushnumber.match(listing[idx - 2])
                assert arg0 is not None
                exits.add(mapname(int(arg0.group(1))))
            elif m := lspec2direct.match(opcode):
                exits.add(mapname(int(m.group(1))))
            elif setlinespecial.match(opcode):
                # TODO: Assumes params are pushed in immediate prior opcodes
                # Stack could have been prepared in earlier instructions
                special = pushnumber.match(listing[idx - 6])
                if special is None:
                    continue
                try:
                    if int(special.group(1)) != ACTION_NEWLEVEL:
                        continue
                except ValueError:
                    continue
                arg0 = pushnumber.match(listing[idx - 5])
                assert arg0 is not None
                exits.add(mapname(int(arg0.group(1))))
            else:
                # TODO: Any other opcodes to look for?
                pass

    return sorted(exits)


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
