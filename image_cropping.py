import cv2
import numpy as np
import os

temp_frame_folder = "temp_frame_storage"
frames = os.listdir(temp_frame_folder)
print(f"{frames = }")

for frame in frames:
    frame_path = os.path.join(temp_frame_folder, frame)
    img = cv2.imread(frame_path)
    cv2.imshow("img", img)
    print(f"Cropping {frame_path = }")
    cropped_image = img[713:img.shape[0], 50:img.shape[1]-50]
    cv2.imshow("cropped_image", cropped_image)

cv2.waitKey(0)

# closing all open windows
cv2.destroyAllWindows()
