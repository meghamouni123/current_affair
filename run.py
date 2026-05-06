import os
import sys
import logging

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    import argparse
    import uvicorn

    p = argparse.ArgumentParser(description='CA Portal — FastAPI + Uvicorn')
    p.add_argument('--port',   type=int,  default=8000)
    p.add_argument('--reload', action='store_true', default=True, help='Auto-reload on code change')
    p.add_argument('--train',  action='store_true', help='Retrain classifier before starting')
    args = p.parse_args()

    if args.train:
        logger.info("Retraining classifier...")
        from backend.classifier import train_classifier
        acc = train_classifier()
        logger.info(f"Training complete — accuracy: {acc:.4f}")

    logger.info("=" * 55)
    logger.info("  CA Portal — FastAPI + Uvicorn")
    logger.info(f"  http://localhost:{args.port}")
    logger.info(f"  Docs → http://localhost:{args.port}/docs")
    logger.info("=" * 55)

    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
