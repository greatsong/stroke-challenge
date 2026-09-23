import pandas as pd, numpy as np, itertools
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
rng=np.random.default_rng(0)
원본=pd.read_csv("stroke.csv").sort_values("id").reset_index(drop=True)
열들=["age","avg_glucose_level","bmi","hypertension","heart_disease"]
몫=pd.Series(원본.index%10)
훈련마스크=(몫<=5).to_numpy(); 풀마스크=(몫>=6).to_numpy()      # 베타 방식: 훈련 60%, 채점 풀 40%
풀id=np.where(풀마스크)[0]; N=len(풀id); y풀=원본.loc[풀id,"stroke"].to_numpy()
print("채점 풀",N,"명, 환자",y풀.sum())
# 설정별로 풀 전체에 대한 예측(0/1)을 만든다. 지운 행은 -1(채점 제외)
설정=[]; 예측=[]
for 결측 in ["지운다","그대로 둔다"]:
    df=원본 if 결측=="그대로 둔다" else 원본.dropna(subset=["bmi"])
    유효=np.zeros(len(원본),bool); 유효[df.index]=True
    for k in range(2,6):
        for 입력열 in itertools.combinations(열들,k):
            입력열=list(입력열)
            X=df[입력열].copy(); tr=훈련마스크[df.index]
            if "bmi" in 입력열 and X["bmi"].isna().any():
                X["bmi"]=X["bmi"].fillna(float(X.loc[tr,"bmi"].median()))
            y=df["stroke"]
            sc=StandardScaler().fit(X[tr])
            lr=LogisticRegression(max_iter=2000,class_weight="balanced").fit(sc.transform(X[tr]),y[tr])
            모델들={("로지스틱",0):lr.predict_proba(sc.transform(X))[:,1]}
            for d in range(1,11):
                dt=DecisionTreeClassifier(max_depth=d,min_samples_leaf=5,random_state=0,class_weight="balanced").fit(X[tr],y[tr])
                모델들[("트리",d)]=dt.predict_proba(X)[:,1]
            for (m,d),p in 모델들.items():
                p전체=np.full(len(원본),np.nan); p전체[df.index]=p
                for th in np.arange(0.05,0.951,0.05):
                    pr=np.where(np.isnan(p전체[풀id]),-1,(p전체[풀id]>=th).astype(int)).astype(np.int8)
                    설정.append((결측,",".join(입력열),m,d,round(th,2))); 예측.append(pr)
P=np.stack(예측); S=len(설정); print("설정",S)
설정표=pd.DataFrame(설정,columns=["결측","입력","모델","깊이","기준"])
def f1(mask):
    pm=P[:,mask]; ym=y풀[mask]; ok=(pm>=0)
    pred=(pm==1); TP=(pred&(ym==1)).sum(1); FP=(pred&(ym==0)).sum(1); FN=((~pred)&ok&(ym==1)).sum(1)
    with np.errstate(invalid="ignore",divide="ignore"):
        f=2*TP/(2*TP+FP+FN)
    f[np.isnan(f)]=0; return f,TP,TP+FP
