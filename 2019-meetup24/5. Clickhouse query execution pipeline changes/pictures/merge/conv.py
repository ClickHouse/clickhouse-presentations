import os

for file in os.listdir('.'):
    name = file.split('.svg')[0]
    cairosvg.svg2png(url=name+'.svg',write_to='png/' + name+'.png')