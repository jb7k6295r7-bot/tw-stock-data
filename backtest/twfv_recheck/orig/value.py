import pandas as pd,numpy as np,sys
def path(E0,g1,pe_T,payout,yrs=10):
    e=E0;divs=[]
    for t in range(1,yrs+1):
        e*= (1+g1) if t<=5 else (1+g1/2)
        divs.append(e*payout)
    return divs,e*pe_T
def pv(divs,term,r): return sum(d/(1+r)**(t+1) for t,d in enumerate(divs))+term/(1+r)**len(divs)
def irr(price,divs,term):
    lo,hi=-0.5,1.0
    for _ in range(100):
        m=(lo+hi)/2
        if pv(divs,term,m)>price: lo=m
        else: hi=m
    return m
def scen(r):
    gh=r.g_hist if pd.notna(r.g_hist) else np.nan
    gc=r.g_cons if pd.notna(r.g_cons) else np.nan
    gn=np.nanmin([gh,gc,0.15]) if pd.notna(gc) else min(gh*0.8,0.15)
    gg=min(np.nanmax([gh,gc]),0.20)
    gb=gn*0.5
    return dict(普通=(gn,min(r.pe_med10,25)),好=(gg,min(r.pe_med10,35)),壞=(gb,min(r.pe_p25,15)))
def run(df):
    out=[]
    for _,r in df.iterrows():
        s=scen(r); res=dict(ticker=r.ticker,name=r['name'],ccy=r.ccy,price=r.price)
        for k,(g,pe) in s.items():
            d,t=path(r.E0,g,pe,r.payout); res[k+'_g']=round(g,3); res[k+'_pe']=pe; res[k+'_年化']=round(irr(r.price,d,t)*100,1)
        d,t=path(r.E0,*s['普通'],r.payout); res['合理買價']=round(pv(d,t,0.10),1)
        d,t=path(r.E0,*s['壞'],r.payout); res['安全買價']=round(pv(d,t,0.07),1)
        res['現價÷合理']=round(r.price/res['合理買價'],2)
        out.append(res)
    return pd.DataFrame(out)
if __name__=='__main__':
    df=pd.read_csv(sys.argv[1]); pd.set_option('display.width',250); print(run(df).to_string(index=False))
