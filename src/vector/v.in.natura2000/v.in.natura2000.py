#!/usr/bin/env python

"""
MODULE:    v.in.natura2000

AUTHOR(S): Helmut Kudrnovsky <alectoria AT gmx at>
           Update to read GeoPackage by Paulo van Breugel

PURPOSE:   Imports Natura 2000 spatial data of protected areas

COPYRIGHT: (C) 2015-2024 by the GRASS Development Team

           This program is free software under the GNU General Public
           License (>=v2). Read the file COPYING that comes with GRASS
           for details.
"""

# %module
# % description: importing of Natura 2000 spatial data of protected areas
# % keyword: vector
# % keyword: geometry
# %end

# %option G_OPT_F_BIN_INPUT
# % key: input
# % required: yes
# %end

# %option G_OPT_V_OUTPUT
# % key: output
# % description: name of imported spatial data set
# % required : no
# % guisection: output
# %end

# %option sitetype
# % key: sitetype
# % description: Select site type of input (A, B or C)
# % required : no
# % guisection: selection
# %end

# %option habitat_code
# % key: habitat_code
# % description: Select habitat code of input
# % required : no
# % guisection: selection
# %end

# %option species_code
# % key: species_code
# % description: Select species of input
# % required : no
# % guisection: selection
# %end

# %option biogeographic_region
# % key: biogeographic_region
# % description: Select biogeographic region of input
# % required : no
# % guisection: selection
# %end

# %option member_state
# % key: member_state
# % description: Select member state of input
# % required : no
# % guisection: selection
# %end

# %option existing_layer
# % key: existing_layer
# % description: Import of existing layer
# % required : no
# % guisection: layer
# %end

# %flag
# % key: b
# % description: Print list of biogeographic regions
# % guisection: print
# %end

# %option G_OPT_F_OUTPUT
# % key: print2file
# % description: Name of file to which the selected list(s) should be printed
# %end

# %flag
# % key: m
# % description: Print list of EU member states codes
# % guisection: print
# %end

# %flag
# % key: h
# % description: Print list of habitats of community interest
# % guisection: print
# %end

# %flag
# % key: s
# % description: Print list of species of community interest
# % guisection: print
# %end

# %flag
# % key: t
# % description: Print list of protected area site types
# % guisection: print
# %end

# %flag
# % key: r
# % description: Limit import to the current region
# % guisection: Selection
# %end

import sys
import os
import csv
import math
import shutil
import tempfile
import grass.script as gs


