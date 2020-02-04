#! /usr/bin/python
#
# doi2nerdm -- resolve a DOI to its metadata and convert it to a NERDm object
#
from __future__ import print_function
import os, sys, json
from argparse import ArgumentParser, Namespace

from nistoar.nerdm.convert import DOIResolver
from nistoar.doi import DOIDoesNotExist, DOIResolutionException

defconfig = {
    "app_name": "NIST Public Data Repository: admin (oar-metadata)",
    "app_url":  "https://data.nist.gov/",
    "email": "datasupport@nist.gov"
}

description = \
"""convert DOI metadata to NERDm metadata"""

epilog = None

def define_opts(progname):
    progname = os.path.basename(progname)
    if progname.endswith(".py"):
        progname = progname[:len(progname)-3]
    parser = ArgumentParser(progname, None, description, epilog)

    parser.add_argument("doi", metavar="DOI", type=str,
                        help="the DOI to resolve")
    parser.add_argument("-a", "--as-authors", dest='out_type', const='authors',
                        action="store_const", default='reference',
                        help="create a NERDm author listing of the authors associated with the given DOI")
    parser.add_argument("-C", "--config-file", dest="config_file",
                        action="store", default=None,
                        help="load the DOI resolver data from the given JSON file")
    parser.add_argument("-c", "--compact-output", dest="pretty",
                        action="store_false", default=True,
                        help="print output JSON data in a compact form (i.e. not pretty)")
    parser.add_argument("-m", "--merge", dest="merge_input", metavar="FILENAME",
                        action="store", default=None,
                        help="merge converted metadata into the NERDm resource record read from the named file; use '-' to read from stardard input")
    parser.add_argument("-s", "--silent", dest="silent", action="store_true",
                        default=False,
                        help="print nothing to standard output or standard error")
    parser.add_argument("-q", "--quiet", dest="quiet", action="store_true",
                        default=False,
                        help="suppress error messages on standard error")

    return parser

class FatalAppError(Exception):
    def __init__(self, message, exitval=8):
        super(FatalAppError, self).__init__(message);
        self.exval = exitval

class ProgCtrl(Namespace):
    def __init__(self, progname):
        self.prog = progname
    def fail(self, message, exitval):
        msg = "{0}: {1}".format(self.prog, message);
        if not self.quiet:
            print(msg, file=sys.stderr)
        raise FatalAppError(msg, exitval)

def main(args):
    parser = define_opts(args[0])
    opts = parser.parse_args(args[1:], ProgCtrl(parser.prog))

    resolver = create_resolver(opts.config_file);

    out = None
    if opts.merge_input:
        try:
            if opts.merge_input == "-":
                # read from stdin
                out = json.load(sys.stdin)

            else:
                with open(opts.merge_input) as fd:
                    out =json.load(fd)
        except IOError as ex:
            opts.fail("Problem reading resource document: "+str(ex), 4);
        except ValueError as ex:
            opts.fail("Problem parsing input JSON data: "+str(ex), 3);

    converted = None
    try: 
        if opts.out_type == 'authors':
            converted = resolver.to_authors(opts.doi)
        else:
            converted = resolver.to_reference(opts.doi)
    except DOIDoesNotExist as ex:
        opts.fail(str(ex), 1)
    except DOIResolutionException as ex:
        opts.fail("Problem resolving DOI: "+str(ex), 2)

    if out:
        if opts.out_type == 'authors':
            out['authors'] = converted
        else:
            if 'references' not in out:
                out['references'] = []
            out['references'].append(converted)
    else:
        out = converted

    if not opts.silent:
        indent = (opts.pretty and 4) or None
        try:
            json.dump(out, sys.stdout, indent=indent)
        except TypeError as ex:
            opts.fail("Problem exporting JSON: "+ex(str), 5);

def create_resolver(config):
    cfg = dict(defconfig)
    if config:
        cfg.update(config)
    try:
        from nistoar.doi.version import __version__ as v
    except ImportError as ex:
        v = "unknown"
    cfg['app_version'] = v
    return DOIResolver.from_config(cfg)

if __name__ == '__main__':
    try:
        main(sys.argv)
        sys.exit(0)
    except FatalAppError as ex:
        sys.exit(ex.exval);



