import omg
import click
import re
from listacs import acsutil


pushnumber = re.compile(".*: PUSHNUMBER (.*)$")
lspec2 = re.compile(".*: LSPEC2 74$")
lspec2direct = re.compile(".*: LSPEC2DIRECT 74, ([^,]*), (.*)$")

"""
Example bytecode sequences to search for:

         396: PUSHNUMBER 34 <- arg0
         404: PUSHNUMBER 0 <- arg1
         412: LSPEC2 74

        2360: LSPEC2DIRECT 74, 41, 0

         928: PUSHNUMBER 74
         936: PUSHNUMBER 5 <- arg0
         944: PUSHNUMBER 0 <- arg1
         952: PUSHNUMBER 0
         960: PUSHNUMBER 0
         968: PUSHNUMBER 0
         976: SETLINESPECIAL

"""

def find_exits(linedefs, behavior):
    s = omg.mapedit.ZLinedef._fmtsize
    # Grab arg0 from all linedefs with action == 74
    exits = set(
        linedefs[i + 7] for i in range(0, len(linedefs), s) if linedefs[i + 6] == 74
    )

    acs = acsutil.Behavior(behavior)

    for script in acs.scripts:
        # TODO: Search for actual opcodes instead of string matching!
        bytecode = list(script.disassemble())
        for idx, opcode in enumerate(bytecode):
            if lspec2.match(opcode):
                # TODO: Assumes params are pushed in immediate prior opcodes
                # Stack could have been prepared in earlier instructions
                arg0 = pushnumber.match(bytecode[idx - 2])
                assert arg0 is not None
                exits.add(int(arg0.group(1)))
            elif m := lspec2direct.match(opcode):
                exits.add(int(m.group(1)))

            # TODO: Any other opcodes to look for?
            # SetLineSpecial maybe?

    return exits


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

    for mapname, exits in mapexits.items():
        s = ", ".join(str(i) for i in exits)
        print(f"{mapname}: {s}")

    # TODO: Convert mapexits into hub/spoke graph

    return 0


if __name__ == "__main__":
    findhubs()
