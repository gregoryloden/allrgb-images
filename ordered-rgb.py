import cv2
import numpy

#Needs to be an even number
BITS_PER_COLOR = 8

SIDE_LENGTH = 2 ** (BITS_PER_COLOR * 3 // 2)
VALUES_PER_COLOR = 2 ** BITS_PER_COLOR
COLOR_MASK = VALUES_PER_COLOR - 1
TOTAL_COLORS = VALUES_PER_COLOR ** 3
RED_SHIFT = BITS_PER_COLOR * 2
GREEN_SHIFT = BITS_PER_COLOR

print("Building image...")
image = numpy.zeros((SIDE_LENGTH, SIDE_LENGTH, 3), numpy.uint8)
for i in range(0, TOTAL_COLORS):
	r = (i >> RED_SHIFT) & COLOR_MASK
	g = (i >> GREEN_SHIFT) & COLOR_MASK
	b = i & COLOR_MASK
	x = i % SIDE_LENGTH
	y = i // SIDE_LENGTH
	image[y, x] = [b, g, r]
print("Writing file...")
cv2.imwrite("ordered-rgb.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
