#!/usr/bin/env python3
"""
Product recommendation system using JSON data.
Finds similar products based on text, image, and combined features.
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
from PIL import Image, ImageDraw, ImageFont
import requests
from json_data_loader import JSONDataLoader

# Try to import matplotlib for visual display
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.gridspec import GridSpec
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib not available. Install with: pip install matplotlib")

class ProductRecommender:
    """Product recommendation system based on similarity."""
    
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
        self.products = []
        self.features = []
        self.similarity_cache = {}
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by removing HTML tags and non-alphanumeric characters."""
        text = re.sub(r'<[^>]+>', ' ', text.lower())
        return re.sub(r'[^a-z0-9 ]', '', text)
    
    def extract_text_features(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract textual features for similarity calculation."""
        text = self.normalize_text(product['name'] + ' ' + product['description'])
        words = text.split()
        
        # Create word frequency vector
        word_freq = Counter(words)
        
        # Extract key features
        features = {
            'word_count': len(words),
            'unique_words': len(set(words)),
            'word_frequency': dict(word_freq),
            'text_length': len(text),
        }
        
        # Category-specific features
        category_keywords = {
            'luxury': ['luxury', 'premium', 'designer', 'couture', 'exclusive'],
            'material': ['leather', 'silk', 'crystal', 'gold', 'silver', 'brass'],
            'style': ['elegant', 'sophisticated', 'classic', 'modern', 'vintage'],
            'occasion': ['evening', 'formal', 'casual', 'party', 'wedding'],
            'size': ['mini', 'small', 'medium', 'large', 'oversized']
        }
        
        for category, keywords in category_keywords.items():
            count = sum(word_freq.get(keyword, 0) for keyword in keywords)
            features[f'{category}_score'] = count
        
        return features
    
    def download_image(self, url: str, product_id: str) -> Optional[str]:
        """Download image from URL and save to cache."""
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{product_id}_{url_hash}.jpg"
            filepath = self.cache_dir / filename
            
            if filepath.exists():
                return str(filepath)
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            try:
                with Image.open(filepath) as img:
                    img.verify()
                return str(filepath)
            except Exception:
                filepath.unlink()
                return None
                
        except Exception as e:
            return None
    
    def extract_image_features(self, image_path: str) -> Dict[str, Any]:
        """Extract visual features for similarity calculation."""
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                width, height = img.size
                img_array = np.array(img)
                
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
                
                return features
                
        except Exception as e:
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
    
    def calculate_text_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate text similarity between two products."""
        # Jaccard similarity for word overlap
        words1 = set(features1['word_frequency'].keys())
        words2 = set(features2['word_frequency'].keys())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        jaccard_similarity = intersection / union
        
        # Weighted similarity based on word frequency
        common_words = words1.intersection(words2)
        weighted_similarity = 0
        total_weight = 0
        
        for word in common_words:
            freq1 = features1['word_frequency'].get(word, 0)
            freq2 = features2['word_frequency'].get(word, 0)
            weight = min(freq1, freq2)
            weighted_similarity += weight
            total_weight += max(freq1, freq2)
        
        weighted_similarity = weighted_similarity / total_weight if total_weight > 0 else 0
        
        # Combine jaccard and weighted similarity
        return (jaccard_similarity + weighted_similarity) / 2
    
    def calculate_image_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate image similarity between two products."""
        if not features1 or not features2:
            return 0.0
        
        # Size similarity
        size_similarity = 1 - abs(features1['aspect_ratio'] - features2['aspect_ratio'])
        
        # Color similarity
        color_distance = (
            abs(features1['mean_r'] - features2['mean_r']) / 255 +
            abs(features1['mean_g'] - features2['mean_g']) / 255 +
            abs(features1['mean_b'] - features2['mean_b']) / 255
        ) / 3
        color_similarity = 1 - color_distance
        
        # Brightness similarity
        brightness_diff = abs(features1['brightness'] - features2['brightness']) / 255
        brightness_similarity = 1 - brightness_diff
        
        # Dominant color similarity
        colors1 = set(features1.get('dominant_colors', []))
        colors2 = set(features2.get('dominant_colors', []))
        
        if colors1 and colors2:
            color_overlap = len(colors1.intersection(colors2)) / len(colors1.union(colors2))
        else:
            color_overlap = 0
        
        # Weighted combination
        similarity = (
            size_similarity * 0.2 +
            color_similarity * 0.3 +
            brightness_similarity * 0.2 +
            color_overlap * 0.3
        )
        
        return max(0, min(1, similarity))
    
    def calculate_combined_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate combined text + image similarity."""
        text_sim = self.calculate_text_similarity(features1['text'], features2['text'])
        image_sim = self.calculate_image_similarity(features1['image'], features2['image'])
        
        # Weighted combination (text 60%, image 40%)
        return text_sim * 0.6 + image_sim * 0.4
    
    def load_products(self, json_file_path: str) -> None:
        """Load products from JSON file and extract features."""
        print(f"Loading products from {json_file_path}...")
        loader = JSONDataLoader(json_file_path)
        
        self.products = loader.get_products()
        print(f"Loaded {len(self.products)} products")
        
        # Extract features for all products
        print("Extracting features...")
        self.features = []
        
        for i, product in enumerate(self.products):
            print(f"Processing product {i+1}/{len(self.products)}: {product['name']}")
            
            # Text features
            text_features = self.extract_text_features(product)
            
            # Image features
            image_features = {}
            if product.get('image'):
                image_path = self.download_image(product['image'], product['id'])
                if image_path:
                    image_features = self.extract_image_features(image_path)
            
            # Combine features
            combined_features = {
                'text': text_features,
                'image': image_features,
                'product_id': product['id'],
                'category': product['category_id']
            }
            
            self.features.append(combined_features)
        
        print(f"Feature extraction complete!")
    
    def load_products_from_config(self, config_file_path: str) -> None:
        """Load products from multiple JSON files listed in a configuration file."""
        print(f"Loading products from configuration file: {config_file_path}")
        
        # Read JSON file paths from config
        json_files = []
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Add JSON file path
                    json_files.append(line)
            
            print(f"Found {len(json_files)} JSON files to process")
            
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file_path}' not found.")
            return
        except Exception as e:
            print(f"Error reading configuration file: {e}")
            return
        
        # Load products from all JSON files
        all_products = []
        for i, json_file in enumerate(json_files, 1):
            print(f"\n📁 Processing file {i}/{len(json_files)}: {json_file}")
            try:
                loader = JSONDataLoader(json_file)
                products = loader.get_products()
                print(f"   Loaded {len(products)} products from this file")
                all_products.extend(products)
            except Exception as e:
                print(f"   ⚠️ Error loading {json_file}: {e}")
                continue
        
        self.products = all_products
        print(f"\n✅ Total products loaded: {len(self.products)}")
        
        # Extract features for all products
        print("\n🔍 Extracting features...")
        self.features = []
        
        for i, product in enumerate(self.products):
            if i % 10 == 0 or i == len(self.products) - 1:
                print(f"Processing product {i+1}/{len(self.products)}: {product['name']}")
            
            # Text features
            text_features = self.extract_text_features(product)
            
            # Image features
            image_features = {}
            if product.get('image'):
                image_path = self.download_image(product['image'], product['id'])
                if image_path:
                    image_features = self.extract_image_features(image_path)
            
            # Combine features
            combined_features = {
                'text': text_features,
                'image': image_features,
                'product_id': product['id'],
                'category': product['category_id']
            }
            
            self.features.append(combined_features)
        
        print(f"✅ Feature extraction complete!")
    
    def find_similar_products(self, product_id: str, top_k: int = 5, 
                             similarity_type: str = 'combined') -> List[Tuple[str, float]]:
        """Find similar products to the given product."""
        # Find the product
        product_idx = None
        for i, product in enumerate(self.products):
            if product['id'] == product_id:
                product_idx = i
                break
        
        if product_idx is None:
            print(f"Product {product_id} not found!")
            return []
        
        target_features = self.features[product_idx]
        similarities = []
        
        print(f"Finding similar products to: {self.products[product_idx]['name']}")
        
        for i, features in enumerate(self.features):
            if i == product_idx:  # Skip the same product
                continue
            
            if similarity_type == 'text':
                similarity = self.calculate_text_similarity(
                    target_features['text'], features['text']
                )
            elif similarity_type == 'image':
                similarity = self.calculate_image_similarity(
                    target_features['image'], features['image']
                )
            else:  # combined
                similarity = self.calculate_combined_similarity(
                    target_features, features
                )
            
            similarities.append((self.products[i]['id'], similarity))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def recommend_products(self, product_id: str, top_k: int = 5) -> None:
        """Recommend similar products."""
        similar_products = self.find_similar_products(product_id, top_k)
        
        if not similar_products:
            print("No similar products found!")
            return
        
        # Find the target product
        target_product = None
        for product in self.products:
            if product['id'] == product_id:
                target_product = product
                break
        
        print(f"\n🎯 Recommendations for: {target_product['name']}")
        print(f"Category: {target_product['category_id']}")
        print(f"Description: {target_product['description']}")
        
        # Display visual recommendations if matplotlib is available
        if MATPLOTLIB_AVAILABLE:
            self._display_visual_recommendations(target_product, similar_products)
        else:
            # Fallback to text-only display
            self._display_text_recommendations(similar_products, target_product)
    
    def _display_visual_recommendations(self, target_product: Dict[str, Any], similar_products: List[Tuple[str, float]]) -> None:
        """Display visual recommendations with images and save to file."""
        print(f"\n🖼️ Visual Recommendations:")
        
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle(f'Product Recommendations for: {target_product["name"]}', fontsize=16, fontweight='bold')
        
        # Create grid layout: 1 row for target, 1 row for recommendations
        gs = GridSpec(2, 6, figure=fig, hspace=0.4, wspace=0.3, top=0.85, bottom=0.15)
        
        # Display target product (top row, centered)
        target_ax = fig.add_subplot(gs[0, 1:5])
        self._display_product_image(target_product, target_ax, "TARGET PRODUCT", is_target=True)
        
        # Display recommended products (bottom row)
        for i, (similar_id, similarity) in enumerate(similar_products[:5]):
            # Find the similar product
            similar_product = None
            for product in self.products:
                if product['id'] == similar_id:
                    similar_product = product
                    break
            
            if similar_product:
                col_idx = i
                rec_ax = fig.add_subplot(gs[1, col_idx])
                self._display_product_image(similar_product, rec_ax, f"#{i+1}", similarity=similarity)
        
        # Adjust layout manually instead of using tight_layout
        plt.subplots_adjust(left=0.05, right=0.95, top=0.85, bottom=0.15, hspace=0.4, wspace=0.3)
        
        # Save the visualization to src/images
        output_filename = f"recommendations_{target_product['id']}.png"
        output_path = self.cache_dir / output_filename
        
        # Ensure the directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the figure
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"📁 Visual recommendations saved to: {output_path}")
        
        # Also display the figure
        plt.show()
        
        # Also show text explanations
        self._display_text_recommendations(similar_products, target_product)
    
    def _display_product_image(self, product: Dict[str, Any], ax, title: str, similarity: float = None, is_target: bool = False) -> None:
        """Display a single product image with description."""
        # Try to load the product image
        image_path = None
        if product.get('image'):
            image_path = self.download_image(product['image'], product['id'])
        
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                ax.imshow(img)
                ax.axis('off')
            except Exception:
                # If image fails to load, show placeholder
                self._show_placeholder_image(ax, "Image Error")
        else:
            # Show placeholder for missing image
            self._show_placeholder_image(ax, "No Image")
        
        # Add title and description
        title_text = title
        if similarity is not None:
            title_text += f"\nSimilarity: {similarity:.3f}"
        
        ax.set_title(title_text, fontsize=10, fontweight='bold', pad=10)
        
        # Add product name and description
        name = product['name'][:30] + "..." if len(product['name']) > 30 else product['name']
        desc = product['description'][:50] + "..." if len(product['description']) > 50 else product['description']
        
        # Add text box with product info
        info_text = f"{name}\n{desc}"
        ax.text(0.5, -0.15, info_text, transform=ax.transAxes, 
                ha='center', va='top', fontsize=8, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.7))
    
    def _show_placeholder_image(self, ax, text: str) -> None:
        """Show a placeholder image when the actual image is not available."""
        ax.text(0.5, 0.5, text, transform=ax.transAxes, ha='center', va='center',
                fontsize=12, bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.7))
        ax.axis('off')
    
    def _display_text_recommendations(self, similar_products: List[Tuple[str, float]], target_product: Dict[str, Any]) -> None:
        """Display text-based recommendations."""
        print(f"\n📋 Detailed Recommendations:")
        
        for i, (similar_id, similarity) in enumerate(similar_products, 1):
            # Find the similar product
            similar_product = None
            for product in self.products:
                if product['id'] == similar_id:
                    similar_product = product
                    break
            
            if similar_product:
                print(f"\n{i}. {similar_product['name']}")
                print(f"   Category: {similar_product['category_id']}")
                print(f"   Description: {similar_product['description']}")
                print(f"   Similarity: {similarity:.3f}")
                
                # Show why it's similar
                self._explain_similarity(target_product, similar_product, similarity)
    
    def _explain_similarity(self, product1: Dict[str, Any], product2: Dict[str, Any], similarity: float) -> None:
        """Explain why two products are similar."""
        # Find features for both products
        features1 = None
        features2 = None
        
        for features in self.features:
            if features['product_id'] == product1['id']:
                features1 = features
            if features['product_id'] == product2['id']:
                features2 = features
        
        if not features1 or not features2:
            return
        
        print(f"   Why similar:")
        
        # Text similarity
        text_sim = self.calculate_text_similarity(features1['text'], features2['text'])
        print(f"     Text similarity: {text_sim:.3f}")
        
        # Image similarity
        image_sim = self.calculate_image_similarity(features1['image'], features2['image'])
        print(f"     Image similarity: {image_sim:.3f}")
        
        # Common words
        words1 = set(features1['text']['word_frequency'].keys())
        words2 = set(features2['text']['word_frequency'].keys())
        common_words = words1.intersection(words2)
        
        if common_words:
            print(f"     Common words: {', '.join(list(common_words)[:5])}")
        
        # Similar categories
        if product1['category_id'] == product2['category_id']:
            print(f"     Same category: {product1['category_id']}")
    
    def analyze_product_catalog(self) -> None:
        """Analyze the entire product catalog."""
        print(f"\n📊 Product Catalog Analysis")
        print(f"Total products: {len(self.products)}")
        
        # Category distribution
        categories = Counter(product['category_id'] for product in self.products)
        print(f"Categories: {dict(categories)}")
        
        # Products with images
        products_with_images = sum(1 for product in self.products if product.get('image'))
        print(f"Products with images: {products_with_images}/{len(self.products)}")
        
        # Average text length
        avg_text_length = np.mean([
            len(product['name'] + ' ' + product['description']) 
            for product in self.products
        ])
        print(f"Average text length: {avg_text_length:.1f} characters")
        
        # List all available product IDs
        print(f"\n📋 Available Product IDs for Recommendations:")
        for i, product in enumerate(self.products, 1):
            print(f"{i:2d}. ID: {product['id']:<20} | Name: {product['name']}")
        
        # Find most similar product pairs
        print(f"\n🔍 Most Similar Product Pairs:")
        similarities = []
        
        for i in range(len(self.products)):
            for j in range(i + 1, len(self.products)):
                similarity = self.calculate_combined_similarity(
                    self.features[i], self.features[j]
                )
                similarities.append((
                    self.products[i]['name'],
                    self.products[j]['name'],
                    similarity
                ))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[2], reverse=True)
        
        # Show top 3 pairs
        for i, (name1, name2, sim) in enumerate(similarities[:3], 1):
            print(f"{i}. {name1} ↔ {name2} (similarity: {sim:.3f})")

