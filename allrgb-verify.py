import cv2
import itertools
import sys

COLOR_COUNT = 256 ** 3
xy_has_color = []

def verify(file_name):
	print(f"Loading {file_name}...")
	image = cv2.imread(file_name)

	print(f"Preparing color states...")
	xy_has_color[:] = itertools.repeat(False, COLOR_COUNT)

	print(f"Evaluating {file_name}...")
	for bgr in image.reshape((COLOR_COUNT, 3)):
		color = (bgr[2] << 16) + (bgr[1] << 8) + bgr[0]
		if xy_has_color[color]:
			print(f"Duplicate color {bgr}")
			return
		else:
			xy_has_color[color] = True

	print(f"Verifying {file_name}...")
	for xy_has_color0 in xy_has_color:
		if not xy_has_color0:
			print(f"Missing color {xy_has_color0}")
			return

file_names = sys.argv[1:]
file_name_i = 0
for file_name in file_names:
	verify(file_name)
	file_name_i += 1
	print(f"Done {file_name_i}/{len(file_names)}")

print("Done")
