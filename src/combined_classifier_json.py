#!/usr/bin/env python3
"""
Combined text + image product classification using JSON data.
Uses both textual and visual features for enhanced classification.
"""
import argparse
import os
import random
import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import hashlib
from collections import Counter, defaultdict
from PIL import Image
import requests
from json_data_loader import JSONDataLoader

class CombinedFeatureExtractor:
    """Extracts both textual and visual features from products."""
    
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
        self.text_features_cache = {}
        self.image_features_cache = {}
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by removing HTML tags and non-alphanumeric characters."""
        text = re.sub(r'<[^>]+>', ' ', text.lower())
        return re.sub(r'[^a-z0-9 ]', '', text)
    
    def extract_text_features(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract textual features from product."""
        # Combine name and description
        text = self.normalize_text(product['name'] + ' ' + product['description'])
        words = text.split()
        
        # Basic text features
        features = {
            'word_count': len(words),
            'char_count': len(text),
            'avg_word_length': np.mean([len(word) for word in words]) if words else 0,
            'unique_words': len(set(words)),
            'text_density': len(words) / max(len(text), 1),
        }
        
        # Word frequency features
        word_freq = Counter(words)
        features['most_common_word'] = word_freq.most_common(1)[0][0] if word_freq else ''
        features['most_common_freq'] = word_freq.most_common(1)[0][1] if word_freq else 0
        
        # Category-specific keywords
        category_keywords = {
            'bag': ['bag', 'purse', 'handbag', 'tote', 'clutch', 'satchel'],
            'shoe': ['shoe', 'boot', 'sandal', 'sneaker', 'heel', 'flat'],
            'dress': ['dress', 'gown', 'frock', 'maxi', 'mini', 'midi'],
            'jewelry': ['ring', 'necklace', 'bracelet', 'earring', 'pendant'],
            'accessory': ['belt', 'scarf', 'hat', 'watch', 'sunglasses'],
            'pillbox': ['pillbox', 'minaudiere', 'crystal', 'evening']
        }
        
        # Count category-specific words
        for category, keywords in category_keywords.items():
            count = sum(word_freq.get(keyword, 0) for keyword in keywords)
            features[f'{category}_keywords'] = count
        
        # Material keywords
        material_keywords = ['leather', 'silk', 'cotton', 'wool', 'crystal', 'gold', 'silver', 'brass']
        features['material_keywords'] = sum(word_freq.get(mat, 0) for mat in material_keywords)
        
        # Color keywords
        color_keywords = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple', 'brown', 'gray']
        features['color_keywords'] = sum(word_freq.get(color, 0) for color in color_keywords)
        
        return features
    
    def download_image(self, url: str, product_id: str) -> Optional[str]:
        """Download image from URL and save to cache."""
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{product_id}_{url_hash}.jpg"
            filepath = self.cache_dir / filename
            
            if filepath.exists():
                return str(filepath)
            
            print(f"Downloading image from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Verify it's a valid image
            try:
                with Image.open(filepath) as img:
                    img.verify()
                return str(filepath)
            except Exception:
                filepath.unlink()
                return None
                
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None
    
    def extract_image_features(self, image_path: str) -> Dict[str, Any]:
        """Extract visual features from image."""
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                width, height = img.size
                img_array = np.array(img)
                
                # Basic features
                features = {
                    'width': width,
                    'height': height,
                    'aspect_ratio': width / height,
                    'total_pixels': width * height,
                }
                
                # Color analysis
                mean_colors = np.mean(img_array, axis=(0, 1))
                std_colors = np.std(img_array, axis=(0, 1))
                
                features.update({
                    'mean_r': mean_colors[0],
                    'mean_g': mean_colors[1],
                    'mean_b': mean_colors[2],
                    'std_r': std_colors[0],
                    'std_g': std_colors[1],
                    'std_b': std_colors[2],
                })
                
                # Brightness and contrast
                brightness = np.mean(img_array)
                contrast = np.std(img_array)
                features.update({
                    'brightness': brightness,
                    'contrast': contrast,
                })
                
                # Dominant colors
                pixels = img_array.reshape(-1, 3)
                dominant_colors = self._get_dominant_colors(pixels)
                features['dominant_colors'] = dominant_colors
                features['num_dominant_colors'] = len(dominant_colors)
                
                # Color distribution
                features.update(self._analyze_color_distribution(img_array))
                
                return features
                
        except Exception as e:
            print(f"Error analyzing image {image_path}: {e}")
            return {}
    
    def _get_dominant_colors(self, pixels: np.ndarray, k: int = 5) -> List[Tuple[int, int, int]]:
        """Get dominant colors using simple clustering."""
        sample_size = min(1000, len(pixels))
        sample_indices = np.random.choice(len(pixels), sample_size, replace=False)
        sample_pixels = pixels[sample_indices]
        
        rounded_pixels = (sample_pixels // 32) * 32
        unique_colors, counts = np.unique(rounded_pixels, axis=0, return_counts=True)
        
        sorted_indices = np.argsort(counts)[::-1]
        dominant_colors = []
        
        for i in sorted_indices[:k]:
            color = tuple(unique_colors[i])
            dominant_colors.append(color)
        
        return dominant_colors
    
    def _analyze_color_distribution(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Analyze color distribution in the image."""
        # Convert to HSV for better color analysis
        from PIL import Image
        img_pil = Image.fromarray(img_array)
        hsv_img = img_pil.convert('HSV')
        hsv_array = np.array(hsv_img)
        
        # Analyze hue distribution
        hue_values = hsv_array[:, :, 0].flatten()
        saturation_values = hsv_array[:, :, 1].flatten()
        value_values = hsv_array[:, :, 2].flatten()
        
        return {
            'avg_hue': np.mean(hue_values),
            'avg_saturation': np.mean(saturation_values),
            'avg_value': np.mean(value_values),
            'hue_std': np.std(hue_values),
            'saturation_std': np.std(saturation_values),
            'value_std': np.std(value_values),
        }
    
    def extract_combined_features(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract both textual and visual features."""
        features = {}
        
        # Text features
        text_features = self.extract_text_features(product)
        for key, value in text_features.items():
            features[f'text_{key}'] = value
        
        # Image features
        if product.get('image'):
            image_path = self.download_image(product['image'], product['id'])
            if image_path:
                image_features = self.extract_image_features(image_path)
                for key, value in image_features.items():
                    if key != 'dominant_colors':  # Skip complex data structures
                        features[f'image_{key}'] = value
            else:
                # Add default image features if download failed
                features.update({
                    'image_width': 0, 'image_height': 0, 'image_aspect_ratio': 0,
                    'image_brightness': 0, 'image_contrast': 0
                })
        else:
            # Add default image features if no image
            features.update({
                'image_width': 0, 'image_height': 0, 'image_aspect_ratio': 0,
                'image_brightness': 0, 'image_contrast': 0
            })
        
        return features

def classify_combined_features(json_file_path: str, categories: Optional[List[str]] = None, 
                              min_products_per_category: int = 1) -> None:
    """
    Perform combined text + image classification.
    
    Args:
        json_file_path: Path to JSON file containing product data
        categories: List of category IDs to classify (None for all suitable categories)
        min_products_per_category: Minimum products required per category
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
    
    # Initialize feature extractor
    extractor = CombinedFeatureExtractor()
    
    # Extract features
    print(f"\n=== Feature Extraction ===")
    all_features = []
    product_labels = []
    successful_extractions = 0
    
    for i, product in enumerate(products):
        print(f"Processing product {i+1}/{len(products)}: {product['name']}")
        
        features = extractor.extract_combined_features(product)
        if features:
            all_features.append(features)
            product_labels.append(product['category_id'])
            successful_extractions += 1
            
            # Show some key features
            print(f"  ✅ Text features: {features['text_word_count']} words, {features['text_unique_words']} unique")
            if features['image_width'] > 0:
                print(f"  ✅ Image features: {features['image_width']}x{features['image_height']}, brightness: {features['image_brightness']:.1f}")
            else:
                print(f"  ⚠️  No image features")
        else:
            print(f"  ❌ Failed to extract features")
    
    print(f"\n=== Results ===")
    print(f"Successfully processed: {successful_extractions}/{len(products)} products")
    
    if successful_extractions == 0:
        print("No products were successfully processed.")
        return
    
    # Analyze features by category
    print(f"\n=== Feature Analysis by Category ===")
    
    category_features = defaultdict(list)
    for features, label in zip(all_features, product_labels):
        category_features[label].append(features)
    
    for category, features_list in category_features.items():
        print(f"\n📊 Category: {category}")
        print(f"   Products: {len(features_list)}")
        
        # Text analysis
        avg_word_count = np.mean([f['text_word_count'] for f in features_list])
        avg_unique_words = np.mean([f['text_unique_words'] for f in features_list])
        print(f"   Avg words: {avg_word_count:.1f}, unique: {avg_unique_words:.1f}")
        
        # Image analysis (if available)
        image_features = [f for f in features_list if f['image_width'] > 0]
        if image_features:
            avg_width = np.mean([f['image_width'] for f in image_features])
            avg_height = np.mean([f['image_height'] for f in image_features])
            avg_brightness = np.mean([f['image_brightness'] for f in image_features])
            print(f"   Avg image size: {avg_width:.0f}x{avg_height:.0f}")
            print(f"   Avg brightness: {avg_brightness:.1f}")
        else:
            print(f"   No image data available")
        
        # Category-specific features
        pillbox_keywords = np.mean([f['text_pillbox_keywords'] for f in features_list])
        material_keywords = np.mean([f['text_material_keywords'] for f in features_list])
        print(f"   Pillbox keywords: {pillbox_keywords:.1f}")
        print(f"   Material keywords: {material_keywords:.1f}")
    
    # Simple classification simulation
    if len(all_features) >= 2 and len(set(product_labels)) >= 2:
        print(f"\n=== Combined Classification Simulation ===")
        
        # Split data
        random.shuffle(list(zip(all_features, product_labels)))
        train_size = max(1, len(all_features) // 2)
        
        train_features = all_features[:train_size]
        train_labels = product_labels[:train_size]
        test_features = all_features[train_size:]
        test_labels = product_labels[train_size:]
        
        print(f"Training on {len(train_features)} products")
        print(f"Testing on {len(test_features)} products")
        
        # Combined distance-based classification
        correct = 0
        total = 0
        
        for test_feat, test_label in zip(test_features, test_labels):
            best_match = None
            best_distance = float('inf')
            
            for train_feat, train_label in zip(train_features, train_labels):
                # Combined distance using both text and image features
                text_distance = (
                    abs(test_feat['text_word_count'] - train_feat['text_word_count']) / 100 +
                    abs(test_feat['text_unique_words'] - train_feat['text_unique_words']) / 50 +
                    abs(test_feat['text_pillbox_keywords'] - train_feat['text_pillbox_keywords']) +
                    abs(test_feat['text_material_keywords'] - train_feat['text_material_keywords'])
                )
                
                image_distance = 0
                if test_feat['image_width'] > 0 and train_feat['image_width'] > 0:
                    image_distance = (
                        abs(test_feat['image_width'] - train_feat['image_width']) / 1000 +
                        abs(test_feat['image_height'] - train_feat['image_height']) / 1000 +
                        abs(test_feat['image_brightness'] - train_feat['image_brightness']) / 100 +
                        abs(test_feat['image_aspect_ratio'] - train_feat['image_aspect_ratio'])
                    )
                
                # Weighted combination (text + image)
                total_distance = text_distance + image_distance * 0.5
                
                if total_distance < best_distance:
                    best_distance = total_distance
                    best_match = train_label
            
            predicted = best_match
            actual = test_label
            
            is_correct = predicted == actual
            if is_correct:
                correct += 1
            total += 1
            
            status = "✓" if is_correct else "✗"
            print(f"   {status} Predicted: {predicted}, Actual: {actual}")
            print(f"      Text distance: {text_distance:.3f}, Image distance: {image_distance:.3f}")
        
        if total > 0:
            accuracy = correct / total
            print(f"\n   Combined classification accuracy: {accuracy:.4f} ({correct}/{total})")
    
    print(f"\n💡 Recommendations:")
    print(f"   1. Add more products for better classification")
    print(f"   2. Ensure products have both descriptive text and high-quality images")
    print(f"   3. Use consistent naming conventions across products")
    print(f"   4. Consider using machine learning libraries for advanced classification")

def main():
    """Main function for combined classification."""
    parser = argparse.ArgumentParser(
        description="Combined text + image product classification using JSON data"
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
    
    args = parser.parse_args()
    
    # Parse categories if provided
    categories = None
    if args.categories:
        categories = [cat.strip() for cat in args.categories.split(',')]
    
    try:
        classify_combined_features(
            json_file_path=args.json_file,
            categories=categories,
            min_products_per_category=args.min_products
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
