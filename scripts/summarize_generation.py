"""汇总已有生成调用及人工标注；不会调用模型。"""
import argparse
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_lab.generation import summarize_reviews

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir',type=Path,help='本轮 runs/dify-generation-* 目录')
    args=parser.parse_args()
    try:
        rows=json.loads((args.run_dir/'results.json').read_text())
        with (args.run_dir/'review.csv').open(newline='',encoding='utf-8') as f:reviews=list(csv.DictReader(f))
        summary=summarize_reviews(rows,reviews)
        (args.run_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(summary,ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:
        print('汇总失败：'+str(exc));return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
