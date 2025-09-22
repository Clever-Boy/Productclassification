# Component Interaction Diagram

## 🔧 Detailed Component Interactions

This diagram shows the detailed interactions between all components in the Product Classification System.

```mermaid
sequenceDiagram
    participant User
    participant Config as Configuration Files
    participant Loader as JSON Data Loader
    participant Analyzer as Multi-Product Analyzer
    participant Extractor as Product Attribute Extractor
    participant Classifier as Classification Systems
    participant Recommender as Product Recommender
    participant Tabular as Tabular Analyzer
    participant Storage as File Storage
    
    User->>Config: Edit product_lists.txt
    User->>Analyzer: Run analysis command
    
    Analyzer->>Config: Read configuration
    Config-->>Analyzer: Return file paths and settings
    
    loop For each JSON file
        Analyzer->>Loader: Load JSON file
        Loader->>Loader: Parse JSON structure
        Loader->>Loader: Extract product data
        Loader-->>Analyzer: Return product list
    end
    
    loop For each product
        Analyzer->>Extractor: Analyze product
        Extractor->>Extractor: Extract sustainability
        Extractor->>Extractor: Extract materials
        Extractor->>Extractor: Extract style
        Extractor->>Extractor: Extract pricing
        Extractor->>Extractor: Extract brand info
        Extractor->>Extractor: Extract dimensions
        Extractor->>Extractor: Extract care info
        Extractor->>Extractor: Extract market data
        Extractor->>Extractor: Extract seasonal info
        Extractor->>Extractor: Assess quality
        Extractor->>Extractor: Generate recommendations
        Extractor->>Extractor: Analyze inventory
        Extractor-->>Analyzer: Return analysis results
    end
    
    Analyzer->>Storage: Save analysis report
    Storage-->>Analyzer: Confirm save
    
    User->>Recommender: Run recommendation command
    Recommender->>Loader: Load all products
    Loader-->>Recommender: Return product data
    
    loop For each product
        Recommender->>Classifier: Extract text features
        Recommender->>Classifier: Extract image features
        Recommender->>Classifier: Calculate similarity
        Classifier-->>Recommender: Return features
    end
    
    Recommender->>Recommender: Find similar products
    Recommender->>Storage: Download/cache images
    Recommender->>Recommender: Display visual recommendations
    
    User->>Tabular: Run tabular analysis
    Tabular->>Analyzer: Get analysis results
    Analyzer-->>Tabular: Return all analyses
    
    Tabular->>Tabular: Create comprehensive chart
    Tabular->>Tabular: Generate Python charts
    Tabular->>Storage: Save Excel file
    Storage-->>Tabular: Confirm save
    
    Tabular-->>User: Display charts and save Excel
```

## 🏗️ Component Architecture Details

### **Data Flow Layers**

```mermaid
graph LR
    subgraph "Input Layer"
        A[JSON Files] --> B[Configuration]
        B --> C[Environment]
    end
    
    subgraph "Processing Layer"
        D[Data Loader] --> E[Multi Analyzer]
        E --> F[Attribute Extractor]
    end
    
    subgraph "Analysis Layer"
        G[Sustainability] --> H[Materials]
        H --> I[Style]
        I --> J[Pricing]
        J --> K[Brand]
        K --> L[Dimensions]
        L --> M[Care]
        M --> N[Market]
        N --> O[Seasonal]
        O --> P[Quality]
        P --> Q[Recommendations]
        Q --> R[Inventory]
    end
    
    subgraph "Output Layer"
        S[Text Reports] --> T[Excel Files]
        T --> U[Python Charts]
        U --> V[Visual Recommendations]
    end
    
    C --> D
    F --> G
    R --> S
```

### **Classification System Architecture**

```mermaid
graph TB
    subgraph "Text Classification"
        TC1[simple_text_classifier.py]
        TC2[basic_text_analyzer.py]
        TC3[categorize_words_json.py]
    end
    
    subgraph "Image Classification"
        IC1[image_classifier_json.py]
        IC2[Image Feature Extraction]
        IC3[Color Analysis]
        IC4[Size Analysis]
    end
    
    subgraph "Combined Classification"
        CC1[combined_classifier_json.py]
        CC2[Feature Fusion]
        CC3[Similarity Calculation]
    end
    
    subgraph "Recommendation Engine"
        RE1[product_recommender_json.py]
        RE2[Visual Display]
        RE3[Similarity Ranking]
    end
    
    TC1 --> CC1
    TC2 --> CC1
    TC3 --> CC1
    IC1 --> CC1
    IC2 --> CC1
    IC3 --> CC1
    IC4 --> CC1
    
    CC1 --> RE1
    CC2 --> RE1
    CC3 --> RE1
    
    RE1 --> RE2
    RE1 --> RE3
```

## 🔄 Processing Pipeline

### **Stage 1: Data Ingestion**
1. **Configuration Reading**: Parse product lists and settings
2. **JSON Loading**: Load and parse product data files
3. **Data Validation**: Check data integrity and structure
4. **Product Extraction**: Extract individual product records

### **Stage 2: Feature Extraction**
1. **Text Processing**: Normalize and analyze product descriptions
2. **Image Processing**: Download and analyze product images
3. **Attribute Extraction**: Extract 12+ product attributes
4. **Feature Caching**: Store computed features for reuse

### **Stage 3: Analysis & Classification**
1. **Sustainability Analysis**: Assess environmental impact
2. **Material Analysis**: Identify and categorize materials
3. **Style Analysis**: Determine design characteristics
4. **Price Analysis**: Evaluate pricing and value
5. **Brand Analysis**: Assess brand reputation and tier
6. **Market Analysis**: Determine target demographics
7. **Quality Assessment**: Evaluate craftsmanship and quality

### **Stage 4: Output Generation**
1. **Report Generation**: Create detailed text reports
2. **Chart Creation**: Generate Python visualizations
3. **Excel Export**: Create comprehensive Excel files
4. **Recommendation Display**: Show visual product recommendations

## 🎯 Key Design Principles

### **Modularity**
- Each component has a single, well-defined responsibility
- Components can be used independently or together
- Easy to add new analysis modules

### **Flexibility**
- Handles various JSON data formats
- Configurable analysis parameters
- Extensible classification systems

### **Performance**
- Image and feature caching
- Batch processing capabilities
- Memory-efficient processing

### **User Experience**
- Visual recommendation interface
- Comprehensive output formats
- Easy configuration management

This architecture ensures a robust, scalable, and maintainable system that can handle complex product analysis tasks while providing excellent user experience and performance.
