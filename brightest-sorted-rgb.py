import cv2
import numpy

#Needs to be an even number
BITS_PER_COLOR = 8

SIDE_LENGTH = 2 ** (BITS_PER_COLOR * 3 // 2)
VALUES_PER_COLOR = 2 ** BITS_PER_COLOR
TOTAL_COLORS = VALUES_PER_COLOR ** 3
BRIGHTEST_COLOR = VALUES_PER_COLOR - 1
TWO_BRIGHTEST = BRIGHTEST_COLOR * 2
TOTAL_BRIGHTNESS = BRIGHTEST_COLOR * 3

print("Building image...")
image = numpy.zeros((SIDE_LENGTH, SIDE_LENGTH, 3), numpy.uint8)
xy = 0
for bright in range(TOTAL_BRIGHTNESS, 0, -1):
	for r in range(min(bright, BRIGHTEST_COLOR), max(bright - TWO_BRIGHTEST, 0) - 1, -1):
		gb_bright = bright - r
		for g in range(min(gb_bright, BRIGHTEST_COLOR), max(gb_bright - BRIGHTEST_COLOR, 0) - 1, -1):
			b_bright = gb_bright - g
			for b in range(min(b_bright, BRIGHTEST_COLOR), max(b_bright, 0) - 1, -1):
				x = xy % SIDE_LENGTH
				y = xy // SIDE_LENGTH
				image[y, x] = [b, g, r]
				xy += 1
print("Writing file...")
cv2.imwrite("brightest-sorted-rgb.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
