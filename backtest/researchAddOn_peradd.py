import pandas as pd, numpy as np
d=pd.read_csv('/home/chemtim/tw-p17/backtest/resultsAddOn/exit5/exits.csv.gz')
d=d[d['世界']=='主']
C=0.00585
out=[]
for st,g in [('營量','A2'),('營飆','A1')]:
    x=d[(d['策略']==st)&(d['格']==g)].drop_duplicates(['sid','tb'])
    seg=np.where(pd.to_datetime(x['加碼日'])<'2022-01-01','2017～2021','2022～')
    p0=x['加碼價'].values; pS=x['S_價'].values
    arms={'同日賣':pS/p0-1-C}
    for a in ['E1a','E2','E5']:
        w=x[f'{a}_w'].fillna(0).values; p1=x[f'{a}_px1'].values
        r=np.where(x[f'{a}_trig'].values==1, w*(p1/p0)+(1-w)*(pS/p0), pS/p0)-1-C
        arms[a]=r
    for s in ['2017～2021','2022～','全部']:
        m=np.ones(len(x),bool) if s=='全部' else (seg==s)
        for k,r in arms.items():
            rr=r[m]; out.append((st,s,k,len(rr),(rr>0).mean(),rr.mean(),np.median(rr)))
o=pd.DataFrame(out,columns=['策略','段','賣法','筆','賺錢比例','平均','中位'])
pd.set_option('display.width',200); print(o.round(3).to_string(index=False))
