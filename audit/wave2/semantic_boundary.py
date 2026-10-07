import copy,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from runbook_verify.parser import parse_runbook
from runbook_verify.checker import Checker
from runbook_verify.actions import apply_action
strategies=['breadth_first','depth_first','randomized_bounded','seeded_chaos_style']
def document(order=('a','b')):
 return {'name':'indirect-capacity oracle','allow_reordering':True,'max_depth':4,'system':{'regions':{'a':{},'b':{}},'services':{'api':{'min_available':1,'replicas':[{'id':f'r{i}','region':r} for i,r in enumerate(order)]}},'traffic_routes':{'web':{'service':'api','weights':{'a':100,'b':0}}}},'steps':[{'id':'up','action':'scale_service','params':{'service':'api','replicas':3,'region':'a'}},{'id':'down','action':'scale_service','params':{'service':'api','replicas':1}},{'id':'shift','action':'shift_traffic','params':{'route':'web','region':'b','percent':100}}]}
def oracle(doc):
 bad=[];legal=[]
 for perm in itertools.permutations(doc['steps']):
  regions=[r['region'] for r in doc['system']['services']['api']['replicas']];target='a';done=set();trace=[]
  for step in perm:
   if not set(step.get('after',[]))<=done:break
   trace.append(step['id']);done.add(step['id'])
   if step['id']=='up':regions+= [step['params']['region']]*(3-len(regions))
   if step['id']=='down':regions=regions[:1]
   if step['id']=='shift':target=step['params']['region']
   if target not in regions:bad.append(list(trace))
  else:legal.append([s['id'] for s in perm])
 return not bad,bad,legal
rows=[]
for order,up,target,mask in itertools.product([('a','b'),('b','a')],['a','b'],['a','b'],range(8)):
 d=document(order);d['steps'][0]['params']['region']=up;d['steps'][2]['params']['region']=target
 for k,(i,j) in enumerate([(0,1),(0,2),(1,2)]):
  if mask&(1<<k):d['steps'][j].setdefault('after',[]).append(d['steps'][i]['id'])
 safe,bad,legal=oracle(d)
 for strategy,por in itertools.product(strategies,[False,True]):
  q=copy.deepcopy(d);q['safety']={'exploration_strategy':strategy,'partial_order_reduction':por,'exploration_seed':23}
  got=Checker(parse_runbook(q)).check();rows.append({'document':q,'oracle_safe':safe,'oracle_bad_prefixes':bad,'oracle_legal_orders':legal,'verdict':got.verdict,'safe':got.safe,'inconclusive':got.inconclusive,'states':got.states_explored,'matches':got.safe==safe and not got.inconclusive})
a=parse_runbook(document());b=parse_runbook(document(('b','a')));b.state.services['api']=b.state.services['api'].with_replicas(tuple(reversed(a.state.services['api'].replicas)));step=a.steps[1]
after_a=apply_action(a.state,step);after_b=apply_action(b.state,step)
dead=document();dead['allow_reordering']=False;dead['steps']=dead['steps'][:2];dead['steps'][0]['after']=['down'];dr=Checker(parse_runbook(dead)).check()
print(json.dumps({'models':64,'checks':len(rows),'mismatches':sum(not r['matches'] for r in rows),'rows':rows,'fingerprint_pair':{'equal_before':a.state.fingerprint()==b.state.fingerprint(),'equal_after':after_a.fingerprint()==after_b.fingerprint(),'retained_a':[r.region for r in after_a.services['api'].replicas],'retained_b':[r.region for r in after_b.services['api'].replicas],'reachable_merge_claimed':False},'blocked_document_order':{'document':dead,'verdict':dr.verdict,'inconclusive':dr.inconclusive,'states':dr.states_explored}},indent=2))
