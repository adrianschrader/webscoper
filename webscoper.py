import os.path
import math
import requests
import argparse
import shutil
import numpy as np
from numpy.lib.format import open_memmap
from scipy import misc
from StringIO import StringIO

tilewidth = 250
directory = './tiles'

class CleanDir(argparse.Action):
        nargs = 0
        def __call__(self, parser, namespace, values, option_string=None):
            if (os.path.exists(directory)):
                shutil.rmtree(directory)

parser = argparse.ArgumentParser()
parser.add_argument('title', metavar='title', type=str, help='title of the picture')
parser.add_argument('url', metavar='url', type=str, help='url to download from')
parser.add_argument('-wh', '--width', metavar='width', type=int, default=1000, help='width of the selected image segment')
parser.add_argument('-ht', '--height', metavar='height', type=int, default=1000, help='height of the selected image segment')
parser.add_argument('-xoff', '--xoffset', metavar='xoff', type=int, default=0, help='horizontal offset')
parser.add_argument('-yoff', '--yoffset', metavar='yoff', type=int, default=0, help='vertical offset')
parser.add_argument('-mag', '--magnification', metavar='magnification', type=float, default=40, help='Magnification (only 40,20,10,5,2.5,1). Saves network bandwidth. ')
parser.add_argument('-q', '--quality', metavar='quality', type=int, default=80, help='JPEG Quality. Select 100 for best, 80 for default. ')
parser.add_argument('-f', '--format', metavar='format', type=str, default='jpg', help='Desired format for the resulting image e.g. jpg, tiff, png')
parser.add_argument('--keep', action='store_true', help='Keep the jpg images, not just mmap files')
parser.add_argument('--recycle', action='store_true', help='Do not download things you have already downloaded, recycle images instead.')
parser.add_argument('--clean', action=CleanDir, nargs=0)

args = parser.parse_args()
serverurl = args.url

def ensureDir():
    if not os.path.exists(directory):
        print('Creating temporary directory...')
        os.makedirs(directory)

def getUrl(name, xoff = 0, yoff = 0, width = 500, zoom = 1, quality = 80):
    options = '+'.join([ str(x) for x in [ xoff, yoff, width, width, zoom, quality ] ])
    return serverurl + name + '.svs?' + options

def getFilename(name, x, y):
    return directory + '/' + name + '_' + str(x) + '_' + str(y) + '.'

def downloadImage(filename, url):
    response = requests.get(url)
    if args.keep:
        with open(filename + args.format, 'wb') as code:
            code.write(response.content)

    return misc.imread(StringIO(response.content));

def mergeDimensions(shape1, shape2):
    return (shape1[0] if shape1[0] < shape2[0] else shape2[0], shape1[1] if shape1[1] < shape2[1] else shape2[1], 3)

def recycleResult(name, xtiles, ytiles, zoom):
    os.rename(name + '.npy', name + '.npy.old');
    old_result = np.load(name + '.npy.old', mmap_mode='r')

    result = open_memmap(name + '.npy', dtype='uint8', mode='w+', shape=(ytiles * tilewidth, xtiles * tilewidth, 3))
    copy_dim = mergeDimensions(old_result.shape, result.shape)
    result[0:copy_dim[0], 0:copy_dim[1]] = old_result[0:copy_dim[0], 0:copy_dim[1]]
    print 'result', result.shape
    print 'dopy', copy_dim

    del old_result
    os.remove(name + '.npy.old')
    return (result, int(math.ceil(copy_dim[1] / tilewidth)), int(math.ceil(copy_dim[0] / tilewidth)))

def downloadGrid(name, xstart, ystart, width, height, mag = 40, quality = 80, fileext = 'jpg'):
    if mag < 0.2 or mag > 40:
        print('Default magnification: 1x. See help page for details. ')
        mag = 1
    else:
        print('Magnification: ' + str(mag) + 'x');
    zoom = int(40 / mag)

    xtiles = int(math.ceil(width / zoom / tilewidth))
    ytiles = int(math.ceil(height / zoom / tilewidth))
    xskip = 0
    yskip = 0

    if args.recycle and os.path.exists(name + '.npy'):
        result, xskip, yskip = recycleResult(name, xtiles, ytiles, zoom)
    else:
        result = open_memmap(name + '.npy', dtype='uint8', mode='w+', shape=(ytiles * tilewidth, xtiles * tilewidth, 3))

    print('Downloading ' + str(xtiles * ytiles) + ' grid tiles (skipping ' + str(xskip * yskip) + ')')
    print('from ' + serverurl + name + '.svs')
    total = xtiles * ytiles

    for x in range(0, xtiles):
        xoff = (xstart / zoom) + x * tilewidth

        for y in range(0, ytiles):
            yoff = (ystart / zoom) + y * tilewidth

            if x >= xskip or y >= yskip:
                img = downloadImage(getFilename(name, x, y), getUrl(name, xoff, yoff, tilewidth, zoom, quality))
                result = concatenate(result, img, x, y)
                del img
                print(' + (' + str(y + ytiles * x + 1) + '/' + str(total) + ') complete')
            else:
                print(' - (' + str(y + ytiles * x + 1) + '/' + str(total) + ') skipped')

    print('Download complete...')
    print('Save mosaic image... (raw: ' + str(round(os.path.getsize(name + '.npy') / 1000000.0, 2)) + 'MB)');
    misc.imsave(name + '.' + fileext, result)
    del result

def skipExisting(name, x, y):
    return (os.path.exists(getFilename(name,x,y) + 'mmap') & args.recycle);

def concatenate(result, img, x, y):
    result[(y * tilewidth):((y + 1) * tilewidth), (x * tilewidth):((x + 1) * tilewidth), :] = img
    return result;

if args.keep:
    ensureDir()
downloadGrid(args.title, args.xoffset, args.yoffset, args.width, args.height, args.magnification, args.quality, args.format);
