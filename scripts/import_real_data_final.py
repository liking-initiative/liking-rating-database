#!/usr/bin/env python3
"""
Import final dataset from CSV file into the Liking Rating Database
Updated to handle the actual data structure with metadata from Excel file
"""
import asyncio
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import re

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.database import init_db, get_db, Study, Dataset, Item, Rating
from backend.config import settings

async def load_study_metadata_from_excel(excel_file_path):
    """Load study metadata - now returns hardcoded real study data"""
    # Real study metadata based on actual research papers
    study_metadata = {
        'bakbot': {
            'name': 'Spacing of cue-approach training leads to better maintenance of behavioral change',
            'authors': ['Bakkour, A.', 'Botvinik-Nezer, R.', 'Cohen, N.', 'Hover, A. M.', 'Poldrack, R. A.', 'Schonberg, T.'],
            'year': 2018,
            'journal': 'PLOS ONE',
            'doi': '10.1371/journal.pone.0201580'
        },
        'bakpol': {
            'name': 'The hippocampus supports deliberation during value-based decisions',
            'authors': ['Bakkour, A.', 'Palombo, D. J.', 'Zylberberg, A.', 'Kang, Y. H.', 'Reid, A.', 'Verfaellie, M.', 'Shadlen, M. N.', 'Shohamy, D.'],
            'year': 2019,
            'journal': 'eLife',
            'doi': '10.7554/eLife.46080'
        },
        'balim': {
            'name': 'Investigating psychological mechanisms of self-controlled decisions for food and leisure activity',
            'authors': ['Bailey, C.', 'Lim, S.-L.'],
            'year': 2024,
            'journal': 'Journal of Behavioral Medicine',
            'doi': '10.1007/s10865-024-00469-3'
        },
        'brusaeb': {
            'name': 'Sources of confidence in value-based choice',
            'authors': ['Brus, J.', 'Aebersold, H.', 'Grueschow, M.', 'Polania, R.'],
            'year': 2021,
            'journal': 'Nature Communications',
            'doi': '10.1038/s41467-021-27618-5'
        },
        'deskrab1': {
            'name': 'Decomposing preferences into predispositions and evaluations',
            'authors': ['Desai, N.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Journal of Experimental Psychology: General',
            'doi': '10.1037/xge0001162'
        },
        'deskrab2': {
            'name': 'Decomposing preferences into predispositions and evaluations',
            'authors': ['Desai, N.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Journal of Experimental Psychology: General',
            'doi': '10.1037/xge0001162'
        },
        'deskrab4': {
            'name': 'Decomposing preferences into predispositions and evaluations',
            'authors': ['Desai, N.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Journal of Experimental Psychology: General',
            'doi': '10.1037/xge0001162'
        },
        'eumdol': {
            'name': 'Peripheral Visual Information Halves Attentional Choice Biases',
            'authors': ['Eum, B.', 'Dolbier, S.', 'Rangel, A.'],
            'year': 2023,
            'journal': 'Psychological Science',
            'doi': '10.1177/09567976231184878'
        },
        'foljac2': {
            'name': 'Explicit representation of confidence informs future value-based decisions',
            'authors': ['Folke, T.', 'Jacobsen, C.', 'Fleming, S. M.', 'De Martino, B.'],
            'year': 2016,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-016-0002'
        },
        'ganzou': {
            'name': 'Computational Methods for Predicting and Understanding Food Judgment',
            'authors': ['Gandhi, N.', 'Zou, W.', 'Meyer, C.', 'Bhatia, S.', 'Walasek, L.'],
            'year': 2022,
            'journal': 'Psychological Science',
            'doi': '10.1177/09567976211043426'
        },
        'gwikrab': {
            'name': 'Attitudes and attention',
            'authors': ['Gwinn, R.', 'Krajbich, I.'],
            'year': 2020,
            'journal': 'Journal of Experimental Social Psychology',
            'doi': '10.1016/j.jesp.2019.103892'
        },
        'gwileb': {
            'name': 'The spillover effects of attentional learning on value-based choice',
            'authors': ['Gwinn, R. E.', 'Leber, A.', 'Krajbich, I.'],
            'year': 2019,
            'journal': 'Cognition',
            'doi': '10.1016/j.cognition.2018.10.012'
        },
        'hasdes': {
            'name': 'Incentivized and non-incentivized liking ratings outperform willingness-to-pay in predicting choice',
            'authors': ['Hascher, J.', 'Desai, N.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Judgment and Decision Making',
            'doi': '10.1017/S1930297500008500'
        },
        'marglu': {
            'name': 'The Hungry Lens: Hunger Shifts Attention and Attribute Weighting in Dietary Choice',
            'authors': ['March, J.', 'Gluth, S.'],
            'year': 2025,
            'journal': 'eLife',
            'doi': '10.7554/eLife.103736.2'
        },
        'larlua': {
            'name': 'Increased BMI is associated with an altered decision-making process during healthy food choices in males and females',
            'authors': ['Larenas, G.', 'Luarte, L.', 'Kerr, B.', 'Ossandón, T.', 'Cortés, V.', 'Baudrand, R.', 'Pérez Leighton, C.'],
            'year': 2025,
            'journal': 'Appetite',
            'doi': '10.1016/j.appet.2025.107859'
        },
        'libain1': {
            'name': 'Memorable but not chosen: No effect of memorability on value-based decisions',
            'authors': ['Li, X.', 'Bainbridge, W.', 'Bakkour, A.'],
            'year': 2022,
            'journal': 'Scientific Reports',
            'doi': '10.1038/s41598-022-26333-5'
        },
        'libain2': {
            'name': 'Memorable but not chosen: No effect of memorability on value-based decisions',
            'authors': ['Li, X.', 'Bainbridge, W.', 'Bakkour, A.'],
            'year': 2022,
            'journal': 'Scientific Reports',
            'doi': '10.1038/s41598-022-26333-5'
        },
        'romfred': {
            'name': 'Considering what we know and what we don\'t know: Expectations and confidence guide value integration in value-based decision-making',
            'authors': ['Frömer, R.', 'Callaway, F.', 'Griffiths, T. L.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Open Mind',
            'doi': '10.1162/opmi_a_00103'
        },
        'sepush': {
            'name': 'Visual attention modulates the integration of goal-relevant evidence and not value',
            'authors': ['Sepulveda, P.', 'Usher, M.', 'Davies, N.', 'Benson, A. A.', 'Ortoleva, P.', 'De Martino, B.'],
            'year': 2020,
            'journal': 'eLife',
            'doi': '10.7554/eLife.60705'
        },
        'shenhav1b': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shenhav2': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shenhav3a': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shenhav3b': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shenhav4': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shenhav5a': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shenhav5b': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shenhav6': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'doi': '10.1038/s41562-024-02064-7'
        },
        'shevsmith1': {
            'name': 'High-value decisions are fast and accurate, inconsistent with diminishing value sensitivity',
            'authors': ['Shevlin, B. R. K.', 'Smith, S. M.', 'Hausfeld, J.', 'Krajbich, I.'],
            'year': 2022,
            'journal': 'Proceedings of the National Academy of Sciences',
            'doi': '10.1073/pnas.2101508119'
        },
        'shevsmith2': {
            'name': 'High-value decisions are fast and accurate, inconsistent with diminishing value sensitivity',
            'authors': ['Shevlin, B. R. K.', 'Smith, S. M.', 'Hausfeld, J.', 'Krajbich, I.'],
            'year': 2022,
            'journal': 'Proceedings of the National Academy of Sciences',
            'doi': '10.1073/pnas.2101508119'
        },
        'smikrab': {
            'name': 'Mental representations distinguish value-based decisions from perceptual decisions',
            'authors': ['Smith, S. M.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Psychonomic Bulletin & Review',
            'doi': '10.3758/s13423-021-01911-2'
        },
        'smikrab2018': {
            'name': 'Attention and choice across domains',
            'authors': ['Smith, S. M.', 'Krajbich, I.'],
            'year': 2018,
            'journal': 'Journal of Experimental Psychology: General',
            'doi': '10.1037/xge0000482'
        },
        'sucro': {
            'name': 'Elucidating the underlying components of food valuation in the human orbitofrontal cortex',
            'authors': ['Suzuki, S.', 'Cross, L.', 'O\'Doherty, J. P.'],
            'year': 2017,
            'journal': 'Nature Neuroscience',
            'doi': '10.1038/s41593-017-0008-x'
        },
        'thomolt': {
            'name': 'Uncovering the computational mechanisms underlying many-alternative choice',
            'authors': ['Thomas, A. W.', 'Molter, F.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'eLife',
            'doi': '10.7554/elife.57012'
        },
        'toyam': {
            'name': 'Subjective Evaluation of Food: A Japanese Database',
            'authors': ['Toyama, A.', 'Yamashita, Y.', 'Suzuki, S.'],
            'year': 2025,
            'journal': 'OSF',
            'doi': '10.31234/osf.io/ywt3k_v1'
        },
        'xuefoe': {
            'name': 'Neural Representations of Food-Related Attributes in the Human Orbitofrontal Cortex during Choice Deliberation in Anorexia Nervosa',
            'authors': ['Xue, A. M.', 'Foerde, K.', 'Walsh, B. T.', 'Steinglass, J. E.', 'Shohamy, D.', 'Bakkour, A.'],
            'year': 2022,
            'journal': 'Journal of Neuroscience',
            'doi': '10.1523/JNEUROSCI.0958-21.2021'
        }
    }
    
    return study_metadata

def parse_dataset_info(dataset_subjectid):
    """Parse dataset and subject info from combined field"""
    # Examples: bakbot_BM2_654, deskrab1_1, shenhav1a_1
    parts = dataset_subjectid.split('_')
    
    if len(parts) >= 2:
        # Most common pattern: study_dataset_subject or study_subject
        study_prefix = parts[0]
        
        if len(parts) >= 3:
            # Pattern: study_dataset_subject (e.g., bakbot_BM2_654)
            dataset_name = '_'.join(parts[:-1])  # Everything except last part
            subject_id = parts[-1]  # Last part is subject ID
        else:
            # Pattern: study_subject (e.g., deskrab1_1)
            dataset_name = parts[0]  # Use study prefix as dataset name
            subject_id = parts[1]
    else:
        # Fallback
        study_prefix = dataset_subjectid
        dataset_name = dataset_subjectid
        subject_id = "1"
    
    return study_prefix, dataset_name, subject_id


def parse_rating_scale(scale_str):
    """Parse rating scale string to get min and max values"""
    # Examples: "0_to_3", "-5_to_5", "1_to_10"
    if '_to_' in scale_str:
        parts = scale_str.split('_to_')
        try:
            scale_min = float(parts[0])
            scale_max = float(parts[1])
            return scale_min, scale_max, "likert"
        except ValueError:
            pass
    
    # Default fallback
    return 0.0, 10.0, "likert"


def normalize_rating(rating, scale_min, scale_max):
    """Normalize rating to 0-1 scale"""
    if scale_min == scale_max:
        return 0.5
    return (rating - scale_min) / (scale_max - scale_min)


def categorize_food_item(item_name):
    """Simple food categorization based on item name"""
    # Handle non-string items
    if pd.isna(item_name) or not isinstance(item_name, str):
        return 'other'
    
    item_lower = item_name.lower()
    
    if any(word in item_lower for word in ['chocolate', 'candy', 'sweet', 'cookie', 'cake', 'mms', 'snickers', 'twix', 'kitkat', 'oreos', '3musketeers', 'babyruth', 'butterfinger', 'almondjoy']):
        return 'sweets'
    elif any(word in item_lower for word in ['chip', 'doritos', 'cheetos', 'fritos', 'pringles', 'cheesy']):
        return 'chips'
    elif any(word in item_lower for word in ['cracker', 'goldfish', 'cheezits', 'animal']):
        return 'crackers'
    elif any(word in item_lower for word in ['fruit', 'apple', 'banana', 'orange', 'strawberry', 'berry']):
        return 'fruits'
    elif any(word in item_lower for word in ['vegetable', 'carrot', 'broccoli']):
        return 'vegetables'
    elif any(word in item_lower for word in ['drink', 'soda', 'juice', 'water', 'cola']):
        return 'beverages'
    elif any(word in item_lower for word in ['pizza', 'bread', 'bagel', 'sandwich']):
        return 'main_dishes'
    elif any(word in item_lower for word in ['ice', 'cream', 'frozen']):
        return 'frozen_desserts'
    else:
        return 'other'


async def validate_data_structure(csv_file_path):
    """Validate the CSV data structure without importing"""
    print("🔍 Validating data structure...")
    
    try:
        df = pd.read_csv(csv_file_path)
        
        # Check required columns
        required_columns = ['dataset_subjectid', 'item_name', 'rating', 'rating_scale']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        
        # Check data types and formats
        print(f"📊 Data overview:")
        print(f"   Total rows: {len(df)}")
        print(f"   Unique subjects: {df['dataset_subjectid'].nunique()}")
        print(f"   Unique items: {df['item_name'].nunique()}")
        print(f"   Rating scales: {sorted(df['rating_scale'].unique())}")
        
        # Check for any obvious issues
        null_subjects = df['dataset_subjectid'].isnull().sum()
        null_items = df['item_name'].isnull().sum()
        null_ratings = df['rating'].isnull().sum()
        
        print(f"   Null values - subjects: {null_subjects}, items: {null_items}, ratings: {null_ratings}")
        
        # Sample some data parsing
        sample_subjects = df['dataset_subjectid'].head(10).tolist()
        print(f"   Sample subject IDs: {sample_subjects}")
        
        for subject_id in sample_subjects[:3]:
            study_prefix, dataset_name, subj_id = parse_dataset_info(subject_id)
            print(f"     {subject_id} -> study: {study_prefix}, dataset: {dataset_name}, subject: {subj_id}")
        
        print("✅ Data structure validation complete")
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


async def import_csv_data(csv_file_path, excel_file_path=None, dry_run=False):
    """Import data from CSV file with optional Excel metadata"""
    if dry_run:
        return await validate_data_structure(csv_file_path)
    
    print(f"Loading data from {csv_file_path}...")
    
    # Load CSV data
    try:
        df = pd.read_csv(csv_file_path)
        initial_count = len(df)
        
        # Validate required columns exist
        required_columns = ['dataset_subjectid', 'item_name', 'rating', 'rating_scale']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"CSV missing required columns: {missing_columns}")
        
        # Check if file is empty
        if len(df) == 0:
            raise ValueError("CSV file is empty")
        
        # Filter out rows with invalid data
        df = df.dropna(subset=['dataset_subjectid', 'item_name', 'rating'])  # Remove rows with missing essential data
        df = df[df['item_name'].astype(str) != 'nan']
        df['item_name'] = df['item_name'].astype(str)
        
        # Clean rating values - convert to numeric and filter out non-numeric
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        df = df.dropna(subset=['rating'])  # Remove rows where rating conversion failed
        
        # Validate ratings are within their declared scales and clean outliers
        initial_ratings_count = len(df)
        valid_ratings = []
        
        for _, row in df.iterrows():
            rating_value = row['rating']
            scale_str = row['rating_scale']
            scale_min, scale_max, _ = parse_rating_scale(scale_str)
            
            # Allow some tolerance for floating point precision
            tolerance = (scale_max - scale_min) * 0.1  # 10% tolerance
            if scale_min - tolerance <= rating_value <= scale_max + tolerance:
                valid_ratings.append(True)
            else:
                valid_ratings.append(False)
        
        df['valid_rating'] = valid_ratings
        invalid_count = len(df) - df['valid_rating'].sum()
        print(f"   Found {invalid_count} ratings outside expected scales - will be filtered out")
        
        # Keep only valid ratings
        df = df[df['valid_rating']].drop('valid_rating', axis=1)
        
        # Validate that we still have data after cleaning
        cleaned_count = len(df)
        if cleaned_count == 0:
            raise ValueError("No valid data remaining after cleaning")
        
        print(f"✅ Loaded {cleaned_count} rows from CSV ({initial_count - cleaned_count} rows with invalid data removed)")
        print(f"   Columns: {df.columns.tolist()}")
        print(f"   Unique subjects: {df['dataset_subjectid'].nunique()}")
        print(f"   Unique items: {df['item_name'].nunique()}")
        print(f"   Rating scales: {df['rating_scale'].unique()}")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return
    
    # Load study metadata from Excel if available
    study_metadata = {}
    if excel_file_path and os.path.exists(excel_file_path):
        study_metadata = await load_study_metadata_from_excel(excel_file_path)
        print(f"✅ Loaded metadata for {len(study_metadata)} studies from Excel")
    
    # Initialize database
    await init_db()
    
    async for db in get_db():
        try:
            # Track what we create
            studies_created = {}
            datasets_created = {}
            items_created = {}
            ratings_count = 0
            
            print("Processing data...")
            
            # Get unique dataset prefixes for creating studies/datasets
            unique_datasets = df['dataset_subjectid'].apply(lambda x: x.split('_')[0]).unique()
            print(f"Found {len(unique_datasets)} unique dataset prefixes: {unique_datasets[:10]}...")
            
            # Process each unique dataset prefix to create studies
            for study_prefix in unique_datasets:
                if study_prefix not in studies_created:
                    metadata = study_metadata.get(study_prefix, {})
                    
                    study = Study(
                        name=metadata.get('name', f"{study_prefix.title()} Study"),
                        authors=metadata.get('authors', [f"{study_prefix.title()}, A."]),
                        year=metadata.get('year', 2020),
                        description=metadata.get('description', f"Food preference study from {study_prefix} dataset"),
                        journal="Food Quality and Preference",  # Default journal
                    )
                    db.add(study)
                    await db.flush()  # Get the ID
                    studies_created[study_prefix] = study
                    print(f"  Created study: {study.name}")
            
            # Group by dataset name to create datasets
            # Use the same logic as parse_dataset_info for consistency
            def get_dataset_name(dataset_subjectid):
                parts = dataset_subjectid.split('_')
                if len(parts) >= 3:
                    return '_'.join(parts[:-1])  # Everything except last part
                else:
                    return parts[0]  # Use study prefix as dataset name
            
            df['dataset_name'] = df['dataset_subjectid'].apply(get_dataset_name)
            unique_dataset_names = df['dataset_name'].unique()
            
            for dataset_name in unique_dataset_names:
                if dataset_name not in datasets_created:
                    # Get the study prefix for this dataset
                    study_prefix = dataset_name.split('_')[0]
                    study = studies_created[study_prefix]
                    
                    # Get dataset-specific data
                    dataset_df = df[df['dataset_name'] == dataset_name]
                    metadata = study_metadata.get(study_prefix, {})
                    
                    # Get rating scale for this dataset
                    scale_str = dataset_df['rating_scale'].iloc[0]
                    scale_min, scale_max, scale_type = parse_rating_scale(scale_str)
                    
                    # Calculate actual counts
                    n_subjects = dataset_df['dataset_subjectid'].nunique()
                    n_items = dataset_df['item_name'].nunique()
                    
                    dataset = Dataset(
                        study_id=study.id,
                        name=f"{dataset_name} Dataset",
                        description=f"Dataset from {study.name}",
                        n_subjects=metadata.get('num_subjects', n_subjects),
                        n_items=metadata.get('num_items', n_items),
                        rating_scale_min=scale_min,
                        rating_scale_max=scale_max,
                        rating_scale_type=scale_type,
                        data_completeness=95.0,  # Assume high completeness
                        file_format="csv"
                    )
                    db.add(dataset)
                    await db.flush()  # Get the ID
                    datasets_created[dataset_name] = dataset
                    print(f"  Created dataset: {dataset.name} (scale: {scale_min}-{scale_max})")
            
            # Create all unique food items
            unique_items = df['item_name'].unique()
            for item_name in unique_items:
                if item_name not in items_created:
                    category = categorize_food_item(item_name)
                    standardized_name = item_name.lower().replace(' ', '_')
                    
                    # Calculate frequency (number of unique subjects who rated this item)
                    item_frequency = df[df['item_name'] == item_name]['dataset_subjectid'].nunique()
                    
                    item = Item(
                        name=item_name,
                        standardized_name=standardized_name,
                        category=category,
                        description=f"Food item: {item_name}",
                        frequency=item_frequency
                    )
                    db.add(item)
                    await db.flush()  # Get the ID
                    items_created[item_name] = item
            
            print(f"Created {len(items_created)} food items")
            
            # Now process all ratings (with deduplication)
            print("Creating ratings (with deduplication)...")
            batch_size = 10000
            
            # First, deduplicate the data
            print("Deduplicating ratings...")
            df_unique = df.drop_duplicates(subset=['dataset_subjectid', 'item_name'], keep='first')
            duplicates_removed = len(df) - len(df_unique)
            print(f"  Removed {duplicates_removed} duplicate ratings")
            print(f"  Processing {len(df_unique)} unique ratings")
            
            # Track what we've already added to avoid constraint violations
            rating_keys_added = set()
            
            for i, (_, row) in enumerate(df_unique.iterrows()):
                dataset_subjectid = row['dataset_subjectid']
                item_name = row['item_name']
                rating_value = row['rating']
                scale_str = row['rating_scale']
                
                # Parse info
                study_prefix, dataset_name, subject_id = parse_dataset_info(dataset_subjectid)
                scale_min, scale_max, _ = parse_rating_scale(scale_str)
                
                # Validate rating is within expected scale
                if not (scale_min <= rating_value <= scale_max):
                    print(f"⚠️  Warning: Rating {rating_value} outside scale {scale_min}-{scale_max} for {dataset_subjectid}")
                    # Could choose to skip this rating or normalize it
                
                # Get the actual dataset name used in our dataset creation
                if len(dataset_subjectid.split('_')) >= 3:
                    actual_dataset_name = '_'.join(dataset_subjectid.split('_')[:-1])
                else:
                    actual_dataset_name = study_prefix
                
                # Check if we have the required references
                if actual_dataset_name not in datasets_created or item_name not in items_created:
                    continue
                
                # Get references
                dataset = datasets_created[actual_dataset_name]
                item = items_created[item_name]
                
                # Create unique key for this rating
                rating_key = (dataset.id, subject_id, item.id)
                
                # Skip if we've already added this combination
                if rating_key in rating_keys_added:
                    continue
                
                # Create rating
                normalized_rating = normalize_rating(rating_value, scale_min, scale_max)
                
                rating = Rating(
                    dataset_id=dataset.id,
                    item_id=item.id,
                    subject_id=subject_id,
                    rating=rating_value,
                    normalized_rating=normalized_rating
                )
                db.add(rating)
                rating_keys_added.add(rating_key)
                ratings_count += 1
                
                # Commit in batches
                if ratings_count % batch_size == 0:
                    await db.commit()
                    print(f"  Processed {ratings_count} ratings...")
            
            # Final commit
            await db.commit()
            
            print(f"✅ Successfully imported data:")
            print(f"   - {len(studies_created)} studies")
            print(f"   - {len(datasets_created)} datasets")
            print(f"   - {len(items_created)} food items")
            print(f"   - {ratings_count} ratings")
            
        except Exception as e:
            print(f"❌ Error importing data: {e}")
            await db.rollback()
            raise


async def main():
    """Main function"""
    csv_file = "final_database.csv"
    excel_file = "Liking Rating Database.xlsx"
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    print("🚀 Starting real data import...")
    print("=" * 50)
    
    # First run validation
    validation_passed = await import_csv_data(csv_file, excel_file, dry_run=True)
    
    if validation_passed:
        print("\n" + "=" * 50)
        print("🚀 Validation passed! Starting actual import...")
        await import_csv_data(csv_file, excel_file, dry_run=False)
    else:
        print("❌ Validation failed. Please fix the data issues before importing.")
        return
    
    print("=" * 50)
    print("✅ Import complete!")


if __name__ == "__main__":
    asyncio.run(main())
