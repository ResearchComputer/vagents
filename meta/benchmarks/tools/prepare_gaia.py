from datasets import load_dataset

ds = load_dataset("gaia-benchmark/GAIA", "2023_all", split="validation", trust_remote_code=True)

datasets = []

for row in ds:
    datum = {
        'id': row['task_id'],
        'query': row['Question'],
        'level': row['Level'],
        'tools': row['Annotator Metadata']['Tools'],
        'answer': row['Final answer']
    }
    datasets.append(datum)
with open(f".local/datasets/gaia.jsonl", "w+") as f:
    for datum in datasets:
        f.write(f"{datum}\n")
        
print(f"Saved {len(ds)} records to .local/datasets/gaia/gaia.jsonl")