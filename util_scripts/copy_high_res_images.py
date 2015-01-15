# -*- coding: utf-8 -*-
"""
-----------------------------------------------------------------------------
  Copyright (C) 2014 Glencoe Software, Inc. All rights reserved.


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
"""

import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rstring, rlong
import omero.scripts as scripts

import re


class copyHighResImages:

    def __init__(self, conn, scriptParams):
        """
        Class to copy high resolution svs and afi files to the new datasets.
        scriptParams have to include target "Project_ID" and a list of
        source dataset "IDS".

        @param conn: BlitzGateway connector
        @param scriptParams: scipt parameters.
        """

        self.FILENAME_REGEX = re.compile(r'^(\w+-\w+)-.*')
        self.conn = conn
        self.target_project_id = scriptParams["Project_ID"]
        self.source_datasets_list = scriptParams["IDs"]
        self.image_dict = self.getImageList()
        self.target_dataset_names = self.getTargetDatasetNames()
        self.query_service = self.conn.getQueryService()
        self.update_service = self.conn.getUpdateService()
        self.dataset_query = \
            "select d from Project as p" \
            " left outer join p.datasetLinks as links" \
            " left outer join links.child as d" \
            " left outer join fetch d.imageLinks as i_link" \
            " left outer join fetch i_link.child" \
            " where p.id = :pid and d.name = :dname"
        self.image_query = "select i from Image as i" \
                           " join fetch i.datasetLinks as dLinks" \
                           " join fetch dLinks.parent" \
                           " where i.id = :id"

    def getImageList(self):
        """
        Retrive images from the source datasets.
        """

        image_dict = {}
        for datasetId in self.source_datasets_list:
            dataset = conn.getObject("Dataset", datasetId)
            for image in dataset.listChildren():
                if "[" in image.getName():
                    continue
                file_name = self.FILENAME_REGEX.match(image.getName())
                if file_name is None:
                    continue
                image_dict[image.getId()] = file_name.group(1)
        return image_dict

    def printImageList(self):
        for image in self.image_dict:
            print image, self.image_dict[image]

    def getTargetDatasetNames(self):
        """
        Convert image names to target dataset names and return as unique
        list.
        """
        dataset_names = set()
        for image in self.image_dict:
            dataset_names.add(self.image_dict[image])
        return dataset_names

    def getDatasetMap(self):
        """
        Convert unique list of dataset names to a map
        (dataset_name, dataset_object).
        """
        dataset_map = {}
        params = omero.sys.ParametersI()
        params.add("pid", rlong(self.target_project_id))
        for name in self.target_dataset_names:
            params.add("dname", rstring(name))
            dataset = self.query_service.findByQuery(
                self.dataset_query, params)
            if dataset is None:
                print "Creating new datset"
                dataset = omero.model.DatasetI()
                dataset.setName(rstring(name))
                dataset = \
                    self.update_service.saveAndReturnObject(dataset)
                datasetId = dataset.getId().getValue()
                print "New dataset ID: ", datasetId
                link = omero.model.ProjectDatasetLinkI()
                print "Linking dataset to ", self.target_project_id
                link.parent = omero.model.ProjectI(
                    self.target_project_id, False)
                link.child = omero.model.DatasetI(datasetId, False)
                self.update_service.saveObject(link)
                dataset = self.query_service.findByQuery(
                    self.dataset_query, params)
            dataset_map[name] = dataset
        return dataset_map

    def saveImagesToServer(self, dataset_dict):
        """
        Convert dataset hash map to list and save linked images to the server.

        @param dataset_dict: map(dataset_name, dataset_object)
        """
        dataset_list = []
        for dataset_name in dataset_dict:
            dataset_list.append(dataset_dict[dataset_name])
        self.update_service.saveAndReturnArray(dataset_list)

    def copyImages(self):
        """
        Link images to the target datasets.
        """
        dataset_dict = self.getDatasetMap()
        for image_id in self.image_dict:
            dataset_target = dataset_dict[self.image_dict[image_id]]
            image_ids = [
                v.id.val for v in dataset_target.linkedImageList()]
            if image_id in image_ids:
                continue
            print "Coping image: ", image_id, self.image_dict[image_id]
            dataset_target.linkImage(omero.model.ImageI(image_id, False))
        self.saveImagesToServer(dataset_dict)

    def run(self):
        """
        Call this methods after class instantiate to copy the images.
        """
        self.copyImages()
        return "Done"


if __name__ == "__main__":
    global datasetId
    dataTypes = [rstring('Dataset')]
    client = scripts.client(
        'copy_high_res_images.py',
        """
        This script copies the full resolution images to the new dataset.
        """,
        scripts.String(
            "Data_Type", optional=False, grouping="1",
            description="Choose source of images (only Dataset supported)",
            values=dataTypes, default="Dataset"),

        scripts.List(
            "IDs", optional=False, grouping="2",
            description="Dataset to tag and copy images from.").ofType(long),

        scripts.Int(
            "Project_ID", optional=False, grouping="3",
            description="Project ID to create new Dataset in."),

        version="0.1",
        authors=["Emil Rozbicki"],
        institutions=["Glencoe Software Inc."],
        contact="emil@glencoesoftware.com",
    )

    try:
        # process the list of args above.
        scriptParams = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)
        # wrap client to use the Blitz Gateway
        conn = BlitzGateway(client_obj=client)
        processImages = copyHighResImages(conn, scriptParams)
        message = processImages.run()
        client.setOutput("Message", rstring(message))
    finally:
        client.closeSession()
