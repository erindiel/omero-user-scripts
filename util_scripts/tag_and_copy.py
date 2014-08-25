#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------------------------------------------
   Copyright (C) 2014 Glencoe Software, Inc. All rights reserved.
------------------------------------------------------------------------------



@author Emil Rozbicki
<a href="mailto:emil@glencoesoftware.com">emil@glencoesoftware.com</a>
@version 0.1
"""

import omero
from omero.gateway import BlitzGateway
from omero.rtypes import rstring
import omero.scripts as scripts


def copyHighresImages(conn, filesetList, scriptParams):
    updateService = conn.getUpdateService()
    datasetId = 0
    for filesetId in filesetList:
        fileset = conn.getObject("Fileset", filesetId)
        for fsImage in fileset.copyImages():
            if 'image #1' in fsImage.getName():
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
                    link = omero.model.ProjectDatasetLinkI()
                    link.parent = omero.model.ProjectI(project.getId(), False)
                    link.child = omero.model.DatasetI(datasetId, False)
                    updateService.saveObject(link)
                print fsImage.getName()
                link = omero.model.DatasetImageLinkI()
                link.parent = omero.model.DatasetI(datasetId, False)
                link.child = omero.model.ImageI(fsImage.getId(), False)
                updateService.saveObject(link)


def tagImages(conn, scriptParams):
    datasetId = scriptParams["IDs"]
    print "\nDataset: %s" % datasetId
    dataset = conn.getObject("Dataset", datasetId)
    counter = 1
    filesetList = []
    for image in dataset.listChildren():
        fileset = image.getFileset()
        if fileset is None:
            continue
        if len(fileset.copyImages()) < 3:
            continue
        if fileset.getId() not in filesetList:
            filesetList.append(fileset.getId())
        image_for_tag = omero.model.ImageI(image.getId(), False)
        name = image.getName()
        tagList_temp = name.split(".")
        tagList = []
        if len(tagList_temp) > 1:
            tag_temp = tagList_temp[0].split("/")
            if len(tag_temp) == 1:
                tag_temp = tagList_temp[0].split("\\")
            tag_temp = tag_temp[len(tag_temp) - 1]
            tagList.append(tag_temp)
            if len(tagList_temp) == 2:
                tag_temp = tagList_temp[1][:3]
                tagList.append(tag_temp)
            if len(tagList_temp) == 3:
                tag_temp = tagList_temp[1] + "." + tagList_temp[2][:3]
                tagList.append(tag_temp)
        if len(tagList_temp) == 1:
            tagList_temp = name.split(" ")
            for tag in tagList_temp:
                tagList.append(tag)
        print counter, "Tags created for: ", image.getName(), tagList
        for tag in tagList:
            imageTag = omero.model.TagAnnotationI()
            imageTag.setTextValue(rstring(tag))
            link = omero.model.ImageAnnotationLinkI()
            link.setChild(imageTag)
            link.setParent(image_for_tag)
            conn.getUpdateService().saveAndReturnObject(link)
        counter += 1
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
            description="Dataset to tag."),

        scripts.String(
            "Suffix", optional=False, grouping="3",
            description="New dataset suffix", default="full_res"),

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
