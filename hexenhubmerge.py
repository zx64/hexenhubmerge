import click
import omg
import os
from collections import defaultdict
from listacs import acsutil


def acs_stats(acs):
    click.echo(
        f"""ACS summary:
    Scripts: {len(acs.scripts)}
    Functions: {len(acs.functions)}
    Strings: {len(acs.strings)}
    Vars: {len(acs.vars)}
    Markers: {len(acs.markers)}
"""
    )


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
    ed.acs = acsutil.Behavior(ed.behavior.data)
    acs_stats(ed.acs)
    return ed


def maxid(seq):
    try:
        return max(s.id for s in seq if s.id is not None)
    except ValueError:
        # May have no custom ids
        return 0


class Specials:
    Teleport = 70
    Teleport_NewMap = 74

    # arg0 of some actions specials refers to a thing id
    action_uses_thing = [Teleport]
    # arg0 of some actions specials refers to a line id
    action_uses_line = []

    # arg0 of some actions should be treated as a fixed number
    action_fixed = [Teleport_NewMap]


class Things:
    PlayerStarts = [1, 2, 3, 4, 9100, 9101, 9102, 9103]
    TeleportDest = 14


class MapMerger:
    gutter = 10.0

    def __init__(self, mapinfo):
        self.map = edit_map(mapinfo)
        self.offset = omg.Vertex(self.map.bounds.max.x + self.gutter, 0.0)
        self.teleport_ids = defaultdict(dict)

        players = [
            thing for thing in self.map.things if thing.type in Things.PlayerStarts
        ]
        min_arg0 = min(players, key=lambda p: p.arg0).arg0
        click.echo(f"Lowest arg0 for player starts is {min_arg0}")
        for thing in self.map.things:
            if thing.type in Things.PlayerStarts and thing.arg0 > min_arg0:
                # click.echo(f"Alt player start {thing.type} {thing.arg0}")
                # thing.type = Things.TeleportDest
                # thing.id = self.teleport_ids[0][thing.arg0]
                # thing.arg0 = 0
                # thing.arg1 = 0
                pass

        # TODO: Do we also need teleport dests for the lowest start positions?

    def fix_teleports(self, source_hubnum, dest_hubnum, spoke_nums):
        for idx, line in enumerate(self.map.linedefs):
            if line.special != Specials.Teleport_NewMap:
                continue
            orig_arg0 = line.arg0
            orig_arg1 = line.arg1
            orig_arg2 = line.arg2
            if line.arg0 == source_hubnum:
                # line.special = Specials.teleport
                # line.arg0 = self.teleport_ids[0][line.arg1]
                # line.arg1 = 0
                # line.arg2 = 0
                result = "to hub"
            elif line.arg0 not in spoke_nums:
                result = f"exiting into MAP{dest_hubnum:02}"
                line.arg0 = dest_hubnum
            else:
                # line.special = Specials.Teleport
                # line.arg0 = self.teleport_ids[line.arg0][line.arg1]
                # line.arg1 = 0
                # line.arg2 = 0
                result = "to spoke"
            click.echo(
                f"lines[{idx}] Teleport_NewMap({orig_arg0}, {orig_arg1}, {orig_arg2}) -> {result}"
            )

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
            if thing.type in Things.PlayerStarts:
                # TODO: Allocate new ids for teleport destinations
                # playerstart.arg0 identifies returning player position
                # playerstart.id is unused(?)
                # teleportdest.arg0 is unused(?)
                # teleportdest.id is referenced by linedefs etc.
                thing.type = Things.TeleportDest
                # thing.id = self.teleport_ids[mapnum][thing.arg0]
                # thing.arg0 = 0

        for idx, line in enumerate(spoke.linedefs):
            line.v1 += base_vertex
            line.v2 += base_vertex
            if line.id is not None:
                line.id += base_linedef_id
            # TODO: More complete parameter fixups
            if line.arg0 is not None:
                if line.special in Specials.action_uses_thing:
                    line.arg0 += base_thing_id
                elif line.special in Specials.action_uses_line:
                    line.arg0 += base_linedef_id
                elif line.special in Specials.action_fixed:
                    # arg0 should be left alone
                    pass
                else:
                    line.arg0 += base_sector_id
            line.sidefront += base_sidedef
            if line.sideback is not None:
                line.sideback += base_sidedef

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
        mapstr = f"MAP{int(mapstr):02}"
    except ValueError:
        return mapstr.upper()


def to_mapnum(mapname):
    return int(mapname[-2:])


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

    click.echo(f"Converting {hubname} to UDMF to use as the starting hub")
    merger = MapMerger(source.maps[hubname])

    for spoke in spokes:
        click.echo(f"Converting and merging {spoke}")
        merger.merge(source.maps[spoke])

    merged_map_name = to_mapname(merged_map_name)
    source_hubnum = to_mapnum(hubname)
    dest_hubnum = to_mapnum(merged_map_name) + 1
    spoke_nums = [to_mapnum(s) for s in maps]
    click.echo(
        f"Merged map will be {merged_map_name} in {click.format_filename(output)}, will exit into MAP{dest_hubnum:02}."
    )
    merger.fix_teleports(source_hubnum, dest_hubnum, spoke_nums)
    if udmf is not None:
        click.echo(f"Dumped UDMF to {click.format_filename(udmf.name)}")
        udmf.write(merger.to_textmap())

    result = omg.WAD(output if os.path.exists(output) else None)
    result.udmfmaps[merged_map_name] = merger.to_lumps()
    result.to_file(output)

    return 0


if __name__ == "__main__":
    hexenhubmerge()
