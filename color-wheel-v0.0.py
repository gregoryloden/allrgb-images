import cv2
import numpy

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

print("Building base color storage...")
color_datas_by_bright_by_saturation = {}
for max_rgb in range(1, VALUES_PER_COLOR):
	for min_rgb in range(0, max_rgb + 1):
		saturation = (max_rgb - min_rgb) / max_rgb
		if saturation not in color_datas_by_bright_by_saturation:
			color_datas_by_bright = {}
			color_datas_by_bright_by_saturation[saturation] = color_datas_by_bright
		else:
			color_datas_by_bright = color_datas_by_bright_by_saturation[saturation]
		for middle_rgb in range(min_rgb, max_rgb + 1):
			bright = min_rgb + middle_rgb + max_rgb
			if bright not in color_datas_by_bright:
				color_datas_by_bright[bright] = []

print("Building secondary state caches...")
#Normalized xy + hue-decrease xy + hue-increase xy
xy_datas_by_hue = {}
for hue_base in range(0, 6):
	for hue_max in range(1, VALUES_PER_COLOR):
		for hue_position in range(0 if hue_max == 1 else 1, hue_max):
			hue = hue_base + hue_position / hue_max
			hue_adjusted = (hue * 8 / 6 + 1) % 8
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
#The four corner hues increase and decrease hues on different axes
xy_datas_by_hue[0.75] = (-1, -1, 1, 0, 0, 1)
xy_datas_by_hue[2.25] = (-1, 1, 0, -1, 1, 0)
xy_datas_by_hue[3.75] = (1, 1, -1, 0, 0, -1)
xy_datas_by_hue[5.25] = (1, -1, 0, 1, -1, 0)
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
colors_brighter_than_brightness = [0] * (MAX_BRIGHTNESS + 1)
min_dists_from_center = [None] * (MAX_BRIGHTNESS + 1)
for bright in range(MAX_BRIGHTNESS, 0, -1):
	colors_brighter = colors_brighter_than_brightness[bright]
	colors_brighter_than_brightness[bright - 1] = colors_brighter + colors_per_brightness[bright]
	min_dists_from_center[bright] = colors_brighter ** 0.5 / 2
min_dists_from_center[0] = (TOTAL_COLORS - 1) ** 0.5 / 2
xy_has_color = [False] * TOTAL_COLORS
image = numpy.zeros((SIDE_LENGTH, SIDE_LENGTH, 3), numpy.uint8)

print("Sorting colors...")
r_progress_mod = VALUES_PER_COLOR / SORT_PROGRESS_INCREMENTS
for r in range(VALUES_PER_COLOR - 1, -1, -1):
	for gb in range(TOTAL_GB_COLORS - 1, -1 if r > 0 else 0, -1):
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
		min_dist_from_center = min_dists_from_center[bright]
		xy_data = xy_datas_by_hue[hue]
		x = xy_data[0] * min_dist_from_center + HALF_SIDE_LENGTH
		y = xy_data[1] * min_dist_from_center + HALF_SIDE_LENGTH
		color_datas_by_bright_by_saturation[saturation][bright].append(((b, g, r), (x, y), xy_data))
	if r % r_progress_mod == 0:
		print(f"Sorted {VALUES_PER_COLOR - r}/{VALUES_PER_COLOR}")

print("Placing initial colors...")
color_datas_unplaced = []
saturation_count = len(color_datas_by_bright_by_saturation)
saturation_progress_mod = saturation_count // SORT_PROGRESS_INCREMENTS
saturation_progress = saturation_count
for (saturation, color_datas_by_bright) in reversed(sorted(color_datas_by_bright_by_saturation.items())):
	for (bright, color_datas) in reversed(sorted(color_datas_by_bright.items())):
		min_dist_from_center = min_dists_from_center[bright]
		for color_data in color_datas:
			(x, y) = color_data[1]
			x = int(x)
			y = int(y)
			xy = y * SIDE_LENGTH + x
			if not xy_has_color[xy]:
				xy_has_color[xy] = True
				image[y, x] = color_data[0]
			else:
				color_datas_unplaced.append(color_data)
	saturation_progress -= 1
	if saturation_progress % saturation_progress_mod == 0:
		print(f"Placed {saturation_count - saturation_progress}/{saturation_count} initial saturations")

