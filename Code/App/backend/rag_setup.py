from pathlib import Path
from typing import Dict, List

import chromadb
import pandas as pd


def prepare_nutrition_documents(csv_path: str) -> Dict:
    """
    Convert nutrition CSV into ChromaDB-ready documents.
    Each food item becomes a searchable document.
    """
    
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1")

    documents = []
    metadatas = []
    ids = []

    for index, row in df.iterrows():
        # Create rich document text for semantic search
        # Clean up the calorie and kJ values
        rank = str(row['No']).replace(' No', '')
        dens = str(row['density']).replace(' density', '')
        tenst = str(row['tensile strength']).replace(' tensile strength', '')
        elon = str(row['elongation at break']).replace(' elongation at break', '')
        mod = str(row['modulus if available']).replace('modulus if available', '')

        # Create rich document text for semantic search
        serving_ref = str(row.get('per100grams', '')).strip()
        material_name = str(row.get('MaterialName', '')).strip()
        family_name = str(row.get('Family', '')).strip()
        strength_value = str(row.get('tensile strength', '')).strip()
        rank_value = str(row.get('No', '')).strip()

        document_text = f"""Material: {material_name}
Family: {family_name}
Rank: {rank}
Properties:
- Density: {dens} g per cc
- Tensile Strength: {tenst} Mpa
- Elongation at Break: {elon} %
- Modulus: {mod} Gpa    
- Serving size reference: {serving_ref}

This is a {material_name.lower()} material that provides {dens} density per 100 grams."""

        # Rich metadata for filtering and exact lookups
        material_key = material_name.lower()
        family_key = family_name.lower()
        metadata = {
            "Material": material_key,
            "Family": family_key,
            "Strength": strength_value.lower(),
            "serving_info": serving_ref,
            "rank": rank_value,
            # Add searchable keywords
            "keywords": f"{material_key} {family_key} {rank_value}".replace(
                " ", "_"
            ),
        }

        documents.append(document_text)
        metadatas.append(metadata)
        ids.append(f"material_{index}")

    return {"documents": documents, "metadatas": metadatas, "ids": ids}


def setup_nutrition_chromadb(csv_path: str, collection_name: str = "materials_db"):
    """
    Create and populate ChromaDB collection with materials data.
    """
    # Initialize ChromaDB   
    #client = chromadb.PersistentClient("../chroma")
    script_dir = Path(__file__).parent.parent.parent  
    client = chromadb.PersistentClient(path=script_dir / "chroma")

    # Create collection (delete if exists)
    try:
        client.delete_collection(collection_name)
    except BaseException:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={
            "description": "Materials database with properties and information"
        },
    )
     # Prepare documents
    data = prepare_nutrition_documents(csv_path)

    # Add to ChromaDB
    collection.add(
        documents=data["documents"], metadatas=data["metadatas"], ids=data["ids"]
    )

    print(
        f"Added {len(data['documents'])} material items to ChromaDB collection '{collection_name}'"
    )
    return collection

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    csv_path = script_dir / "data" / "final.csv"
    collection = setup_nutrition_chromadb(csv_path, "materials_db")


    chroma_client = chromadb.PersistentClient(path="chroma")
    materials_db = chroma_client.get_collection(name="materials_db")

    results = materials_db.query(query_texts=["Acrylonitrile"], n_results=3)
    for i, doc in enumerate(results["documents"][0]):
        print(results["metadatas"][0][i])
        print(doc)
        print("\n")