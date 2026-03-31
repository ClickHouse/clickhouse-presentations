import os
import imageio

png_dir = '.'
images = []
for i in range(18):
    file_name = 'merge_{}.svg.png'.format(i)
    if file_name.endswith('.png'):
        file_path = os.path.join(png_dir, file_name)
        for j in range(12):
            images.append(imageio.imread(file_path))
imageio.mimsave('merge.gif', images)