def main():

    habitat_code_input = options["habitat_code"]
    species_code_input = options["species_code"]
    biogeoreg_long = options["biogeographic_region"]
    biogeoreg_long2 = biogeoreg_long.replace(" ", "_")
    biogeoreg_long_quoted = '"' + biogeoreg_long + '"'
    habitat_view = "v" + habitat_code_input
    habitat_spatial_view = "sv" + habitat_code_input
    species_view = "v" + species_code_input
    species_spatial_view = "sv" + species_code_input
    biogeoreg_view = "v" + biogeoreg_long2
    biogeoreg_spatial_view = "sv" + biogeoreg_long2
    layer_exist = options["existing_layer"]
    global tmp

    options = {
        "input": "/home/paulo/Downloads/Natura2000.gpkg",
        "print2file": "/home/paulo/Desktop/output.txt",
        "output": "AAA4",
        "sitetype": "A",
        "member_state": "NL",
    }
    flags = {"r": ""}

    # Input variables
    n2k_input = options["input"]
    n2k_output = options["output"]
    outputfile = options["print2file"]
    pa_sitetype_input = options["sitetype"]
    ms_input = options["member_state"]
    if flags["r"]:
        flag_r = "r"
    else:
        flag_r = None

    # Get list of biogeographic regions
    if flags["b"]:
        bioregions = (
            gs.read_command(
                "db.select",
                sql="SELECT BIOGEOGRAPHICREG FROM BIOREGION GROUP BY BIOGEOGRAPHICREG",
                driver="ogr",
                database=n2k_input,
            )
            .strip()
            .split("\n")[1:]
        )
        if outputfile:
            with open(outputfile, "a") as file:
                file.write("Biogeographic regions:\n")
                file.write("\n".join(bioregions))
                file.write("\n\n")
        else:
            gs.message("Biogeographic regions:")
            gs.message(" | ".join(bioregions))
            gs.message("\n")

    # Get list of EU member states
    if flags["m"]:
        eumembers = (
            gs.read_command(
                "db.select",
                sql="SELECT MS FROM NaturaSite_polygon GROUP BY MS",
                driver="ogr",
                database=n2k_input,
            )
            .strip()
            .split("\n")[1:]
        )
        if outputfile:
            with open(outputfile, "a") as file:
                file.write("EU member states:\n")
                file.write("\n".join(eumembers))
                file.write("\n\n")
        else:
            gs.message("EU member states:")
            gs.message(" | ".join(eumembers))
            gs.message("\n")

    # Get list of habitat codes
    if flags["h"]:
        habitats = (
            gs.read_command(
                "db.select",
                sql="SELECT HABITATCODE, DESCRIPTION FROM HABITATS GROUP BY HABITATCODE",
                driver="ogr",
                database=n2k_input,
            )
            .strip()
            .split("\n")[1:]
        )
        if outputfile:
            with open(outputfile, "a") as file:
                file.write("habitat codes of EU community interest:\n")
                for habitatid in habitats:
                    id, habitat = habitatid.split("|")
                    file.write(f"{id} | {habitat}\n")
                file.write("\n\n")
        else:
            gs.message("habitat codes of EU community interest:")
            for habitatid in habitats:
                id, habitat = habitatid.split("|")
                gs.message(f"{id} | {habitat}")
                gs.message("\n")

    # Get list of species
    if flags["s"]:
        species = (
            gs.read_command(
                "db.select",
                sql="SELECT SPECIESCODE, SPECIESNAME FROM SPECIES GROUP BY SPECIESCODE",
                driver="ogr",
                database=n2k_input,
            )
            .strip()
            .split("\n")[1:]
        )
        if outputfile:
            with open(outputfile, "a") as file:
                file.write("species of EU community interest:\n")
                for specid in species:
                    id, spec = specid.split("|")
                    file.write(f"{id} | {spec}\n")
                file.write("\n\n")
        else:
            gs.message("species of EU community interest:")
            for specid in species:
                id, spec = specid.split("|")
                gs.message(f"{id} | {spec}")
                gs.message("\n")

    # Get list of site types
    if flags["t"]:
        sitetypes = (
            gs.read_command(
                "db.select",
                sql="SELECT SITETYPE FROM NATURA2000SITES GROUP BY SITETYPE",
                driver="ogr",
                database=n2k_input,
            )
            .strip()
            .split("\n")[1:]
        )
        if outputfile:
            with open(outputfile, "a") as file:
                file.write("Site types:\n")
                for siteid in sitetypes:
                    id, site = siteid.split("|")
                    file.write(f"{id} | {site}\n")
                file.write("\n\n")
        else:
            gs.message("Site types:")
            for siteid in species:
                id, site = siteid.split("|")
                gs.message(f"{id} | {site}")
                gs.message("\n")

    # Import protected areas of selected type
    if pa_sitetype_input:
        gs.message(
            _("importing protected areas of site type: {}".format(pa_sitetype_input))
        )
        gs.message("may take some time ...")
        if flags["r"]:
            flag_r = "r"
        else:
            flag_r = None
        gs.run_command(
            "v.in.ogr",
            input=n2k_input,
            layer="NaturaSite_polygon",
            output=n2k_output,
            where=f"SITETYPE = '{pa_sitetype_input}'",
            flags=flag_r,
            quiet=False,
        )

    # Import protected areas of selected the member state
    if ms_input:
        gs.message(_("importing protected areas of member state: {}".format(ms_input)))
        gs.message("may take some time ...")
        gs.run_command(
            "v.in.ogr",
            input=n2k_input,
            layer="NaturaSite_polygon",
            output=n2k_output,
            where=f"MS = '{ms_input}'",
            flags=flag_r,
            quiet=False,
        )

    # HIER GEBLEVEN

    if habitat_code_input:
        gs.message(
            "importing protected areas with habitat (code): %s" % habitat_code_input
        )
        gs.message("preparing (spatial) views in the sqlite/spatialite database:")
        conn = db.connect("%s" % n2k_input)
        c = conn.cursor()
        # create view of defined habitat
        gs.message("view: %s" % habitat_view)
        sqlhabitat = 'CREATE VIEW "%s" AS ' % (habitat_view)
        sqlhabitat += "SELECT * FROM HABITATS "
        sqlhabitat += 'WHERE HABITATCODE = "%s" ' % (habitat_code_input)
        sqlhabitat += 'ORDER BY "SITECODE"'
        gs.message(sqlhabitat)
        c.execute(sqlhabitat)
        # create spatial view of defined habitat - part 1
        gs.message("spatial view: %s" % habitat_spatial_view)
        sqlhabitatspatial1 = 'CREATE VIEW "%s" AS ' % (habitat_spatial_view)
        sqlhabitatspatial1 += (
            'SELECT "a"."ROWID" AS "ROWID", "a"."PK_UID" AS "PK_UID", '
        )
        sqlhabitatspatial1 += (
            '"a"."SITECODE" AS "SITECODE", "a"."SITENAME" AS "SITENAME", '
        )
        sqlhabitatspatial1 += '"a"."RELEASE_DA" AS "RELEASE_DA", "a"."MS" AS "MS", '
        sqlhabitatspatial1 += (
            '"a"."SITETYPE" AS "SITETYPE", "a"."Geometry" AS "Geometry", '
        )
        sqlhabitatspatial1 += '"b"."SITECODE" AS "SITECODE_1", "b"."HABITATCODE" AS "HABITATCODE", "b"."DESCRIPTION" AS "DESCRIPTION", '
        sqlhabitatspatial1 += '"b"."COVER_HA" AS "COVER_HA", "b"."CAVES" AS "CAVES", "b"."REPRESENTATIVITY" AS "REPRESENTATIVITY", '
        sqlhabitatspatial1 += (
            '"b"."RELSURFACE" AS "RELSURFACE", "b"."CONSERVATION" AS "CONSERVATION", '
        )
        sqlhabitatspatial1 += '"b"."GLOBAL_ASSESMENT" AS "GLOBAL_ASSESMENT", "b"."DATAQUALITY" AS "DATAQUALITY", '
        sqlhabitatspatial1 += '"b"."PERCENTAGECOVER" AS "PERCENTAGECOVER" '
        sqlhabitatspatial1 += 'FROM "Natura2000polygon" AS "a" '
        sqlhabitatspatial1 += 'JOIN %s AS "b" USING ("SITECODE") ' % (habitat_view)
        sqlhabitatspatial1 += 'ORDER BY "a"."SITECODE";'
        gs.message(sqlhabitatspatial1)
        c.execute(sqlhabitatspatial1)
        # create spatial view of defined habitat - part 2
        sqlhabitatspatial2 = "INSERT INTO views_geometry_columns "
        sqlhabitatspatial2 += "(view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only) "
        sqlhabitatspatial2 += (
            'VALUES ("%s", "geometry", "rowid", "natura2000polygon", "geometry", 1);'
            % (habitat_spatial_view.lower())
        )
        gs.message(sqlhabitatspatial2)
        # execute spatial vieww
        c.execute(sqlhabitatspatial2)
        conn.commit()
        conn.close()
        # import spatial view
        gs.message("importing data...")
        gs.message("may take some time...")
        gs.run_command(
            "v.in.ogr",
            input="%s" % (n2k_input),
            layer="%s" % (habitat_spatial_view),
            output=n2k_output,
            quiet=False,
        )

    if species_code_input:
        gs.message(
            "importing protected areas with species (code): %s" % species_code_input
        )
        gs.message("preparing (spatial) views in the sqlite/spatialite database:")
        conn = db.connect("%s" % n2k_input)
        c = conn.cursor()
        # create view of defined species
        gs.message("view: %s" % species_view)
        sqlspecies = 'CREATE VIEW "%s" AS ' % (species_view)
        sqlspecies += "SELECT * FROM SPECIES "
        sqlspecies += 'WHERE SPECIESCODE = "%s" ' % (species_code_input)
        sqlspecies += 'ORDER BY "SITECODE"'
        gs.message(sqlspecies)
        c.execute(sqlspecies)
        # create spatial view of defined species - part 1
        gs.message("spatial view: %s" % species_spatial_view)
        sqlspeciesspatial1 = 'CREATE VIEW "%s" AS ' % (species_spatial_view)
        sqlspeciesspatial1 += (
            'SELECT "a"."ROWID" AS "ROWID", "a"."PK_UID" AS "PK_UID", '
        )
        sqlspeciesspatial1 += (
            '"a"."SITECODE" AS "SITECODE", "a"."SITENAME" AS "SITENAME", '
        )
        sqlspeciesspatial1 += '"a"."RELEASE_DA" AS "RELEASE_DA", "a"."MS" AS "MS", '
        sqlspeciesspatial1 += (
            '"a"."SITETYPE" AS "SITETYPE", "a"."Geometry" AS "Geometry", '
        )
        sqlspeciesspatial1 += (
            '"b"."COUNTRY_CODE" AS "COUNTRY_CODE", "b"."SITECODE" AS "SITECODE_1", '
        )
        sqlspeciesspatial1 += (
            '"b"."SPECIESNAME" AS "SPECIESNAME", "b"."SPECIESCODE" AS "SPECIESCODE", '
        )
        sqlspeciesspatial1 += (
            '"b"."REF_SPGROUP" AS "REF_SPGROUP", "b"."SPGROUP" AS "SPGROUP", '
        )
        sqlspeciesspatial1 += '"b"."SENSITIVE" AS "SENSITIVE", "b"."NONPRESENCEINSITE" AS "NONPRESENCEINSITE", '
        sqlspeciesspatial1 += '"b"."POPULATION_TYPE" AS "POPULATION_TYPE", "b"."LOWERBOUND" AS "LOWERBOUND", '
        sqlspeciesspatial1 += (
            '"b"."UPPERBOUND" AS "UPPERBOUND", "b"."COUNTING_UNIT" AS "COUNTING_UNIT", '
        )
        sqlspeciesspatial1 += '"b"."ABUNDANCE_CATEGORY" AS "ABUNDANCE_CATEGORY", '
        sqlspeciesspatial1 += (
            '"b"."DATAQUALITY" AS "DATAQUALITY", "b"."POPULATION" AS "POPULATION", '
        )
        sqlspeciesspatial1 += (
            '"b"."CONSERVATION" AS "CONSERVATION", "b"."ISOLATION" AS "ISOLATION", '
        )
        sqlspeciesspatial1 += '"b"."GLOBAL" AS "GLOBAL" '
        sqlspeciesspatial1 += 'FROM "Natura2000polygon" AS "a" '
        sqlspeciesspatial1 += 'JOIN %s AS "b" USING ("SITECODE") ' % (species_view)
        sqlspeciesspatial1 += 'ORDER BY "a"."SITECODE";'
        gs.message(sqlspeciesspatial1)
        c.execute(sqlspeciesspatial1)
        # create spatial view of defined habitat - part 2
        sqlspeciesspatial2 = "INSERT INTO views_geometry_columns "
        sqlspeciesspatial2 += "(view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only) "
        sqlspeciesspatial2 += (
            'VALUES ("%s", "geometry", "rowid", "natura2000polygon", "geometry", 1);'
            % (species_spatial_view.lower())
        )
        gs.message(sqlspeciesspatial2)
        # execute spatial view
        c.execute(sqlspeciesspatial2)
        conn.commit()
        conn.close()
        # import spatial view
        gs.message("importing data...")
        gs.message("may take some time...")
        gs.run_command(
            "v.in.ogr",
            input="%s" % (n2k_input),
            layer="%s" % (species_spatial_view),
            output=n2k_output,
            quiet=False,
        )

    if biogeoreg_long:
        gs.message(
            "importing protected areas of biogeographic region: %s" % biogeoreg_long
        )
        gs.message("preparing (spatial) views in the sqlite/spatialite database:")
        conn = db.connect("%s" % n2k_input)
        c = conn.cursor()
        # create view of defined biogeographic region
        gs.message("view: %s" % biogeoreg_view)
        sqlbioreg = 'CREATE VIEW "%s" AS ' % (biogeoreg_view)
        sqlbioreg += "SELECT * FROM BIOREGION "
        sqlbioreg += 'WHERE BIOGEFRAPHICREG = "%s" ' % (biogeoreg_long)
        sqlbioreg += 'ORDER BY "SITECODE"'
        gs.message(sqlbioreg)
        c.execute(sqlbioreg)
        # create spatial view of defined biogeographical region - part 1
        gs.message("spatial view: %s" % biogeoreg_spatial_view)
        sqlbioregspatial1 = 'CREATE VIEW "%s" AS ' % (biogeoreg_spatial_view)
        sqlbioregspatial1 += 'SELECT "a"."ROWID" AS "ROWID", "a"."PK_UID" AS "PK_UID", '
        sqlbioregspatial1 += '"a"."RELEASE_DA" AS "RELEASE_DA", "a"."MS" AS "MS", '
        sqlbioregspatial1 += (
            '"a"."SITETYPE" AS "SITETYPE", "a"."Geometry" AS "Geometry", '
        )
        sqlbioregspatial1 += '"b"."SITECODE" AS "SITECODE_1", "b"."BIOGEFRAPHICREG" AS "BIOGEFRAPHICREG", '
        sqlbioregspatial1 += '"b"."PERCENTAGE" AS "PERCENTAGE" '
        sqlbioregspatial1 += 'FROM "Natura2000polygon" AS "a" '
        sqlbioregspatial1 += 'JOIN %s AS "b" USING ("SITECODE") ' % (biogeoreg_view)
        sqlbioregspatial1 += 'ORDER BY "a"."SITECODE";'
        gs.message(sqlbioregspatial1)
        c.execute(sqlbioregspatial1)
        # create spatial view of defined biogeographical region - part 2
        sqlbioregspatial2 = "INSERT INTO views_geometry_columns "
        sqlbioregspatial2 += "(view_name, view_geometry, view_rowid, f_table_name, f_geometry_column, read_only) "
        sqlbioregspatial2 += (
            'VALUES ("%s", "geometry", "rowid", "natura2000polygon", "geometry", 1);'
            % (biogeoreg_spatial_view.lower())
        )
        gs.message(sqlbioregspatial2)
        # execute spatial view
        c.execute(sqlbioregspatial2)
        conn.commit()
        conn.close()
        # import spatial view
        gs.message("importing data...")
        gs.message("may take some time...")
        gs.run_command(
            "v.in.ogr",
            input="%s" % (n2k_input),
            layer="%s" % (biogeoreg_spatial_view),
            output=n2k_output,
            quiet=False,
        )

    if layer_exist:
        gs.message("importing existing spatial layer %s of the dataset" % layer_exist)
        gs.run_command(
            "v.in.ogr",
            input="%s" % (n2k_input),
            layer="%s" % (layer_exist),
            output=n2k_output,
            quiet=False,
        )


if __name__ == "__main__":
    options, flags = gs.parser()
    sys.exit(main())
