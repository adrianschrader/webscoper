import os.path
import math
import requests
import argparse
import shutil
import numpy as np
from scipy import misc
from StringIO import StringIO

tilewidth = 250
directory = './tiles'

class CleanDir(argparse.Action):
        nargs = 0
        def __call__(self, parser, namespace, values, option_string=None):
            if (os.path.exists(directory)):
                shutil.rmtree(directory)
            if (os.path.exists('./result.mmap')):
                os.remove('./result.mmap')

parser = argparse.ArgumentParser()
parser.add_argument('title', metavar='title', type=str, help='title of the picture')
parser.add_argument('url', metavar='url', type=str, help='url to download from')
parser.add_argument('-wh', '--width', metavar='width', type=int, default=1000, help='width of the selected image segment')
parser.add_argument('-ht', '--height', metavar='height', type=int, default=1000, help='height of the selected image segment')
parser.add_argument('-xoff', '--xoffset', metavar='xoff', type=int, default=0, help='horizontal offset')
parser.add_argument('-yoff', '--yoffset', metavar='yoff', type=int, default=0, help='vertical offset')
parser.add_argument('-mag', '--magnification', metavar='magnification', type=float, default=40, help='Magnification. Saves network bandwidth. ')
parser.add_argument('-q', '--quality', metavar='quality', type=int, default=80, help='JPEG Quality. Select 100 for best, 80 for default. ')
parser.add_argument('--keep', action='store_true', help='Keep the jpg images, not just mmap files')
parser.add_argument('--recycle', action='store_true', help='Do not download things you have already downloaded, recycle images instead.')
parser.add_argument('--clean', action=CleanDir, nargs=0)

args = parser.parse_args()
serverurl = args.url

def ensureDir():
    if not os.path.exists(directory):
        print('Creating temporary directory...')
        os.makedirs(directory)

def purgeTiles():
    if not args.keep:
        print('!')

def getUrl(name, xoff = 0, yoff = 0, width = 500, zoom = 1, quality = 80):
    options = '+'.join([ str(x) for x in [ xoff, yoff, width, width, zoom, quality ] ])
    return serverurl + name + '.svs?' + options

def getFilename(name, x, y):
    return directory + '/' + name + '_' + str(x) + '_' + str(y) + '.'

def downloadImage(filename, url):
    response = requests.get(url)
    img = np.memmap(filename + 'mmap', dtype='uint8', mode='w+', shape=(tilewidth,tilewidth, 3));
    img[:] = misc.imread(StringIO(response.content))[:];

    if args.keep:
        with open(filename + 'jpg', 'wb') as code:
            code.write(response.content)

    return img;


def downloadGrid(name, xstart, ystart, width, height, mag = 40, quality = 80):
    if (mag not in [40, 20, 10, 5, 2.5, 1]):
        print('Default magnification: 5x. See help page for details. ')
        mag = 5
    else:
        print('Magnification: ' + str(mag) + 'x');
    zoom = int(40 / mag)

    xtiles = int(math.ceil(width / zoom / tilewidth)) + 1
    ytiles = int(math.ceil(height / zoom / tilewidth)) + 1
    result = np.memmap('result.mmap', dtype='uint8', mode='w+', shape=(ytiles * tilewidth, xtiles * tilewidth, 3));

    print('Downloading '+str(xtiles*ytiles)+' grid tiles')
    print('from ' + serverurl + name + '.svs/view.ampl')

    skipped = 0
    total = xtiles * ytiles

    for x in range(0, xtiles):
        xoff = (xstart / zoom) + x * tilewidth

        for y in range(0, ytiles):
            yoff = (ystart / zoom) + y * tilewidth

            if (skipExisting(name, x, y)):
                img = np.memmap(getFilename(name, x, y) + 'mmap', dtype='uint8', mode='r', shape=(tilewidth, tilewidth, 3))
                result = concatenate(result, img, x, y)
                skipped += 1
                print(' - (' + str(y + ytiles * x + 1) + '/' + str(total) + ') skipped')
            else:
                img = downloadImage(getFilename(name, x, y), getUrl(name, xoff, yoff, tilewidth, zoom, quality))
                result = concatenate(result, img, x, y)

                print(' - (' + str(y + ytiles * x + 1) + '/' + str(total) + ') complete')

    print('Download complete... (total: ' + str(total) + ', skipped: ' + str(skipped) + ', downloaded: ' + str(total - skipped) + ')')
    print('Save mosaic image... (' + str(os.path.getsize('result.mmap') / 1000000) + 'MB)');
    misc.imsave('result.jpg', result);

def skipExisting(name, x, y):
    return (os.path.exists(getFilename(name,x,y) + 'mmap') & args.recycle);

def concatenate(result, img, x, y):
    result[(y * tilewidth):((y + 1) * tilewidth), (x * tilewidth):((x + 1) * tilewidth), :] = img
    return result;


ensureDir()
downloadGrid(args.title, args.xoffset, args.yoffset, args.width, args.height, args.magnification, args.quality);
