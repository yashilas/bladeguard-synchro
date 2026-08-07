"""
Script to convert final.csv to text format for RAG database.
Reads the CSV and creates formatted text documents for each food item.
"""

import pandas as pd
from pathlib import Path


def create_materials_text_database(csv_path: str, output_path: str):
    """
    Convert materials CSV into a text file with formatted documents.
    Each material item becomes a formatted text entry.
    """
    # Read the CSV with a robust encoding fallback
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1")

    documents = []

    for index, row in df.iterrows():
        # Clean up the calorie and kJ values
        dens = str(row['density']).replace(' density', '')
        tenst = str(row['tensile strength']).replace(' tensile strength', '')
        elon = str(row['elongation at break']).replace(' elongation at break', '')
        mod = str(row['modulus if available']).replace('modulus if available', '')

        # Create rich document text for semantic search
        serving_ref = str(row.get('per100grams', '')).strip()
        material_name = str(row.get('MaterialName', '')).strip()
        family_name = str(row.get('Family', '')).strip()
        document_text = f"""Material: {material_name}
Family: {family_name}
Properties:
- Density: {dens} g per cc
- Tensile Strength: {tenst} Mpa
- Elongation at Break: {elon} %
- Modulus: {mod} Gpa    
- Serving size reference: {serving_ref}

This is a {material_name.lower()} material that provides {dens} density per 100 grams."""

        documents.append(document_text)

    # Write all documents to the output file
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, doc in enumerate(documents):
            f.write(doc)
            # Add separator between documents (except for the last one)
            if i < len(documents) - 1:
                f.write('\n\n---\n\n')

    print(f"Successfully created {output_path}")
    print(f"Converted {len(documents)} material items from {csv_path}")
    return len(documents)


if __name__ == "__main__":
    # Define paths    
    data_dir = Path(__file__).parent.parent.parent   / "data" 
    csv_path = data_dir / "ranked_materials.csv"
    output_path = data_dir / "materials_database.txt"

    # Create the text database
    num_items = create_materials_text_database(str(csv_path), str(output_path))
    print(f"\nOutput file location: {output_path}")
    print(f"Total items processed: {num_items}")
