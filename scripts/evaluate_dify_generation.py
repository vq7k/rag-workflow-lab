"""PyCharm Run：真实调用 Dify 应用生成回答，保留证据并创建人工标注表。"""
import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_lab.retrieval import DifyClient
from rag_lab.generation import execute_cases,summarize_reviews


def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def load_env():
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            key,sep,value=line.partition('=')
            if not sep: raise ValueError('.env 格式应为 KEY=value')
            if key in {'DIFY_API_BASE','DIFY_APP_API_KEY'}:
                os.environ.setdefault(key,value.strip().strip('\"\''))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',default='baseline-v1')
    parser.add_argument('--snapshot',type=Path,help='运行前核查并脱敏的应用配置 JSON 快照')
    args=parser.parse_args()
    try:
        load_env()
        key=os.environ.get('DIFY_APP_API_KEY','')
        if not key: raise ValueError('缺少 DIFY_APP_API_KEY；应用 Key 与知识库 Key 不同，请在本地 .env 填写')
        client=DifyClient(os.environ.get('DIFY_API_BASE','http://localhost/v1'),key,timeout=600)
        cases_path=ROOT/'data/evaluation/stack-generation-v0.json'
        data=json.loads(cases_path.read_text())
        if hashlib.sha256((ROOT/data['source_file']).read_bytes()).hexdigest()!=data['source_sha256']:
            raise ValueError('资料哈希变化，先重新核对预期')
        snapshot=json.loads(args.snapshot.read_text()) if args.snapshot else None
    except (ValueError,OSError) as exc:
        print('启动失败：'+str(exc));return 1
    run=ROOT/'runs'/('dify-generation-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    run.mkdir(parents=True)
    save=lambda name,value:write_json(run/name,value)
    save('cases.json',data)
    save('config.json',{'label':args.label,'started_at':datetime.now(timezone.utc).isoformat(),
         'api_base':client.base_url,'endpoint':'/chat-messages','test_set_version':data['version'],
         'test_set_sha256':hashlib.sha256(cases_path.read_bytes()).hexdigest(),
         'source_sha256':data['source_sha256'],'configuration_snapshot':snapshot,
         'configuration_verified':False,'configuration_note':'需人工核对快照与运行中的应用，脚本不证明配置一致',
         'timeout_s':600,'retry':False,'cache_state':'unknown'})
    print('运行目录：'+str(run.relative_to(ROOT)),flush=True)
    print('开始真实模型调用；每题单轮独立会话，多轮按返回会话续传。',flush=True)
    def request(payload):
        print('提问：'+payload['query'],flush=True)
        response,elapsed=client.request('/chat-messages',payload)
        print(f'收到回答，客户端耗时 {elapsed:.2f}s',flush=True)
        return response,elapsed
    rows=execute_cases(data['cases'],request,save,user='rag-lab-'+run.name)
    with (run/'review.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['case_id','turn','core','source','conditions','refusal','multiturn','overall','reason','reviewer']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({'case_id':row['case_id'],'turn':row['turn'],'overall':'pending'})
    save('summary.json',summarize_reviews(rows,[]))
    print('调用结束，未进行语义自动评分。请对照 response 与 cases 填写 review.csv，再运行汇总脚本。')
    return int(any(r['status']!='ok' for r in rows))

if __name__=='__main__':raise SystemExit(main())
