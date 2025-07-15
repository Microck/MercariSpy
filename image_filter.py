#!/usr/bin/env python3.9
import requests
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple
from logging_config import get_logger


class ImageFilter:
    """
    Provides image-based filtering for Mercari product images.
    Filters out images with solid colored or low-quality backgrounds.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger("ImageFilter")
        
        # Filtering parameters
        self.background_color_threshold = config["filtering"]["background_color_threshold"]
        self.max_solid_color_ratio = config["filtering"]["max_solid_color_ratio"]
        self.enabled = config["filtering"]["background_filter_enabled"]
    
    def _download_image(self, image_url: str) -> Optional[np.ndarray]:
        """
        Download and convert image to RGB array.
        
        Args:
            image_url: URL of the image to download
            
        Returns:
            RGB numpy array or None if download fails
        """
        try:
            if not image_url:
                return None
                
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Open image with PIL
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert to numpy array
            np_image = np.array(img)
            
            return np_image
            
        except Exception as e:
            self.logger.debug(f"Failed to download/process image: {e}")
            return None
    
    def _calculate_background_ratio(self, image: np.ndarray) -> float:
        """
        Calculate the ratio of solid/dull background to total image.
        
        Algorithm:
        1. Identify background pixels (edges + similar colors)
        2. Calculate ratio of background pixels to total pixels
        
        Args:
            image: RGB numpy array (H x W x 3)
            
        Returns:
            float: Background ratio (0.0 to 1.0)
        """
        try:
            if len(image.shape) != 3 or image.shape[2] != 3:
                return 0.0
            
            height, width, _ = image.shape
            total_pixels = height * width
            
            # Sample pixels from the edges (border area)
            border_width = max(1, min(width // 10, height // 10, 20))
            
            # Create mask for border pixels
            border_pixels = []
            
            # Top and bottom borders
            for w in range(width):
                for h in range(border_width):
                    border_pixels.append(image[h, w])
                    border_pixels.append(image[height-1-h, w])
            
            # Left and right borders
            for h in range(border_width, height - border_width):
                for w in range(border_width):
                    border_pixels.append(image[h, w])
                    border_pixels.append(image[h, width-1-w])
            
            border_pixels = np.array(border_pixels)
            
            # Calculate dominant color in border
            border_color = np.mean(border_pixels, axis=0)
            
            # Calculate color variance in border
            color_threshold = 30  # Color difference threshold
            border_variance = np.std(border_pixels, axis=0)
            avg_variance = np.mean(border_variance)
            
            # If low variance in border, consider it solid background
            is_solid_background = avg_variance < 20
            
            # Count pixels close to border color
            color_diff = np.linalg.norm(image - border_color, axis=2)
            background_pixels = np.sum(color_diff < color_threshold)
            
            # Calculate ratio
            background_ratio = background_pixels / total_pixels
            
            # Handle edge case where solid color takes over
            if is_solid_background and background_ratio < 0.1:
                background_ratio = 0.1  # Force minimum background
            
            return float(background_ratio)
            
        except Exception as e:
            self.logger.debug(f"Error calculating background ratio: {e}")
            return 0.0
    
    def _is_low_quality(self, image: np.ndarray) -> bool:
        """
        Check if image is low quality (blurry, low resolution).
        
        Args:
            image: RGB numpy array
            
        Returns:
            bool: True if image is low quality
        """
        try:
            height, width, _ = image.shape
            
            # Check minimum resolution
            if height < 100 or width < 100:
                return True
            
            # Calculate image sharpness (Laplacian variance)
            gray = np.dot(image[...,:3], [0.2989, 0.5870, 0.1140])
            
            # Simple edge detection
            laplacian = np.abs(np.gradient(gray)[0]) + np.abs(np.gradient(gray)[1])
            sharpness = laplacian.var()
            
            # Threshold for sharpness (tuned for Mercari images)
            sharpness_threshold = 1000
            
            return sharpness < sharpness_threshold
            
        except Exception as e:
            self.logger.debug(f"Error checking image quality: {e}")
            return False
    
    def _has_solid_color_background(self, image: np.ndarray) -> bool:
        """
        Check if image has a solid color background.
        
        Args:
            image: RGB numpy array
            
        Returns:
            bool: True if image has solid background
        """
        try:
            if not self.enabled:
                return False
            
            background_ratio = self._calculate_background_ratio(image)
            
            # If background ratio exceeds threshold, consider it solid
            passes_filter = background_ratio > self.max_solid_color_ratio
            
            self.logger.debug(
                f"Background filter: {background_ratio:.2f} vs threshold {self.max_solid_color_ratio}, "
                f"result: {'BLOCKED' if passes_filter else 'PASSED'}"
            )
            
            return passes_filter
            
        except Exception as e:
            self.logger.debug(f"Error checking solid background: {e}")
            return False
    
    def filter_background(self, image_url: str) -> bool:
        """
        Main filtering method to determine if an image should be included.
        
        Args:
            image_url: URL of the product image
            
        Returns:
            bool: True if image passes filtering, False otherwise
        """
        try:
            if not self.enabled:
                return True  # Pass all images if filtering is disabled
            
            # Download and process image
            image = self._download_image(image_url)
            if image is None:
                # If we can't download/process, allow the image
                return True
            
            # Check image quality first
            if self._is_low_quality(image):
                self.logger.debug("Image filtered: low quality")
                return False
            
            # Check for solid background
            solid_background = self._has_solid_color_background(image)
            if solid_background:
                self.logger.debug("Image filtered: solid background detected")
                return False
            
            # All checks passed
            return True
            
        except Exception as e:
            self.logger.warning(f"Error in background filtering: {e}")
            # On error, allow the image
            return True
    
    def analyze_image(self, image_url: str) -> Optional[dict]:
        """
        Analyze image properties for debugging and fine-tuning.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            dict: Analysis results
        """
        try:
            image = self._download_image(image_url)
            if image is None:
                return None
            
            height, width, _ = image.shape
            background_ratio = self._calculate_background_ratio(image)
            low_quality = self._is_low_quality(image)
            solid_background = self._has_solid_color_background(image)
            
            return {
                "url": image_url,
                "dimensions": {"width": width, "height": height},
                "background_ratio": background_ratio,
                "is_low_quality": low_quality,
                "has_solid_background": solid_background,
                "passes_filter": not low_quality and not solid_background
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing image: {e}")
            return None


if __name__ == "__main__":
    import json
    
    # Test the image filter
    with open("config.json", 'r') as f:
        config = json.load(f)
    
    # Enable filtering for testing
    config["filtering"]["background_filter_enabled"] = True
    
    image_filter = ImageFilter(config)
    
    # Test URLs (sample Mercari product images)
    test_urls = [
        "https://static.mercdn.net/item/detail/orig/photos/m123456789_1.jpg",
        "https://static.mercdn.net/item/detail/orig/photos/m987654321_1.jpg"
    ]
    
    for url in test_urls:
        print(f"\nAnalyzing: {url}")
        result = image_filter.analyze_image(url)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("Failed to analyze image")