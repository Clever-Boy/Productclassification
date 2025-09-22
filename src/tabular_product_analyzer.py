#!/usr/bin/env python3
"""
Tabular product analyzer that creates charts with product ID as rows and metrics as columns.
Includes inventory analysis and SKU quantity tracking.
"""
import argparse
import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
from multi_product_analyzer import MultiProductAnalyzer

class TabularProductAnalyzer:
    """Creates tabular charts from product analysis data."""
    
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
        self.multi_analyzer = MultiProductAnalyzer(cache_dir)
    
    def _safe_join(self, items, max_items: int = None, separator: str = ', ') -> str:
        """Safely join list items, handling different data types."""
        if not items:
            return ''
        
        # Limit items if max_items is specified
        if max_items is not None:
            items = items[:max_items]
        
        # Convert all items to strings and filter out empty ones
        string_items = []
        for item in items:
            if item is not None:
                if isinstance(item, dict):
                    # If it's a dict, try to get a meaningful string representation
                    if 'name' in item:
                        string_items.append(str(item['name']))
                    elif 'value' in item:
                        string_items.append(str(item['value']))
                    else:
                        string_items.append(str(item))
                else:
                    string_items.append(str(item))
        
        return separator.join(string_items)
    
    def create_comprehensive_chart(self, analyses: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create a comprehensive tabular chart with ALL metrics including inventory."""
        
        # Prepare data for DataFrame
        chart_data = []
        
        for analysis in analyses:
            row_data = {
                # === BASIC INFORMATION ===
                'Product_ID': analysis['product_id'],
                'Product_Name': analysis['name'],
                'Category': analysis['category'],
                'Source_File': analysis.get('source_file', 'unknown'),
                'List_Name': analysis.get('list_name', 'unknown'),
                'Generated_Description': analysis.get('generated_description', '')[:200] + '...' if len(analysis.get('generated_description', '')) > 200 else analysis.get('generated_description', ''),
                'Original_Description': analysis.get('description', '')[:200] + '...' if len(analysis.get('description', '')) > 200 else analysis.get('description', ''),
                
                # === INVENTORY & SKU ANALYSIS ===
                'SKU_Number': analysis['inventory_analysis'].get('sku_number', 'unknown'),
                'Stock_Status': analysis['inventory_analysis'].get('stock_status', 'unknown'),
                'Quantity_Available': analysis['inventory_analysis'].get('quantity_available', 0),
                'Quantity_On_Hand': analysis['inventory_analysis'].get('quantity_on_hand', 0),
                'Quantity_On_Order': analysis['inventory_analysis'].get('quantity_on_order', 0),
                'Inventory_Status': analysis['inventory_analysis'].get('inventory_status', 'unknown'),
                'Next_Availability_Date': analysis['inventory_analysis'].get('next_availability_date', 'unknown'),
                'Inventory_Locations': len(analysis['inventory_analysis'].get('inventory_locations', [])),
                
                # === PRICE & VALUE ANALYSIS ===
                'Price_Range': analysis['price_analysis'].get('price_range', 'unknown'),
                'Luxury_Level': analysis['price_analysis'].get('luxury_level', 'unknown'),
                'Value_Assessment': analysis['price_analysis'].get('value_assessment', 'unknown'),
                'Comparative_Value': analysis['price_analysis'].get('comparative_value', 'unknown'),
                'Price_Positioning': analysis['price_analysis'].get('price_positioning', 'unknown'),
                'Value_Score': analysis['price_analysis'].get('value_score', 'unknown'),
                
                # === BRAND & QUALITY ANALYSIS ===
                'Brand_Name': analysis['brand_analysis'].get('brand_name', 'unknown'),
                'Brand_Tier': analysis['brand_analysis'].get('brand_tier', 'unknown'),
                'Reputation_Score': analysis['brand_analysis'].get('reputation_score', 'unknown'),
                'Brand_Heritage': analysis['brand_analysis'].get('brand_heritage', 'unknown'),
                'Brand_Exclusivity': analysis['brand_analysis'].get('brand_exclusivity', 'unknown'),
                'Overall_Quality': analysis['quality_assessment'].get('overall_quality', 'unknown'),
                'Craftsmanship_Level': analysis['quality_assessment'].get('craftsmanship_level', 'unknown'),
                'Construction_Quality': analysis['quality_assessment'].get('construction_quality', 'unknown'),
                'Finish_Quality': analysis['quality_assessment'].get('finish_quality', 'unknown'),
                'Quality_Indicators': self._safe_join(analysis['quality_assessment'].get('quality_indicators', []), 3),
                
                # === MATERIALS & STYLE ANALYSIS ===
                'Primary_Materials': self._safe_join(analysis['materials'].get('primary_materials', []), 3),
                'Secondary_Materials': self._safe_join(analysis['materials'].get('secondary_materials', []), 3),
                'Material_Quality': analysis['materials'].get('material_quality', 'unknown'),
                'Material_Durability': analysis['materials'].get('material_durability', 'unknown'),
                'Style_Era': analysis['style'].get('style_era', 'unknown'),
                'Design_Style': analysis['style'].get('design_style', 'unknown'),
                'Color_Palette': self._safe_join(analysis['style'].get('color_palette', []), 3),
                'Occasions': self._safe_join(analysis['style'].get('occasions', []), 3),
                'Gender': analysis['style'].get('gender', 'unknown'),
                'Formality_Level': analysis['style'].get('formality_level', 'unknown'),
                
                # === DIMENSIONS & CARE ANALYSIS ===
                'Size_Category': analysis['dimensions'].get('size_category', 'unknown'),
                'Portability': analysis['dimensions'].get('portability', 'unknown'),
                'Weight_Lbs': analysis['dimensions'].get('weight', 'unknown'),
                'Dimensions_Summary': analysis['dimensions'].get('dimensions_summary', 'unknown'),
                'Care_Level': analysis['care_analysis'].get('care_level', 'unknown'),
                'Durability': analysis['care_analysis'].get('durability', 'unknown'),
                'Maintenance_Requirements': self._safe_join(analysis['care_analysis'].get('maintenance_requirements', []), 3),
                'Care_Instructions': self._safe_join(analysis['care_analysis'].get('care_instructions', []), 3),
                
                # === SUSTAINABILITY ANALYSIS ===
                'Is_Sustainable': analysis['sustainability'].get('is_sustainable', False),
                'Sustainability_Score': analysis['sustainability'].get('sustainability_score', 0),
                'Sustainable_Materials': self._safe_join(analysis['sustainability'].get('sustainable_materials', [])),
                'Certifications': self._safe_join(analysis['sustainability'].get('certifications', [])),
                'Environmental_Impact': analysis['sustainability'].get('environmental_impact', 'unknown'),
                'Ethical_Manufacturing': analysis['sustainability'].get('ethical_manufacturing', 'unknown'),
                'Sustainability_Keywords': self._safe_join(analysis['sustainability'].get('sustainability_keywords', []), 5),
                
                # === MARKET & TRENDS ANALYSIS ===
                'Target_Age': analysis['market_analysis'].get('target_age', 'unknown'),
                'Target_Income': analysis['market_analysis'].get('target_income', 'unknown'),
                'Market_Segment': analysis['market_analysis'].get('market_segment', 'unknown'),
                'Personality_Traits': self._safe_join(analysis['market_analysis'].get('personality_traits', []), 3),
                'Lifestyle_Fit': analysis['market_analysis'].get('lifestyle_fit', 'unknown'),
                'Demographic_Appeal': self._safe_join(analysis['market_analysis'].get('demographic_appeal', []), 3),
                'Season': analysis['seasonal_analysis'].get('season', 'unknown'),
                'Trend_Level': analysis['seasonal_analysis'].get('trend_level', 'unknown'),
                'Timeless_Factor': analysis['seasonal_analysis'].get('timeless_factor', 'unknown'),
                'Seasonal_Appeal': self._safe_join(analysis['seasonal_analysis'].get('seasonal_appeal', []), 3),
                'Trend_Keywords': self._safe_join(analysis['seasonal_analysis'].get('trend_keywords', []), 3),
                
                # === USAGE RECOMMENDATIONS ===
                'Styling_Tips': self._safe_join(analysis['recommendations'].get('styling_tips', []), 3),
                'Care_Tips': self._safe_join(analysis['recommendations'].get('care_tips', []), 3),
                'Pairing_Suggestions': self._safe_join(analysis['recommendations'].get('pairing_suggestions', []), 3),
                'Usage_Scenarios': self._safe_join(analysis['recommendations'].get('usage_scenarios', []), 3),
            }
            
            # Add individual dimensions if available
            if analysis['dimensions'].get('dimensions'):
                for dim_name, dim_value in analysis['dimensions']['dimensions'].items():
                    row_data[f'{dim_name.title()}_Inches'] = dim_value
            
            # Add inventory details by location
            for location in analysis['inventory_analysis'].get('inventory_locations', []):
                store_name = location['store']
                row_data[f'{store_name}_Status'] = location['status']
                row_data[f'{store_name}_Quantity'] = location['quantity']
                row_data[f'{store_name}_OnHand'] = location['on_hand']
            
            chart_data.append(row_data)
        
        # Create DataFrame
        df = pd.DataFrame(chart_data)
        
        return df
    
    def create_inventory_summary(self, analyses: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create a focused inventory summary table."""
        
        inventory_data = []
        
        for analysis in analyses:
            inventory = analysis['inventory_analysis']
            
            row_data = {
                'Product_ID': analysis['product_id'],
                'Product_Name': analysis['name'],
                'SKU_Number': inventory['sku_number'],
                'Stock_Status': inventory['stock_status'],
                'Total_Available': inventory['quantity_available'],
                'On_Hand': inventory['quantity_on_hand'],
                'On_Order': inventory['quantity_on_order'],
                'Inventory_Status': inventory['inventory_status'],
                'Next_Availability': inventory['next_availability_date'],
                'Brand': analysis['brand_analysis']['brand_name'],
                'Price_Range': analysis['price_analysis']['price_range'],
                'Category': analysis['category']
            }
            
            # Add inventory by location
            for location in inventory['inventory_locations']:
                row_data[f'{location["store"]}_Status'] = location['status']
                row_data[f'{location["store"]}_Qty'] = location['quantity']
                row_data[f'{location["store"]}_OnHand'] = location['on_hand']
            
            inventory_data.append(row_data)
        
        return pd.DataFrame(inventory_data)
    
    def create_metrics_summary(self, analyses: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create a metrics summary table."""
        
        metrics_data = []
        
        for analysis in analyses:
            row_data = {
                'Product_ID': analysis['product_id'],
                'Product_Name': analysis['name'],
                'SKU': analysis['inventory_analysis']['sku_number'],
                'Stock_Status': analysis['inventory_analysis']['stock_status'],
                'Qty_Available': analysis['inventory_analysis']['quantity_available'],
                'Price_Range': analysis['price_analysis']['price_range'],
                'Brand_Tier': analysis['brand_analysis']['brand_tier'],
                'Quality_Level': analysis['quality_assessment']['overall_quality'],
                'Sustainability_Score': analysis['sustainability']['sustainability_score'],
                'Style_Era': analysis['style']['style_era'],
                'Size_Category': analysis['dimensions']['size_category'],
                'Care_Level': analysis['care_analysis']['care_level'],
                'Market_Segment': analysis['market_analysis']['market_segment'],
                'Trend_Level': analysis['seasonal_analysis']['trend_level']
            }
            
            metrics_data.append(row_data)
        
        return pd.DataFrame(metrics_data)
    
    def save_comprehensive_chart_to_excel(self, analyses: List[Dict[str, Any]], output_file: str) -> None:
        """Save comprehensive chart with overview to Excel file."""
        
        # Ensure the directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create comprehensive chart with ALL metrics
        comprehensive_chart = self.create_comprehensive_chart(analyses)
        
        # Create overview summary
        overview_summary = self._create_overview_summary(analyses)
        
        # Save to Excel with comprehensive chart (no overview summary)
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Main comprehensive chart with all metrics
            comprehensive_chart.to_excel(writer, sheet_name='Comprehensive_Analysis', index=False)
            
            # Additional focused charts for reference
            inventory_chart = self.create_inventory_summary(analyses)
            metrics_chart = self.create_metrics_summary(analyses)
            inventory_chart.to_excel(writer, sheet_name='Inventory_Details', index=False)
            metrics_chart.to_excel(writer, sheet_name='Key_Metrics', index=False)
        
        print(f"Comprehensive chart with overview saved to Excel file: {output_file}")
        
        # Display charts from Python
        self._display_python_charts(comprehensive_chart, analyses)
    
    def _display_python_charts(self, comprehensive_chart: pd.DataFrame, analyses: List[Dict[str, Any]]) -> None:
        """Display charts using Python matplotlib."""
        
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Set style
            plt.style.use('default')
            sns.set_palette("husl")
            
            # Create figure with subplots (3x2 for more charts)
            fig, axes = plt.subplots(3, 2, figsize=(15, 18))
            fig.suptitle('Product Analysis Dashboard', fontsize=16, fontweight='bold')
            
            # 1. Stock Status Pie Chart
            stock_data = comprehensive_chart['Stock_Status'].value_counts()
            if not stock_data.empty:
                axes[0, 0].pie(stock_data.values, labels=stock_data.index, autopct='%1.1f%%', startangle=90)
                axes[0, 0].set_title('Stock Status Distribution', fontweight='bold')
                axes[0, 0].axis('equal')
            
            # 2. Price Range Bar Chart
            price_data = comprehensive_chart['Price_Range'].value_counts()
            if not price_data.empty:
                axes[0, 1].bar(range(len(price_data)), price_data.values, color='skyblue', edgecolor='black')
                axes[0, 1].set_title('Price Range Distribution', fontweight='bold')
                axes[0, 1].set_xlabel('Price Range')
                axes[0, 1].set_ylabel('Count')
                axes[0, 1].set_xticks(range(len(price_data)))
                axes[0, 1].set_xticklabels(price_data.index, rotation=45, ha='right')
            
            # 3. Brand Tier Bar Chart
            brand_data = comprehensive_chart['Brand_Tier'].value_counts()
            if not brand_data.empty:
                axes[1, 0].bar(range(len(brand_data)), brand_data.values, color='lightcoral', edgecolor='black')
                axes[1, 0].set_title('Brand Tier Distribution', fontweight='bold')
                axes[1, 0].set_xlabel('Brand Tier')
                axes[1, 0].set_ylabel('Count')
                axes[1, 0].set_xticks(range(len(brand_data)))
                axes[1, 0].set_xticklabels(brand_data.index, rotation=45, ha='right')
            
            # 4. Sustainability Yes/No Bar Chart
            sustainability_data = comprehensive_chart['Is_Sustainable'].value_counts()
            if not sustainability_data.empty:
                # Convert to Yes/No format
                yes_no_data = {'Yes': sustainability_data.get(True, 0), 'No': sustainability_data.get(False, 0)}
                axes[1, 1].bar(yes_no_data.keys(), yes_no_data.values(), color=['green', 'red'], edgecolor='black')
                axes[1, 1].set_title('Sustainability: Yes vs No', fontweight='bold')
                axes[1, 1].set_xlabel('Sustainability Status')
                axes[1, 1].set_ylabel('Number of Products')
                axes[1, 1].grid(True, alpha=0.3)
            
            # 5. Inventory Categories Bar Chart
            # Count products with Available, On Hand, On Order quantities > 0
            available_count = (comprehensive_chart['Quantity_Available'] > 0).sum()
            on_hand_count = (comprehensive_chart['Quantity_On_Hand'] > 0).sum()
            on_order_count = (comprehensive_chart['Quantity_On_Order'] > 0).sum()
            
            inventory_categories = ['Available', 'On Hand', 'On Order']
            inventory_counts = [available_count, on_hand_count, on_order_count]
            
            axes[2, 0].bar(inventory_categories, inventory_counts, color=['lightgreen', 'darkgreen', 'orange'], edgecolor='black')
            axes[2, 0].set_title('Products with Inventory by Category', fontweight='bold')
            axes[2, 0].set_xlabel('Inventory Category')
            axes[2, 0].set_ylabel('Number of Products')
            axes[2, 0].grid(True, alpha=0.3)
            
            # 6. Market Analysis Chart
            market_data = comprehensive_chart['Market_Segment'].value_counts()
            if not market_data.empty:
                # Map market segments to standard categories
                market_mapping = {
                    'mass market': 'Mass Market',
                    'mid-market': 'Mid Market', 
                    'luxury market': 'Luxury Market',
                    'premium': 'Luxury Market',
                    'budget': 'Mass Market',
                    'unknown': 'Unknown'
                }
                
                # Clean and map market segments
                cleaned_markets = {}
                for market, count in market_data.items():
                    if pd.notna(market):
                        mapped_market = market_mapping.get(market.lower(), market.title())
                        cleaned_markets[mapped_market] = cleaned_markets.get(mapped_market, 0) + count
                
                if cleaned_markets:
                    axes[2, 1].bar(cleaned_markets.keys(), cleaned_markets.values(), 
                                  color=['lightblue', 'gold', 'purple', 'gray'], edgecolor='black')
                    axes[2, 1].set_title('Market Segment Distribution', fontweight='bold')
                    axes[2, 1].set_xlabel('Market Segment')
                    axes[2, 1].set_ylabel('Number of Products')
                    axes[2, 1].tick_params(axis='x', rotation=45)
                    axes[2, 1].grid(True, alpha=0.3)
            
            # Adjust layout and display
            plt.tight_layout()
            plt.show()
            
            print("📊 Charts displayed successfully!")
            
        except ImportError:
            print("⚠️  Chart display requires matplotlib and seaborn. Install with: pip install matplotlib seaborn")
            self._display_text_charts(comprehensive_chart)
        except Exception as e:
            print(f"⚠️  Error displaying charts: {e}")
            self._display_text_charts(comprehensive_chart)
    
    def _display_text_charts(self, comprehensive_chart: pd.DataFrame) -> None:
        """Display charts as text when matplotlib is not available."""
        
        print(f"\n{'='*80}")
        print(f"📊 TEXT-BASED CHARTS")
        print(f"{'='*80}")
        
        # 1. Stock Status Chart
        stock_data = comprehensive_chart['Stock_Status'].value_counts()
        if not stock_data.empty:
            print(f"\n📦 STOCK STATUS DISTRIBUTION:")
            total = stock_data.sum()
            for status, count in stock_data.items():
                percentage = (count / total) * 100
                bar = "█" * int(percentage / 2)  # Scale bar to fit
                print(f"  {status:<15}: {count:>3} ({percentage:>5.1f}%) {bar}")
        
        # 2. Price Range Chart
        price_data = comprehensive_chart['Price_Range'].value_counts()
        if not price_data.empty:
            print(f"\n💰 PRICE RANGE DISTRIBUTION:")
            total = price_data.sum()
            for price_range, count in price_data.items():
                percentage = (count / total) * 100
                bar = "█" * int(percentage / 2)
                print(f"  {price_range:<15}: {count:>3} ({percentage:>5.1f}%) {bar}")
        
        # 3. Brand Tier Chart
        brand_data = comprehensive_chart['Brand_Tier'].value_counts()
        if not brand_data.empty:
            print(f"\n🏷️  BRAND TIER DISTRIBUTION:")
            total = brand_data.sum()
            for brand_tier, count in brand_data.items():
                percentage = (count / total) * 100
                bar = "█" * int(percentage / 2)
                print(f"  {brand_tier:<15}: {count:>3} ({percentage:>5.1f}%) {bar}")
        
        # 4. Sustainability Yes/No
        sustainability_data = comprehensive_chart['Is_Sustainable'].value_counts()
        if not sustainability_data.empty:
            print(f"\n🌱 SUSTAINABILITY: YES vs NO:")
            yes_count = sustainability_data.get(True, 0)
            no_count = sustainability_data.get(False, 0)
            total = yes_count + no_count
            yes_percentage = (yes_count / total) * 100 if total > 0 else 0
            no_percentage = (no_count / total) * 100 if total > 0 else 0
            
            yes_bar = "█" * int(yes_percentage / 2)
            no_bar = "█" * int(no_percentage / 2)
            print(f"  Yes: {yes_count:>3} ({yes_percentage:>5.1f}%) {yes_bar}")
            print(f"  No:  {no_count:>3} ({no_percentage:>5.1f}%) {no_bar}")
        
        # 5. Inventory Categories
        available_count = (comprehensive_chart['Quantity_Available'] > 0).sum()
        on_hand_count = (comprehensive_chart['Quantity_On_Hand'] > 0).sum()
        on_order_count = (comprehensive_chart['Quantity_On_Order'] > 0).sum()
        total_products = len(comprehensive_chart)
        
        print(f"\n📦 INVENTORY CATEGORIES:")
        print(f"  Available: {available_count:>3} products")
        print(f"  On Hand:   {on_hand_count:>3} products")
        print(f"  On Order:  {on_order_count:>3} products")
        print(f"  Total:     {total_products:>3} products")
        
        # 6. Market Analysis
        market_data = comprehensive_chart['Market_Segment'].value_counts()
        if not market_data.empty:
            print(f"\n🏪 MARKET SEGMENT DISTRIBUTION:")
            total = market_data.sum()
            for market, count in market_data.items():
                if pd.notna(market):
                    percentage = (count / total) * 100
                    bar = "█" * int(percentage / 2)
                    print(f"  {market:<15}: {count:>3} ({percentage:>5.1f}%) {bar}")
        
        print(f"\n{'='*80}")
    
    def _create_summary_statistics(self, analyses: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create summary statistics table."""
        
        if not analyses:
            return pd.DataFrame()
        
        # Calculate statistics
        total_products = len(analyses)
        sustainable_count = sum(1 for a in analyses if a['sustainability']['is_sustainable'])
        in_stock_count = sum(1 for a in analyses if a['inventory_analysis']['stock_status'] == 'in_stock')
        total_quantity = sum(a['inventory_analysis']['quantity_available'] for a in analyses)
        
        # Price distribution
        price_ranges = {}
        for analysis in analyses:
            price_range = analysis['price_analysis']['price_range']
            price_ranges[price_range] = price_ranges.get(price_range, 0) + 1
        
        # Brand distribution
        brand_tiers = {}
        for analysis in analyses:
            brand_tier = analysis['brand_analysis']['brand_tier']
            brand_tiers[brand_tier] = brand_tiers.get(brand_tier, 0) + 1
        
        # Stock status distribution
        stock_statuses = {}
        for analysis in analyses:
            stock_status = analysis['inventory_analysis']['stock_status']
            stock_statuses[stock_status] = stock_statuses.get(stock_status, 0) + 1
        
        # Create summary data
        summary_data = [
            {'Metric': 'Total Products', 'Value': total_products, 'Percentage': '100.0%'},
            {'Metric': 'Sustainable Products', 'Value': sustainable_count, 'Percentage': f'{sustainable_count/total_products*100:.1f}%'},
            {'Metric': 'In Stock Products', 'Value': in_stock_count, 'Percentage': f'{in_stock_count/total_products*100:.1f}%'},
            {'Metric': 'Total Quantity Available', 'Value': total_quantity, 'Percentage': 'N/A'},
        ]
        
        # Add price range distribution
        for price_range, count in price_ranges.items():
            summary_data.append({
                'Metric': f'Price Range: {price_range}',
                'Value': count,
                'Percentage': f'{count/total_products*100:.1f}%'
            })
        
        # Add brand tier distribution
        for brand_tier, count in brand_tiers.items():
            summary_data.append({
                'Metric': f'Brand Tier: {brand_tier}',
                'Value': count,
                'Percentage': f'{count/total_products*100:.1f}%'
            })
        
        # Add stock status distribution
        for stock_status, count in stock_statuses.items():
            summary_data.append({
                'Metric': f'Stock Status: {stock_status}',
                'Value': count,
                'Percentage': f'{count/total_products*100:.1f}%'
            })
        
        return pd.DataFrame(summary_data)
    
    def _create_overview_summary(self, analyses: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create comprehensive overview summary with categories as rows and metrics as columns."""
        
        if not analyses:
            return pd.DataFrame()
        
        total_products = len(analyses)
        
        # Calculate comprehensive statistics
        overview_data = {}
        
        # === INVENTORY OVERVIEW ===
        in_stock_count = sum(1 for a in analyses if a['inventory_analysis'].get('stock_status') == 'in_stock')
        on_order_count = sum(1 for a in analyses if a['inventory_analysis'].get('stock_status') == 'on_order')
        out_of_stock_count = sum(1 for a in analyses if a['inventory_analysis'].get('stock_status') == 'out_of_stock')
        total_quantity = sum(a['inventory_analysis'].get('quantity_available', 0) for a in analyses)
        total_on_hand = sum(a['inventory_analysis'].get('quantity_on_hand', 0) for a in analyses)
        total_on_order = sum(a['inventory_analysis'].get('quantity_on_order', 0) for a in analyses)
        
        overview_data['INVENTORY OVERVIEW'] = {
            'Total Products': {'Value': total_products, 'Percentage': '100.0%'},
            'In Stock Products': {'Value': in_stock_count, 'Percentage': f'{in_stock_count/total_products*100:.1f}%'},
            'On Order Products': {'Value': on_order_count, 'Percentage': f'{on_order_count/total_products*100:.1f}%'},
            'Out of Stock Products': {'Value': out_of_stock_count, 'Percentage': f'{out_of_stock_count/total_products*100:.1f}%'},
            'Total Quantity Available': {'Value': total_quantity, 'Percentage': 'N/A'},
            'Total On Hand': {'Value': total_on_hand, 'Percentage': 'N/A'},
            'Total On Order': {'Value': total_on_order, 'Percentage': 'N/A'},
        }
        
        # === PRICE OVERVIEW ===
        price_ranges = {}
        luxury_levels = {}
        for analysis in analyses:
            price_range = analysis['price_analysis'].get('price_range', 'unknown')
            luxury_level = analysis['price_analysis'].get('luxury_level', 'unknown')
            price_ranges[price_range] = price_ranges.get(price_range, 0) + 1
            luxury_levels[luxury_level] = luxury_levels.get(luxury_level, 0) + 1
        
        price_data = {}
        for price_range, count in price_ranges.items():
            price_data[f'Price Range: {price_range}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        for luxury_level, count in luxury_levels.items():
            price_data[f'Luxury Level: {luxury_level}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        overview_data['PRICE OVERVIEW'] = price_data
        
        # === BRAND OVERVIEW ===
        brand_tiers = {}
        brand_names = {}
        for analysis in analyses:
            brand_tier = analysis['brand_analysis'].get('brand_tier', 'unknown')
            brand_name = analysis['brand_analysis'].get('brand_name', 'unknown')
            brand_tiers[brand_tier] = brand_tiers.get(brand_tier, 0) + 1
            brand_names[brand_name] = brand_names.get(brand_name, 0) + 1
        
        brand_data = {}
        for brand_tier, count in brand_tiers.items():
            brand_data[f'Brand Tier: {brand_tier}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        sorted_brands = sorted(brand_names.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (brand_name, count) in enumerate(sorted_brands, 1):
            brand_data[f'Top Brand #{i}: {brand_name}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        overview_data['BRAND OVERVIEW'] = brand_data
        
        # === SUSTAINABILITY OVERVIEW ===
        sustainable_count = sum(1 for a in analyses if a['sustainability'].get('is_sustainable', False))
        avg_sustainability_score = sum(a['sustainability'].get('sustainability_score', 0) for a in analyses) / total_products
        
        overview_data['SUSTAINABILITY OVERVIEW'] = {
            'Sustainable Products': {'Value': sustainable_count, 'Percentage': f'{sustainable_count/total_products*100:.1f}%'},
            'Average Sustainability Score': {'Value': f'{avg_sustainability_score:.1f}', 'Percentage': 'N/A'},
        }
        
        # === MATERIALS OVERVIEW ===
        all_materials = []
        for analysis in analyses:
            all_materials.extend(analysis['materials'].get('primary_materials', []))
            all_materials.extend(analysis['materials'].get('secondary_materials', []))
        
        material_counts = {}
        for material in all_materials:
            if material and material != 'unknown':
                material_counts[material] = material_counts.get(material, 0) + 1
        
        materials_data = {}
        sorted_materials = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (material, count) in enumerate(sorted_materials, 1):
            materials_data[f'Top Material #{i}: {material}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        overview_data['MATERIALS OVERVIEW'] = materials_data
        
        # === STYLE OVERVIEW ===
        style_eras = {}
        design_styles = {}
        for analysis in analyses:
            style_era = analysis['style'].get('style_era', 'unknown')
            design_style = analysis['style'].get('design_style', 'unknown')
            style_eras[style_era] = style_eras.get(style_era, 0) + 1
            design_styles[design_style] = design_styles.get(design_style, 0) + 1
        
        style_data = {}
        for style_era, count in style_eras.items():
            style_data[f'Style Era: {style_era}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        for design_style, count in design_styles.items():
            style_data[f'Design Style: {design_style}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        overview_data['STYLE OVERVIEW'] = style_data
        
        # === QUALITY OVERVIEW ===
        quality_levels = {}
        craftsmanship_levels = {}
        for analysis in analyses:
            quality_level = analysis['quality_assessment'].get('overall_quality', 'unknown')
            craftsmanship_level = analysis['quality_assessment'].get('craftsmanship_level', 'unknown')
            quality_levels[quality_level] = quality_levels.get(quality_level, 0) + 1
            craftsmanship_levels[craftsmanship_level] = craftsmanship_levels.get(craftsmanship_level, 0) + 1
        
        quality_data = {}
        for quality_level, count in quality_levels.items():
            quality_data[f'Quality Level: {quality_level}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        for craftsmanship_level, count in craftsmanship_levels.items():
            quality_data[f'Craftsmanship Level: {craftsmanship_level}'] = {'Value': count, 'Percentage': f'{count/total_products*100:.1f}%'}
        
        overview_data['QUALITY OVERVIEW'] = quality_data
        
        # Convert to DataFrame with categories as rows and metrics as columns
        return self._convert_overview_to_dataframe(overview_data)
    
    def _convert_overview_to_dataframe(self, overview_data: Dict[str, Dict[str, Dict[str, str]]]) -> pd.DataFrame:
        """Convert overview data to DataFrame with categories as rows and metrics as columns."""
        
        # Get all unique metrics across all categories
        all_metrics = set()
        for category_data in overview_data.values():
            all_metrics.update(category_data.keys())
        
        # Create DataFrame
        df_data = {}
        for metric in sorted(all_metrics):
            df_data[f'{metric}_Value'] = []
            df_data[f'{metric}_Percentage'] = []
        
        # Add category column
        df_data['Category'] = []
        
        # Fill data
        for category, metrics in overview_data.items():
            df_data['Category'].append(category)
            
            for metric in sorted(all_metrics):
                if metric in metrics:
                    df_data[f'{metric}_Value'].append(metrics[metric]['Value'])
                    df_data[f'{metric}_Percentage'].append(metrics[metric]['Percentage'])
                else:
                    df_data[f'{metric}_Value'].append('')
                    df_data[f'{metric}_Percentage'].append('')
        
        return pd.DataFrame(df_data)
    
    def analyze_and_create_charts(self, config_file_path: str, output_file: str = None) -> None:
        """Analyze products and create tabular charts."""
        
        # Analyze all product lists
        results = self.multi_analyzer.analyze_all_lists(config_file_path)
        
        if not results:
            print("No analysis results found.")
            return
        
        # Collect all analyses
        all_analyses = []
        for result in results:
            all_analyses.extend(result['analyses'])
        
        if not all_analyses:
            print("No product analyses found.")
            return
        
        # Generate output filename if not provided
        if not output_file:
            output_file = "src/product_analysis_charts.xlsx"
        
        # Create and save charts
        print(f"\n{'='*80}")
        print(f"CREATING TABULAR CHARTS")
        print(f"{'='*80}")
        print(f"Total products to chart: {len(all_analyses)}")
        
        # Create comprehensive chart with ALL metrics
        comprehensive_chart = self.create_comprehensive_chart(all_analyses)
        
        # Display preview of comprehensive chart
        print(f"\n📊 COMPREHENSIVE ANALYSIS CHART PREVIEW:")
        preview_columns = ['Product_ID', 'Product_Name', 'SKU_Number', 'Stock_Status', 'Quantity_Available', 
                          'Price_Range', 'Brand_Tier', 'Quality_Level', 'Sustainability_Score', 'Style_Era']
        available_columns = [col for col in preview_columns if col in comprehensive_chart.columns]
        print(comprehensive_chart[available_columns].head())
        
        print(f"\n📊 CHART DIMENSIONS:")
        print(f"Rows (Products): {len(comprehensive_chart)}")
        print(f"Columns (Metrics): {len(comprehensive_chart.columns)}")
        print(f"Total Data Points: {len(comprehensive_chart) * len(comprehensive_chart.columns)}")
        
        # Save comprehensive chart with overview
        self.save_comprehensive_chart_to_excel(all_analyses, output_file)
        
        # Display overview summary
        print(f"\n📊 OVERVIEW SUMMARY:")
        overview_summary = self._create_overview_summary(all_analyses)
        print(overview_summary.to_string(index=False))

def main():
    """Main function for tabular product analysis."""
    parser = argparse.ArgumentParser(
        description="Create tabular charts with product ID as rows and metrics as columns"
    )
    parser.add_argument(
        "--product-lists-config", 
        required=True,
        help="Path to product lists configuration file"
    )
    parser.add_argument(
        "--output-file",
        help="Output Excel file path (default: src/product_analysis_charts.xlsx)"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = TabularProductAnalyzer()
        analyzer.analyze_and_create_charts(args.product_lists_config, args.output_file)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
