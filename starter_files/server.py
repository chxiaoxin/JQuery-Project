from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from urlparse import urlparse, parse_qs

import urllib, urllib2
import shutil
import json
import uuid
import re

# in-memory entries database for simplicity
entries = []

class ExtendedHTTPHandler(SimpleHTTPRequestHandler):
  """
  Serves files in the local directory. Allows CRUD operations on entries.
  """
  PUT_PATH_REGEX = re.compile(r'/entries/([^/]+)$')
  DELETE_PATH_REGEX = re.compile(r'/entries/([^/]+)/delete$')

  def __init__(self, *args, **kwargs):
    """
    Creates an ExtendedHTTPHandler that serves entries.
    """
    SimpleHTTPRequestHandler.__init__(self, *args, **kwargs)

  def do_GET(self):
    """
    Handles GET requests.
    """
    if self.path == '/entries':
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps(entries))
    else:
      # let SimpleHTTPRequestHandler serve static files
      return SimpleHTTPRequestHandler.do_GET(self)

  def entry_index_by_id(self, entry_id):
    """
    Returns the entry that has the given id, or None if no such entry exists.
    """
    for index, entry in enumerate(entries):
      if entry['id'] == entry_id:
        return index
    return None

  def validate_entry_data(self, data):
    """
    Validates that the given data is in the form of an entry.
    """
    name = data.get('name')
    address = data.get('address')
    description = data.get('description')

    # name, address, and description must be non-empty strings
    if (not isinstance(name, basestring) or
        not isinstance(address, basestring) or
        not isinstance(description, basestring) or
        name == '' or address == '' or description == ''):
      self.send_response(422)
      self.send_header('Content-type', 'text/plain')
      self.end_headers()

      error = 'Must provide a valid name, address, and description.'
      self.wfile.write(error)
      return False

    return True

  def validate_entry_id(self, entry_id):
    """
    Validates that the given entry_id is valid.
    """
    # id must correspond to an entry
    if (not isinstance(entry_id, basestring) or
        self.entry_index_by_id(entry_id) is None):
      self.send_response(422)
      self.send_header('Content-type', 'text/plain')
      self.end_headers()

      error = 'Must provide a valid string id that refers to an entry.'
      self.wfile.write(error)
      return False

    return True

  def do_POST(self):
    """
    Handles POST requests.
    """
    is_post = self.path == '/entries'
    is_put = bool(self.PUT_PATH_REGEX.match(self.path))
    is_delete = bool(self.DELETE_PATH_REGEX.match(self.path))

    if is_post or is_put or is_delete:
      valid = True

      if is_post or is_put:
        # read entry from request body
        length = int(self.headers.getheader('content-length', 0))
        try:
          data = json.loads(self.rfile.read(length))
        except ValueError:
          self.send_response(422)
          self.send_header('Content-type', 'text/plain')
          self.end_headers()

          error = 'Must provide a valid JSON body.'
          self.wfile.write(error)
          return

        # must validate all entry fields
        valid = valid and self.validate_entry_data(data)

      # for put and delete, must validate id
      if is_put:
        entry_id = self.PUT_PATH_REGEX.match(self.path).group(1)
        valid = valid and self.validate_entry_id(entry_id)

      if is_delete:
        entry_id = self.DELETE_PATH_REGEX.match(self.path).group(1)
        valid = valid and self.validate_entry_id(entry_id)

      if valid:
        self.send_response(200)
        self.end_headers()

        # perform appropriate action
        if is_post:
          entry = {
            'id': str(uuid.uuid4()),
            'name': data['name'],
            'address': data['address'],
            'description': data['description'],
          }

          entries.append(entry)
          self.wfile.write(json.dumps(entry))
        elif is_put:
          entry = {
            'id': entry_id,
            'name': data['name'],
            'address': data['address'],
            'description': data['description'],
          }

          index = self.entry_index_by_id(entry_id)
          entries[index] = entry
          self.wfile.write(json.dumps(entry))
        else:  # delete path
          index = self.entry_index_by_id(entry_id)
          entries.pop(index)

          success = {'success': True}
          self.wfile.write(json.dumps(success))
    else:
      return SimpleHTTPRequestHandler.do_POST(self)


# server on 0.0.0.0:8000
try:
  server = HTTPServer(('0.0.0.0', 8000), ExtendedHTTPHandler)
  print 'Serving on 127.0.0.1:8000'
  server.serve_forever()
except KeyboardInterrupt:
  server.socket.close()
