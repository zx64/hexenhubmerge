import click
import omg
import os


class MapBounds:
    def __init__(self, maped):
        verts = maped.vertexes
        min_x = min(verts, key=lambda v: v.x).x
        min_y = min(verts, key=lambda v: v.y).y
        max_x = max(verts, key=lambda v: v.x).x
        max_y = max(verts, key=lambda v: v.y).y

        self.min = omg.Vertex(min_x, min_y)
        self.max = omg.Vertex(max_x, max_y)

    def width(self):
        return self.max.x - self.min.x


def move_map(maped, by):
    for vert in maped.vertexes:
        vert.x += by.x
        vert.y += by.y

    for thing in maped.things:
        thing.x += by.x
        thing.y += by.y


def edit_map(mapinfo):
    ed = omg.UMapEditor(mapinfo, "Hexen")
    ed.bounds = MapBounds(ed)
    return ed


def maxid(seq):
    try:
        return max(s.id for s in seq if s.id is not None)
    except ValueError:
        # May have no custom ids
        return 0


class MapMerger:
    player_start_types = [1, 2, 3, 4, 9100, 9101, 9102, 9103]
    teleport_dest_type = 14
    gutter = 10.0

    def __init__(self, mapinfo):
        self.map = edit_map(mapinfo)
        self.offset = omg.Vertex(self.map.bounds.max.x + self.gutter, 0.0)

    def to_textmap(self):
        return self.map.to_textmap()

    def to_lumps(self):
        return self.map.to_lumps()

    def merge(self, mapinfo):
        spoke = edit_map(mapinfo)

        self.offset.x -= spoke.bounds.min.x
        move_map(spoke, self.offset)
        self.offset.x += spoke.bounds.max.x + self.gutter

        base_vertex = len(self.map.vertexes)
        base_linedef = len(self.map.linedefs)
        base_sidedef = len(self.map.sidedefs)
        base_sector = len(self.map.sectors)

        # TODO: Compact allocated IDs?
        base_sector_id = maxid(self.map.sectors)
        base_thing_id = maxid(self.map.things)
        base_linedef_id = maxid(self.map.linedefs)

        for thing in spoke.things:
            if thing.id:
                thing.id += base_thing_id
            if thing.type in self.player_start_types:
                # TODO: Allocate new ids for teleport destinations
                thing.type = self.teleport_dest_type

        for line in spoke.linedefs:
            line.v1 += base_vertex
            line.v2 += base_vertex
            # TODO: Should these be base_linedef or base_thing_id
            if line.id is not None:
                line.id += base_linedef
            if line.arg0 is not None:
                line.arg0 += base_linedef
            line.sidefront += base_sidedef
            if line.sideback is not None:
                line.sideback += base_sidedef
            # TODO: Replace map change triggers (other than hub exit) with teleports to
            # previously allocated teleport destinations

        for side in spoke.sidedefs:
            side.sector += base_sector

        for sector in spoke.sectors:
            if sector.id is not None:
                sector.id += base_sector_id

        self.merge_acs(spoke, base_sector_id, base_thing_id, base_linedef_id)

        self.map.things.extend(spoke.things)
        self.map.linedefs.extend(spoke.linedefs)
        self.map.vertexes.extend(spoke.vertexes)
        self.map.sidedefs.extend(spoke.sidedefs)
        self.map.sectors.extend(spoke.sectors)

    def merge_acs(self, spoke, base_sector_id, base_thing_id, base_linedef_id):
        """
        TODO:
* Merge string tables and fix references
* Renumber and append scripts
* Resolve map variable conflicts
* Fix linedefs that reference scripts by number
* Fix references to sectors, things and linedefs inside scripts
* Simplify cross map triggers and references (return trigger etc.)
* Specials etc. set by script will need similar fixups
"""
        pass


def to_mapname(mapstr):
    try:
        mapstr = f"MAP{int(mapstr)}"
    except ValueError:
        return mapstr.upper()


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

    hubname = to_mapname(hub)
    if hubname not in source.maps:
        click.echo(f"Error: Hub {hubname} not found in source wad.")
        return 1

    spokes = [to_mapname(s) for s in maps]
    missing = [mapname for mapname in spokes if mapname not in source.maps]

    if missing:
        mstr = ", ".join(missing)
        click.echo(f"Error: Could not find {mstr}")
        return 1

    click.echo(f"Using {hubname} as the starting hub")
    merger = MapMerger(source.maps[hubname])

    for spoke in spokes:
        click.echo(f"Merging {spoke} starting at {merger.offset.x}")
        merger.merge(source.maps[spoke])

    merged_map_name = to_mapname(merged_map_name)
    click.echo(
        f"Merged map will be {merged_map_name} in {click.format_filename(output)}"
    )
    if udmf is not None:
        click.echo(f"Dumped UDMF to {click.format_filename(udmf.name)}")
        udmf.write(merger.to_textmap())

    result = omg.WAD(output if os.path.exists(output) else None)
    result.udmfmaps[merged_map_name] = merger.to_lumps()
    result.to_file(output)

    return 0


if __name__ == "__main__":
    hexenhubmerge()
