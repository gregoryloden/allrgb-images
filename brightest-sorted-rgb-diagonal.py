import cv2
import numpy

#Needs to be an even number
BITS_PER_COLOR = 8

SIDE_LENGTH = 2 ** (BITS_PER_COLOR * 3 // 2)
SIDE_LENGTH_M1 = SIDE_LENGTH - 1
VALUES_PER_COLOR = 2 ** BITS_PER_COLOR
TOTAL_COLORS = VALUES_PER_COLOR ** 3
BRIGHTEST_COLOR = VALUES_PER_COLOR - 1
TWO_BRIGHTEST = BRIGHTEST_COLOR * 2
TOTAL_BRIGHTNESS = BRIGHTEST_COLOR * 3

print("Building image")
image = numpy.zeros((SIDE_LENGTH, SIDE_LENGTH, 3), numpy.uint8)

def iter_gen_pixel():
	for bright in range(0, TOTAL_BRIGHTNESS + 1):
		for r in range(max(bright - TWO_BRIGHTEST, 0), min(bright, BRIGHTEST_COLOR) + 1):
			gb_bright = bright - r
			for g in range(max(gb_bright - BRIGHTEST_COLOR, 0), min(gb_bright, BRIGHTEST_COLOR) + 1):
				yield (gb_bright - g, g, r)

gen_pixel = iter_gen_pixel()
for diagonal in range(0, SIDE_LENGTH_M1 * 2 + 1):
	for x in range(max(0, diagonal - SIDE_LENGTH_M1), min(diagonal + 1, SIDE_LENGTH)):
		image[diagonal - x, x] = next(gen_pixel)

print("Writing file...")
cv2.imwrite("brightest-sorted-rgb-diagonal.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
