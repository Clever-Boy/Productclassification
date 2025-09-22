#!/usr/bin/env python3
"""
Multi-product analyzer that reads multiple JSON files from a product lists configuration
and displays comprehensive analysis for each product.
"""
import argparse
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import Counter, defaultdict
from product_analyzer_from_file import ProductAttributeExtractor
from json_data_loader import JSONDataLoader

class MultiProductAnalyzer:
    """Analyzes multiple products from different JSON files."""
    
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
        self.analyzer = ProductAttributeExtractor(cache_dir)
    
    def read_product_lists_config(self, config_file_path: str) -> List[Dict[str, Any]]:
        """Read product lists configuration from file."""
        product_lists = []
        
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                json_files = []
                
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Check for new product list section
                    if line.startswith('[') and line.endswith(']'):
                        # Save previous list if exists
                        if json_files:
                            # Auto-generate list name from first file
                            first_file = json_files[0]
                            list_name = self._generate_list_name_from_file(first_file)
                            product_lists.append({
                                'name': list_name,
                                'json_files': json_files.copy(),
                                'categories': None,  # Will be auto-detected
                                'min_products': 1,   # Default value
                                'output_file': None   # Will be auto-generated
                            })
                            json_files.clear()
                    
                    # Simple JSON file path (no key=value format)
                    elif not '=' in line and not line.startswith('['):
                        # Treat as JSON file path
                        json_files.append(line)
                    else:
                        print(f"Warning: Invalid configuration line {line_num}: {line}")
                
                # Add the last list if there are files
                if json_files:
                    # Auto-generate list name from first file
                    first_file = json_files[0]
                    list_name = self._generate_list_name_from_file(first_file)
                    product_lists.append({
                        'name': list_name,
                        'json_files': json_files,
                        'categories': None,  # Will be auto-detected
                        'min_products': 1,   # Default value
                        'output_file': None   # Will be auto-generated
                    })
        
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file_path}' not found.")
            return []
        except Exception as e:
            print(f"Error reading configuration file: {e}")
            return []
        
        return product_lists
    
    def _generate_list_name_from_file(self, file_path: str) -> str:
        """Generate a list name from the JSON file path."""
        # Extract filename without extension
        filename = Path(file_path).stem
        
        # Clean up the filename
        clean_name = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name.replace('_', ' ').replace('-', ' ')
        
        # Capitalize words
        clean_name = ' '.join(word.capitalize() for word in clean_name.split())
        
        # If empty or too short, use a default
        if not clean_name or len(clean_name) < 3:
            clean_name = "Product Collection"
        
        return clean_name
    
    def analyze_product_list(self, product_list_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze all products in a product list."""
        list_name = product_list_config['name']
        json_files = product_list_config['json_files']
        categories = product_list_config['categories']
        min_products = product_list_config['min_products']
        
        # Auto-generate output file name if not specified
        if not product_list_config.get('output_file'):
            safe_name = "".join(c for c in list_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_').lower()
            # Create analysis files in src folder
            product_list_config['output_file'] = f"src/{safe_name}_analysis.txt"
        
        print(f"\n{'='*60}")
        print(f"ANALYZING PRODUCT LIST: {list_name}")
        print(f"{'='*60}")
        print(f"JSON Files: {len(json_files)}")
        print(f"Categories: {categories if categories else 'Auto-detect from files'}")
        print(f"Min Products per Category: {min_products}")
        print(f"Output File: {product_list_config['output_file']}")
        
        all_analyses = []
        all_products = []
        
        # Process each JSON file
        for i, json_file in enumerate(json_files):
            print(f"\n--- Processing File {i+1}/{len(json_files)}: {json_file} ---")
            
            try:
                # Load JSON data
                loader = JSONDataLoader(json_file)
                loader.print_statistics()
                
                # Get suitable categories if none specified
                if categories is None:
                    file_categories = loader.get_categories_to_predict(min_products)
                else:
                    file_categories = categories
                
                if not file_categories:
                    print(f"No suitable categories found in {json_file}")
                    continue
                
                # Get products for selected categories
                products = loader.get_products(file_categories)
                print(f"Analyzing {len(products)} products from {len(file_categories)} categories")
                
                # Analyze each product
                for j, product in enumerate(products):
                    print(f"\nProcessing product {j+1}/{len(products)}")
                    analysis = self.analyzer.analyze_product(product)
                    analysis['source_file'] = json_file
                    analysis['list_name'] = list_name
                    all_analyses.append(analysis)
                    all_products.append(product)
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
        
        # Compile results
        results = {
            'list_name': list_name,
            'total_products': len(all_analyses),
            'source_files': json_files,
            'analyses': all_analyses,
            'products': all_products,
            'summary_stats': self._calculate_summary_stats(all_analyses)
        }
        
        return results
    
    def _calculate_summary_stats(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics across all analyses."""
        if not analyses:
            return {}
        
        stats = {
            'total_products': len(analyses),
            'sustainable_count': sum(1 for a in analyses if a['sustainability']['is_sustainable']),
            'avg_sustainability_score': np.mean([a['sustainability']['sustainability_score'] for a in analyses]),
            'price_ranges': Counter([a['price_analysis']['price_range'] for a in analyses]),
            'brand_tiers': Counter([a['brand_analysis']['brand_tier'] for a in analyses]),
            'quality_levels': Counter([a['quality_assessment']['overall_quality'] for a in analyses]),
            'style_eras': Counter([a['style']['style_era'] for a in analyses if a['style']['style_era']]),
            'size_categories': Counter([a['dimensions']['size_category'] for a in analyses]),
            'care_levels': Counter([a['care_analysis']['care_level'] for a in analyses]),
            'market_segments': Counter([a['market_analysis']['market_segment'] for a in analyses]),
            'trend_levels': Counter([a['seasonal_analysis']['trend_level'] for a in analyses])
        }
        
        # Calculate percentages
        total = stats['total_products']
        if total > 0:
            stats['sustainable_percentage'] = (stats['sustainable_count'] / total) * 100
        
        return stats
    
    def display_product_parameters(self, analysis: Dict[str, Any]) -> str:
        """Display detailed parameters for a single product."""
        result = f"\n🎯 PRODUCT: {analysis['name']}\n"
        result += f"   ID: {analysis['product_id']}\n"
        result += f"   Category: {analysis['category']}\n"
        result += f"   Source: {analysis['source_file']}\n"
        result += f"   List: {analysis['list_name']}\n"
        
        # Basic Info
        result += f"\n📝 DESCRIPTION:\n"
        result += f"   {analysis['generated_description']}\n"
        
        # Sustainability
        sustainability = analysis['sustainability']
        result += f"\n🌱 SUSTAINABILITY:\n"
        result += f"   Sustainable: {'✅ Yes' if sustainability['is_sustainable'] else '❌ No'}\n"
        result += f"   Score: {sustainability['sustainability_score']}/10\n"
        if sustainability['sustainable_materials']:
            result += f"   Sustainable Materials: {', '.join(sustainability['sustainable_materials'])}\n"
        if sustainability['certifications']:
            result += f"   Certifications: {', '.join(sustainability['certifications'])}\n"
        
        # Materials
        materials = analysis['materials']
        result += f"\n🏗️  MATERIALS:\n"
        if materials['primary_materials']:
            result += f"   Primary: {', '.join(materials['primary_materials'])}\n"
        if materials['secondary_materials']:
            result += f"   Secondary: {', '.join(materials['secondary_materials'])}\n"
        if materials['construction_methods']:
            result += f"   Construction: {', '.join(materials['construction_methods'])}\n"
        
        # Style
        style = analysis['style']
        result += f"\n🎨 STYLE:\n"
        result += f"   Era: {style['style_era'] if style['style_era'] else 'Unknown'}\n"
        result += f"   Design: {style['design_style'] if style['design_style'] else 'Unknown'}\n"
        if style['color_palette']:
            result += f"   Colors: {', '.join(style['color_palette'])}\n"
        if style['occasions']:
            result += f"   Occasions: {', '.join(style['occasions'])}\n"
        
        # Price
        price = analysis['price_analysis']
        result += f"\n💰 PRICE:\n"
        if price['comparative_value']:
            result += f"   Range: {price['price_range']} (${price['comparative_value']:.0f})\n"
            result += f"   Luxury Level: {price['luxury_level']}\n"
            result += f"   Value: {price['value_assessment']}\n"
        
        # Brand
        brand = analysis['brand_analysis']
        result += f"\n🏷️  BRAND:\n"
        result += f"   Name: {brand['brand_name']}\n"
        result += f"   Tier: {brand['brand_tier']}\n"
        result += f"   Reputation: {brand['reputation_score']}/10\n"
        if brand['heritage_indicators']:
            result += f"   Heritage: {', '.join(brand['heritage_indicators'])}\n"
        
        # Dimensions
        dims = analysis['dimensions']
        result += f"\n📏 DIMENSIONS:\n"
        result += f"   Size: {dims['size_category']}\n"
        result += f"   Portability: {dims['portability']}\n"
        if dims['dimensions']:
            dim_str = ', '.join([f"{k}: {v}\"" for k, v in dims['dimensions'].items()])
            result += f"   Measurements: {dim_str}\n"
        if dims['weight']:
            result += f"   Weight: {dims['weight']} lbs\n"
        
        # Care
        care = analysis['care_analysis']
        result += f"\n🧽 CARE:\n"
        result += f"   Level: {care['care_level']}\n"
        result += f"   Durability: {care['durability']}\n"
        if care['maintenance_tips']:
            result += f"   Tips: {', '.join(care['maintenance_tips'])}\n"
        
        # Market
        market = analysis['market_analysis']
        result += f"\n🎯 MARKET:\n"
        result += f"   Age: {market['target_age']}\n"
        result += f"   Income: {market['target_income']}\n"
        result += f"   Segment: {market['market_segment']}\n"
        if market['personality_traits']:
            result += f"   Personality: {', '.join(market['personality_traits'])}\n"
        
        # Seasonal
        seasonal = analysis['seasonal_analysis']
        result += f"\n📅 SEASONAL:\n"
        result += f"   Season: {seasonal['season']}\n"
        result += f"   Trend: {seasonal['trend_level']}\n"
        result += f"   Timeless: {seasonal['timeless_factor']}\n"
        
        # Quality
        quality = analysis['quality_assessment']
        result += f"\n⭐ QUALITY:\n"
        result += f"   Overall: {quality['overall_quality']}\n"
        result += f"   Craftsmanship: {quality['craftsmanship_level']}\n"
        if quality['quality_indicators']:
            result += f"   Indicators: {', '.join(quality['quality_indicators'])}\n"
        
        # Recommendations
        recs = analysis['recommendations']
        result += f"\n💡 RECOMMENDATIONS:\n"
        if recs['styling_tips']:
            result += f"   Styling: {', '.join(recs['styling_tips'][:2])}\n"
        if recs['usage_scenarios']:
            result += f"   Usage: {', '.join(recs['usage_scenarios'][:2])}\n"
        if recs['care_tips']:
            result += f"   Care: {', '.join(recs['care_tips'][:2])}\n"
        
        return result
    
    def display_summary_stats(self, results: Dict[str, Any]) -> str:
        """Display summary statistics for a product list."""
        stats = results['summary_stats']
        if not stats:
            return "No statistics available."
        
        result = f"\n{'='*60}\n"
        result += f"SUMMARY STATISTICS: {results['list_name']}\n"
        result += f"{'='*60}\n"
        
        result += f"\n📊 OVERVIEW:\n"
        result += f"   Total Products: {stats['total_products']}\n"
        result += f"   Sustainable: {stats['sustainable_count']}/{stats['total_products']} ({stats.get('sustainable_percentage', 0):.1f}%)\n"
        result += f"   Avg Sustainability Score: {stats['avg_sustainability_score']:.1f}/10\n"
        
        result += f"\n💰 PRICE DISTRIBUTION:\n"
        for price_range, count in stats['price_ranges'].most_common():
            result += f"   {price_range}: {count} products\n"
        
        result += f"\n🏷️  BRAND DISTRIBUTION:\n"
        for brand_tier, count in stats['brand_tiers'].most_common():
            result += f"   {brand_tier}: {count} products\n"
        
        result += f"\n⭐ QUALITY DISTRIBUTION:\n"
        for quality_level, count in stats['quality_levels'].most_common():
            result += f"   {quality_level}: {count} products\n"
        
        result += f"\n🎨 STYLE DISTRIBUTION:\n"
        for style_era, count in stats['style_eras'].most_common():
            result += f"   {style_era}: {count} products\n"
        
        result += f"\n📏 SIZE DISTRIBUTION:\n"
        for size_category, count in stats['size_categories'].most_common():
            result += f"   {size_category}: {count} products\n"
        
        result += f"\n🧽 CARE DISTRIBUTION:\n"
        for care_level, count in stats['care_levels'].most_common():
            result += f"   {care_level}: {count} products\n"
        
        result += f"\n🎯 MARKET DISTRIBUTION:\n"
        for market_segment, count in stats['market_segments'].most_common():
            result += f"   {market_segment}: {count} products\n"
        
        result += f"\n📅 TREND DISTRIBUTION:\n"
        for trend_level, count in stats['trend_levels'].most_common():
            result += f"   {trend_level}: {count} products\n"
        
        return result
    
    def analyze_all_lists(self, config_file_path: str) -> List[Dict[str, Any]]:
        """Analyze all product lists from configuration file."""
        product_lists = self.read_product_lists_config(config_file_path)
        
        if not product_lists:
            print("No product lists found in configuration file.")
            return []
        
        all_results = []
        
        for product_list_config in product_lists:
            try:
                results = self.analyze_product_list(product_list_config)
                all_results.append(results)
                
                # Display individual product parameters
                print(f"\n{'='*80}")
                print(f"DETAILED PRODUCT PARAMETERS")
                print(f"{'='*80}")
                
                for analysis in results['analyses']:
                    print(self.display_product_parameters(analysis))
                
                # Display summary statistics
                print(self.display_summary_stats(results))
                
                # Save to file if specified
                if product_list_config.get('output_file'):
                    self.save_results_to_file(results, product_list_config['output_file'])
                
            except Exception as e:
                print(f"Error analyzing product list '{product_list_config['name']}': {e}")
                continue
        
        return all_results
    
    def save_results_to_file(self, results: Dict[str, Any], output_file: str) -> None:
        """Save analysis results to file."""
        try:
            # Ensure the directory exists
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"PRODUCT ANALYSIS RESULTS: {results['list_name']}\n")
                f.write("="*60 + "\n\n")
                
                # Write individual product parameters
                f.write("DETAILED PRODUCT PARAMETERS\n")
                f.write("="*60 + "\n")
                
                for analysis in results['analyses']:
                    f.write(self.display_product_parameters(analysis))
                    f.write("\n")
                
                # Write summary statistics
                f.write(self.display_summary_stats(results))
            
            print(f"\nResults saved to: {output_file}")
            
        except Exception as e:
            print(f"Error saving results to file: {e}")

def main():
    """Main function for multi-product analysis."""
    parser = argparse.ArgumentParser(
        description="Multi-product analyzer that reads multiple JSON files from product lists configuration"
    )
    parser.add_argument(
        "--product-lists-config", 
        required=True,
        help="Path to product lists configuration file"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = MultiProductAnalyzer()
        results = analyzer.analyze_all_lists(args.product_lists_config)
        
        if results:
            print(f"\n{'='*80}")
            print(f"ANALYSIS COMPLETE")
            print(f"{'='*80}")
            print(f"Total product lists analyzed: {len(results)}")
            total_products = sum(r['total_products'] for r in results)
            print(f"Total products analyzed: {total_products}")
        else:
            print("No results generated.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
