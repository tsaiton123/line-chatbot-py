import cv2
import numpy as np

def transform_papers_to_squares(image_path, output_dir, min_area=1000, max_area_ratio=0.9):
    # Load the image
    image = cv2.imread(image_path)
    original = image.copy()
    image_height, image_width = image.shape[:2]
    max_area = image_height * image_width * max_area_ratio  # Define max area as a ratio of the image size
    
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur and edge detection
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    # Find contours in the edge-detected image
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # List to store file paths of the transformed images
    transformed_image_paths = []
    
    # Sort contours by area and process each valid quadrilateral
    valid_count = 0
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        
        # Filter based on area
        if area < min_area or area > max_area:
            continue  # Ignore too small or too large contours
        
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Only process contours with four points (quadrilateral)
        if len(approx) == 4:
            # Check if the contour is convex
            if not cv2.isContourConvex(approx):
                continue
            
            # Get the corner points of the quadrilateral
            points = approx.reshape(4, 2)
            
            # Create a consistent order of points (top-left, top-right, bottom-right, bottom-left)
            def order_points(pts):
                rect = np.zeros((4, 2), dtype="float32")
                s = pts.sum(axis=1)
                rect[0] = pts[np.argmin(s)]
                rect[2] = pts[np.argmax(s)]
                diff = np.diff(pts, axis=1)
                rect[1] = pts[np.argmin(diff)]
                rect[3] = pts[np.argmax(diff)]
                return rect
            
            rect = order_points(points)
            
            # Determine the width and height of the new transformed image
            (tl, tr, br, bl) = rect
            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            maxWidth = max(int(widthA), int(widthB))
            
            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)
            maxHeight = max(int(heightA), int(heightB))
            
            # Check aspect ratio
            aspect_ratio = float(maxWidth) / float(maxHeight)
            if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                continue  # Ignore quadrilaterals with strange aspect ratios
            
            # Define the destination points for the perspective transform
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]], dtype="float32")
            
            # Compute the perspective transform matrix and apply it
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(original, M, (maxWidth, maxHeight))
            
            # Save each valid quadrilateral to a file in the /tmp directory
            output_image_path = f"{output_dir}/transformed_{valid_count+1}.jpg"
            cv2.imwrite(output_image_path, warped)
            transformed_image_paths.append(output_image_path)
            valid_count += 1
            
    return transformed_image_paths
