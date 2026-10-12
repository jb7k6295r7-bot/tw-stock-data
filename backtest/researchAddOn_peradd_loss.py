import pandas as pd, numpy as np
d=pd.read_csv('/home/chemtim/tw-p17/backtest/resultsAddOn/exit5/exits.csv.gz'); d=d[d['世界']=='主']
C=0.00585; out=[]
for st,g in [('營量','A2'),('營飆','A1')]:
    x=d[(d['策略']==st)&(d['格']==g)].drop_duplicates(['sid','tb'])
    p0=x['加碼價'].values; pS=x['S_價'].values; arms={'同日賣':pS/p0-1-C}
    for a in ['E1a','E1b','E2','E3','E5','D1_5','D1_10','D5']:
        w=x[f'{a}_w'].fillna(0).values; p1=x[f'{a}_px1'].values
        arms[a]=np.where(x[f'{a}_trig'].values==1, w*(p1/p0)+(1-w)*(pS/p0), pS/p0)-1-C
    for k,r in arms.items():
        L=r[r<=0]; W=r[r>0]
        out.append((st,k,len(r),(r>0).mean(),r.mean(),L.mean(),np.percentile(r,10),r.min(),(r<=-0.15).mean(),W.mean()))
o=pd.DataFrame(out,columns=['策略','賣法','筆','賺錢比例','平均','賠的平均','p10','最差','賠超過15%比例','賺的平均'])
pd.set_option('display.width',220); print(o.round(3).to_string(index=False))