def 순위(v): return (-v).argsort().argsort()+1
# ── 1. 베타의 고정 분할: 공개 = 몫 6·7, 최종 = 몫 8·9
공개=np.isin(몫.to_numpy()[풀id],[6,7]); 최종=~공개
f공,TP공,안공=f1(공개); f최,TP최,안최=f1(최종)
print("\n[고정 분할] 공개 환자",y풀[공개].sum(),"명 / 최종 환자",y풀[최종].sum(),"명")
t=설정표.copy(); t["공개F1"]=f공.round(4); t["최종F1"]=f최.round(4); t["공개순위"]=순위(f공); t["최종순위"]=순위(f최)
t["공개찾음"]=TP공; t["최종찾음"]=TP최
print("공개 상위 10 →  최종 순위"); print(t.sort_values("공개순위").head(10).to_string(index=False))
print("\n최종 상위 5 ← 공개 순위"); print(t.sort_values("최종순위").head(5).to_string(index=False))
from scipy.stats import spearmanr
print("\n스피어만(전체)",round(spearmanr(f공,f최).correlation,3)," 공개 상위 100 안에서",round(spearmanr(f공[t.공개순위<=100],f최[t.공개순위<=100]).correlation,3))
# ── 2. 무작위 분할 300번: 공개 1등의 최종 순위와 점수 하락
R=300; 결과=[]
for r in range(R):
    m=np.zeros(N,bool); m[rng.choice(N,N//2,replace=False)]=True
    a,_,_=f1(m); b,_,_=f1(~m)
    i=a.argmax(); rb=순위(b)
    결과.append((a[i],b[i],b.max(),rb[i],설정표.깊이[i],np.median(a-b)))
결과=pd.DataFrame(결과,columns=["공개1등_공개F1","공개1등_최종F1","최종최고F1","공개1등의최종순위","공개1등깊이","전체중앙차"])
print("\n[무작위 분할 300번] 공개 1등의 운명")
print("공개 F1 평균",결과.공개1등_공개F1.mean().round(4),"→ 최종 F1 평균",결과.공개1등_최종F1.mean().round(4),
      "(그 분할의 최종 최고",결과.최종최고F1.mean().round(4),")")
print("공개 1등의 최종 순위: 중앙값",int(결과.공개1등의최종순위.median()),"· 10위 안 비율",(결과.공개1등의최종순위<=10).mean().round(2),"· 100위 안",(결과.공개1등의최종순위<=100).mean().round(2))
print("전체 설정의 공개−최종 중앙값(잡음 기준선)",결과.전체중앙차.mean().round(4))
print("공개 1등의 깊이 분포:",결과.공개1등깊이.value_counts().sort_index().to_dict(), " (0=로지스틱)")
# ── 3. 과적합인가 잡음인가: 설정별 F1의 분할 간 표준편차를 복잡도별로
편차=[];
for r in range(100):
    m=np.zeros(N,bool); m[rng.choice(N,N//2,replace=False)]=True
    a,_,_=f1(m); b,_,_=f1(~m); 편차.append(a-b)
편차=np.abs(np.stack(편차)).mean(0)
설정표["분할간차"]=편차; 설정표["평균F1"]=(f공+f최)/2
print("\n[복잡도별] 공개−최종 절대차 평균(잡음 크기) · 상위권(평균F1≥0.28)만")
g=설정표[설정표.평균F1>=0.28].groupby("깊이")["분할간차"].agg(["mean","count"]).round(4); print(g.to_string())
# ── 4. 제출 횟수와 승자의 저주: 팀이 k번 시도해 공개 최고를 고르면 최종은?
print("\n[제출 횟수 k별] 공개 최고 설정의 최종 F1 (200회 평균)")
for k in [3,10,30,100,1000,S]:
    공,최,오=[],[],[]
    for r in range(200):
        m=np.zeros(N,bool); m[rng.choice(N,N//2,replace=False)]=True
        a,_,_=f1(m); b,_,_=f1(~m)
        idx=rng.choice(S,k,replace=False) if k<S else np.arange(S)
        i=idx[a[idx].argmax()]; 공.append(a[i]); 최.append(b[i]); 오.append(b[idx].max())
    print(f"k={k:>5}  공개 최고 {np.mean(공):.4f} → 최종 {np.mean(최):.4f}  (하락 {np.mean(공)-np.mean(최):.4f}) · 그 k개 중 최종 최고 {np.mean(오):.4f}")
# ── 5. 잡음 바닥: 최종 세트(환자 약 50명)에서 F1의 부트스트랩 표준오차
i=f최.argmax(); pm=P[i,최종]; ym=y풀[최종]; ok=pm>=0; pm=pm[ok]; ym=ym[ok]; bs=[]
for r in range(1000):
    j=rng.integers(0,len(ym),len(ym)); pr=pm[j]==1; yy=ym[j]
    TP=(pr&(yy==1)).sum(); FP=(pr&(yy==0)).sum(); FN=((~pr)&(yy==1)).sum(); bs.append(2*TP/(2*TP+FP+FN))
print("\n[잡음 바닥] 최종 1등 F1",round(f최[i],4),"부트스트랩 표준오차",round(np.std(bs),4),"→ ±",round(2*np.std(bs),3),"안은 구별 불가")
