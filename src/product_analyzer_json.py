#!/usr/bin/env python3
"""
Enhanced product analyzer that generates descriptions and extracts additional attributes
like environmental sustainability from JSON data.
"""
import argparse
import os
import re
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import hashlib
from collections import Counter, defaultdict
from PIL import Image
import requests
from json_data_loader import JSONDataLoader

class ProductAttributeExtractor:
    """Extracts and analyzes product attributes from JSON data."""
    
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
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by removing HTML tags and non-alphanumeric characters."""
        text = re.sub(r'<[^>]+>', ' ', text.lower())
        return re.sub(r'[^a-z0-9 ]', '', text)
    
    def extract_sustainability_attributes(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract environmental sustainability attributes."""
        sustainability = {
            'is_sustainable': False,
            'sustainability_score': 0,
            'sustainable_materials': [],
            'eco_friendly_features': [],
            'certifications': [],
            'sustainability_keywords': []
        }
        
        # Combine all text fields for analysis
        text_fields = [
            product.get('name', ''),
            product.get('description', ''),
            product.get('shortDescription', ''),
            product.get('longDescription', ''),
        ]
        
        # Also check nested fields in Bergdorf Goodman format
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            text_fields.extend([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('keySellingPoints', ''),
                style_data.get('copyKeySellingPoints', ''),
                style_data.get('shortDescription', ''),
                style_data.get('name', ''),
            ])
            
            # Check for sustainable materials in the style data
            if 'sustainableMaterials' in style_data:
                sustainability['sustainable_materials'].extend(style_data['sustainableMaterials'])
                sustainability['sustainability_score'] += len(style_data['sustainableMaterials']) * 2
        
        combined_text = ' '.join([str(field) for field in text_fields if field]).lower()
        
        # Sustainability keywords and their weights
        sustainability_keywords = {
            # Materials
            'organic': 3, 'recycled': 3, 'recyclable': 2, 'biodegradable': 3,
            'sustainable': 3, 'eco-friendly': 3, 'environmentally friendly': 3,
            'natural': 2, 'renewable': 2, 'upcycled': 3,
            
            # Certifications
            'leed': 2, 'energy star': 2, 'fair trade': 3, 'rainforest alliance': 3,
            'usda organic': 3, 'fsc certified': 3, 'greenguard': 2,
            
            # Processes
            'carbon neutral': 3, 'zero waste': 3, 'low impact': 2,
            'water efficient': 2, 'energy efficient': 2, 'locally sourced': 2,
            
            # Negative indicators
            'plastic': -1, 'synthetic': -1, 'chemical': -1, 'toxic': -2,
            'non-recyclable': -2, 'disposable': -1
        }
        
        # Check for sustainable materials
        sustainable_materials = [
            'organic cotton', 'bamboo', 'hemp', 'linen', 'wool', 'silk',
            'recycled plastic', 'recycled metal', 'recycled glass',
            'cork', 'jute', 'sisal', 'seagrass', 'rattan'
        ]
        
        # Analyze text for sustainability indicators
        found_keywords = []
        score = 0
        
        for keyword, weight in sustainability_keywords.items():
            if keyword in combined_text:
                found_keywords.append(keyword)
                score += weight
        
        # Check for sustainable materials
        found_materials = []
        for material in sustainable_materials:
            if material in combined_text:
                found_materials.append(material)
                score += 2
        
        # Check for certifications
        certifications = [
            'leed', 'energy star', 'fair trade', 'rainforest alliance',
            'usda organic', 'fsc certified', 'greenguard', 'bluesign'
        ]
        
        found_certifications = []
        for cert in certifications:
            if cert in combined_text:
                found_certifications.append(cert)
                score += 3
        
        # Determine if product is sustainable
        is_sustainable = score >= 3
        
        sustainability.update({
            'is_sustainable': is_sustainable,
            'sustainability_score': max(0, score),
            'sustainable_materials': found_materials,
            'eco_friendly_features': found_keywords,
            'certifications': found_certifications,
            'sustainability_keywords': found_keywords
        })
        
        return sustainability
    
    def extract_material_attributes(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract material and construction attributes."""
        materials = {
            'primary_materials': [],
            'secondary_materials': [],
            'construction_methods': [],
            'finish_types': [],
            'hardware_materials': []
        }
        
        # Combine text fields
        text_fields = [
            product.get('name', ''),
            product.get('description', ''),
        ]
        
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            text_fields.extend([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('shortDescription', ''),
                style_data.get('name', ''),
            ])
            
            # Extract materials from structured fields
            if 'firstMaterial' in style_data and style_data['firstMaterial']:
                if isinstance(style_data['firstMaterial'], dict):
                    materials['primary_materials'].append(style_data['firstMaterial'].get('name', ''))
                else:
                    materials['primary_materials'].append(str(style_data['firstMaterial']))
            
            if 'secondMaterial' in style_data and style_data['secondMaterial']:
                if isinstance(style_data['secondMaterial'], dict):
                    materials['secondary_materials'].append(style_data['secondMaterial'].get('name', ''))
                else:
                    materials['secondary_materials'].append(str(style_data['secondMaterial']))
            
            if 'thirdMaterial' in style_data and style_data['thirdMaterial']:
                if isinstance(style_data['thirdMaterial'], dict):
                    materials['secondary_materials'].append(style_data['thirdMaterial'].get('name', ''))
                else:
                    materials['secondary_materials'].append(str(style_data['thirdMaterial']))
            
            # Extract from materialId array
            if 'materialId' in style_data and style_data['materialId']:
                for material in style_data['materialId']:
                    if isinstance(material, dict) and 'name' in material:
                        materials['primary_materials'].append(material['name'])
        
        combined_text = ' '.join([str(field) for field in text_fields if field]).lower()
        
        # Material categories
        material_categories = {
            'leather': ['leather', 'cowhide', 'calfskin', 'lambskin', 'suede'],
            'fabric': ['cotton', 'silk', 'wool', 'linen', 'polyester', 'nylon', 'rayon'],
            'metal': ['gold', 'silver', 'brass', 'bronze', 'steel', 'aluminum', 'copper'],
            'crystal': ['crystal', 'glass', 'diamond', 'gemstone', 'pearl'],
            'wood': ['wood', 'oak', 'mahogany', 'walnut', 'bamboo'],
            'plastic': ['plastic', 'acrylic', 'resin', 'pvc'],
            'natural': ['cork', 'jute', 'hemp', 'seagrass', 'rattan']
        }
        
        # Extract materials
        for category, materials_list in material_categories.items():
            for material in materials_list:
                if material in combined_text:
                    materials['primary_materials'].append(material)
        
        # Construction methods
        construction_keywords = [
            'handcrafted', 'handmade', 'machine made', 'woven', 'knitted',
            'stitched', 'welded', 'molded', 'cast', 'forged'
        ]
        
        for method in construction_keywords:
            if method in combined_text:
                materials['construction_methods'].append(method)
        
        # Finish types
        finish_keywords = [
            'polished', 'matte', 'glossy', 'brushed', 'textured', 'smooth',
            'embossed', 'engraved', 'etched', 'painted', 'coated'
        ]
        
        for finish in finish_keywords:
            if finish in combined_text:
                materials['finish_types'].append(finish)
        
        return materials
    
    def extract_style_attributes(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract style and design attributes."""
        style = {
            'style_era': '',
            'design_style': '',
            'color_palette': [],
            'patterns': [],
            'occasions': [],
            'target_demographic': ''
        }
        
        # Combine text fields
        text_fields = [
            product.get('name', ''),
            product.get('description', ''),
        ]
        
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            text_fields.extend([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('shortDescription', ''),
                style_data.get('name', ''),
            ])
            
            # Extract from occasionStyle array
            if 'occasionStyle' in style_data and style_data['occasionStyle']:
                for occasion in style_data['occasionStyle']:
                    if isinstance(occasion, dict) and 'name' in occasion:
                        style['occasions'].append(occasion['name'])
                    else:
                        style['occasions'].append(str(occasion))
            
            # Extract gender/demographic
            if 'gender' in style_data and style_data['gender']:
                if isinstance(style_data['gender'], dict):
                    style['target_demographic'] = style_data['gender'].get('name', '')
                else:
                    style['target_demographic'] = str(style_data['gender'])
        
        combined_text = ' '.join([str(field) for field in text_fields if field]).lower()
        
        # Style eras
        era_keywords = {
            'vintage': ['vintage', 'retro', 'classic', 'antique'],
            'modern': ['modern', 'contemporary', 'minimalist', 'sleek'],
            'bohemian': ['bohemian', 'boho', 'eclectic', 'artistic'],
            'preppy': ['preppy', 'traditional', 'conservative', 'classic'],
            'edgy': ['edgy', 'bold', 'dramatic', 'statement']
        }
        
        for era, keywords in era_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    style['style_era'] = era
                    break
        
        # Design styles
        design_styles = [
            'minimalist', 'maximalist', 'geometric', 'floral', 'abstract',
            'art deco', 'art nouveau', 'mid-century', 'industrial', 'rustic'
        ]
        
        for design_style in design_styles:
            if design_style in combined_text:
                style['design_style'] = design_style
                break
        
        # Colors
        colors = [
            'black', 'white', 'red', 'blue', 'green', 'yellow', 'pink',
            'purple', 'brown', 'gray', 'silver', 'gold', 'navy', 'beige'
        ]
        
        for color in colors:
            if color in combined_text:
                style['color_palette'].append(color)
        
        # Patterns
        patterns = [
            'striped', 'polka dot', 'floral', 'geometric', 'abstract',
            'chevron', 'houndstooth', 'plaid', 'paisley', 'animal print'
        ]
        
        for pattern in patterns:
            if pattern in combined_text:
                style['patterns'].append(pattern)
        
        # Occasions
        occasions = [
            'casual', 'formal', 'evening', 'wedding', 'party', 'business',
            'vacation', 'date night', 'cocktail', 'black tie'
        ]
        
        for occasion in occasions:
            if occasion in combined_text:
                style['occasions'].append(occasion)
        
        return style
    
    def generate_product_description(self, product: Dict[str, Any], 
                                   sustainability: Dict[str, Any],
                                   materials: Dict[str, Any],
                                   style: Dict[str, Any]) -> str:
        """Generate a comprehensive product description."""
        name = product.get('name', 'Unknown Product')
        category = product.get('category_id', 'Unknown Category')
        
        # Start with basic description
        description_parts = [f"This {name} is a {category} product"]
        
        # Add material information
        if materials['primary_materials']:
            materials_text = ', '.join(materials['primary_materials'][:3])
            description_parts.append(f"crafted from {materials_text}")
        
        # Add construction method
        if materials['construction_methods']:
            construction = materials['construction_methods'][0]
            description_parts.append(f"using {construction} techniques")
        
        # Add style information
        if style['style_era']:
            description_parts.append(f"in a {style['style_era']} style")
        
        if style['design_style']:
            description_parts.append(f"with {style['design_style']} design elements")
        
        # Add color information
        if style['color_palette']:
            colors_text = ', '.join(style['color_palette'][:3])
            description_parts.append(f"featuring {colors_text} colors")
        
        # Add occasion information
        if style['occasions']:
            occasions_text = ', '.join(style['occasions'][:2])
            description_parts.append(f"perfect for {occasions_text} occasions")
        
        # Add sustainability information
        if sustainability['is_sustainable']:
            description_parts.append("This product is environmentally sustainable")
            
            if sustainability['sustainable_materials']:
                materials_text = ', '.join(sustainability['sustainable_materials'])
                description_parts.append(f"made with sustainable materials including {materials_text}")
            
            if sustainability['certifications']:
                certs_text = ', '.join(sustainability['certifications'])
                description_parts.append(f"certified by {certs_text}")
        
        # Combine description parts
        description = '. '.join(description_parts) + '.'
        
        return description
    
    def analyze_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive product analysis."""
        print(f"Analyzing product: {product['name']}")
        
        # Extract all attributes
        sustainability = self.extract_sustainability_attributes(product)
        materials = self.extract_material_attributes(product)
        style = self.extract_style_attributes(product)
        
        # Generate description
        description = self.generate_product_description(product, sustainability, materials, style)
        
        # Compile analysis
        analysis = {
            'product_id': product['id'],
            'name': product['name'],
            'category': product['category_id'],
            'generated_description': description,
            'sustainability': sustainability,
            'materials': materials,
            'style': style,
            'analysis_summary': {
                'is_sustainable': sustainability['is_sustainable'],
                'sustainability_score': sustainability['sustainability_score'],
                'primary_materials': materials['primary_materials'][:3],
                'style_era': style['style_era'],
                'target_occasions': style['occasions'][:3]
            }
        }
        
        return analysis

def analyze_products_from_json(json_file_path: str, categories: Optional[List[str]] = None, 
                              min_products_per_category: int = 1) -> None:
    """
    Analyze products from JSON file and generate descriptions with attributes.
    
    Args:
        json_file_path: Path to JSON file containing product data
        categories: List of category IDs to analyze (None for all suitable categories)
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
        print("No suitable categories found for analysis.")
        return
    
    # Get products for selected categories
    products = loader.get_products(categories)
    print(f"\nAnalyzing {len(products)} products from {len(categories)} categories")
    
    # Initialize analyzer
    analyzer = ProductAttributeExtractor()
    
    # Analyze each product
    print(f"\n=== Product Analysis ===")
    analyses = []
    
    for i, product in enumerate(products):
        print(f"\nProcessing product {i+1}/{len(products)}")
        analysis = analyzer.analyze_product(product)
        analyses.append(analysis)
    
    # Display results
    print(f"\n=== Analysis Results ===")
    
    for analysis in analyses:
        print(f"\n🎯 Product: {analysis['name']}")
        print(f"   Category: {analysis['category']}")
        print(f"   ID: {analysis['product_id']}")
        
        print(f"\n📝 Generated Description:")
        print(f"   {analysis['generated_description']}")
        
        print(f"\n🌱 Sustainability Analysis:")
        sustainability = analysis['sustainability']
        print(f"   Sustainable: {'✅ Yes' if sustainability['is_sustainable'] else '❌ No'}")
        print(f"   Score: {sustainability['sustainability_score']}/10")
        
        if sustainability['sustainable_materials']:
            print(f"   Sustainable Materials: {', '.join(sustainability['sustainable_materials'])}")
        
        if sustainability['certifications']:
            print(f"   Certifications: {', '.join(sustainability['certifications'])}")
        
        if sustainability['eco_friendly_features']:
            print(f"   Eco-friendly Features: {', '.join(sustainability['eco_friendly_features'][:3])}")
        
        print(f"\n🏗️  Materials & Construction:")
        materials = analysis['materials']
        if materials['primary_materials']:
            print(f"   Primary Materials: {', '.join(materials['primary_materials'][:3])}")
        
        if materials['construction_methods']:
            print(f"   Construction: {', '.join(materials['construction_methods'][:2])}")
        
        if materials['finish_types']:
            print(f"   Finish: {', '.join(materials['finish_types'][:2])}")
        
        print(f"\n🎨 Style & Design:")
        style = analysis['style']
        if style['style_era']:
            print(f"   Style Era: {style['style_era']}")
        
        if style['design_style']:
            print(f"   Design Style: {style['design_style']}")
        
        if style['color_palette']:
            print(f"   Colors: {', '.join(style['color_palette'][:3])}")
        
        if style['occasions']:
            print(f"   Occasions: {', '.join(style['occasions'][:3])}")
        
        print(f"\n📊 Summary:")
        summary = analysis['analysis_summary']
        print(f"   Sustainable: {'Yes' if summary['is_sustainable'] else 'No'}")
        print(f"   Key Materials: {', '.join(summary['primary_materials']) if summary['primary_materials'] else 'Unknown'}")
        print(f"   Style: {summary['style_era'] if summary['style_era'] else 'Unknown'}")
        print(f"   Best For: {', '.join(summary['target_occasions']) if summary['target_occasions'] else 'Various'}")
    
    # Overall statistics
    print(f"\n=== Overall Statistics ===")
    
    sustainable_count = sum(1 for a in analyses if a['sustainability']['is_sustainable'])
    avg_sustainability_score = np.mean([a['sustainability']['sustainability_score'] for a in analyses])
    
    print(f"Total Products Analyzed: {len(analyses)}")
    print(f"Sustainable Products: {sustainable_count}/{len(analyses)} ({sustainable_count/len(analyses)*100:.1f}%)")
    print(f"Average Sustainability Score: {avg_sustainability_score:.1f}/10")
    
    # Most common materials
    all_materials = []
    for analysis in analyses:
        all_materials.extend(analysis['materials']['primary_materials'])
    
    if all_materials:
        material_counts = Counter(all_materials)
        print(f"Most Common Materials: {dict(material_counts.most_common(3))}")
    
    # Most common styles
    all_styles = [a['style']['style_era'] for a in analyses if a['style']['style_era']]
    if all_styles:
        style_counts = Counter(all_styles)
        print(f"Most Common Styles: {dict(style_counts.most_common(3))}")

def main():
    """Main function for product analysis."""
    parser = argparse.ArgumentParser(
        description="Enhanced product analyzer with description generation and attribute extraction"
    )
    parser.add_argument(
        "--json-file", 
        required=True,
        help="Path to JSON file containing product data"
    )
    parser.add_argument(
        "--categories", 
        help="Comma-separated list of categories to analyze. If not specified, all suitable categories are used."
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
        analyze_products_from_json(
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
