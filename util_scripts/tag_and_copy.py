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
from omero.rtypes import rstring
import omero.scripts as scripts


# This function creates a new dataset and copies to it
# the full resolution images from an AFI fileset. New folder is called
# "CurrentFolderName_userDefinedSuffix".
# The full resolution images are matched by: "image #1".
def copyHighresImages(conn, filesetList, scriptParams):
    updateService = conn.getUpdateService()
    datasetId = 0
    for filesetId in filesetList:
        fileset = conn.getObject("Fileset", filesetId)
        for fsImage in fileset.copyImages():
            # Copy images containing "image #1" string.
            if "image #1" in fsImage.getName():
                # If this is the first image to copy create a new dataset.
                if datasetId == 0:
                    datasetOriginal = conn.getObject(
                        "Dataset", scriptParams["IDs"])
                    project = datasetOriginal.getParent()
                    datasetNew = omero.model.DatasetI()
                    datasetNew.setName(
                        rstring(datasetOriginal.getName()
                                + "_" + scriptParams["Suffix"]))
                    datasetNew =\
                        conn.getUpdateService().saveAndReturnObject(datasetNew)
                    datasetId = datasetNew.getId().getValue()
                    # Link the data to the current Project.
                    link = omero.model.ProjectDatasetLinkI()
                    link.parent = omero.model.ProjectI(project.getId(), False)
                    link.child = omero.model.DatasetI(datasetId, False)
                    updateService.saveObject(link)
                print fsImage.getName()
                # Copy the image to the new dataset.
                link = omero.model.DatasetImageLinkI()
                link.parent = omero.model.DatasetI(datasetId, False)
                link.child = omero.model.ImageI(fsImage.getId(), False)
                updateService.saveObject(link)


# This function loops through the images in the Dataset, creates a list
# of tags for each image and creates a list of unique filesets in the Dataset.
def tagImages(conn, scriptParams):
    datasetId = scriptParams["IDs"]
    print "\nDataset: %s" % datasetId
    dataset = conn.getObject("Dataset", datasetId)
    counter = 1
    filesetList = []
    for image in dataset.listChildren():
        fileset = image.getFileset()

        # Conditions to tag and copy the images:
        # If image does not belog to a fileset - skip
        # (it's not a part of an AFI fileset).
        if fileset is None:
            continue
        # If the fileset does not have exactly 3 images - skip
        # (it's not an AFI filset).
        if len(fileset.copyImages()) == 3:
            continue
        # Do not store duplicates in the fileset list.
        if fileset.getId() not in filesetList:
            filesetList.append(fileset.getId())

        # Create tags based on the Image name.
        # If the Image name is based on the file name,
        # the name and the extension is used to create two tags,
        # e.g 1235_abce.afi will be split into: 1235_abce and afi.
        image_for_tag = omero.model.ImageI(image.getId(), False)
        name = image.getName()
        # Split on '.' to separate name from extension.
        tagList_temp = name.split(".")
        tagList = []
        if len(tagList_temp) > 1:
            # If the file name contains the system path ignore it (unix).
            tag_temp = tagList_temp[0].split("/")
            if len(tag_temp) == 1:
                # If the file name contains
                # system path ignore it (windows).
                tag_temp = tagList_temp[0].split("\\")
            tag_temp = tag_temp[len(tag_temp) - 1]
            tagList.append(tag_temp)

            # If the file has simple extension "name.ext"
            # then use ext as a tag.
            if len(tagList_temp) == 2:
                tag_temp = tagList_temp[1][:3]
                tagList.append(tag_temp)
            # If the file has two term extension "name.ome.tif"
            # then use ome.tif as a tag
            if len(tagList_temp) == 3:
                tag_temp = tagList_temp[1] + "." + tagList_temp[2][:3]
                tagList.append(tag_temp)
        # If the Image name is not based on a file name (name.extension)
        # then use each word as a separte tag.
        if len(tagList_temp) == 1:
            tagList_temp = name.split(" ")
            for tag in tagList_temp:
                tagList.append(tag)
        print counter, "Tags created for: ", image.getName(), tagList
        # Attach the tags to the Image.
        for tag in tagList:
            imageTag = omero.model.TagAnnotationI()
            imageTag.setTextValue(rstring(tag))
            link = omero.model.ImageAnnotationLinkI()
            link.setChild(imageTag)
            link.setParent(image_for_tag)
            conn.getUpdateService().saveAndReturnObject(link)
        counter += 1
    # Copy full resolution images to a saparate Dataset.
    copyHighresImages(conn, filesetList, scriptParams)
    message = "DONE"
    return message

if __name__ == "__main__":
    global datasetId
    dataTypes = [rstring('Dataset')]
    client = scripts.client(
        'Tag_and_copy_full_res.py',
        """
        This script tags images in the dataset using their name and copies
        full resolution image to the new dataset.
        """,
        scripts.String(
            "Data_Type", optional=False, grouping="1",
            description="Choose source of images (only Dataset supported)",
            values=dataTypes, default="Dataset"),

        scripts.Int(
            "IDs", optional=False, grouping="2",
            description="Dataset to tag and copy images from."),

        scripts.String(
            "Suffix", optional=False, grouping="3",
            description="New dataset suffix.", default="full_res"),

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
        message = tagImages(conn, scriptParams)
        client.setOutput("Message", rstring(message))
    finally:
        client.closeSession()
