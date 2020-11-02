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
    return max(s.id for s in seq if s.id is not None)


class MapMerger:
    player_start_ids = [1, 2, 3, 4, 9100, 9101, 9102, 9103]
    teleport_dest_id = 14
    gutter = 10.0

    def __init__(self, hub):
        self.hub = hub
        self.offset = omg.Vertex(hub.bounds.max.x + self.gutter, 0.0)
        self.base_sector_id = maxid(hub.sectors)
        self.base_thing_id = maxid(hub.things)

    def to_textmap(self):
        return self.hub.to_textmap()

    def to_lumps(self):
        return self.hub.to_lumps()

    def merge(self, spoke):
        self.offset.x -= spoke.bounds.min.x
        move_map(spoke, self.offset)

        min_vertex = len(self.hub.vertexes)
        min_linedef = len(self.hub.linedefs)
        min_sidedef = len(self.hub.sidedefs)
        min_sector = len(self.hub.sectors)

        for thing in spoke.things:
            if thing.id:
                thing.id += self.base_thing_id
            if thing.type in self.player_start_ids:
                thing.type = self.teleport_dest_id
            self.hub.things.append(thing)

        for line in spoke.linedefs:
            line.v1 += min_vertex
            line.v2 += min_vertex
            if line.id is not None:
                line.id += min_linedef
            if line.arg0 is not None:
                line.arg0 += min_linedef
            line.sidefront += min_sidedef
            if line.sideback is not None:
                line.sideback += min_sidedef
            self.hub.linedefs.append(line)

        for vert in spoke.vertexes:
            self.hub.vertexes.append(vert)

        for side in spoke.sidedefs:
            side.sector += min_sector
            self.hub.sidedefs.append(side)

        for sector in spoke.sectors:
            if sector.id:
                sector.id += self.base_sector_id
            self.hub.sectors.append(sector)

        self.offset.x += spoke.bounds.max.x + self.gutter
        self.base_sector_id += maxid(spoke.sectors)
        self.base_thing_id += maxid(spoke.things)


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
    merger = MapMerger(edit_map(source.maps[hubname]))

    for spoke in spokes:
        click.echo(f"Merging {spoke} starting at {merger.offset.x}")
        merger.merge(edit_map(source.maps[spoke]))

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
