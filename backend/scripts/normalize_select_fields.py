#!/usr/bin/env python3
"""
Script to normalize all select field options in entity JSON files.
Converts {value, label} objects to simple string arrays where value=label.
"""
import json
import os
from pathlib import Path

def normalize_select_options(options):
    """Convert select options to simple string array."""
    if not options:
        return options
    
    # Already normalized (list of strings)
    if isinstance(options, list) and all(isinstance(o, str) for o in options):
        return options
    
    # Convert object format to strings
    if isinstance(options, list):
        normalized = []
        for opt in options:
            if isinstance(opt, dict):
                # Use label if available, otherwise value
                label = opt.get('label', opt.get('value', ''))
                if label:
                    normalized.append(label)
            elif isinstance(opt, str):
                normalized.append(opt)
        return normalized
    
    return options

def process_entity_file(file_path):
    """Process a single entity JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        modified = False
        
        # Process fields
        for field in data.get('fields', []):
            if field.get('field_type') == 'select' and 'options' in field:
                original = field['options']
                normalized = normalize_select_options(original)
                
                if original != normalized:
                    field['options'] = normalized
                    modified = True
                    print(f"  ✓ Normalized field: {field['name']}")
        
        # Write back if modified
        if modified:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Updated: {file_path.name}")
            return True
        
        return False
    
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Find and process all entity JSON files."""
    backend_dir = Path(__file__).parent.parent
    modules_dir = backend_dir / 'app' / 'modules'
    
    if not modules_dir.exists():
        print(f"Modules directory not found: {modules_dir}")
        return
    
    total_files = 0
    updated_files = 0
    
    # Scan all module directories
    for module_dir in modules_dir.iterdir():
        if not module_dir.is_dir() or module_dir.name.startswith('_'):
            continue
        
        entities_dir = module_dir / 'entities'
        if not entities_dir.exists():
            continue
        
        # Process all JSON files in entities directory
        for item in entities_dir.iterdir():
            json_file = None
            
            # Flat structure: entities/{entity}.json
            if item.is_file() and item.suffix == '.json':
                json_file = item
            # Nested structure: entities/{entity}/{entity}.json
            elif item.is_dir():
                nested_json = item / f"{item.name}.json"
                if nested_json.exists():
                    json_file = nested_json
            
            if json_file:
                total_files += 1
                if process_entity_file(json_file):
                    updated_files += 1
    
    print(f"\n📊 Summary:")
    print(f"   Total entity files: {total_files}")
    print(f"   Updated files: {updated_files}")
    print(f"   Unchanged files: {total_files - updated_files}")

if __name__ == '__main__':
    main()
