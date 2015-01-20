# coding=utf-8
'''
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

Edit the attributes of an object.
'''

import omero
import omero.clients
assert omero

from omero.rtypes import rstring, rtype, rtime, rdouble

import omero.scripts as scripts


def run():
    '''
    '''
    client = scripts.client(
        'Edit_Object_Attribute.py',
        'Edit the attributes of an object',

        scripts.String('Data_Type', optional=False, grouping='1',
                       description='The data type you want to work with.'),

        scripts.Long('ID', optional=False, grouping='2',
                     description='Object ID'),

        scripts.String('Attribute', optional=False, grouping='3',
                       description='Attribute to set'),

        scripts.String('Attribute_Type', optional=False, grouping='4',
                       description='Type of the attribute to set',
                       values=[
                           rstring('Bool'), rstring('Double'),
                           rstring('Float'), rstring('Int'),
                           rstring('Long'), rstring('Time'),
                           rstring('String')
                       ], default='String'),

        scripts.String('Value', optional=False, grouping='5',
                       description='Value to set'),

        version='0.1',
        authors=['Chris Allan'],
        institutions=['Glencoe Software Inc.'],
        contact='support@glencoesoftware.com',
    )

    try:
        script_params = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                script_params[key] = client.getInput(key, unwrap=True)

        session = client.getSession()
        update_service = session.getUpdateService()
        query_service = session.getQueryService()

        value = script_params['Value']
        if script_params['Attribute_Type'] == 'Bool':
            value = rtype(bool(value))
        elif script_params['Attribute_Type'] == 'Double':
            value = rdouble(float(value))
        elif script_params['Attribute_Type'] == 'Float':
            value = rtype(float(value))
        elif script_params['Attribute_Type'] == 'Int':
            value = rtype(int(value))
        elif script_params['Attribute_Type'] == 'Long':
            value = rtype(long(value))
        elif script_params['Attribute_Type'] == 'Time':
            value = rtime(long(value))
        else:
            value = rtype(value)

        ctx = {'omero.group': '-1'}
        o = query_service.get(
            script_params['Data_Type'], script_params['ID'], ctx)
        setattr(o, script_params['Attribute'], value)
        ctx = None
        try:
            ctx = {'omero.group': str(o.details.group.id.val)}
        except AttributeError:
            pass
        update_service.saveObject(o, ctx)

        client.setOutput('Message', rstring(
            'Setting of attribute successful.'))
    finally:
        client.closeSession()

if __name__ == '__main__':
    run()
