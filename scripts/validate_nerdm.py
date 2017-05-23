#!/usr/bin/python
#
# A script that will validate a nerdm record
#
from __future__ import print_function

import os, sys
from ejsonschema.cli import validate

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
oarpypath = os.path.join(basedir, "python")
if 'OAR_HOME' in os.environ:
    basedir = os.environ['OAR_HOME']

schemadir = os.path.join(basedir, 'etc', 'schemas')
if not os.path.exists(schemadir):
    schemadir = os.path.join(basedir, 'model')

prog = os.path.basename(sys.argv[0])
if not prog or prog == 'python':
    prog = "validate_nerdm"
if sys.argv[0] == 'python':
    sys.argv.pop(0)

if '-L' not in sys.argv and '--schema-location' not in sys.argv and \
   os.path.exists(schemadir):
    sys.argv[1:1] = "-L {0}".format(schemadir).split()
if '-M' not in sys.argv and '--mongodb-safe' not in sys.argv and \
   '--val-prop-prefix' not in sys.argv:
    sys.argv[1:1] = ["-M"]

runner = validate.Validate(prog)

sys.exit(runner.execute())
