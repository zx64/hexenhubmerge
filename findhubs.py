import omg
import click
import re
from listacs import acsutil


pushnumber = re.compile(".*: PUSHNUMBER (.*)$")
lspec2 = re.compile(".*: LSPEC2 74$")
lspec2direct = re.compile(".*: LSPEC2DIRECT 74, ([^,]*), (.*)$")


def find_exits(maped):
    exits = set()
    for line in maped.linedefs:
        if line.action != 74:
            continue
        exits.add(line.arg0)

    acs = acsutil.Behavior(maped.behavior.data)

    for script in acs.scripts:
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
@click.argument("wadname", required=True, type=click.Path(exists=True, readable=True))
def findhubs(wadname):
    wad = omg.WAD(wadname)

    mapexits = {}

    for mapname, mapinfo in wad.maps.items():
        mapexits[mapname] = find_exits(omg.MapEditor(mapinfo))

    for mapname, exits in mapexits.items():
        s = ", ".join(str(i) for i in exits)
        print(f"{mapname}: {s}")

    # TODO: Convert mapexits into hub/spoke graph

    return 0


if __name__ == "__main__":
    findhubs()
