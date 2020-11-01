import click
import omg
import os

player_start_ids = [1, 2, 3, 4, 9100, 9101, 9102, 9103]
teleport_dest_id = 14
map_gutter = 10.0


def MergeMap(destmap, sourcemap, start_x):
    min_x = min(sourcemap.vertexes, key=lambda v: v.x).x
    max_x = max(sourcemap.vertexes, key=lambda v: v.x).x

    start_x -= min_x
    min_vertex = len(destmap.vertexes)
    min_linedef = len(destmap.linedefs)
    min_sidedef = len(destmap.sidedefs)
    min_sector = len(destmap.sectors)
    # min_thing = len(destmap.things)

    for thing in sourcemap.things:
        if thing.type in player_start_ids:
            thing.type = teleport_dest_id
        thing.x += start_x
        destmap.things.append(thing)

    for line in sourcemap.linedefs:
        line.v1 += min_vertex
        line.v2 += min_vertex
        if line.id is not None:
            line.id += min_linedef
        if line.arg0 is not None:
            line.arg0 += min_linedef
        line.sidefront += min_sidedef
        if line.sideback is not None:
            line.sideback += min_sidedef
        destmap.linedefs.append(line)

    for vert in sourcemap.vertexes:
        vert.x += start_x
        destmap.vertexes.append(vert)

    for side in sourcemap.sidedefs:
        side.sector += min_sector
        destmap.sidedefs.append(side)

    for sector in sourcemap.sectors:
        if sector.id:
            sector.id += min_sector
        destmap.sectors.append(sector)

    start_x += max_x + map_gutter
    return start_x


def CanonMapName(mapname):
    try:
        mapname = f"MAP{int(mapname)}"
    except ValueError:
        return mapname.upper()


@click.command()
@click.option("-n", "--merged-map-name", default="MAP01", type=str)
@click.option("-u", "--udmf", type=click.File("w"))
@click.argument("input", required=True, type=click.Path(exists=True, readable=True))
@click.argument("output", required=True, type=click.Path(dir_okay=False, writable=True))
@click.argument("hub", required=True)
@click.argument("maps", nargs=-1)
def hexenhubmerge(input, output, merged_map_name, hub, maps, udmf):
    """Merge HUB and MAPS from INPUT.wad into a single map in OUTPUT.wad as NAME"""

    source = omg.WAD(input)

    hub = CanonMapName(hub)
    if hub not in source.maps:
        click.echo(f"Error: Hub {hub} not found in source wad.")
        return 1

    maps = [CanonMapName(s) for s in maps]
    missing = [mapname for mapname in maps if mapname not in source.maps]

    if missing:
        mstr = ", ".join(missing)
        click.echo(f"Error: Could not find {mstr}")
        return 1

    click.echo(f"Using {hub} as the starting hub")
    merged = omg.UMapEditor(source.maps[hub], "Hexen")
    start_x = max(merged.vertexes, key=lambda v: v.x).x + map_gutter

    for mapname in maps:
        click.echo(f"Merging {mapname} starting at {start_x}")
        start_x = MergeMap(
            merged, omg.UMapEditor(source.maps[mapname], "Hexen"), start_x
        )

    click.echo(
        f"Merged map will be {merged_map_name} in {click.format_filename(output)}"
    )
    if udmf is not None:
        click.echo(f"Dumped UDMF to {click.format_filename(udmf.name)}")
        udmf.write(merged.to_textmap())
    if os.path.exists(output):
        result = omg.WAD(output)
    else:
        result = omg.WAD()
    result.udmfmaps[merged_map_name.upper()] = merged.to_lumps()
    result.to_file(output)

    return 0


if __name__ == "__main__":
    hexenhubmerge()
