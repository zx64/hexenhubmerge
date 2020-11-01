import click
import omg
import os
from tqdm import tqdm


@click.command()
@click.option("-ns", "--namespace")
@click.argument("input", required=True, type=click.Path(exists=True, readable=True))
@click.argument("output", required=True, type=click.Path(dir_okay=False, writable=True))
def toudmf(input, output, namespace):
    """Convert all maps in INPUT.wad to UDMF and write to OUTPUT.wad"""

    source = omg.WAD(input)
    dest = omg.WAD(output if os.path.exists(output) else None)

    try:
        with tqdm(source.maps.items(), unit="map") as t:
            for mapname, mapinfo in t:
                t.write(mapname)
                dest.udmfmaps[mapname] = omg.UMapEditor(mapinfo, namespace).to_lumps()
        dest.to_file(output)
    except AttributeError:
        click.echo("Incorrect Namespace (-ns) for map format?")
        return 1

    return 0


if __name__ == "__main__":
    toudmf()
