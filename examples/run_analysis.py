#!/usr/bin/env python3
"""
Example script to run product analysis.
This demonstrates how to use the product classification system.
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def run_example_analysis():
    """Run example product analysis."""
    print("🚀 Product Classification System - Example Analysis")
    print("=" * 60)
    
    # Check if product_lists.txt exists
    config_file = Path(__file__).parent / "product_lists.txt"
    
    if not config_file.exists():
        print("❌ Configuration file not found!")
        print(f"Please create: {config_file}")
        print("\nExample content:")
        print("# Product Lists Configuration")
        print("# Add your JSON file paths here:")
        print("# C:\\Users\\YourName\\Downloads\\styles\\product1.json")
        print("# C:\\Users\\YourName\\Downloads\\styles\\product2.json")
        return
    
    print(f"✅ Found configuration file: {config_file}")
    
    # Import the analyzer
    try:
        from multi_product_analyzer import MultiProductAnalyzer
        
        print("\n📊 Running Multi-Product Analysis...")
        analyzer = MultiProductAnalyzer()
        results = analyzer.analyze_all_lists(str(config_file))
        
        if results:
            print(f"\n✅ Analysis complete! Processed {len(results)} product lists.")
            print("\n📁 Check the examples/ folder for output files.")
        else:
            print("\n⚠️ No results generated. Check your configuration file.")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the examples/ folder.")
    except Exception as e:
        print(f"❌ Error running analysis: {e}")

def run_example_recommendations():
    """Run example product recommendations."""
    print("\n🎯 Product Recommendations Example")
    print("=" * 40)
    
    config_file = Path(__file__).parent / "product_lists.txt"
    
    if not config_file.exists():
        print("❌ Configuration file not found!")
        return
    
    try:
        from product_recommender_json import ProductRecommender
        
        print("📊 Loading products and analyzing...")
        recommender = ProductRecommender()
        recommender.load_products_from_config(str(config_file))
        
        if len(recommender.products) > 1:
            # Get recommendations for the first product
            first_product_id = recommender.products[0]['id']
            print(f"\n🎯 Getting recommendations for: {first_product_id}")
            recommender.recommend_products(first_product_id, top_k=3)
        else:
            print("⚠️ Need at least 2 products for recommendations")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error running recommendations: {e}")

if __name__ == "__main__":
    print("Choose an example to run:")
    print("1. Run Product Analysis")
    print("2. Run Product Recommendations")
    print("3. Run Both")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        run_example_analysis()
    elif choice == "2":
        run_example_recommendations()
    elif choice == "3":
        run_example_analysis()
        run_example_recommendations()
    else:
        print("Invalid choice. Please run the script again.")
