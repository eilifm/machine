from subprocess import Popen
from tempfile import mkdtemp
from os.path import realpath, join, basename, splitext, exists
from shutil import copy, move, rmtree
from logging import getLogger
import json

from . import paths

def cache(srcjson, destdir, bucketname='openaddresses'):
    ''' Python wrapper for openaddress-cache.
    
        Return a dictionary of cache details, including URL and md5 hash:
        
          {
            "cache": URL of cached data,
            "fingerprint": md5 hash of data,
            "version": data version as date?
          }
    '''
    source, _ = splitext(basename(srcjson))
    workdir = mkdtemp(prefix='cache-')
    logger = getLogger('openaddr')

    # Work on a copy of source JSON
    tmpjson = join(workdir, basename(srcjson))
    copy(srcjson, tmpjson)

    #
    # Run openaddresses-cache from a fresh working directory.
    #
    errpath = join(destdir, source+'-cache.stderr')
    outpath = join(destdir, source+'-cache.stdout')

    with open(errpath, 'w') as stderr, open(outpath, 'w') as stdout:
        index_js = join(paths.cache, 'index.js')
        cmd_args = dict(cwd=workdir, stderr=stderr, stdout=stdout)

        logger.debug('openaddresses-cache {0} {1}'.format(tmpjson, workdir))

        cmd = Popen(('node', index_js, tmpjson, workdir, bucketname), **cmd_args)
        cmd.wait()

        with open(join(destdir, source+'-cache.status'), 'w') as file:
            file.write(str(cmd.returncode))

    logger.debug('{0} --> {1}'.format(source, workdir))

    with open(tmpjson) as file:
        data = json.load(file)
        
    rmtree(workdir)

    return dict(cache=data.get('cache', None),
                fingerprint=data.get('fingerprint', None),
                version=data.get('version', None))

def conform(srcjson, destdir, extras, bucketname='openaddresses'):
    ''' Python wrapper for openaddresses-conform.

        Return a dictionary of conformed details, a CSV URL and local path:
        
          {
            "processed": URL of conformed CSV,
            "path": Local filesystem path to conformed CSV
          }
    '''
    source, _ = splitext(basename(srcjson))
    workdir = mkdtemp(prefix='conform-')
    logger = getLogger('openaddr')

    #
    # Work on a copy of source JSON, with cache URL grafted in.
    #
    tmpjson = join(workdir, basename(srcjson))

    with open(srcjson, 'r') as src_file, open(tmpjson, 'w') as tmp_file:
        data = json.load(src_file)
        data.update(extras)
        json.dump(data, tmp_file)

    #
    # Run openaddresses-conform from a fresh working directory.
    #
    # It tends to error silently and truncate data if it finds any existing
    # data. Also, it wants to be able to write a file called ./tmp.csv.
    #
    errpath = join(destdir, source+'-conform.stderr')
    outpath = join(destdir, source+'-conform.stdout')

    with open(errpath, 'w') as stderr, open(outpath, 'w') as stdout:
        index_js = join(paths.conform, 'index.js')
        cmd_args = dict(cwd=workdir, stderr=stderr, stdout=stdout)

        logger.debug('openaddresses-conform {0} {1}'.format(tmpjson, workdir))

        cmd = Popen(('node', index_js, tmpjson, workdir, bucketname), **cmd_args)
        cmd.wait()

        with open(join(destdir, source+'-conform.status'), 'w') as file:
            file.write(str(cmd.returncode))

    logger.debug('{0} --> {1}'.format(source, workdir))

    #
    # Move resulting files to destination directory.
    #
    zip_path = join(destdir, source+'.zip')
    csv_path = join(destdir, source+'.csv')
    
    if exists(join(workdir, source+'.zip')):
        move(join(workdir, source+'.zip'), zip_path)
        logger.debug(zip_path)

    if exists(join(workdir, source, 'out.csv')):
        move(join(workdir, source, 'out.csv'), csv_path)
        logger.debug(csv_path)

    with open(tmpjson) as file:
        data = json.load(file)
        
    rmtree(workdir)

    return dict(processed=data.get('processed', None),
                path=(realpath(csv_path) if exists(csv_path) else None))