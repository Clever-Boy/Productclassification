#!/usr/bin/env python3
"""
Basic text analysis without any ML libraries.
Uses simple word frequency analysis for product classification.
"""
import argparse
import random
import re
import operator
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter, defaultdict
from json_data_loader import JSONDataLoader

def normalize_text(text: str) -> str:
    """
    Normalize text by removing HTML tags and non-alphanumeric characters.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text
    """
    text = re.sub(r'<[^>]+>', ' ', text.lower())
    return re.sub(r'[^a-z0-9 ]', '', text)

def analyze_text_basic(json_file_path: str, categories: Optional[List[str]] = None, 
                      min_products_per_category: int = 1) -> None:
    """
    Perform basic text analysis without ML libraries.
    
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
        print("No suitable categories found for analysis.")
        return
    
    # Get products for selected categories
    products = loader.get_products(categories)
    print(f"\nAnalyzing {len(products)} products from {len(categories)} categories")
    
    # Analyze text by category
    category_texts = defaultdict(list)
    category_word_counts = defaultdict(Counter)
    
    for product in products:
        category = product['category_id']
        text = normalize_text(product['name'] + ' ' + product['description'])
        words = text.split()
        
        category_texts[category].append(text)
        category_word_counts[category].update(words)
    
    print(f"\n=== Text Analysis Results ===")
    
    # Show word frequency by category
    for category in categories:
        if category in category_word_counts:
            word_count = category_word_counts[category]
            total_words = sum(word_count.values())
            unique_words = len(word_count)
            
            print(f"\n📊 Category: {category}")
            print(f"   Total products: {len(category_texts[category])}")
            print(f"   Total words: {total_words}")
            print(f"   Unique words: {unique_words}")
            
            # Show top 10 words
            top_words = word_count.most_common(10)
            print(f"   Top words: {', '.join([f'{word}({count})' for word, count in top_words])}")
            
            # Show sample product names
            sample_products = category_texts[category][:3]
            print(f"   Sample products:")
            for i, product_text in enumerate(sample_products, 1):
                preview = product_text[:60] + "..." if len(product_text) > 60 else product_text
                print(f"     {i}. {preview}")
    
    # Find common words across categories
    print(f"\n🔍 Cross-Category Analysis:")
    
    if len(categories) > 1:
        # Find words that appear in multiple categories
        word_categories = defaultdict(set)
        for category, word_count in category_word_counts.items():
            for word in word_count.keys():
                word_categories[word].add(category)
        
        # Words that appear in multiple categories
        multi_category_words = {word: cats for word, cats in word_categories.items() 
                               if len(cats) > 1}
        
        if multi_category_words:
            print(f"   Words appearing in multiple categories:")
            for word, cats in sorted(multi_category_words.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                print(f"     '{word}': {', '.join(sorted(cats))}")
        else:
            print(f"   No words appear in multiple categories")
    
    # Simple classification simulation
    print(f"\n🎯 Classification Simulation:")
    
    if len(products) >= 2:
        # Split into train/test
        random.shuffle(products)
        train_size = max(1, len(products) // 2)
        train_products = products[:train_size]
        test_products = products[train_size:]
        
        print(f"   Training on {len(train_products)} products")
        print(f"   Testing on {len(test_products)} products")
        
        # Build simple word-based classifier
        category_words = defaultdict(set)
        for product in train_products:
            category = product['category_id']
            text = normalize_text(product['name'] + ' ' + product['description'])
            words = set(text.split())
            category_words[category].update(words)
        
        # Test classification
        correct = 0
        total = 0
        
        print(f"\n   Sample predictions:")
        for product in test_products:
            text = normalize_text(product['name'] + ' ' + product['description'])
            words = set(text.split())
            
            # Find category with most word overlap
            best_category = None
            best_score = 0
            
            for category, category_word_set in category_words.items():
                overlap = len(words.intersection(category_word_set))
                if overlap > best_score:
                    best_score = overlap
                    best_category = category
            
            actual_category = product['category_id']
            predicted_category = best_category if best_category else "unknown"
            
            is_correct = predicted_category == actual_category
            if is_correct:
                correct += 1
            total += 1
            
            status = "✓" if is_correct else "✗"
            print(f"   {status} '{product['name'][:40]}...'")
            print(f"      Actual: {actual_category}, Predicted: {predicted_category} (score: {best_score})")
        
        if total > 0:
            accuracy = correct / total
            print(f"\n   Simple classification accuracy: {accuracy:.4f} ({correct}/{total})")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    print(f"   1. Add more products for better analysis (currently {len(products)} products)")
    print(f"   2. Ensure products have descriptive names and descriptions")
    print(f"   3. Use consistent category names across products")
    print(f"   4. Consider adding more categories for better classification")

def main():
    """Main function for basic text analysis."""
    parser = argparse.ArgumentParser(
        description="Basic text analysis without ML libraries"
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
        analyze_text_basic(
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
