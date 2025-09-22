#!/usr/bin/env python3
"""
Simple text-based product classification without TensorFlow.
Uses basic machine learning techniques that don't require TensorFlow.
"""
import argparse
import random
import numpy as np
import re
import operator
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
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

def classify_text_simple(json_file_path: str, categories: Optional[List[str]] = None, 
                        min_products_per_category: int = 3) -> None:
    """
    Perform simple text-based classification using scikit-learn.
    
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
        print("No suitable categories found for training.")
        return
    
    # Get products for selected categories
    products = loader.get_products(categories)
    print(f"\nTraining with {len(products)} products from {len(categories)} categories")
    
    if len(products) < 5:
        print("Warning: Very few products for training. Results may be poor.")
        print("Consider adding more products or lowering --min-products")
    
    # Prepare text data
    texts = []
    labels = []
    
    for product in products:
        # Combine name and description
        text = normalize_text(product['name'] + ' ' + product['description'])
        texts.append(text)
        labels.append(product['category_id'])
    
    print(f"Prepared {len(texts)} text samples")
    
    # Check if we have enough data
    if len(set(labels)) < 2:
        print("Error: Need at least 2 different categories for classification.")
        return
    
    # Split data into train/test
    if len(texts) < 10:
        # Use all data for training if very small dataset
        X_train, X_test = texts, texts
        y_train, y_test = labels, labels
        print("Using all data for training (small dataset)")
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        print(f"Training set: {len(X_train)} samples")
        print(f"Test set: {len(X_test)} samples")
    
    # Create TF-IDF features
    print("\nCreating TF-IDF features...")
    vectorizer = TfidfVectorizer(
        max_features=1000,  # Limit vocabulary size
        stop_words='english',
        ngram_range=(1, 2)  # Use unigrams and bigrams
    )
    
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)
    
    print(f"Feature matrix shape: {X_train_tfidf.shape}")
    
    # Train Naive Bayes classifier
    print("\nTraining Naive Bayes classifier...")
    classifier = MultinomialNB()
    classifier.fit(X_train_tfidf, y_train)
    
    # Make predictions
    y_pred = classifier.predict(X_test_tfidf)
    
    # Calculate accuracy
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n=== Results ===")
    print(f"Overall accuracy: {accuracy:.4f}")
    
    # Show detailed results
    print(f"\nDetailed classification report:")
    print(classification_report(y_test, y_pred))
    
    # Show sample predictions
    print(f"\nSample predictions:")
    for i in range(min(10, len(X_test))):
        predicted = y_pred[i]
        actual = y_test[i]
        text_preview = X_test[i][:50] + "..." if len(X_test[i]) > 50 else X_test[i]
        
        status = "✓" if predicted == actual else "✗"
        print(f"{status} '{text_preview}'")
        print(f"    Actual: {actual}, Predicted: {predicted}")
    
    # Show feature importance (top words for each category)
    print(f"\nTop words for each category:")
    feature_names = vectorizer.get_feature_names_out()
    
    for category in categories:
        if category in classifier.classes_:
            class_idx = list(classifier.classes_).index(category)
            # Get log probabilities for this class
            log_probs = classifier.feature_log_prob_[class_idx]
            # Get top 10 features
            top_indices = np.argsort(log_probs)[-10:][::-1]
            top_words = [feature_names[i] for i in top_indices]
            print(f"  {category}: {', '.join(top_words)}")

def main():
    """Main function for simple text classification."""
    parser = argparse.ArgumentParser(
        description="Simple text-based product classification using scikit-learn"
    )
    parser.add_argument(
        "--json-file", 
        required=True,
        help="Path to JSON file containing product data (e.g., style.json)"
    )
    parser.add_argument(
        "--categories", 
        help="Comma-separated list of categories to classify. If not specified, all suitable categories are used."
    )
    parser.add_argument(
        "--min-products", 
        type=int, 
        default=3,
        help="Minimum number of products required per category (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Parse categories if provided
    categories = None
    if args.categories:
        categories = [cat.strip() for cat in args.categories.split(',')]
    
    try:
        classify_text_simple(
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
