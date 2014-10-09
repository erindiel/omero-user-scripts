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

import os
from os import listdir
from os.path import isfile, join
import os.path
import subprocess


def create_csv_list(plateId, directory):
    plate = conn.getObject("Plate", plateId)
    list = []
    header = ['ImageNumber', 'Row', 'Column', 'Field', 'Name', 'URL_DNA']
    list.append(header)
    counter = 1
    print 'In'
    for well in plate.listChildren():
        index = well.countWellSample()
        print 'Found ', index
        for index in xrange(0, index):
            print index
            list.append([])
            list[counter].append(counter)
            list[counter].append(well.getRow())
            list[counter].append(well.getColumn())
            list[counter].append(index)
            list[counter].append(well.getImage(index).getName())
            list[counter].append(
                'omero:iid=' + str(well.getImage(index).getId()))
            counter += 1
            print counter

    import csv
    filePath = os.path.join(directory, 'image_list.csv')
    myfile = open(filePath, 'wb')
    wr = csv.writer(myfile)
    for row in list:
        wr.writerow(row)
    myfile.close()
    return filePath


def get_pipeline_file(conn, plateId, fileId, directory):
    file_path = os.path.join(directory, 'pipe.cppipe')
    plate = conn.getObject("Plate", plateId)
    for ann in plate.listAnnotations():
        if isinstance(ann, omero.gateway.FileAnnotationWrapper):
            print "File ID:", ann.getFile().getId(), ann.getFile().getName(),\
                "Size:", ann.getFile().getSize()
            if (ann.getFile().getId() == int(fileId)):
                f = open(str(file_path), 'w')
                try:
                    for chunk in ann.getFileInChunks():
                        f.write(chunk)
                finally:
                    f.close()
    return file_path


def upload_result(conn, plateId, filePath):
    plate = conn.getObject("Plate", plateId)
    namespace = str(plateId) + ".cell_profiler.results"
    fileAnn = conn.createFileAnnfromLocalFile(
        filePath, mimetype="text/plain", ns=namespace, desc=None)
    plate.linkAnnotation(fileAnn)


def clean_directory(directory):
    for root, dirs, files in os.walk(directory):
        for f in files:
            os.unlink(os.path.join(root, f))


def process_plate(conn, scriptParams):
    directory = '/Users/emilrozbicki/cell_profiler/'
    clean_directory(directory)
    #session conn.getSession().getUuid().getValue()
    cell_profiler_dir = '/Users/emilrozbicki/git/CellProfiler/'
    omeroIdsFilePath = create_csv_list(scriptParams['IDs'], directory)
    cpPipeFilePath = get_pipeline_file(
        conn, scriptParams['IDs'], scriptParams['file_Id'], directory)
    outputPath = os.path.join(directory, 'result.mat')
    print omeroIdsFilePath
    print cpPipeFilePath
    print outputPath
    admin = conn.getAdminService()
    string = 'python ' + cell_profiler_dir + 'CellProfiler.py ' + '-r -c' \
        + ' --omero-credentials ' + 'host=localhost,port=4064,'\
        + 'session-id=' + admin.getEventContext().sessionUuid\
        + ' -p ' + cpPipeFilePath + ' --data-file=' + omeroIdsFilePath \
        + ' -o ' + directory + ' ' + outputPath
    subprocess.call(string, shell=True)
    filesAfter = [f for f in listdir(directory) if isfile(join(directory, f))]
    for fileName in filesAfter:
        if '.cppipe' not in fileName:
            print 'Uploading', fileName
            filePath = os.path.join(directory, fileName)
            upload_result(conn, scriptParams['IDs'], filePath)
    message = "DONE"
    return message


if __name__ == "__main__":
    global datasetId
    dataTypes = [rstring('Plate')]
    client = scripts.client(
        'Analyse_plate_with_Cell_Profiler.py',
        """
        This script tags images in the dataset using their name and copies
        full resolution image to the new dataset.
        """,
        scripts.String(
            "Data_Type", optional=False, grouping="1",
            description="Choose source of images (only Plate supported)",
            values=dataTypes, default="Plate"),

        scripts.Int(
            "IDs", optional=False, grouping="2",
            description="Plate to process."),

        scripts.String(
            "file_Id", optional=False, grouping="3",
            description="File holding cp pipeline"),

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
        message = process_plate(conn, scriptParams)
        client.setOutput("Message", rstring(message))
    finally:
        client.closeSession()
