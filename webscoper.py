import os.path
import math
import requests
import argparse
import shutil
import numpy as np
from numpy.lib.format import open_memmap
from scipy import misc
from StringIO import StringIO

# Parameter action: Clean the kept jpeg files from disk
class CleanDir(argparse.Action):
        nargs = 0
        def __call__(self, parser, namespace, values, option_string=None):
            if (os.path.exists(directory)):
                shutil.rmtree(directory)

# Create and configure parser
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
parser.add_argument('--clean', action=CleanDir, nargs=0, help='Delete the directory created by --keep. Caution!')

# Global variables (There is no reason for them to exist, but
# converting them to parameters or cmd arguments is work)
args = parser.parse_args()
serverurl = args.url
tilewidth = 250
directory = './tiles'

# Create a directory if it does not already exists
def ensureDir():
    if not os.path.exists(directory):
        print('Creating temporary directory...')
        os.makedirs(directory)

# Combines parameters to the source api url. Only works for WebScope
def getUrl(name, xoff = 0, yoff = 0, width = 500, zoom = 1, quality = 80):
    options = '+'.join([ str(x) for x in [ xoff, yoff, width, width, zoom, quality ] ])
    return serverurl + name + '.svs?' + options

# Source api needs a different reprentation of the magnification. Also caps values
def getZoom(mag):
    if mag < 0.2 or mag > 40:
        print('Default magnification: 1x. See help page for details. ')
        mag = 1
    else:
        print('Magnification: ' + str(mag) + 'x');
    return int(40 / mag)

def getFilename(name, x, y):
    return directory + '/' + name + '_' + str(x) + '_' + str(y) + '.'

# Download an image from the source, save in seperate folder if necessary
def downloadImage(filename, url):
    response = requests.get(url)
    if args.keep:
        with open(filename + args.format, 'wb') as code:
            code.write(response.content)

    return misc.imread(StringIO(response.content));

# Search for the common pixels in both shapes, starting at (0, 0)
def mergeDimensions(shape1, shape2):
    return (shape1[0] if shape1[0] < shape2[0] else shape2[0], shape1[1] if shape1[1] < shape2[1] else shape2[1], 3)

# Add the image to the mosaic at the right position
def concatenate(result, img, x, y):
    result[(y * tilewidth):((y + 1) * tilewidth), (x * tilewidth):((x + 1) * tilewidth), :] = img
    return result;

# Load the result from the previous run and set the new dimensions
def recycleResult(name, xtiles, ytiles, zoom):
    # Matrix has to be resized, so we need another array, so there needs to be room, so we have to get rid of stuff.
    os.rename(name + '.npy', name + '.npy.old');
    old_result = np.load(name + '.npy.old', mmap_mode='r')

    # Create a matrix with the right dimensions and copying corresponding data into it
    result = open_memmap(name + '.npy', dtype='uint8', mode='w+', shape=(ytiles * tilewidth, xtiles * tilewidth, 3))
    copy_dim = mergeDimensions(old_result.shape, result.shape)
    result[0:copy_dim[0], 0:copy_dim[1]] = old_result[0:copy_dim[0], 0:copy_dim[1]]
    print 'result', result.shape
    print 'dopy', copy_dim

    # Get rid of old matrix
    del old_result
    os.remove(name + '.npy.old')
    return (result, int(math.ceil(copy_dim[1] / tilewidth)), int(math.ceil(copy_dim[0] / tilewidth)))

def downloadTiles(name, result, xstart, ystart, xtiles, ytiles, xskip, yskip, zoom, quality):
    # Announce job
    print('Downloading ' + str(xtiles * ytiles) + ' grid tiles (skipping ' + str(xskip * yskip) + ')')
    print('from: ' + serverurl + name + '.svs')

    # Iterate over all the tiles
    for x in range(0, xtiles):
        xoff = (xstart / zoom) + x * tilewidth

        for y in range(0, ytiles):
            yoff = (ystart / zoom) + y * tilewidth

            # If the tile does not exist on disk/memory (you can never be sure)
            if x >= xskip or y >= yskip:
                # Download image and add it to the result
                img = downloadImage(getFilename(name, x, y), getUrl(name, xoff, yoff, tilewidth, zoom, quality))
                result = concatenate(result, img, x, y)

                # Get rid of the downloaded image. Clutters memory.
                del img

                # Announce progress. yeah!
                print(' + (' + str(y + ytiles * x + 1) + '/' + str(total) + ') complete')
            else:
                # Announce laziness. yeah!
                print(' - (' + str(y + ytiles * x + 1) + '/' + str(total) + ') skipped')

    # Announe success
    print('Download complete...')
    return result

def download(name, xstart, ystart, width, height, mag = 40, quality = 80, fileext = 'jpg'):
    # Initialize and normalize variables
    zoom = getMag(mag)
    xtiles = int(math.ceil(width / zoom / tilewidth))
    ytiles = int(math.ceil(height / zoom / tilewidth))
    total = xtiles * ytiles
    xskip = 0
    yskip = 0

    # Create memory-based matrix or get one from previous runs
    if args.recycle and os.path.exists(name + '.npy'):
        result, xskip, yskip = recycleResult(name, xtiles, ytiles, zoom)
    else:
        result = open_memmap(name + '.npy', dtype='uint8', mode='w+', shape=(ytiles * tilewidth, xtiles * tilewidth, 3))

    # Create directory if it is not already in place (for tile images only)
    if args.keep:
        ensureDir()

    # Download all missing tiles, skip tiles from previous run
    result = downloadTiles(name, result, xstart, ystart, xtiles, ytiles, xskip, yskip, zoom, quality)

    # Save the stitched image to disk (this coasts a lot of RAM, but I have no idea how to save it without RAM)
    print('Save stitched image... (raw: ' + str(round(os.path.getsize(name + '.npy') / 1000000.0, 2)) + 'MB)');
    misc.imsave(name + '.' + fileext, result)

    # Clear memory and flush all data to disk for next run
    del result

# Download the desired image in small steps. See help for help. 
download(args.title, args.xoffset, args.yoffset, args.width, args.height, args.magnification, args.quality, args.format);
