# webscoper
Downloads images of histological samples in full quality from Leica's WebScope Flashapplet.

## Dependencies
```bash
pip install numpy scipy pillow
```

## Help Page
```output
usage: script.py [-h] [-wh width] [-ht height] [-xoff xoff] [-yoff yoff]
                 [-mag magnification] [-q quality] [--keep] [--recycle]
                 title url

positional arguments:
  title                 title of the picture
  url                   url to download from

optional arguments:
  -h, --help            show this help message and exit
  -wh width, --width width
                        width of the selected image segment
  -ht height, --height height
                        height of the selected image segment
  -xoff xoff, --xoffset xoff
                        horizontal offset
  -yoff yoff, --yoffset yoff
                        vertical offset
  -mag magnification, --magnification magnification
                        Magnification. Saves network bandwidth.
  -q quality, --quality quality
                        JPEG Quality. Select 100 for best, 80 for default.
  --keep                Keep the jpg images, not just mmap files
  --recycle             Do not download things you have already downloaded,
                        recycle images instead.
```

## Usage
```bash
python webscoper.py K03 http://129.206.229.111/HeiCuMed/Histo/

python webscoper.py K03 http://129.206.229.111/HeiCuMed/Histo/ -xoff 0 -yoff 0 --width 82000 --height 27000 --mag 2.5 --keep

python script.py K03 http://129.206.229.111/HeiCuMed/Histo/ -xoff 40000 -yoff 5500 --width 7000 --height 5000 --mag 40 --recycle
```
