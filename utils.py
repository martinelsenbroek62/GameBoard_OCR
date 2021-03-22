import cv2,sys
import numpy as np
from PIL import ImageFont, ImageDraw, Image

#font_text = ImageFont.truetype("data/agencyr.ttf", 18)
#font_text = ImageFont.truetype("data/TT Squares Condensed Bold.otf", 13)
font_text = ImageFont.truetype("data/TT Lakes Condensed Bold DEMO.otf", 12)


def _resize_img(img, dx, dy):
	if img.shape[0] == dy and img.shape[1] == dx: return img
	img_pil = Image.fromarray(img)
	img_pil = img_pil.resize((dx, dy), Image.ANTIALIAS)
	img = np.array(img_pil)
	return img


def show(img):
	h,w = img.shape[:2]
	cv2.imshow("img", cv2.resize(img, (w*10,h*10)))
	#img2 = cv2.imread("data/squads_left.png")
	#cv2.imshow("img2", img2)
	img2 = cv2.imread("data/digits/ranked/06.png")
	h,w = img2.shape[:2]
	cv2.imshow("img2", cv2.resize(img2, (w*10,h*10)))
	cv2.waitKey(0)
