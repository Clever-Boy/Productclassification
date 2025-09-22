#!/usr/bin/env python3
"""
JSON-based data loader for product classification.
Works with style.json files containing digitalAssets and product information.
"""
import json
import os
import random
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hashlib
import re

class JSONDataLoader:
    """
    Loads product data from JSON files instead of database.
    Compatible with style.json format containing digitalAssets.
    """
    
    def __init__(self, json_file_path: str):
        """
        Initialize JSON data loader.
        
        Args:
            json_file_path: Path to the JSON file containing product data
        """
        self.json_file_path = json_file_path
        self.data = self._load_json_data()
        self.products = self._extract_products()
        self.categories = self._extract_categories()
        
    def _load_json_data(self) -> Dict[str, Any]:
        """Load JSON data from file."""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"JSON file not found: {self.json_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    def _extract_products(self) -> List[Dict[str, Any]]:
        """Extract products from JSON data."""
        products = []
        
        # Handle different JSON structures
        if isinstance(self.data, list):
            # If JSON is a list of products
            items = self.data
        elif isinstance(self.data, dict):
            # If JSON has a products key or similar
            if 'products' in self.data:
                items = self.data['products']
            elif 'styles' in self.data:
                items = self.data['styles']
            elif 'items' in self.data:
                items = self.data['items']
            elif 'pal' in self.data:
                # Bergdorf Goodman format - single product
                items = [self.data]
            else:
                # Assume the dict itself contains product data
                items = [self.data]
        else:
            raise ValueError("Unsupported JSON structure")
        
        for item in items:
            product = self._extract_product_from_item(item)
            if product:
                products.append(product)
        
        return products
    
    def _extract_product_from_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract product information from a single JSON item.
        Handles various JSON structures including digitalAssets and Bergdorf Goodman format.
        """
        try:
            # Handle Bergdorf Goodman format (single product with nested structure)
            if 'pal' in item and 'style' in item['pal']:
                return self._extract_bg_product(item)
            
            # Handle standard product array format
            product_id = self._get_nested_value(item, ['id', 'productId', 'styleId', 'sku'])
            name = self._get_nested_value(item, ['name', 'productName', 'styleName', 'title'])
            description = self._get_nested_value(item, ['description', 'shortDescription', 'longDescription'])
            category = self._get_nested_value(item, ['category', 'categoryId', 'department', 'classification'])
            
            # Extract image URL from digitalAssets
            image_url = self._extract_image_url(item)
            
            # Skip if essential fields are missing
            if not product_id or not name:
                return None
            
            # Generate category if not present
            if not category:
                category = self._generate_category_from_name(name)
            
            return {
                'id': str(product_id),
                'name': str(name),
                'description': str(description) if description else '',
                'category_id': str(category),
                'image': image_url,
                'raw_data': item  # Preserve the full raw data structure
            }
            
        except Exception as e:
            print(f"Error extracting product from item: {e}")
            return None
    
    def _extract_bg_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract product information from Bergdorf Goodman JSON format.
        """
        try:
            pal_data = item['pal']
            style_data = pal_data['style']
            sku_data = pal_data.get('sku', {})
            variation_data = pal_data.get('variation', {})
            
            # Extract product ID from webProductID (primary) or sku.id (fallback)
            product_id = None
            if 'variation' in pal_data and 'storeFronts' in pal_data['variation']:
                store_fronts = pal_data['variation']['storeFronts']
                for store in store_fronts.values():
                    if 'webProduct' in store and store['webProduct']:
                        product_id = store['webProduct'][0].get('webProductID')
                        break
            
            # Fallback to sku.id if no webProductID found
            if not product_id and 'id' in sku_data:
                product_id = sku_data['id']
            
            # Extract name and description
            name = style_data.get('name', '')
            description = style_data.get('shortDescription', '')
            
            # Extract category from classification or taxonomy
            category = None
            if 'classification' in style_data:
                classification = style_data['classification']
                category = classification.get('name', '')
            
            # If no classification, try to extract from taxonomy levels
            if not category and 'taxonomies' in item:
                taxonomies = item['taxonomies']
                if taxonomies:
                    # Use the most specific taxonomy level (highest levelNumber)
                    taxonomy = max(taxonomies, key=lambda x: x.get('levelNumber', 0))
                    category = taxonomy.get('name', '')
            
            # Extract image URL from digitalAssets (at top level of item)
            image_url = self._extract_image_url(item)
            
            # Skip if essential fields are missing
            if not product_id or not name:
                return None
            
            # Generate category if not present
            if not category:
                category = self._generate_category_from_name(name)
            
            return {
                'id': str(product_id),
                'name': str(name),
                'description': str(description) if description else '',
                'category_id': str(category),
                'image': image_url,
                'pal': pal_data  # Preserve the full PAL data structure
            }
            
        except Exception as e:
            print(f"Error extracting BG product: {e}")
            return None
    
    def _get_nested_value(self, data: Dict[str, Any], keys: List[str]) -> Optional[str]:
        """Get value from nested dictionary using multiple possible keys."""
        for key in keys:
            if key in data:
                return data[key]
        return None
    
    def _extract_image_url(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract image URL from digitalAssets or other image fields."""
        # For Bergdorf Goodman format, check pal.digitalAssets first
        if 'pal' in item and 'digitalAssets' in item['pal']:
            digital_assets = item['pal']['digitalAssets']
            if isinstance(digital_assets, list):
                for asset in digital_assets:
                    if isinstance(asset, dict):
                        # Check nested assetName structure first (Bergdorf Goodman format)
                        if 'assetName' in asset and isinstance(asset['assetName'], dict):
                            asset_name = asset['assetName']
                            if 'linkURL' in asset_name:
                                image_url = asset_name['linkURL']
                                if image_url and self._is_image_url(image_url):
                                    return image_url
                        
                        # Look for linkURL directly in the asset
                        if 'linkURL' in asset:
                            image_url = asset['linkURL']
                            if image_url and self._is_image_url(image_url):
                                return image_url
        
        # Try digitalAssets at top level (standard format)
        if 'digitalAssets' in item and isinstance(item['digitalAssets'], list):
            for asset in item['digitalAssets']:
                if isinstance(asset, dict):
                    # Check nested assetName structure first
                    if 'assetName' in asset and isinstance(asset['assetName'], dict):
                        asset_name = asset['assetName']
                        if 'linkURL' in asset_name:
                            image_url = asset_name['linkURL']
                            if image_url and self._is_image_url(image_url):
                                return image_url
                    
                    # Look for linkURL directly in the asset
                    if 'linkURL' in asset:
                        image_url = asset['linkURL']
                        if image_url and self._is_image_url(image_url):
                            return image_url
                    
                    # Look for other image URL fields
                    image_url = self._get_nested_value(asset, [
                        'url', 'imageUrl', 'src', 'href'
                    ])
                    if image_url and self._is_image_url(image_url):
                        return image_url
        
        # Try other common image fields
        image_url = self._get_nested_value(item, [
            'image', 'imageUrl', 'thumbnail', 'photo', 'picture', 'img'
        ])
        
        if image_url and self._is_image_url(image_url):
            return image_url
        
        return None
    
    def _is_image_url(self, url: str) -> bool:
        """Check if URL points to an image."""
        if not url or not isinstance(url, str):
            return False
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']
        url_lower = url.lower()
        
        # Check file extension
        for ext in image_extensions:
            if ext in url_lower:
                return True
        
        # Check for common image hosting patterns
        image_patterns = ['image', 'photo', 'img', 'media', 'cdn']
        for pattern in image_patterns:
            if pattern in url_lower:
                return True
        
        return False
    
    def _generate_category_from_name(self, name: str) -> str:
        """Generate a category from product name if none exists."""
        if not name:
            return 'unknown'
        
        # Simple category extraction based on keywords
        name_lower = name.lower()
        
        category_keywords = {
            'dress': ['dress', 'gown', 'frock'],
            'shirt': ['shirt', 'blouse', 'top', 'tee'],
            'pants': ['pants', 'trousers', 'jeans', 'leggings'],
            'shoes': ['shoe', 'boot', 'sandal', 'sneaker'],
            'bag': ['bag', 'purse', 'handbag', 'tote'],
            'jacket': ['jacket', 'blazer', 'coat', 'outerwear'],
            'accessories': ['belt', 'scarf', 'hat', 'jewelry', 'watch'],
            'skirt': ['skirt', 'mini', 'midi', 'maxi']
        }
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category
        
        return 'other'
    
    def _extract_categories(self) -> List[str]:
        """Extract unique categories from products."""
        categories = set()
        for product in self.products:
            categories.add(product['category_id'])
        return list(categories)
    
    def get_products(self, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get products, optionally filtered by categories.
        
        Args:
            categories: List of category IDs to filter by
            
        Returns:
            List of product dictionaries
        """
        if categories is None:
            return self.products.copy()
        
        filtered_products = []
        for product in self.products:
            if product['category_id'] in categories:
                filtered_products.append(product)
        
        return filtered_products
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return self.categories.copy()
    
    def get_categories_to_predict(self, min_products: int = 10) -> List[str]:
        """
        Get categories suitable for prediction (with minimum number of products).
        
        Args:
            min_products: Minimum number of products required per category
            
        Returns:
            List of category IDs
        """
        category_counts = {}
        for product in self.products:
            cat = product['category_id']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        suitable_categories = []
        for category, count in category_counts.items():
            if count >= min_products:
                suitable_categories.append(category)
        
        return suitable_categories
    
    def get_products_for_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Get all products for a specific category."""
        products = []
        for product in self.products:
            if product['category_id'] == category_id:
                products.append(product)
        return products
    
    def get_product_images_to_crawl(self) -> List[Dict[str, Any]]:
        """Get products with images that need downloading."""
        products_with_images = []
        for product in self.products:
            if product['image']:
                products_with_images.append({
                    'id': product['id'],
                    'image': product['image']
                })
        return products_with_images
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loaded data."""
        category_counts = {}
        for product in self.products:
            cat = product['category_id']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        products_with_images = sum(1 for p in self.products if p['image'])
        
        return {
            'total_products': len(self.products),
            'total_categories': len(self.categories),
            'products_with_images': products_with_images,
            'category_distribution': category_counts,
            'suitable_categories': len(self.get_categories_to_predict())
        }
    
    def print_statistics(self):
        """Print data statistics."""
        stats = self.get_statistics()
        
        print("=== JSON Data Statistics ===")
        print(f"Total products: {stats['total_products']}")
        print(f"Total categories: {stats['total_categories']}")
        print(f"Products with images: {stats['products_with_images']}")
        print(f"Suitable categories (10+ products): {stats['suitable_categories']}")
        print("\nCategory distribution:")
        
        for category, count in sorted(stats['category_distribution'].items(), 
                                    key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count} products")

def load_json_data(json_file_path: str) -> JSONDataLoader:
    """
    Convenience function to load JSON data.
    
    Args:
        json_file_path: Path to JSON file
        
    Returns:
        JSONDataLoader instance
    """
    return JSONDataLoader(json_file_path)

# Example usage
if __name__ == "__main__":
    # Example usage
    json_file = "style.json"  # Replace with your actual file path
    
    if os.path.exists(json_file):
        loader = load_json_data(json_file)
        loader.print_statistics()
        
        # Get suitable categories for training
        suitable_categories = loader.get_categories_to_predict(min_products=5)
        print(f"\nCategories suitable for training: {suitable_categories}")
        
        # Get products for a specific category
        if suitable_categories:
            sample_category = suitable_categories[0]
            products = loader.get_products_for_category(sample_category)
            print(f"\nSample products from '{sample_category}':")
            for i, product in enumerate(products[:3]):  # Show first 3
                print(f"  {i+1}. {product['name']} - {product['category_id']}")
    else:
        print(f"JSON file '{json_file}' not found.")
        print("Please provide the path to your style.json file.")
