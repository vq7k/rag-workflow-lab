"""Dify 真实生成调用的会话编排；不对语义质量自动打分。"""
import time


def execute_cases(cases, request, save, user='rag-lab-evaluation'):
    """request(payload)->(response, elapsed_s); save(name, JSON) 负责即时留证。"""
    rows=[]
    for case in cases:
        conversation=''
        broken=False
        for turn, query in enumerate(case['turns'],1):
            stem=f"{case['id']}-T{turn}"
            row={'case_id':case['id'],'turn':turn,'status':'skipped' if broken else 'running'}
            if broken:
                row['error']='前序轮失败，不以新会话伪装连续对话'
                rows.append(row)
                save('results.json',rows)
                continue
            payload={'inputs':{},'query':query,'response_mode':'blocking',
                     'conversation_id':conversation,'user':user}
            save(stem+'-request.json',payload)
            started=time.perf_counter()
            try:
                response,elapsed=request(payload)
                save(stem+'-response.json',response)
                if not (isinstance(response.get('answer'),str) and response['answer'].strip()
                        and isinstance(response.get('conversation_id'),str) and response['conversation_id']
                        and isinstance(response.get('message_id'),str) and response['message_id']):
                    raise ValueError('响应缺少非空 answer、conversation_id 或 message_id')
                if conversation and response['conversation_id'] != conversation:
                    raise ValueError('续轮响应改变 conversation_id')
                conversation=response['conversation_id']
                row.update(status='ok',latency_s=elapsed,conversation_id=conversation,
                           message_id=response['message_id'])
            except (RuntimeError,ValueError,OSError) as exc:
                # request 层必须保证错误信息不含密钥和响应正文。
                row.update(status='failed',latency_s=round(time.perf_counter()-started,4),error=str(exc))
                broken=True
            rows.append(row)
            save('results.json',rows)
    return rows


def summarize_reviews(rows,reviews):
    index={}
    for review in reviews:
        key=(review['case_id'],int(review['turn']))
        if key in index: raise ValueError('人工标注题号与轮次重复')
        if review.get('overall') not in {'pass','fail','pending'}: raise ValueError('overall 必须为 pass/fail/pending')
        index[key]=review
    expected={(r['case_id'],r['turn']) for r in rows}
    if set(index)-expected: raise ValueError('标注包含不属于本轮的题号或轮次')
    counts={'planned_turns':len(rows),'execution_ok':0,'execution_failed_or_skipped':0,
            'quality_passed':0,'quality_failed':0,'quality_pending':0}
    for row in rows:
        if row['status']!='ok':
            counts['execution_failed_or_skipped']+=1
            continue
        counts['execution_ok']+=1
        review=index.get((row['case_id'],row['turn']),{})
        state=review.get('overall','pending')
        if state in {'pass','fail'} and not review.get('reason','').strip():
            raise ValueError('通过或不通过必须填写 reason，说明人工判断依据')
        counts[{'pass':'quality_passed','fail':'quality_failed','pending':'quality_pending'}[state]]+=1
    counts['scope']='开发回归计数；执行成功不代表语义通过，pending 不算通过'
    return counts
