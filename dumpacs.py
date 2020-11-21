import click
import omg
from listacs import acsutil
from tqdm import tqdm


def dump(mapname, lump):
    # TODO: Extract more of the front end from listacs.py into callables
    # Until then, for %A in (*.o) do listacs.py -o %~nA.acs -d %A
    acs = acsutil.Behavior(lump)
    with open(f"tmp/{mapname}.o", "wb") as f:
        f.write(acs.data)


@click.command()
@click.argument(
    "wad_filename", required=True, type=click.Path(exists=True, readable=True)
)
def dumpacs(wad_filename):
    """Extract and decompile all BEHAVIOR lumps from a wad"""

    source = omg.WAD(wad_filename)

    with tqdm(source.maps.items(), unit="map") as t:
        for mapname, mapinfo in t:
            try:
                dump(mapname, mapinfo["BEHAVIOR"].data)
            except KeyError:
                pass

    return 0


if __name__ == "__main__":
    dumpacs()
