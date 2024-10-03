import cv2
import numpy
import itertools
import math

# Similar algorithm as https://allrgb.com/color-wheel-v2 , but going top-down instead of inside-outward
#
# - Brightest colors at the top
# - An even distribution of hues and saturations are selected when there are more than enough for the current row
# - Prominent rays are visible along hues with multiple saturations

#Needs to be an even number
BITS_PER_COLOR = 8

SIDE_LENGTH = 2 ** (BITS_PER_COLOR * 3 // 2)
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

print("Building base color storage and secondary state caches...")
color_datas_by_hue_by_bright = {}
for bright in range(MAX_BRIGHTNESS + 1):
	color_datas_by_hue_by_bright[bright] = {}
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
		color_datas_by_hue = color_datas_by_hue_by_bright[bright]
		if hue in color_datas_by_hue:
			color_datas_by_hue[hue].append((saturation, (b, g, r)))
		else:
			color_datas_by_hue[hue] = [(saturation, (b, g, r))]
	if r % r_progress_mod == 0:
		print(f"Sorted {(VALUES_PER_COLOR - r) * TOTAL_GB_COLORS}/{TOTAL_COLORS} colors")

print("Placing colors...")
placing_progress = 0
placing_progress_i = 1
last_placed_brightness = MAX_BRIGHTNESS
color_datas_to_place_by_hue = {}
ordered_colors_to_place = []
offsets_per_hue = []
monochromes = []
unplaced_color_datas_by_hue = {}
unplaced_ordered_hues = []
add_counts_by_hue = {}
for band_num in range(1, SIDE_LENGTH + 1):
	band_size = SIDE_LENGTH
	color_datas_to_place_by_hue.clear()
	color_datas_to_place_count = 0
	monochromes.clear()
	#Determine which colors we're going to place in this band
	while True:
		band_available_space_count = band_size - color_datas_to_place_count - len(monochromes)
		if band_available_space_count == 0:
			break
		#First things first - backfill with any unplaced colors
		#If we have more colors than available spaces, pick an even distribution of hues
		if len(unplaced_ordered_hues) > band_available_space_count:
			#Pick an even distribution of hues from our unplaced colors
			next_hue_pick_i = 0
			colors_picked_so_far = 0
			unplaced_ordered_hues_len = len(unplaced_ordered_hues)
			add_counts_by_hue.clear()
			for unplaced_ordered_hue_i in range(unplaced_ordered_hues_len):
				if unplaced_ordered_hue_i == next_hue_pick_i:
					hue = unplaced_ordered_hues[unplaced_ordered_hue_i]
					add_counts_by_hue[hue] = add_counts_by_hue.get(hue, 0) + 1
					colors_picked_so_far += 1
					next_hue_pick_i = \
						colors_picked_so_far * unplaced_ordered_hues_len // band_available_space_count
				else:
					unplaced_ordered_hues[unplaced_ordered_hue_i - colors_picked_so_far] = \
						unplaced_ordered_hues[unplaced_ordered_hue_i]
			del unplaced_ordered_hues[-band_available_space_count:]
			#For each count per hue, pick the most saturated color, and a selection of less-saturated colors
			#	evenly distributed across the saturation range for that color
			for (hue, add_count) in add_counts_by_hue.items():
				unplaced_color_datas = unplaced_color_datas_by_hue[hue]
				unplaced_color_datas_len = len(unplaced_color_datas)
				#Add all the colors, we don't need to find specific colors
				if add_count == unplaced_color_datas_len:
					if hue in color_datas_to_place_by_hue:
						color_datas_to_place_by_hue[hue].extend(unplaced_color_datas)
					else:
						color_datas_to_place_by_hue[hue] = unplaced_color_datas
					del unplaced_color_datas_by_hue[hue]
				#Pull add_count colors at even intervals so that we get a mix of saturated and
				#	less-saturated colors
				else:
					if hue in color_datas_to_place_by_hue:
						color_datas_to_place = color_datas_to_place_by_hue[hue]
					else:
						color_datas_to_place = []
						color_datas_to_place_by_hue[hue] = color_datas_to_place
					#Add them from back to front (most- to least-saturated) so that array indices remain the
					#	same as we remove from the list
					for add_i in range(add_count, 0, -1):
						color_datas_to_place.append(
							unplaced_color_datas.pop(
								add_i * unplaced_color_datas_len // add_count - 1))
			color_datas_to_place_count += band_available_space_count
			break
		#If we have enough colors to use them all up, do so
		elif len(unplaced_ordered_hues) > 0:
			for (hue, color_datas) in unplaced_color_datas_by_hue.items():
				if hue in color_datas_to_place_by_hue:
					color_datas_to_place_by_hue[hue].extend(color_datas)
				else:
					color_datas_to_place_by_hue[hue] = color_datas
			color_datas_to_place_count += len(unplaced_ordered_hues)
			unplaced_color_datas_by_hue.clear()
			unplaced_ordered_hues.clear()
			continue
		#If we get here, we've used up all chromatic colors of the most recent brightness and we still need to place
		#	more colors in this band
		#Monochrome colors get added after all other colors of their brightness
		if last_placed_brightness % 3 == 0:
			monochromes.append(last_placed_brightness // 3)
			#Black is the last color
			if last_placed_brightness == 0:
				break
		#Collect all colors of the next brightness, sorted by hue, but don't add them now; we'll do that next loop
		last_placed_brightness -= 1
		for (hue, color_datas) in sorted(color_datas_by_hue_by_bright[last_placed_brightness].items()):
			#Saturation is the first element in a color data, so the most saturated colors will be at the end
			unplaced_color_datas_by_hue[hue] = sorted(color_datas)
			unplaced_ordered_hues.extend(itertools.repeat(hue, len(color_datas)))
	#Resize the colors list to hold all the colors
	colors_list_resize_amount = color_datas_to_place_count - len(ordered_colors_to_place)
	if colors_list_resize_amount > 0:
		ordered_colors_to_place.extend(itertools.repeat(None, colors_list_resize_amount))
		offsets_per_hue.extend(itertools.repeat(None, colors_list_resize_amount))
	elif colors_list_resize_amount < 0:
		del ordered_colors_to_place[colors_list_resize_amount:]
		del offsets_per_hue[colors_list_resize_amount:]
	#Insert the hues in order into the colors list
	offset_total = 0
	offset_raw_total = 0
	ordered_color_i = 0
	for (hue, color_datas_to_place) in sorted(color_datas_to_place_by_hue.items()):
		for _ in range(len(color_datas_to_place)):
			offset = ordered_color_i - (hue * color_datas_to_place_count / 6) + 0.5
			offset_raw_total += offset
			offset_total += abs(offset)
			offsets_per_hue[ordered_color_i] = offset
			ordered_colors_to_place[ordered_color_i] = hue
			ordered_color_i += 1
	#Insert space for monochrome colors if applicable
	for _ in range(len(monochromes)):
		#Calculate the best position that shifts the most hues closest to their ideal position
		new_offset_total = offset_total
		offset_best_total = offset_total
		monochrome_best_i = color_datas_to_place_count
		for monochrome_i in range(color_datas_to_place_count - 1, -1, -1):
			offset = offsets_per_hue[monochrome_i]
			#Monochrome colors don't have an offset
			if offset is None:
				continue
			new_offset_total += abs(offset + 1) - abs(offset)
			if new_offset_total <= offset_best_total \
					and (monochrome_i == 0 \
						or ordered_colors_to_place[monochrome_i] \
							!= ordered_colors_to_place[monochrome_i - 1]):
				offset_best_total = new_offset_total
				monochrome_best_i = monochrome_i
		#Move and update the offsets before inserting Nones for monochrome colors
		offset_raw_total += color_datas_to_place_count - monochrome_i
		offsets_per_hue.append(None)
		for offset_i in range(color_datas_to_place_count, monochrome_i, -1):
			old_offset = offsets_per_hue[offset_i - 1]
			offsets_per_hue[offset_i] = old_offset + 1 if old_offset else None
		offsets_per_hue[monochrome_i] = None
		ordered_colors_to_place.insert(monochrome_i, None)
	#Replace hues with colors
	color_i = 0
	while color_i < band_size:
		hue = ordered_colors_to_place[color_i]
		if hue is None:
			monochrome = monochromes.pop(0)
			ordered_colors_to_place[color_i] = (monochrome, monochrome, monochrome)
			color_i += 1
			continue
		color_datas_to_place = color_datas_to_place_by_hue[hue]
		if len(color_datas_to_place) == 1:
			ordered_colors_to_place[color_i] = color_datas_to_place[0][1]
			color_i += 1
		else:
			#Mix different brightnesses together so that they're all sorted by saturation
			color_datas_to_place.sort()
			color_i_next = color_i
			color_i_min = color_i
			color_i_max = color_i + len(color_datas_to_place) - 1
			#Go inward from both edges placing the least saturated colors first, so that the most saturated colors
			#	go in the middle
			for color_data in color_datas_to_place:
				ordered_colors_to_place[color_i_next] = color_data[1]
				if color_i_next == color_i_min:
					color_i_next = color_i_max
					color_i_min += 1
				else:
					color_i_next = color_i_min
					color_i_max -= 1
			color_i += len(color_datas_to_place)
	#Rotate the colors list left if applicable;
	offset_average = offset_raw_total / band_size
	if offset_average > 0.5:
		#Rotate the list left
		offset_shift = math.ceil(offset_average - 0.5)
		values_to_place_at_end = ordered_colors_to_place[:offset_shift]
		for color_i in range(len(ordered_colors_to_place) - offset_shift):
			ordered_colors_to_place[color_i] = ordered_colors_to_place[color_i + offset_shift]
		ordered_colors_to_place[-offset_shift:] = values_to_place_at_end
	elif offset_average < -0.5:
		#We should never need to rotate the list right
		raise RuntimeError(f"Tried to rotate the colors list right by {-offfset_average}")
	#Add all the colors in the colors list to the image, starting with the first magenta-range pixel
	#We track the position of the next pixel, and advance it to the next position each loop for each section of the band
	color_y = band_num - 1
	for color_i in range(band_size):
		image[color_y, color_i] = ordered_colors_to_place[color_i]
	placing_progress += band_size
	if placing_progress >= placing_progress_i * TOTAL_COLORS / PLACE_PROGRESS_INCREMENTS:
		print(
			f"Placed {placing_progress}/{TOTAL_COLORS} colors ({band_num}/{SIDE_LENGTH} bands," +
			f" {placing_progress_i}/{PLACE_PROGRESS_INCREMENTS})")
		placing_progress_i += 1

print("Writing file...")
cv2.imwrite("hue-over-brightness-descending.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
