#!/usr/bin/env python3
"""
Image-based product classification using JSON data.
Downloads images from URLs and performs classification.
"""
import argparse
import os
import random
import requests
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import hashlib
from PIL import Image
import numpy as np
from json_data_loader import JSONDataLoader

class ImageDownloader:
    """Handles downloading and caching of product images."""
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # Auto-detect the correct path based on current working directory
            if Path("src/images").exists():
                cache_dir = "src/images"
            elif Path("images").exists():
                cache_dir = "images"
            else:
                cache_dir = "images"  # Default to local images folder
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def download_image(self, url: str, product_id: str) -> Optional[str]:
        """
        Download image from URL and save to cache.
        
        Args:
            url: Image URL
            product_id: Product identifier for filename
            
        Returns:
            Path to downloaded image or None if failed
        """
        try:
            # Create filename from URL hash and product ID
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{product_id}_{url_hash}.jpg"
            filepath = self.cache_dir / filename
            
            # Return cached file if exists
            if filepath.exists():
                return str(filepath)
            
            # Download image
            print(f"Downloading image from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Verify it's a valid image
            try:
                with Image.open(filepath) as img:
                    img.verify()
                return str(filepath)
            except Exception:
                filepath.unlink()  # Delete invalid image
                return None
                
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None

class SimpleImageAnalyzer:
    """Simple image analysis without deep learning libraries."""
    
    def __init__(self):
        self.feature_cache = {}
    
    def extract_basic_features(self, image_path: str) -> Dict[str, Any]:
        """
        Extract basic features from image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary of basic image features
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Basic features
                width, height = img.size
                aspect_ratio = width / height
                
                # Convert to numpy array
                img_array = np.array(img)
                
                # Color analysis
                mean_colors = np.mean(img_array, axis=(0, 1))
                std_colors = np.std(img_array, axis=(0, 1))
                
                # Brightness
                brightness = np.mean(img_array)
                
                # Dominant colors (simplified)
                pixels = img_array.reshape(-1, 3)
                dominant_colors = self._get_dominant_colors(pixels)
                
                features = {
                    'width': width,
                    'height': height,
                    'aspect_ratio': aspect_ratio,
                    'mean_r': mean_colors[0],
                    'mean_g': mean_colors[1],
                    'mean_b': mean_colors[2],
                    'std_r': std_colors[0],
                    'std_g': std_colors[1],
                    'std_b': std_colors[2],
                    'brightness': brightness,
                    'dominant_colors': dominant_colors,
                    'total_pixels': width * height
                }
                
                return features
                
        except Exception as e:
            print(f"Error analyzing image {image_path}: {e}")
            return {}
    
    def _get_dominant_colors(self, pixels: np.ndarray, k: int = 5) -> List[Tuple[int, int, int]]:
        """Get dominant colors using simple clustering."""
        # Simple approach: sample pixels and find most common colors
        sample_size = min(1000, len(pixels))
        sample_indices = np.random.choice(len(pixels), sample_size, replace=False)
        sample_pixels = pixels[sample_indices]
        
        # Round colors to reduce precision
        rounded_pixels = (sample_pixels // 32) * 32
        
        # Count unique colors
        unique_colors, counts = np.unique(rounded_pixels, axis=0, return_counts=True)
        
        # Sort by frequency
        sorted_indices = np.argsort(counts)[::-1]
        dominant_colors = []
        
        for i in sorted_indices[:k]:
            color = tuple(unique_colors[i])
            dominant_colors.append(color)
        
        return dominant_colors

def classify_images_from_json(json_file_path: str, categories: Optional[List[str]] = None, 
                             min_products_per_category: int = 1, download_images: bool = True) -> None:
    """
    Perform image-based classification using JSON data.
    
    Args:
        json_file_path: Path to JSON file containing product data
        categories: List of category IDs to classify (None for all suitable categories)
        min_products_per_category: Minimum products required per category
        download_images: Whether to download images or use cached ones
    """
    # Load JSON data
    print(f"Loading data from {json_file_path}...")
    loader = JSONDataLoader(json_file_path)
    loader.print_statistics()
    
    # Get suitable categories if none specified
    if categories is None:
        categories = loader.get_categories_to_predict(min_products_per_category)
        print(f"\nUsing categories with {min_products_per_category}+ products: {categories}")
    
    if not categories:
        print("No suitable categories found for classification.")
        return
    
    # Get products for selected categories
    products = loader.get_products(categories)
    print(f"\nProcessing {len(products)} products from {len(categories)} categories")
    
    # Initialize components
    downloader = ImageDownloader()
    analyzer = SimpleImageAnalyzer()
    
    # Process images
    image_features = []
    product_labels = []
    successful_downloads = 0
    
    print(f"\n=== Image Processing ===")
    
    for i, product in enumerate(products):
        print(f"Processing product {i+1}/{len(products)}: {product['name']}")
        
        if not product['image']:
            print(f"  No image URL available")
            continue
        
        # Download image
        if download_images:
            image_path = downloader.download_image(product['image'], product['id'])
        else:
            # Look for cached image
            url_hash = hashlib.md5(product['image'].encode()).hexdigest()[:8]
            filename = f"{product['id']}_{url_hash}.jpg"
            image_path = downloader.cache_dir / filename
            image_path = str(image_path) if image_path.exists() else None
        
        if not image_path:
            print(f"  Failed to get image")
            continue
        
        # Extract features
        features = analyzer.extract_basic_features(image_path)
        if not features:
            print(f"  Failed to extract features")
            continue
        
        image_features.append(features)
        product_labels.append(product['category_id'])
        successful_downloads += 1
        
        print(f"  ✅ Successfully processed image")
        print(f"     Size: {features['width']}x{features['height']}")
        print(f"     Brightness: {features['brightness']:.1f}")
        print(f"     Dominant colors: {len(features['dominant_colors'])}")
    
    print(f"\n=== Results ===")
    print(f"Successfully processed: {successful_downloads}/{len(products)} images")
    
    if successful_downloads == 0:
        print("No images were successfully processed.")
        return
    
    # Analyze features by category
    print(f"\n=== Feature Analysis by Category ===")
    
    category_features = {}
    for features, label in zip(image_features, product_labels):
        if label not in category_features:
            category_features[label] = []
        category_features[label].append(features)
    
    for category, features_list in category_features.items():
        print(f"\n📊 Category: {category}")
        print(f"   Images: {len(features_list)}")
        
        # Calculate average features
        avg_width = np.mean([f['width'] for f in features_list])
        avg_height = np.mean([f['height'] for f in features_list])
        avg_brightness = np.mean([f['brightness'] for f in features_list])
        avg_aspect_ratio = np.mean([f['aspect_ratio'] for f in features_list])
        
        print(f"   Average size: {avg_width:.0f}x{avg_height:.0f}")
        print(f"   Average aspect ratio: {avg_aspect_ratio:.2f}")
        print(f"   Average brightness: {avg_brightness:.1f}")
        
        # Color analysis
        all_colors = []
        for f in features_list:
            all_colors.extend(f['dominant_colors'])
        
        if all_colors:
            # Find most common colors
            color_counts = {}
            for color in all_colors:
                color_counts[color] = color_counts.get(color, 0) + 1
            
            top_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"   Common colors: {top_colors}")
    
    # Simple classification simulation
    if len(image_features) >= 2 and len(set(product_labels)) >= 2:
        print(f"\n=== Classification Simulation ===")
        
        # Split data
        random.shuffle(list(zip(image_features, product_labels)))
        train_size = max(1, len(image_features) // 2)
        
        train_features = image_features[:train_size]
        train_labels = product_labels[:train_size]
        test_features = image_features[train_size:]
        test_labels = product_labels[train_size:]
        
        print(f"Training on {len(train_features)} images")
        print(f"Testing on {len(test_features)} images")
        
        # Simple distance-based classification
        correct = 0
        total = 0
        
        for test_feat, test_label in zip(test_features, test_labels):
            # Find closest training example
            best_match = None
            best_distance = float('inf')
            
            for train_feat, train_label in zip(train_features, train_labels):
                # Simple distance based on key features
                distance = (
                    abs(test_feat['width'] - train_feat['width']) / 1000 +
                    abs(test_feat['height'] - train_feat['height']) / 1000 +
                    abs(test_feat['brightness'] - train_feat['brightness']) / 100 +
                    abs(test_feat['aspect_ratio'] - train_feat['aspect_ratio'])
                )
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = train_label
            
            predicted = best_match
            actual = test_label
            
            is_correct = predicted == actual
            if is_correct:
                correct += 1
            total += 1
            
            status = "✓" if is_correct else "✗"
            print(f"   {status} Predicted: {predicted}, Actual: {actual} (distance: {best_distance:.3f})")
        
        if total > 0:
            accuracy = correct / total
            print(f"\n   Simple image classification accuracy: {accuracy:.4f} ({correct}/{total})")
    
    print(f"\n💡 Recommendations:")
    print(f"   1. Add more products with images for better classification")
    print(f"   2. Ensure images are high quality and well-lit")
    print(f"   3. Use consistent image styles across categories")
    print(f"   4. Consider using deep learning for more advanced features")

def main():
    """Main function for image classification."""
    parser = argparse.ArgumentParser(
        description="Image-based product classification using JSON data"
    )
    parser.add_argument(
        "--json-file", 
        required=True,
        help="Path to JSON file containing product data"
    )
    parser.add_argument(
        "--categories", 
        help="Comma-separated list of categories to classify. If not specified, all suitable categories are used."
    )
    parser.add_argument(
        "--min-products", 
        type=int, 
        default=1,
        help="Minimum number of products required per category (default: 1)"
    )
    parser.add_argument(
        "--no-download", 
        action="store_true",
        help="Don't download images, use cached ones only"
    )
    
    args = parser.parse_args()
    
    # Parse categories if provided
    categories = None
    if args.categories:
        categories = [cat.strip() for cat in args.categories.split(',')]
    
    try:
        classify_images_from_json(
            json_file_path=args.json_file,
            categories=categories,
            min_products_per_category=args.min_products,
            download_images=not args.no_download
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
