import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

from classifier import train_classifier

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=str, default=None,
                   help='Path to CSV with text,category columns (default: data/cleaned_dataset.csv)')
    args = p.parse_args()

    print("Training MPNet + Logistic Regression classifier...")
    print("This will download all-mpnet-base-v2 (~420 MB) on first run.")
    acc = train_classifier(args.dataset)
    print(f"\nDone. Validation Accuracy: {acc:.4f}")
    print("Model saved to models/ca_classifier_mpnet.pkl")
