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


def get_dataset_list(conn, projectId):
    project = conn.getObject("Project", projectId)
    datasetList = {}
    for dataset in project.listChildren():
        dataset.getName()
        datasetList[dataset.getName()] = dataset.getId()
    return datasetList


# Get dataset name from image name.
def format_image_name(fileName):
    name = fileName.split("-")[0] + "-" + fileName.split("-")[1]
    return name


# This function creates a new dataset and copies to it
# the full resolution images from an AFI fileset. New folder is called
# "CurrentFolderName_userDefinedSuffix".
# The full resolution images are matched by: "image #1".
def copyHighresImages(conn, filesetList, scriptParams):
    updateService = conn.getUpdateService()
    datasetId = 0
    project = conn.getObject("Project", scriptParams["Project_ID"])
    datasetList = get_dataset_list(conn, scriptParams["Project_ID"])
    for filesetId in filesetList:
        fileset = conn.getObject("Fileset", filesetId)
        for fsImage in fileset.copyImages():
            # Copy full resolution image, which does not contain "[]"
            imageName = fsImage.getName()
            if "[" not in imageName:
                newDatasetName = format_image_name(imageName)
                # If the dataset does not exist in the specified Project_ID
                # create new dataset and add to the list
                if newDatasetName not in datasetList:
                    datasetNew = omero.model.DatasetI()
                    datasetNew.setName(rstring(newDatasetName))
                    datasetNew =\
                        conn.getUpdateService().saveAndReturnObject(datasetNew)
                    datasetId = datasetNew.getId().getValue()
                    link = omero.model.ProjectDatasetLinkI()
                    link.parent = omero.model.ProjectI(project.getId(), False)
                    link.child = omero.model.DatasetI(datasetId, False)
                    updateService.saveObject(link)
                    datasetList["newDatasetName"] = datasetId
                else:
                    datasetId = datasetList["newDatasetName"]
                # If this is the first image to copy create a new dataset.
                print fsImage.getName()
                # Copy the image to the new dataset.
                link = omero.model.DatasetImageLinkI()
                link.parent = omero.model.DatasetI(datasetId, False)
                link.child = omero.model.ImageI(fsImage.getId(), False)
                updateService.saveObject(link)


# This function loops through the images in the Dataset, creates a list
# of tags for each image and creates a list of unique filesets in the Dataset.
def tagImages(conn, dataset, scriptParams):
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
        if len(fileset.copyImages()) != 3:
            continue

        # Create tags based on the Image name.
        # If the Image name is based on the file name,
        # the name and the extension is used to create two tags,
        # e.g 1235_abce.afi will be split into: 1235_abce and afi.
        imageForLink = omero.model.ImageI(image.getId(), False)
        name = image.getName()
        # Split on '.' to separate name from extension.
        tagListTemp = name.split(".")
        tagList = []

        # Current Tag List -> to avoid adding the same tag  more then once.
        currentTagList = []
        for tag in image.listAnnotations():
            try:
                currentTagList.append(tag.getTextValue())
            except:
                pass

        if len(tagListTemp) > 1:
            # If the file name contains the system path ignore it (unix).
            tagTemp = tagListTemp[0].split("/")
            if len(tagTemp) == 1:
                # If the file name contains
                # system path ignore it (windows).
                tagTemp = tagListTemp[0].split("\\")
            tagTemp = tagTemp[len(tagTemp) - 1]
            if tagTemp not in currentTagList:
                tagList.append(tagTemp)

            # If the file has a simple extension "name.ext"
            # then use ext as a tag.
            if len(tagListTemp) == 2:
                tagTemp = tagListTemp[1][:3]
                if tagTemp not in currentTagList:
                    tagList.append(tagTemp)
            # If the file has two term extension "name.ome.tif"
            # then use ome.tif as a tag
            if len(tagListTemp) == 3:
                tagTemp = tagListTemp[1] + "." + tagListTemp[2][:3]
                if tagTemp not in currentTagList:
                    tagList.append(tagTemp)
        # If the Image name is not based on a file name (name.extension)
        # then use each word as a separte tag.
        if len(tagListTemp) == 1:
            tagListTemp = name.split(" ")
            for tag in tagListTemp:
                if tag in currentTagList:
                    continue
                tagList.append(tag)
        print counter, "Tags created for: ", image.getName(), tagList,\
            currentTagList
        # Attach the tags to the Image.

        if len(tagList) == 0:
            print counter, "Skipping: ", image.getName()
            counter += 1
            continue
        counter += 1

        # Do not store duplicates in the fileset list.
        if fileset.getId() not in filesetList:
            filesetList.append(fileset.getId())

        for tag in tagList:
            imageTag = omero.model.TagAnnotationI()
            imageTag.setTextValue(rstring(tag))
            link = omero.model.ImageAnnotationLinkI()
            link.setChild(imageTag)
            link.setParent(imageForLink)
            conn.getUpdateService().saveAndReturnObject(link)
    # Copy full resolution images to a saparate Dataset.
    copyHighresImages(conn, filesetList, scriptParams)
    message = "DONE"
    return message


# This function loops through the datasets.
def tagDatasets(conn, scriptParams):
    for datasetId in scriptParams["IDs"]:
        print "\nDataset: %s" % datasetId
        dataset = conn.getObject("Dataset", datasetId)
        tagImages(conn, dataset, scriptParams)
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

        scripts.Int(
            "Project_ID", optional=False, grouping="2",
            description="Project ID to create new Dataset in."),

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
        message = tagDatasets(conn, scriptParams)
        client.setOutput("Message", rstring(message))
    finally:
        client.closeSession()