def main():
    """Main function for product recommendation."""
    parser = argparse.ArgumentParser(
        description="Product recommendation system using JSON data"
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--json-file", 
        help="Path to single JSON file containing product data"
    )
    input_group.add_argument(
        "--config-file", 
        help="Path to configuration file listing multiple JSON files"
    )
    
    parser.add_argument(
        "--recommend", 
        help="Product ID to find recommendations for"
    )
    parser.add_argument(
        "--top-k", 
        type=int, 
        default=5,
        help="Number of recommendations to return (default: 5)"
    )
    parser.add_argument(
        "--similarity-type", 
        choices=['text', 'image', 'combined'],
        default='combined',
        help="Type of similarity to use (default: combined)"
    )
    parser.add_argument(
        "--analyze", 
        action="store_true",
        help="Analyze the entire product catalog"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize recommender
        recommender = ProductRecommender()
        
        # Load products
        if args.json_file:
            recommender.load_products(args.json_file)
        elif args.config_file:
            recommender.load_products_from_config(args.config_file)
        
        if args.analyze:
            # Analyze catalog
            recommender.analyze_product_catalog()
        
        if args.recommend:
            # Find recommendations
            recommender.recommend_products(args.recommend, args.top_k)
        
        if not args.analyze and not args.recommend:
            print("Use --recommend <product_id> to find recommendations or --analyze to analyze the catalog")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
