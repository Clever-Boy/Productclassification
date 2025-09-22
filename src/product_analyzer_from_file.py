#!/usr/bin/env python3
"""
Enhanced product analyzer that reads configuration from a text file
and generates descriptions with attribute extraction from JSON data.
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
            if 'sustainableMaterials' in style_data and style_data['sustainableMaterials']:
                sustainability['sustainable_materials'].extend(style_data['sustainableMaterials'])
                sustainability['sustainability_score'] += len(style_data['sustainableMaterials']) * 2
        
        # Also check raw_data for additional information
        elif 'raw_data' in product:
            raw_data = product['raw_data']
            if 'pal' in raw_data and 'style' in raw_data['pal']:
                style_data = raw_data['pal']['style']
                text_fields.extend([
                    style_data.get('copyBlock', ''),
                    style_data.get('legacyCopyBlock', ''),
                    style_data.get('keySellingPoints', ''),
                    style_data.get('copyKeySellingPoints', ''),
                    style_data.get('shortDescription', ''),
                    style_data.get('name', ''),
                ])
                
                # Check for sustainable materials in the style data
                if 'sustainableMaterials' in style_data and style_data['sustainableMaterials']:
                    sustainability['sustainable_materials'].extend(style_data['sustainableMaterials'])
                    sustainability['sustainability_score'] += len(style_data['sustainableMaterials']) * 2
        
        combined_text = ' '.join([str(field) for field in text_fields if field]).lower()
        
        # Debug: Print what text we're analyzing
        print(f"DEBUG: Analyzing text: {combined_text[:200]}...")
        
        # Sustainability keywords and their weights
        sustainability_keywords = {
            # Materials
            'organic': 3, 'recycled': 3, 'recyclable': 2, 'biodegradable': 3,
            'sustainable': 3, 'eco-friendly': 3, 'environmentally friendly': 3,
            'natural': 2, 'renewable': 2, 'upcycled': 3,
            
            # Luxury craftsmanship (sustainable practices)
            'handcrafted': 2, 'handmade': 2, 'artisan': 2, 'couture': 2,
            'made in italy': 2, 'made in france': 2, 'made in germany': 2,
            'european': 1, 'italian': 1, 'french': 1, 'german': 1,
            
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
        
        # Check for Bergdorf Goodman format first
        style_data = None
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
        elif 'raw_data' in product and 'pal' in product['raw_data'] and 'style' in product['raw_data']['pal']:
            style_data = product['raw_data']['pal']['style']
        
        if style_data:
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
        
        # Debug: Print what materials we found
        print(f"DEBUG: Found materials - Primary: {materials['primary_materials']}, Secondary: {materials['secondary_materials']}")
        print(f"DEBUG: Analyzing text for materials: {combined_text[:200]}...")
        
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
        
        # Extract materials (avoid duplicates)
        for category, materials_list in material_categories.items():
            for material in materials_list:
                if material in combined_text:
                    # Avoid duplicates by checking case-insensitive
                    material_lower = material.lower()
                    if not any(m.lower() == material_lower for m in materials['primary_materials']):
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
    
    def extract_price_analysis(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract price and value analysis."""
        price_info = {
            'price_range': 'unknown',
            'value_assessment': 'unknown',
            'luxury_level': 'unknown',
            'price_indicators': [],
            'comparative_value': None
        }
        
        # Check for price information in various fields
        price_fields = []
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            price_fields.extend([
                style_data.get('nmInitialRetail', ''),
                style_data.get('initialCost', ''),
                style_data.get('comparativeValue', ''),
            ])
            
            # Check variation data for current retail prices
            if 'variation' in product['pal'] and 'storeFronts' in product['pal']['variation']:
                store_fronts = product['pal']['variation']['storeFronts']
                for store_name, store_data in store_fronts.items():
                    if 'pricing' in store_data:
                        for zone, pricing in store_data['pricing'].items():
                            if 'regularRetail' in pricing:
                                price_fields.append(pricing['regularRetail'])
        
        # Extract numeric prices
        prices = []
        for field in price_fields:
            if field and str(field).replace('.', '').isdigit():
                prices.append(float(field))
        
        if prices:
            avg_price = sum(prices) / len(prices)
            price_info['comparative_value'] = avg_price
            
            # Determine price range
            if avg_price < 50:
                price_info['price_range'] = 'budget'
                price_info['luxury_level'] = 'affordable'
            elif avg_price < 200:
                price_info['price_range'] = 'mid-range'
                price_info['luxury_level'] = 'moderate'
            elif avg_price < 1000:
                price_info['price_range'] = 'premium'
                price_info['luxury_level'] = 'high-end'
            else:
                price_info['price_range'] = 'luxury'
                price_info['luxury_level'] = 'ultra-luxury'
            
            # Value assessment based on materials and craftsmanship
            materials_score = 0
            if 'pal' in product and 'style' in product['pal']:
                style_data = product['pal']['style']
                if 'firstMaterial' in style_data:
                    materials_score += 1
                if 'secondMaterial' in style_data:
                    materials_score += 1
                if 'materialId' in style_data and style_data['materialId']:
                    materials_score += len(style_data['materialId'])
            
            if materials_score >= 3 and avg_price > 500:
                price_info['value_assessment'] = 'excellent'
            elif materials_score >= 2 and avg_price > 200:
                price_info['value_assessment'] = 'good'
            elif avg_price < 100:
                price_info['value_assessment'] = 'budget-friendly'
            else:
                price_info['value_assessment'] = 'moderate'
        
        return price_info
    
    def extract_brand_analysis(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract brand and reputation analysis."""
        brand_info = {
            'brand_name': 'unknown',
            'brand_tier': 'unknown',
            'reputation_score': 0,
            'heritage_indicators': [],
            'brand_keywords': []
        }
        
        # Extract brand information
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            
            # Get brand name
            if 'brandName' in style_data and style_data['brandName']:
                if isinstance(style_data['brandName'], dict):
                    brand_info['brand_name'] = style_data['brandName'].get('name', 'unknown')
                else:
                    brand_info['brand_name'] = str(style_data['brandName'])
            
            # Get brand advertised
            if 'brandAdvertised' in style_data and style_data['brandAdvertised']:
                if isinstance(style_data['brandAdvertised'], dict):
                    brand_info['brand_name'] = style_data['brandAdvertised'].get('name', brand_info['brand_name'])
        
        # Analyze brand tier and reputation
        brand_name = brand_info['brand_name'].lower()
        
        # Luxury brands
        luxury_brands = ['hermes', 'chanel', 'louis vuitton', 'gucci', 'prada', 'dior', 'balenciaga', 'valentino', 'givenchy', 'judith leiber']
        designer_brands = ['michael kors', 'coach', 'kate spade', 'tory burch', 'rebecca minkoff', 'marc jacobs']
        contemporary_brands = ['zara', 'h&m', 'forever 21', 'uniqlo', 'gap']
        
        if any(brand in brand_name for brand in luxury_brands):
            brand_info['brand_tier'] = 'luxury'
            brand_info['reputation_score'] = 9
            brand_info['heritage_indicators'].append('luxury heritage')
        elif any(brand in brand_name for brand in designer_brands):
            brand_info['brand_tier'] = 'designer'
            brand_info['reputation_score'] = 7
            brand_info['heritage_indicators'].append('designer brand')
        elif any(brand in brand_name for brand in contemporary_brands):
            brand_info['brand_tier'] = 'contemporary'
            brand_info['reputation_score'] = 5
        else:
            brand_info['brand_tier'] = 'unknown'
            brand_info['reputation_score'] = 5
        
        # Check for heritage indicators in text
        heritage_keywords = ['couture', 'heritage', 'since', 'established', 'founded', 'artisan', 'handcrafted']
        combined_text = ' '.join([
            product.get('name', ''),
            product.get('description', ''),
        ])
        
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            combined_text += ' ' + ' '.join([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('brandAdvertised', {}).get('copyBrandBio', '') if isinstance(style_data.get('brandAdvertised'), dict) else '',
            ])
        
        for keyword in heritage_keywords:
            if keyword in combined_text.lower():
                brand_info['heritage_indicators'].append(keyword)
                brand_info['reputation_score'] += 1
        
        return brand_info
    
    def extract_dimensions_analysis(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract size and dimensions analysis."""
        dimensions = {
            'size_category': 'unknown',
            'dimensions': {},
            'weight': None,
            'size_notes': [],
            'portability': 'unknown'
        }
        
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            
            # Extract dimensions
            dim_fields = {
                'length': ['itemLengthInches', 'boxedLengthInches'],
                'width': ['itemWidthInches', 'boxedWidthInches'],
                'height': ['itemHeightInches', 'boxedHeightInches'],
                'depth': ['itemDepthInches', 'boxedDepthInches']
            }
            
            for dimension, fields in dim_fields.items():
                for field in fields:
                    if field in style_data and style_data[field]:
                        try:
                            dimensions['dimensions'][dimension] = float(style_data[field])
                            break
                        except (ValueError, TypeError):
                            continue
            
            # Extract weight
            weight_fields = ['itemWeightLbs', 'boxedWeightLbs']
            for field in weight_fields:
                if field in style_data and style_data[field]:
                    try:
                        dimensions['weight'] = float(style_data[field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Determine size category
            if dimensions['dimensions']:
                max_dim = max(dimensions['dimensions'].values())
                if max_dim < 3:
                    dimensions['size_category'] = 'mini'
                    dimensions['portability'] = 'very portable'
                elif max_dim < 6:
                    dimensions['size_category'] = 'small'
                    dimensions['portability'] = 'portable'
                elif max_dim < 12:
                    dimensions['size_category'] = 'medium'
                    dimensions['portability'] = 'moderately portable'
                else:
                    dimensions['size_category'] = 'large'
                    dimensions['portability'] = 'less portable'
            
            # Check for size-related notes
            size_keywords = ['compact', 'mini', 'small', 'medium', 'large', 'oversized', 'petite', 'plus']
            combined_text = ' '.join([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('shortDescription', ''),
            ]).lower()
            
            for keyword in size_keywords:
                if keyword in combined_text:
                    dimensions['size_notes'].append(keyword)
        
        return dimensions
    
    def extract_care_analysis(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract care instructions and maintenance analysis."""
        care_info = {
            'care_level': 'unknown',
            'care_instructions': [],
            'maintenance_tips': [],
            'durability': 'unknown',
            'special_care': []
        }
        
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            
            # Extract care instructions
            care_fields = ['careInstruction']
            for field in care_fields:
                if field in style_data and style_data[field]:
                    if isinstance(style_data[field], list):
                        care_info['care_instructions'].extend(style_data[field])
                    else:
                        care_info['care_instructions'].append(str(style_data[field]))
            
            # Analyze materials for care requirements
            materials = []
            if 'firstMaterial' in style_data and style_data['firstMaterial']:
                if isinstance(style_data['firstMaterial'], dict):
                    materials.append(style_data['firstMaterial'].get('name', '').lower())
                else:
                    materials.append(str(style_data['firstMaterial']).lower())
            
            if 'secondMaterial' in style_data and style_data['secondMaterial']:
                if isinstance(style_data['secondMaterial'], dict):
                    materials.append(style_data['secondMaterial'].get('name', '').lower())
                else:
                    materials.append(str(style_data['secondMaterial']).lower())
            
            # Determine care level based on materials
            high_maintenance = ['leather', 'suede', 'silk', 'wool', 'cashmere']
            medium_maintenance = ['cotton', 'linen', 'denim']
            low_maintenance = ['polyester', 'nylon', 'acrylic', 'plastic']
            
            if any(mat in ' '.join(materials) for mat in high_maintenance):
                care_info['care_level'] = 'high maintenance'
                care_info['maintenance_tips'].append('Professional cleaning recommended')
            elif any(mat in ' '.join(materials) for mat in medium_maintenance):
                care_info['care_level'] = 'medium maintenance'
                care_info['maintenance_tips'].append('Regular cleaning required')
            elif any(mat in ' '.join(materials) for mat in low_maintenance):
                care_info['care_level'] = 'low maintenance'
                care_info['maintenance_tips'].append('Easy care materials')
            
            # Check for special care requirements
            special_care_keywords = ['dry clean only', 'hand wash', 'spot clean', 'professional cleaning']
            combined_text = ' '.join([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
            ]).lower()
            
            for keyword in special_care_keywords:
                if keyword in combined_text:
                    care_info['special_care'].append(keyword)
            
            # Assess durability
            durability_indicators = ['durable', 'sturdy', 'long-lasting', 'quality construction']
            if any(indicator in combined_text for indicator in durability_indicators):
                care_info['durability'] = 'high'
            elif 'delicate' in combined_text or 'fragile' in combined_text:
                care_info['durability'] = 'low'
            else:
                care_info['durability'] = 'medium'
        
        return care_info
    
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
        
        # Check for Bergdorf Goodman format first
        style_data = None
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
        elif 'raw_data' in product and 'pal' in product['raw_data'] and 'style' in product['raw_data']['pal']:
            style_data = product['raw_data']['pal']['style']
        
        if style_data:
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
            'edgy': ['edgy', 'bold', 'dramatic', 'statement'],
            'luxury': ['couture', 'luxury', 'premium', 'high-end', 'designer', 'artisan'],
            'formal': ['formal', 'elegant', 'sophisticated', 'refined', 'evening']
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
            'vacation', 'date night', 'cocktail', 'black tie', 'gala',
            'opera', 'theater', 'special occasion', 'luxury event'
        ]
        
        for occasion in occasions:
            if occasion in combined_text:
                style['occasions'].append(occasion)
        
        return style
    
    def extract_target_market_analysis(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract target market and demographic analysis."""
        market_info = {
            'target_age': 'unknown',
            'target_income': 'unknown',
            'lifestyle': 'unknown',
            'personality_traits': [],
            'market_segment': 'unknown'
        }
        
        # Analyze based on price, brand, and style
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            
            # Extract price for income analysis
            price_fields = ['nmInitialRetail', 'initialCost', 'comparativeValue']
            prices = []
            for field in price_fields:
                if field in style_data and style_data[field]:
                    try:
                        prices.append(float(style_data[field]))
                    except (ValueError, TypeError):
                        continue
            
            if prices:
                avg_price = sum(prices) / len(prices)
                if avg_price > 1000:
                    market_info['target_income'] = 'high income'
                    market_info['market_segment'] = 'luxury market'
                elif avg_price > 500:
                    market_info['target_income'] = 'upper middle class'
                    market_info['market_segment'] = 'premium market'
                elif avg_price > 200:
                    market_info['target_income'] = 'middle class'
                    market_info['market_segment'] = 'mid-market'
                else:
                    market_info['target_income'] = 'budget conscious'
                    market_info['market_segment'] = 'mass market'
            
            # Analyze gender and demographic
            if 'gender' in style_data and style_data['gender']:
                if isinstance(style_data['gender'], dict):
                    gender = style_data['gender'].get('name', '').lower()
                else:
                    gender = str(style_data['gender']).lower()
                
                if 'women' in gender:
                    market_info['target_age'] = 'adult women'
                    market_info['lifestyle'] = 'professional/social'
                elif 'men' in gender:
                    market_info['target_age'] = 'adult men'
                    market_info['lifestyle'] = 'professional/casual'
                else:
                    market_info['target_age'] = 'unisex'
                    market_info['lifestyle'] = 'versatile'
            
            # Analyze personality traits from style and materials
            combined_text = ' '.join([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('shortDescription', ''),
            ]).lower()
            
            personality_keywords = {
                'sophisticated': ['elegant', 'sophisticated', 'refined', 'classic'],
                'bold': ['bold', 'dramatic', 'statement', 'eye-catching'],
                'minimalist': ['minimalist', 'clean', 'simple', 'understated'],
                'romantic': ['romantic', 'feminine', 'delicate', 'soft'],
                'edgy': ['edgy', 'modern', 'contemporary', 'trendy']
            }
            
            for trait, keywords in personality_keywords.items():
                if any(keyword in combined_text for keyword in keywords):
                    market_info['personality_traits'].append(trait)
        
        return market_info
    
    def extract_seasonal_analysis(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract seasonal and trend analysis."""
        seasonal_info = {
            'season': 'unknown',
            'trend_level': 'unknown',
            'timeless_factor': 'unknown',
            'seasonal_keywords': [],
            'trend_indicators': []
        }
        
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            
            # Check for seasonal information in delivery data
            if 'variation' in product['pal'] and 'deliverySeason' in product['pal']['variation']:
                delivery_seasons = product['pal']['variation']['deliverySeason']
                if delivery_seasons:
                    for season_data in delivery_seasons:
                        if 'fashionSeason' in season_data and season_data['fashionSeason']:
                            if isinstance(season_data['fashionSeason'], dict):
                                season_name = season_data['fashionSeason'].get('name', '').lower()
                            else:
                                season_name = str(season_data['fashionSeason']).lower()
                            
                            if 'spring' in season_name:
                                seasonal_info['season'] = 'spring'
                            elif 'summer' in season_name:
                                seasonal_info['season'] = 'summer'
                            elif 'fall' in season_name or 'autumn' in season_name:
                                seasonal_info['season'] = 'fall'
                            elif 'winter' in season_name:
                                seasonal_info['season'] = 'winter'
            
            # Analyze text for seasonal keywords
            combined_text = ' '.join([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('shortDescription', ''),
            ]).lower()
            
            seasonal_keywords = {
                'spring': ['spring', 'fresh', 'light', 'pastel', 'floral'],
                'summer': ['summer', 'beach', 'vacation', 'bright', 'sunny'],
                'fall': ['fall', 'autumn', 'cozy', 'warm', 'earth tones'],
                'winter': ['winter', 'holiday', 'festive', 'warm', 'layering']
            }
            
            for season, keywords in seasonal_keywords.items():
                if any(keyword in combined_text for keyword in keywords):
                    seasonal_info['seasonal_keywords'].append(season)
                    if seasonal_info['season'] == 'unknown':
                        seasonal_info['season'] = season
            
            # Determine trend level
            trend_keywords = ['trendy', 'trending', 'latest', 'new', 'current', 'fashion-forward']
            timeless_keywords = ['classic', 'timeless', 'traditional', 'heritage', 'vintage']
            
            if any(keyword in combined_text for keyword in trend_keywords):
                seasonal_info['trend_level'] = 'trendy'
                seasonal_info['trend_indicators'].extend([kw for kw in trend_keywords if kw in combined_text])
            elif any(keyword in combined_text for keyword in timeless_keywords):
                seasonal_info['trend_level'] = 'timeless'
                seasonal_info['timeless_factor'] = 'high'
            else:
                seasonal_info['trend_level'] = 'neutral'
                seasonal_info['timeless_factor'] = 'medium'
        
        return seasonal_info
    
    def extract_quality_assessment(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract quality and craftsmanship assessment."""
        quality_info = {
            'overall_quality': 'unknown',
            'craftsmanship_level': 'unknown',
            'quality_indicators': [],
            'construction_quality': 'unknown',
            'finish_quality': 'unknown'
        }
        
        if 'pal' in product and 'style' in product['pal']:
            style_data = product['pal']['style']
            
            # Analyze materials for quality
            materials = []
            if 'firstMaterial' in style_data and style_data['firstMaterial']:
                if isinstance(style_data['firstMaterial'], dict):
                    materials.append(style_data['firstMaterial'].get('name', '').lower())
                else:
                    materials.append(str(style_data['firstMaterial']).lower())
            
            if 'secondMaterial' in style_data and style_data['secondMaterial']:
                if isinstance(style_data['secondMaterial'], dict):
                    materials.append(style_data['secondMaterial'].get('name', '').lower())
                else:
                    materials.append(str(style_data['secondMaterial']).lower())
            
            # High-quality materials
            premium_materials = ['leather', 'silk', 'cashmere', 'wool', 'crystal', 'gold', 'silver', 'brass']
            if any(mat in ' '.join(materials) for mat in premium_materials):
                quality_info['quality_indicators'].append('premium materials')
                quality_info['overall_quality'] = 'high'
            
            # Analyze text for quality indicators
            combined_text = ' '.join([
                style_data.get('copyBlock', ''),
                style_data.get('legacyCopyBlock', ''),
                style_data.get('shortDescription', ''),
            ]).lower()
            
            quality_keywords = {
                'handcrafted': ['handcrafted', 'handmade', 'artisan', 'crafted'],
                'premium': ['premium', 'luxury', 'high-end', 'couture'],
                'durable': ['durable', 'sturdy', 'long-lasting', 'quality'],
                'attention_detail': ['attention to detail', 'meticulous', 'precision', 'flawless']
            }
            
            for quality_type, keywords in quality_keywords.items():
                if any(keyword in combined_text for keyword in keywords):
                    quality_info['quality_indicators'].append(quality_type)
                    if quality_info['overall_quality'] == 'unknown':
                        quality_info['overall_quality'] = 'high'
            
            # Assess craftsmanship
            craftsmanship_keywords = ['handcrafted', 'handmade', 'artisan', 'couture', 'made in italy', 'made in france']
            if any(keyword in combined_text for keyword in craftsmanship_keywords):
                quality_info['craftsmanship_level'] = 'artisan'
            elif 'machine made' in combined_text:
                quality_info['craftsmanship_level'] = 'industrial'
            else:
                quality_info['craftsmanship_level'] = 'standard'
            
            # Construction and finish quality
            if 'quality construction' in combined_text or 'premium finish' in combined_text:
                quality_info['construction_quality'] = 'high'
                quality_info['finish_quality'] = 'high'
            elif 'delicate' in combined_text or 'fragile' in combined_text:
                quality_info['construction_quality'] = 'delicate'
                quality_info['finish_quality'] = 'fine'
            else:
                quality_info['construction_quality'] = 'standard'
                quality_info['finish_quality'] = 'standard'
        
        return quality_info
    
    def generate_usage_recommendations(self, product: Dict[str, Any], 
                                     style: Dict[str, Any],
                                     dimensions: Dict[str, Any],
                                     care_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate usage recommendations and styling tips."""
        recommendations = {
            'styling_tips': [],
            'usage_scenarios': [],
            'care_tips': [],
            'storage_tips': [],
            'pairing_suggestions': []
        }
        
        # Generate styling tips based on style analysis
        if style['style_era'] == 'luxury':
            recommendations['styling_tips'].append('Pair with elegant, sophisticated pieces')
            recommendations['styling_tips'].append('Perfect for formal occasions and special events')
        elif style['style_era'] == 'modern':
            recommendations['styling_tips'].append('Works well with contemporary, minimalist outfits')
            recommendations['styling_tips'].append('Great for professional settings')
        elif style['style_era'] == 'vintage':
            recommendations['styling_tips'].append('Complements vintage-inspired or retro looks')
            recommendations['styling_tips'].append('Adds character to classic ensembles')
        
        # Usage scenarios based on occasions
        if style['occasions']:
            for occasion in style['occasions']:
                recommendations['usage_scenarios'].append(f'Ideal for {occasion} events')
        
        # Care tips based on materials and care analysis
        if care_info['care_level'] == 'high maintenance':
            recommendations['care_tips'].append('Handle with care - avoid rough surfaces')
            recommendations['care_tips'].append('Store in protective case when not in use')
        elif care_info['care_level'] == 'medium maintenance':
            recommendations['care_tips'].append('Regular cleaning recommended')
            recommendations['care_tips'].append('Store in dry, cool place')
        else:
            recommendations['care_tips'].append('Easy to maintain with regular care')
        
        # Storage tips based on size and materials
        if dimensions['size_category'] == 'mini':
            recommendations['storage_tips'].append('Compact size makes it perfect for small spaces')
            recommendations['storage_tips'].append('Easy to carry in any bag')
        elif dimensions['size_category'] == 'large':
            recommendations['storage_tips'].append('Requires adequate storage space')
            recommendations['storage_tips'].append('Consider protective storage solutions')
        
        # Pairing suggestions based on colors and style
        if style['color_palette']:
            color = style['color_palette'][0].lower()
            if color in ['black', 'white', 'gray']:
                recommendations['pairing_suggestions'].append('Versatile neutral colors - pairs with everything')
            elif color in ['red', 'pink']:
                recommendations['pairing_suggestions'].append('Bold colors - pair with neutrals for balance')
            elif color in ['blue', 'green']:
                recommendations['pairing_suggestions'].append('Cool tones - complements warm earth tones')
        
        return recommendations
    
    def extract_inventory_analysis(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract inventory and SKU analysis."""
        inventory_info = {
            'sku_number': 'unknown',
            'inventory_status': 'unknown',
            'quantity_available': 0,
            'quantity_on_hand': 0,
            'quantity_on_order': 0,
            'inventory_locations': [],
            'stock_status': 'unknown',
            'next_availability_date': None
        }
        
        if 'pal' in product and 'sku' in product['pal']:
            sku_data = product['pal']['sku']
            
            # Extract SKU number
            if 'skuNumber' in sku_data:
                inventory_info['sku_number'] = str(sku_data['skuNumber'])
            
            # Check store fronts for inventory
            if 'storeFronts' in sku_data:
                store_fronts = sku_data['storeFronts']
                
                for store_name, store_data in store_fronts.items():
                    if 'inventory' in store_data:
                        inventory = store_data['inventory']
                        
                        # Extract inventory status
                        if 'status' in inventory:
                            inventory_info['inventory_status'] = inventory['status']
                        
                        # Extract quantities
                        if 'totalQuantity' in inventory:
                            inventory_info['quantity_available'] += inventory['totalQuantity']
                        
                        if 'onHandQuantity' in inventory:
                            inventory_info['quantity_on_hand'] += inventory['onHandQuantity']
                        
                        if 'futureQuantity' in inventory:
                            inventory_info['quantity_on_order'] += inventory['futureQuantity']
                        
                        # Extract next availability date
                        if 'nextAvailabilityDate' in inventory and inventory['nextAvailabilityDate']:
                            inventory_info['next_availability_date'] = inventory['nextAvailabilityDate']
                        
                        # Track inventory locations
                        inventory_info['inventory_locations'].append({
                            'store': store_name,
                            'status': inventory.get('status', 'unknown'),
                            'quantity': inventory.get('totalQuantity', 0),
                            'on_hand': inventory.get('onHandQuantity', 0)
                        })
            
            # Determine overall stock status
            total_qty = inventory_info['quantity_available']
            if total_qty > 0:
                inventory_info['stock_status'] = 'in_stock'
            elif inventory_info['quantity_on_order'] > 0:
                inventory_info['stock_status'] = 'on_order'
            else:
                inventory_info['stock_status'] = 'out_of_stock'
        
        return inventory_info
    
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
        price_analysis = self.extract_price_analysis(product)
        brand_analysis = self.extract_brand_analysis(product)
        dimensions = self.extract_dimensions_analysis(product)
        care_analysis = self.extract_care_analysis(product)
        market_analysis = self.extract_target_market_analysis(product)
        seasonal_analysis = self.extract_seasonal_analysis(product)
        quality_assessment = self.extract_quality_assessment(product)
        inventory_analysis = self.extract_inventory_analysis(product)
        recommendations = self.generate_usage_recommendations(product, style, dimensions, care_analysis)
        
        # Generate description
        description = self.generate_product_description(product, sustainability, materials, style)
        
        # Compile comprehensive analysis
        analysis = {
            'product_id': product['id'],
            'name': product['name'],
            'category': product['category_id'],
            'generated_description': description,
            'sustainability': sustainability,
            'materials': materials,
            'style': style,
            'price_analysis': price_analysis,
            'brand_analysis': brand_analysis,
            'dimensions': dimensions,
            'care_analysis': care_analysis,
            'market_analysis': market_analysis,
            'seasonal_analysis': seasonal_analysis,
            'quality_assessment': quality_assessment,
            'inventory_analysis': inventory_analysis,
            'recommendations': recommendations,
            'analysis_summary': {
                'is_sustainable': sustainability['is_sustainable'],
                'sustainability_score': sustainability['sustainability_score'],
                'primary_materials': materials['primary_materials'][:3],
                'style_era': style['style_era'],
                'target_occasions': style['occasions'][:3],
                'price_range': price_analysis['price_range'],
                'brand_tier': brand_analysis['brand_tier'],
                'quality_level': quality_assessment['overall_quality'],
                'sku_number': inventory_analysis['sku_number'],
                'stock_status': inventory_analysis['stock_status'],
                'quantity_available': inventory_analysis['quantity_available']
            }
        }
        
        return analysis

def read_config_file(config_file_path: str) -> Dict[str, Any]:
    """Read configuration from a text file."""
    config = {
        'json_file': '',
        'categories': None,
        'min_products': 1,
        'output_file': None
    }
    
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'json_file':
                        config['json_file'] = value
                    elif key == 'categories':
                        if value.lower() != 'none':
                            config['categories'] = [cat.strip() for cat in value.split(',')]
                    elif key == 'min_products':
                        config['min_products'] = int(value)
                    elif key == 'output_file':
                        config['output_file'] = value
                    else:
                        print(f"Warning: Unknown configuration key '{key}' on line {line_num}")
                else:
                    print(f"Warning: Invalid configuration line {line_num}: {line}")
    
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        return None
    
    return config

def analyze_products_from_json(json_file_path: str, categories: Optional[List[str]] = None, 
                              min_products_per_category: int = 1, output_file: Optional[str] = None) -> None:
    """
    Analyze products from JSON file and generate descriptions with attributes.
    
    Args:
        json_file_path: Path to JSON file containing product data
        categories: List of category IDs to analyze (None for all suitable categories)
        min_products_per_category: Minimum products required per category
        output_file: Optional file to save results to
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
    results_text = ""
    results_text += f"\n=== Analysis Results ===\n"
    
    for analysis in analyses:
        results_text += f"\n🎯 Product: {analysis['name']}\n"
        results_text += f"   Category: {analysis['category']}\n"
        results_text += f"   ID: {analysis['product_id']}\n"
        
        results_text += f"\n📝 Generated Description:\n"
        results_text += f"   {analysis['generated_description']}\n"
        
        results_text += f"\n🌱 Sustainability Analysis:\n"
        sustainability = analysis['sustainability']
        results_text += f"   Sustainable: {'✅ Yes' if sustainability['is_sustainable'] else '❌ No'}\n"
        results_text += f"   Score: {sustainability['sustainability_score']}/10\n"
        
        if sustainability['sustainable_materials']:
            results_text += f"   Sustainable Materials: {', '.join(sustainability['sustainable_materials'])}\n"
        
        if sustainability['certifications']:
            results_text += f"   Certifications: {', '.join(sustainability['certifications'])}\n"
        
        if sustainability['eco_friendly_features']:
            results_text += f"   Eco-friendly Features: {', '.join(sustainability['eco_friendly_features'][:3])}\n"
        
        results_text += f"\n🏗️  Materials & Construction:\n"
        materials = analysis['materials']
        if materials['primary_materials']:
            results_text += f"   Primary Materials: {', '.join(materials['primary_materials'][:3])}\n"
        
        if materials['construction_methods']:
            results_text += f"   Construction: {', '.join(materials['construction_methods'][:2])}\n"
        
        if materials['finish_types']:
            results_text += f"   Finish: {', '.join(materials['finish_types'][:2])}\n"
        
        results_text += f"\n🎨 Style & Design:\n"
        style = analysis['style']
        if style['style_era']:
            results_text += f"   Style Era: {style['style_era']}\n"
        
        if style['design_style']:
            results_text += f"   Design Style: {style['design_style']}\n"
        
        if style['color_palette']:
            results_text += f"   Colors: {', '.join(style['color_palette'][:3])}\n"
        
        if style['occasions']:
            results_text += f"   Occasions: {', '.join(style['occasions'][:3])}\n"
        
        results_text += f"\n💰 Price & Value Analysis:\n"
        price = analysis['price_analysis']
        if price['comparative_value']:
            results_text += f"   Price Range: {price['price_range']} (${price['comparative_value']:.0f})\n"
            results_text += f"   Luxury Level: {price['luxury_level']}\n"
            results_text += f"   Value Assessment: {price['value_assessment']}\n"
        
        results_text += f"\n🏷️  Brand Analysis:\n"
        brand = analysis['brand_analysis']
        results_text += f"   Brand: {brand['brand_name']}\n"
        results_text += f"   Brand Tier: {brand['brand_tier']}\n"
        results_text += f"   Reputation Score: {brand['reputation_score']}/10\n"
        if brand['heritage_indicators']:
            results_text += f"   Heritage: {', '.join(brand['heritage_indicators'])}\n"
        
        results_text += f"\n📏 Dimensions & Size:\n"
        dims = analysis['dimensions']
        results_text += f"   Size Category: {dims['size_category']}\n"
        results_text += f"   Portability: {dims['portability']}\n"
        if dims['dimensions']:
            dim_str = ', '.join([f"{k}: {v}\"" for k, v in dims['dimensions'].items()])
            results_text += f"   Dimensions: {dim_str}\n"
        if dims['weight']:
            results_text += f"   Weight: {dims['weight']} lbs\n"
        
        results_text += f"\n🧽 Care & Maintenance:\n"
        care = analysis['care_analysis']
        results_text += f"   Care Level: {care['care_level']}\n"
        results_text += f"   Durability: {care['durability']}\n"
        if care['maintenance_tips']:
            results_text += f"   Tips: {', '.join(care['maintenance_tips'])}\n"
        
        results_text += f"\n🎯 Target Market:\n"
        market = analysis['market_analysis']
        results_text += f"   Target Age: {market['target_age']}\n"
        results_text += f"   Target Income: {market['target_income']}\n"
        results_text += f"   Market Segment: {market['market_segment']}\n"
        if market['personality_traits']:
            results_text += f"   Personality: {', '.join(market['personality_traits'])}\n"
        
        results_text += f"\n📅 Seasonal & Trends:\n"
        seasonal = analysis['seasonal_analysis']
        results_text += f"   Season: {seasonal['season']}\n"
        results_text += f"   Trend Level: {seasonal['trend_level']}\n"
        results_text += f"   Timeless Factor: {seasonal['timeless_factor']}\n"
        
        results_text += f"\n⭐ Quality Assessment:\n"
        quality = analysis['quality_assessment']
        results_text += f"   Overall Quality: {quality['overall_quality']}\n"
        results_text += f"   Craftsmanship: {quality['craftsmanship_level']}\n"
        if quality['quality_indicators']:
            results_text += f"   Quality Indicators: {', '.join(quality['quality_indicators'])}\n"
        
        results_text += f"\n💡 Recommendations:\n"
        recs = analysis['recommendations']
        if recs['styling_tips']:
            results_text += f"   Styling Tips: {', '.join(recs['styling_tips'][:2])}\n"
        if recs['usage_scenarios']:
            results_text += f"   Usage: {', '.join(recs['usage_scenarios'][:2])}\n"
        if recs['care_tips']:
            results_text += f"   Care Tips: {', '.join(recs['care_tips'][:2])}\n"
        
        results_text += f"\n📊 Summary:\n"
        summary = analysis['analysis_summary']
        results_text += f"   Sustainable: {'Yes' if summary['is_sustainable'] else 'No'}\n"
        results_text += f"   Key Materials: {', '.join(summary['primary_materials']) if summary['primary_materials'] else 'Unknown'}\n"
        results_text += f"   Style: {summary['style_era'] if summary['style_era'] else 'Unknown'}\n"
        results_text += f"   Price Range: {summary['price_range']}\n"
        results_text += f"   Brand Tier: {summary['brand_tier']}\n"
        results_text += f"   Quality Level: {summary['quality_level']}\n"
        results_text += f"   Best For: {', '.join(summary['target_occasions']) if summary['target_occasions'] else 'Various'}\n"
    
    # Overall statistics
    results_text += f"\n=== Overall Statistics ===\n"
    
    sustainable_count = sum(1 for a in analyses if a['sustainability']['is_sustainable'])
    avg_sustainability_score = np.mean([a['sustainability']['sustainability_score'] for a in analyses])
    
    results_text += f"Total Products Analyzed: {len(analyses)}\n"
    results_text += f"Sustainable Products: {sustainable_count}/{len(analyses)} ({sustainable_count/len(analyses)*100:.1f}%)\n"
    results_text += f"Average Sustainability Score: {avg_sustainability_score:.1f}/10\n"
    
    # Most common materials
    all_materials = []
    for analysis in analyses:
        all_materials.extend(analysis['materials']['primary_materials'])
    
    if all_materials:
        material_counts = Counter(all_materials)
        results_text += f"Most Common Materials: {dict(material_counts.most_common(3))}\n"
    
    # Most common styles
    all_styles = [a['style']['style_era'] for a in analyses if a['style']['style_era']]
    if all_styles:
        style_counts = Counter(all_styles)
        results_text += f"Most Common Styles: {dict(style_counts.most_common(3))}\n"
    
    # Print results to console
    print(results_text)
    
    # Save to file if specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(results_text)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Error saving results to file: {e}")

def main():
    """Main function for product analysis."""
    parser = argparse.ArgumentParser(
        description="Enhanced product analyzer with description generation and attribute extraction"
    )
    parser.add_argument(
        "--config-file", 
        required=True,
        help="Path to configuration text file"
    )
    
    args = parser.parse_args()
    
    # Read configuration from file
    config = read_config_file(args.config_file)
    if config is None:
        return 1
    
    # Validate required configuration
    if not config['json_file']:
        print("Error: json_file is required in configuration file")
        return 1
    
    try:
        analyze_products_from_json(
            json_file_path=config['json_file'],
            categories=config['categories'],
            min_products_per_category=config['min_products'],
            output_file=config['output_file']
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
