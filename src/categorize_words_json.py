#!/usr/bin/env python3
"""
Text-based product classification using JSON data.
Works with style.json files containing digitalAssets and product information.
"""
import argparse
import random
import numpy as np
import re
import operator
import tensorflow as tf
import math
from typing import List, Dict, Any, Tuple, Optional
from tensorflow import keras
from tensorflow.keras import layers
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

def compute_tf_data_for_products(products: List[Dict[str, Any]], 
                                vocab_indices: Dict[str, int], 
                                category_indices: Dict[str, int], 
                                seen_categories: List[str]) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """
    Compute TF (Term Frequency) data for products.
    
    Args:
        products: List of product dictionaries
        vocab_indices: Vocabulary word to index mapping
        category_indices: Category to index mapping
        seen_categories: List of seen categories
        
    Returns:
        Tuple of (feature arrays, label arrays)
    """
    xs = []
    ys = []
    for p in products:
        text = normalize_text(p['name'] + ' ' + p['description'])
        words = text.split()
        bow = np.zeros(len(vocab_indices))
        for w in words:
            if w in vocab_indices:
                bow[vocab_indices[w]] = 1
        y = np.zeros(len(seen_categories))
        y[category_indices[p['category_id']]] = 1
        xs.append(bow)
        ys.append(y)
    return xs, ys

def prep_word_training(products: List[Dict[str, Any]]) -> Tuple[keras.Model, Dict[str, int], Dict[str, int], List[str]]:
    """
    Prepare word-based training data and create TensorFlow 2.x model.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        Tuple of (model, vocab_indices, category_indices, seen_categories)
    """
    vocab = {}
    seen_categories = []
    
    # Build vocabulary and category lists
    for p in products:
        if p['category_id'] not in seen_categories:
            seen_categories.append(p['category_id'])
        text = normalize_text(p['name'] + ' ' + p['description'])
        words = text.split()
        for w in words:
            vocab[w] = vocab.get(w, 0) + 1
    
    # Sort vocabulary by frequency and take top 20000 words
    sorted_vocab = sorted(vocab.items(), key=operator.itemgetter(1))
    vocab_indices = {word: idx for idx, (word, _) in enumerate([w[0] for w in sorted_vocab[-20000:]])}
    category_indices = {cat: idx for idx, cat in enumerate(seen_categories)}
    
    vocab_size = len(vocab_indices)
    num_categories = len(seen_categories)
    num_hidden_layers = 100
    
    print(f"Vocabulary size: {vocab_size}")
    print(f"Number of categories: {num_categories}")
    print(f"Categories: {seen_categories}")
    
    # Create TensorFlow 2.x model using Keras
    model = keras.Sequential([
        layers.Dense(num_hidden_layers, activation='relu', input_shape=(vocab_size,)),
        layers.Dense(num_categories, activation='softmax')
    ])
    
    # Compile model
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model, vocab_indices, category_indices, seen_categories

def classify_text_from_json(json_file_path: str, categories: Optional[List[str]] = None, 
                           min_products_per_category: int = 10) -> None:
    """
    Perform text-based classification using JSON data.
    
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
    
    if len(products) < 20:
        print("Warning: Very few products for training. Results may be poor.")
    
    # Shuffle products
    random.shuffle(products)
    
    # Prepare model and data
    model, vocab_indices, category_indices, seen_categories = prep_word_training(products)
    
    # Split data into train/test
    train_size = int(0.8 * len(products))  # Use 80% for training
    train_products = products[:train_size]
    test_products = products[train_size:]
    
    print(f"Training set: {len(train_products)} products")
    print(f"Test set: {len(test_products)} products")
    
    # Prepare training data
    train_x, train_y = compute_tf_data_for_products(train_products, vocab_indices, category_indices, seen_categories)
    test_x, test_y = compute_tf_data_for_products(test_products, vocab_indices, category_indices, seen_categories)
    
    # Convert to numpy arrays
    train_x = np.array(train_x)
    train_y = np.array(train_y)
    test_x = np.array(test_x)
    test_y = np.array(test_y)
    
    print(f"Feature matrix shape: {train_x.shape}")
    print(f"Label matrix shape: {train_y.shape}")
    
    # Train the model
    print("\nTraining model...")
    epochs = 10  # Reduced for faster training
    
    for epoch in range(epochs):
        print(f"Epoch {epoch + 1}/{epochs}")
        
        # Shuffle training data
        indices = np.random.permutation(len(train_x))
        train_x_shuffled = train_x[indices]
        train_y_shuffled = train_y[indices]
        
        # Train in batches
        batch_size = 32
        for i in range(0, len(train_x_shuffled), batch_size):
            batch_x = train_x_shuffled[i:i+batch_size]
            batch_y = train_y_shuffled[i:i+batch_size]
            
            model.train_on_batch(batch_x, batch_y)
            
            if i % 100 == 0 and i > 0:
                print(f"  Batch {i} of {len(train_x_shuffled)}")
        
        # Evaluate on test set
        test_loss, test_accuracy = model.evaluate(test_x, test_y, verbose=0)
        print(f"  Test accuracy: {test_accuracy:.4f}")
    
    # Final evaluation
    print("\n=== Final Results ===")
    predictions = model.predict(test_x)
    correct = 0
    
    print("\nSample predictions:")
    for i, p in enumerate(test_products[:10]):  # Show first 10 predictions
        predicted_cat = seen_categories[np.argmax(predictions[i])]
        prediction_score = np.max(predictions[i])
        actual_cat = p['category_id']
        
        is_correct = predicted_cat == actual_cat
        if is_correct:
            correct += 1
        
        status = "✓" if is_correct else "✗"
        print(f"{status} {p['name'][:50]}...")
        print(f"    Actual: {actual_cat}, Predicted: {predicted_cat} ({prediction_score:.3f})")
    
    # Calculate overall accuracy
    for i, p in enumerate(test_products):
        predicted_cat = seen_categories[np.argmax(predictions[i])]
        if p['category_id'] == predicted_cat:
            correct += 1
    
    final_accuracy = correct / len(test_products)
    print(f"\nOverall accuracy: {final_accuracy:.4f} ({correct}/{len(test_products)})")
    
    # Category-wise accuracy
    print("\nCategory-wise accuracy:")
    category_correct = {}
    category_total = {}
    
    for i, p in enumerate(test_products):
        cat = p['category_id']
        category_total[cat] = category_total.get(cat, 0) + 1
        
        predicted_cat = seen_categories[np.argmax(predictions[i])]
        if cat == predicted_cat:
            category_correct[cat] = category_correct.get(cat, 0) + 1
    
    for cat in sorted(category_total.keys()):
        correct_count = category_correct.get(cat, 0)
        total_count = category_total[cat]
        accuracy = correct_count / total_count
        print(f"  {cat}: {accuracy:.3f} ({correct_count}/{total_count})")

def main():
    """Main function for JSON-based text classification."""
    parser = argparse.ArgumentParser(
        description="Text-based product classification using JSON data"
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
        default=10,
        help="Minimum number of products required per category (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Parse categories if provided
    categories = None
    if args.categories:
        categories = [cat.strip() for cat in args.categories.split(',')]
    
    try:
        classify_text_from_json(
            json_file_path=args.json_file,
            categories=categories,
            min_products_per_category=args.min_products
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
