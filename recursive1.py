import cv2
import numpy

#Needs to be an even number
BITS_PER_COLOR = 8

SIDE_LENGTH = 2 ** (BITS_PER_COLOR * 3 // 2)
TOTAL_COLORS = SIDE_LENGTH * SIDE_LENGTH
PROGRESS_INCREMENTS = 32

print("Building base color storage...")
image = numpy.zeros((SIDE_LENGTH, SIDE_LENGTH, 3), numpy.uint8)

print("Placing colors..")
for y in range(SIDE_LENGTH):
	for x in range(SIDE_LENGTH):
		x_bits = x
		y_bits = y
		shift = 0
		r = 0
		g = 0
		b = 0
		while x_bits | y_bits > 0:
			x_bit_0 = x_bits & 1
			y_bits_01 = y_bits & 3
			if ((y_bits_01 == 1) if x_bit_0 == 0 else (y_bits_01 != 1)):
			#if ((y_bits_01 == 1) if x_bit_0 == 0 else (y_bits_01 != 2)):
				r += 1 << shift
			if ((y_bits_01 == 2) if x_bit_0 == 0 else (y_bits_01 != 2)):
			#if ((y_bits_01 == 2) if x_bit_0 == 0 else (y_bits_01 != 1)):
				g += 1 << shift
			if ((y_bits_01 == 3) if x_bit_0 == 0 else (y_bits_01 != 3)):
			#if ((y_bits_01 == 3) if x_bit_0 == 0 else (y_bits_01 != 0)):
				b += 1 << shift
			y_bit_2 = y_bits & 4
			x_bits_12 = x_bits & 6
			if ((x_bits_12 == 2) if y_bit_2 == 0 else (x_bits_12 != 2)):
			#if ((x_bits_12 == 2) if y_bit_2 == 0 else (x_bits_12 != 4)):
				r += 2 << shift
			if ((x_bits_12 == 4) if y_bit_2 == 0 else (x_bits_12 != 4)):
			#if ((x_bits_12 == 4) if y_bit_2 == 0 else (x_bits_12 != 2)):
				g += 2 << shift
			if ((x_bits_12 == 6) if y_bit_2 == 0 else (x_bits_12 != 6)):
			#if ((x_bits_12 == 6) if y_bit_2 == 0 else (x_bits_12 != 0)):
				b += 2 << shift
			x_bits >>= 3
			y_bits >>= 3
			shift += 2
		image[y, x] = (b, g, r)
	if (y + 1) % (SIDE_LENGTH / PROGRESS_INCREMENTS) == 0:
		progress = (y + 1) * PROGRESS_INCREMENTS // SIDE_LENGTH
		print(f"Placed {(y + 1) * SIDE_LENGTH}/{TOTAL_COLORS} colors ({progress}/{PROGRESS_INCREMENTS})")

print("Writing file...")
cv2.imwrite("recursive1a.png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
print("Done")
