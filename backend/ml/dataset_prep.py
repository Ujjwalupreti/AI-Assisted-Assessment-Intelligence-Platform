import pandas as pd
import json

def load_and_clean_data(csv_path: str) -> pd.DataFrame:
    """
    Step 1 & 2: Load and Clean Dataset
    Requires CSV with: question, topic, bloom_level, difficulty, question_type
    """
    df = pd.read_csv(csv_path)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['question'])
    
    # Remove empty questions
    df = df.dropna(subset=['question', 'bloom_level', 'topic', 'difficulty', 'question_type'])
    
    return df

def generate_annotation_template(output_path: str, sample_size: int = 100):
    """
    Step 4: Generate a blank template for human experts to label.
    """
    df = pd.DataFrame(columns=['question', 'topic', 'bloom_level', 'difficulty', 'question_type'])
    # Insert empty rows to be filled
    df = df.append([{}] * sample_size, ignore_index=True)
    df.to_csv(output_path, index=False)
    print(f"Annotation template saved to {output_path}")

def split_dataset(df: pd.DataFrame, train_ratio=0.7, val_ratio=0.15):
    """
    Step 6: Split data avoiding leakage.
    """
    from sklearn.model_selection import train_test_split
    
    train, temp = train_test_split(df, train_size=train_ratio, random_state=42)
    val_size = val_ratio / (1 - train_ratio)
    val, test = train_test_split(temp, train_size=val_size, random_state=42)
    
    return train, val, test

if __name__ == '__main__':
    print("Dataset Prep utilities ready.")
