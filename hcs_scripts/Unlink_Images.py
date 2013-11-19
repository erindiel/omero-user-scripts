# coding=utf-8
"""
-----------------------------------------------------------------------------
  Copyright (C) 2013 Glencoe Software, Inc. All rights reserved.


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

------------------------------------------------------------------------------

Unlink Images from a given Plate.
"""

import omero
import omero.clients

from omero.rtypes import rlong
from omero.rtypes import rstring

from omero.sys import ParametersI

import omero.scripts as scripts


def run():
    """
    """
    data_types = [rstring("Plate")]

    client = scripts.client(
        "Unlink_Images.py",
        "Unlink Images from a given Plate",

        scripts.String("Data_Type", optional=False, grouping="1",
                       description="The data type you want to work with.",
                       values=data_types,
                       default="Plate"),

        scripts.List("IDs", optional=False, grouping="2",
                     description="List of Plate IDs").ofType(rlong(0)),

        version="0.1",
        authors=["Chris Allan"],
        institutions=["Glencoe Software Inc."],
        contact="support@glencoesoftware.com",
    )

    try:
        script_params = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                script_params[key] = client.getInput(key, unwrap=True)

        session = client.getSession()
        update_service = session.getUpdateService()
        query_service = session.getQueryService()

        count = 0
        for plate_id in script_params["IDs"]:
            params = ParametersI()
            params.addId(plate_id)
            plate = query_service.findByQuery(
                "SELECT p from Plate AS p "
                "LEFT JOIN FETCH p.wells as w "
                "LEFT JOIN FETCH w.wellSamples as ws "
                "WHERE p.id = :id", params)
            for well in plate.copyWells():
                count += well.sizeOfWellSamples()
                well.clearWellSamples()
            update_service.saveObject(plate)

        client.setOutput("Message", rstring(
            "Unlinking of %d Image(s) successful." % count))
    finally:
        client.closeSession()

if __name__ == "__main__":
    run()