print("Placing remaining chromatic colors...")
print(f"{len(color_datas_unplaced)} colors remaining")
remaining_pass = 1
remaining_progress_mod = TOTAL_COLORS // SORT_PROGRESS_INCREMENTS
while len(color_datas_unplaced) > 0:
	color_datas_to_place = color_datas_unplaced
	color_datas_unplaced = []
	total_color_datas_to_place = len(color_datas_to_place)
	remaining_progress_increments = (total_color_datas_to_place + remaining_progress_mod - 1) // remaining_progress_mod
	for remaining_progress_increment in range(0, remaining_progress_increments):
		color_datas_to_place_min = \
			total_color_datas_to_place * remaining_progress_increment // remaining_progress_increments
		color_datas_to_place_max = \
			total_color_datas_to_place * (remaining_progress_increment + 1) // remaining_progress_increments
		for color_data_i in range(color_datas_to_place_min, color_datas_to_place_max):
			color_data = color_datas_to_place[color_data_i]
			(base_x, base_y) = color_data[1]
			(normalized_x, normalized_y, hue_decrease_x, hue_decrease_y, hue_increase_x, hue_increase_y) = \
				color_data[2]
			brightness_adjusted_base_x = base_x
			brightness_adjusted_base_y = base_y
			hue_change_dist = remaining_pass
			while True:
				#Try decreasing the hue location
				x = int(brightness_adjusted_base_x + hue_decrease_x * hue_change_dist)
				y = int(brightness_adjusted_base_y + hue_decrease_y * hue_change_dist)
				xy = y * SIDE_LENGTH + x
				if x >= 0 and x < SIDE_LENGTH and y >= 0 and y < SIDE_LENGTH and not xy_has_color[xy]:
					xy_has_color[xy] = True
					image[y, x] = color_data[0]
					break
				#Try increasing the hue location
				x = int(brightness_adjusted_base_x + hue_increase_x * hue_change_dist)
				y = int(brightness_adjusted_base_y + hue_increase_y * hue_change_dist)
				xy = y * SIDE_LENGTH + x
				if x >= 0 and x < SIDE_LENGTH and y >= 0 and y < SIDE_LENGTH and not xy_has_color[xy]:
					xy_has_color[xy] = True
					image[y, x] = color_data[0]
					break
				#Try reducing the brightness location
				brightness_adjusted_base_x += normalized_x
				brightness_adjusted_base_y += normalized_y
				x = int(brightness_adjusted_base_x)
				y = int(brightness_adjusted_base_y)
				xy = y * SIDE_LENGTH + x
				if x >= 0 and x < SIDE_LENGTH and y >= 0 and y < SIDE_LENGTH and not xy_has_color[xy]:
					xy_has_color[xy] = True
					image[y, x] = color_data[0]
					break
				#Stop if we've reached the extent of our search this pass
				elif hue_change_dist == 1:
					color_datas_unplaced.append(color_data)
					break
				hue_change_dist -= 1
		print(f"Placed {color_datas_to_place_max}/{total_color_datas_to_place} colors in pass {remaining_pass}")
	colors_placed_this_pass = total_color_datas_to_place - len(color_datas_unplaced)
	print(f"{colors_placed_this_pass} placed, {len(color_datas_unplaced)} colors remaining")
	if remaining_pass >= 25:
		print("Bailing after 25 passes")
		break
	remaining_pass += 1
#TODO place fallback colors

print("Placing monochrome colors...")
#TODO place monochrome colors

print("Writing file...")
cv2.imwrite("color-wheel-v0.0.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
