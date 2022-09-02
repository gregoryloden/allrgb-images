import cv2
import numpy

#Needs to be an even number
BITS_PER_COLOR = 8

SIDE_LENGTH = 2 ** (BITS_PER_COLOR * 3 // 2)
VALUES_PER_COLOR = 2 ** BITS_PER_COLOR
COLOR_MASK = VALUES_PER_COLOR - 1
TOTAL_BG_COLORS = VALUES_PER_COLOR ** 2
GREEN_SHIFT = BITS_PER_COLOR
SORT_PROGRESS_INCREMENTS = 32

print("Building sorted storage...")
bgrs_by_bright_by_saturation = {}
for max_rgb in range(1, VALUES_PER_COLOR):
	for min_rgb in range(0, max_rgb + 1):
		saturation = (max_rgb - min_rgb) / max_rgb
		if saturation not in bgrs_by_bright_by_saturation:
			bgrs_by_bright = {}
			bgrs_by_bright_by_saturation[saturation] = bgrs_by_bright
		else:
			bgrs_by_bright = bgrs_by_bright_by_saturation[saturation]
		for middle_rgb in range(min_rgb, max_rgb + 1):
			bright = min_rgb + middle_rgb + max_rgb
			if bright not in bgrs_by_bright:
				bgrs_by_bright[bright] = []
print("Sorting colors...")
r_progress_mod = VALUES_PER_COLOR / SORT_PROGRESS_INCREMENTS
for r in range(VALUES_PER_COLOR - 1, -1, -1):
	for i in range(TOTAL_BG_COLORS - 1, -1 if r > 0 else 0, -1):
		g = (i >> GREEN_SHIFT) & COLOR_MASK
		b = i & COLOR_MASK
		bright = r + g + b
		max_rgb = max(r, max(g, b))
		min_rgb = min(r, min(g, b))
		saturation = (max_rgb - min_rgb) / max_rgb
		bgrs_by_bright_by_saturation[saturation][bright].append((b, g, r))
	if r % r_progress_mod == 0:
		print(f"Sorted {VALUES_PER_COLOR - r}/{VALUES_PER_COLOR}")
print("Allocating image...")
image = numpy.zeros((SIDE_LENGTH, SIDE_LENGTH, 3), numpy.uint8)
print("Building image...")
xy = 0
saturation_count = len(bgrs_by_bright_by_saturation)
saturation_progress_mod = saturation_count // SORT_PROGRESS_INCREMENTS
saturation_progress = saturation_count
for (saturation, bgrs_by_bright) in reversed(sorted(bgrs_by_bright_by_saturation.items())):
	for (bright, bgrs) in reversed(sorted(bgrs_by_bright.items())):
		for bgr in bgrs:
			x = xy % SIDE_LENGTH
			y = xy // SIDE_LENGTH
			image[y, x] = bgr
			xy += 1
	saturation_progress -= 1
	if saturation_progress % saturation_progress_mod == 0:
		print(f"Placed {saturation_count - saturation_progress}/{saturation_count} saturations")
print("Writing file...")
cv2.imwrite("saturation-over-brightness.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
