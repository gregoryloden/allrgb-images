import cv2
import numpy
import heapq

# An attempt to create a color wheel as nice looking as possible. Saturated colors get priority over desaturated colors of the same hue for an exact position.
# 
# General algorithm:
# - Sort by brightness (r + g + b), then by saturation
# - For each brightness, determine the band of squares around the center that those pixels should occupy

#Needs to be an even number
BITS_PER_COLOR = 8

SIDE_LENGTH = 2 ** (BITS_PER_COLOR * 3 // 2)
HALF_SIDE_LENGTH = SIDE_LENGTH // 2
VALUES_PER_COLOR = 2 ** BITS_PER_COLOR
COLOR_MASK = VALUES_PER_COLOR - 1
TOTAL_GB_COLORS = VALUES_PER_COLOR ** 2
TOTAL_COLORS = VALUES_PER_COLOR ** 3
RED_SHIFT = BITS_PER_COLOR * 2
GREEN_SHIFT = BITS_PER_COLOR
BRIGHTEST_COLOR = VALUES_PER_COLOR - 1
TWO_BRIGHTEST = BRIGHTEST_COLOR * 2
MAX_BRIGHTNESS = BRIGHTEST_COLOR * 3
SORT_PROGRESS_INCREMENTS = 32
PLACE_PROGRESS_INCREMENTS = 64
#Adjust hues so that the top-right corner is 0, ranging up to 8, allowing easier comparison operators
#Further adjust it by a super tiny amount (a quarter-pixel at the edge) so that opposite hues round in opposite directions
HUE_ADJUSTMENT_SHIFT = 1 + 0.25 / HALF_SIDE_LENGTH

print("Building base color storage...")
color_datas_by_saturation_by_bright = {}
for bright in range(1, MAX_BRIGHTNESS):
	color_datas_by_saturation = {}
	color_datas_by_saturation_by_bright[bright] = color_datas_by_saturation
	for max_rgb in range(bright // 3 + 1, min(bright, BRIGHTEST_COLOR) + 1):
		for min_rgb in range(max(bright - 2 * max_rgb, 0), (bright - max_rgb) // 2 + 1):
			saturation = (max_rgb - min_rgb) / max_rgb
			if saturation not in color_datas_by_saturation:
				color_datas_by_saturation[saturation] = []
color_datas_by_saturation_by_bright[MAX_BRIGHTNESS] = {None: []}
color_datas_by_saturation_by_bright[0] = {None: []}

print("Building secondary state caches...")
#normalized xy + hue-decrease xy + hue-increase xy
xy_datas_by_hue = {}
for hue_base in range(0, 6):
	for hue_max in range(1, VALUES_PER_COLOR):
		for hue_position in range(0 if hue_max == 1 else 1, hue_max):
			hue = hue_base + hue_position / hue_max
			hue_adjusted = (hue * 8 / 6 + HUE_ADJUSTMENT_SHIFT) % 8
			#top/left leaning
			if hue_adjusted < 4:
				#top leaning
				if hue_adjusted < 2:
					xy_datas_by_hue[hue] = (1 - hue_adjusted, -1, 1, 0, -1, 0)
				#left leaning
				else:
					xy_datas_by_hue[hue] = (-1, hue_adjusted - 3, 0, -1, 0, 1)
			#bottom/right leaning
			else:
				#bottom leaning
				if hue_adjusted < 6:
					xy_datas_by_hue[hue] = (hue_adjusted - 5, 1, -1, 0, 1, 0)
				#right leaning
				else:
					xy_datas_by_hue[hue] = (1, 7 - hue_adjusted, 0, 1, 0, -1)
colors_per_brightness = [1] * (MAX_BRIGHTNESS + 1)
for c_n in range(2, 4):
	c_n_len = c_n * BRIGHTEST_COLOR + 1
	c_i_half_max = c_n * BRIGHTEST_COLOR // 2 + 1
	c = 1
	for c_i in range(1, c_i_half_max):
		c += colors_per_brightness[c_i]
		if c_i >= VALUES_PER_COLOR:
			c -= colors_per_brightness[c_n_len - c_i];
		colors_per_brightness[c_i] = c
	for c_i in range(c_i_half_max, c_n_len):
		colors_per_brightness[c_i] = colors_per_brightness[c_n_len - 1 - c_i]
max_dists_from_center = [None] * (MAX_BRIGHTNESS + 1)
dists_from_center_colors_total = 0
for bright in range(MAX_BRIGHTNESS, -1, -1):
	dists_from_center_colors_total += colors_per_brightness[bright]
	max_dists_from_center[bright] = dists_from_center_colors_total ** 0.5 / 2
min_dists_from_center = max_dists_from_center[1:]
min_dists_from_center.append(0)
xy_has_color = [False] * TOTAL_COLORS
image = numpy.zeros((SIDE_LENGTH, SIDE_LENGTH, 3), numpy.uint8)

print("Sorting colors...")
r_progress_mod = VALUES_PER_COLOR / SORT_PROGRESS_INCREMENTS
for r in range(BRIGHTEST_COLOR, -1, -1):
	for gb in range(TOTAL_GB_COLORS - 1, -1, -1):
		g = (gb >> GREEN_SHIFT) & COLOR_MASK
		b = gb & COLOR_MASK
		bright = r + g + b
		max_rgb = max(r, g, b)
		min_rgb = min(r, g, b)
		if max_rgb == min_rgb:
			#Skip monochrome colors
			continue
		hue_range = max_rgb - min_rgb
		saturation = hue_range / max_rgb
		#red (1): magenta (0) <= value <= yellow (2)
		if r == max_rgb:
			#magenta (0) <= value <= red (1)
			if g == min_rgb:
				hue = (r - b) / hue_range
			#red (1) < value <= yellow (2)
			else:
				hue = (g - b) / hue_range + 1
		#green (3): yellow (2) < value <= cyan (4)
		elif g == max_rgb:
			#yellow (2) < value <= green (3)
			if b == min_rgb:
				hue = (g - r) / hue_range + 2
			#green (3) < value <= cyan (4)
			else:
				hue = (b - r) / hue_range + 3
		#blue (5): cyan (4) < value < magenta (0)
		else:
			#cyan (4) < value <= blue (5)
			if r == min_rgb:
				hue = (b - g) / hue_range + 4
			#blue (5) < value < magenta (0)
			else:
				hue = (r - g) / hue_range + 5
		color_datas_by_saturation_by_bright[bright][saturation].append(((b, g, r), hue))
	if r % r_progress_mod == 0:
		print(f"Sorted {(VALUES_PER_COLOR - r) * TOTAL_GB_COLORS}/{TOTAL_COLORS} colors")
print("Placing colors...")
next_color_datas_to_place_per_saturation = []
placing_color_progress = 0
placing_color_progress_i = 1
for bright in range(MAX_BRIGHTNESS, -1, -1):
	color_datas_to_place_per_saturation = next_color_datas_to_place_per_saturation
	next_color_datas_to_place_per_saturation = sorted(color_datas_by_saturation_by_bright[bright].items())
	color_datas_to_place_per_saturation.append(next_color_datas_to_place_per_saturation.pop())
	color_datas_to_place_per_saturation.reverse()
	min_dist_from_center = min_dists_from_center[bright]
	max_dist_from_center = max_dists_from_center[bright]
	hue_search_cache = {}
	for (_, color_datas_to_place) in color_datas_to_place_per_saturation:
		for (bgr, hue) in color_datas_to_place:
			xy_data = xy_datas_by_hue[hue]
			base_x = xy_data[0] * min_dist_from_center + HALF_SIDE_LENGTH
			base_y = xy_data[1] * min_dist_from_center + HALF_SIDE_LENGTH
			x = int(base_x)
			y = int(base_y)
			xy = y * SIDE_LENGTH + x

#TODO instead of placing colors where they're supposed to go based on angle, calculate based on total colors of that brightness and total hues of that brightness
#just because a hueis "supposed" to go in one place doesn't mean we can fit all the colors in if we put it there
#In a brightness level:
#When picking spots for the hues, place them at the highest brightness first before going to lower brightnesses, but use the same hue throughout (the most saturated version), and only reassign to desaturated versions after all pixels have been placed
#still calculate where the next brightness goes at the edge
#place the next level brightness until only the right number of pixels at the current level remain?

			#Simple placement, the color's target spot hasn't been taken yet
			if not xy_has_color[xy]:
				xy_has_color[xy] = True
				image[y, x] = bgr
				continue
			if hue in hue_search_cache:
				search_data = hue_search_cache[hue]
			else:
				max_x = int(xy_data[0] * max_dist_from_center + HALF_SIDE_LENGTH)
				max_y = int(xy_data[1] * max_dist_from_center + HALF_SIDE_LENGTH)
				search_data = [
					max(abs(max_x - x), abs(max_y - y)), #max distance adds
					0, #last distance adds
					0 #current hue increase/decrease
				]
				hue_search_cache[hue] = search_data
			#TODO keep trying to place the color
	if bright % 3 == 2:
		#TODO place monochrome colors
		pass
	placing_color_progress += colors_per_brightness[bright]
	placing_color_progress_target = placing_color_progress_i * TOTAL_COLORS / SORT_PROGRESS_INCREMENTS
	if placing_color_progress >= placing_color_progress_target:
		print(f"Placed ~{placing_color_progress}/{TOTAL_COLORS} colors")
		placing_color_progress_i += 1

print("Writing file...")
cv2.imwrite("color-wheel-v0.1.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
