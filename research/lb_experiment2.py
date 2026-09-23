exec(open("lb_experiment.py").read().split("# ── 1.")[0])   # 데이터·예측 행렬·f1 함수만 재사용
rng=np.random.default_rng(1)
# A. 공개 1등의 하락 폭을 복잡도별로 (무작위 분할 300번)
rows=[]
for r in range(300):
    m=np.zeros(N,bool); m[rng.choice(N,N//2,replace=False)]=True
    a,_,_=f1(m); b,_,_=f1(~m); i=a.argmax(); rb=순위(b)
    rows.append((설정표.모델[i]+("" if 설정표.깊이[i]==0 else str(설정표.깊이[i])), a[i]-b[i], rb[i]))
A=pd.DataFrame(rows,columns=["공개1등모델","하락","최종순위"])
print("[A] 공개 1등을 차지한 모델별 · 최종에서의 하락과 순위 (300분할)")
print(A.groupby("공개1등모델").agg(횟수=("하락","size"),하락평균=("하락","mean"),최종순위중앙=("최종순위","median")).round(4).sort_values("횟수",ascending=False).to_string())
# B. 설정 자체의 잡음 크기(분할 간 |공개−최종| 평균)를 복잡도별로, 상위 500 설정만
편차=[]
for r in range(100):
    m=np.zeros(N,bool); m[rng.choice(N,N//2,replace=False)]=True
    a,_,_=f1(m); b,_,_=f1(~m); 편차.append(np.abs(a-b))
편차=np.stack(편차).mean(0); 전체,_,_=f1(np.ones(N,bool)); 설정표["잡음"]=편차; 설정표["전체F1"]=전체
상위=설정표.sort_values("전체F1",ascending=False).head(500)
print("\n[B] 상위 500 설정의 분할 간 흔들림(|공개−최종| 평균) · 깊이별 (0=로지스틱)")
print(상위.groupby("깊이")["잡음"].agg(["mean","count"]).round(4).to_string())
# C. 연수 규모 시뮬레이션: T팀이 각 k번 시도, 팀은 공개 최고 기록을 제출. 최종은 그 기록의 최종 F1
print("\n[C] 팀 단위: 공개 1등 팀이 최종에서도 1등일 확률 · 최종 3위 밖으로 밀릴 확률 · 공개 1등 팀의 최종 순위 중앙값 (500회)")
for T in (8,15):
    for k in (20,50):
        같음=0; 밖=0; 순위들=[]
        for r in range(500):
            m=np.zeros(N,bool); m[rng.choice(N,N//2,replace=False)]=True
            a,_,_=f1(m); b,_,_=f1(~m)
            pub=[];fin=[]
            for t_ in range(T):
                idx=rng.choice(S,k,replace=False); i=idx[a[idx].argmax()]; pub.append(a[i]); fin.append(b[i])
            p1=int(np.argmax(pub)); fr=순위(np.array(fin))
            같음+= fr[p1]==1; 밖+= fr[p1]>3; 순위들.append(fr[p1])
        print(f"팀 {T:>2} × 시도 {k:>2}:  그대로 1등 {같음/500:.0%} · 3위 밖 {밖/500:.0%} · 최종 순위 중앙값 {int(np.median(순위들))}")
# D. 지금 실습실(테스트 30%, 환자 82명)에서 F1 표준오차 — 공개/최종 없이도 순위가 잡음인지
df=원본.copy(); t=(df.index%10<3).to_numpy(); X=df[["age","avg_glucose_level","heart_disease"]]; y=df["stroke"].to_numpy()
sc=StandardScaler().fit(X[~t]); lr=LogisticRegression(max_iter=2000,class_weight="balanced").fit(sc.transform(X[~t]),y[~t])
pr=(lr.predict_proba(sc.transform(X[t]))[:,1]>=0.80); yt=y[t]; bs=[]
for r in range(2000):
    j=rng.integers(0,len(yt),len(yt)); p=pr[j]; yy=yt[j]; TP=(p&(yy==1)).sum(); FP=(p&(yy==0)).sum(); FN=((~p)&(yy==1)).sum(); bs.append(2*TP/(2*TP+FP+FN))
print(f"\n[D] 지금 실습실 F1 1등(0.342)의 부트스트랩 표준오차 {np.std(bs):.4f} — 1등과 10등 차이 0.02는 이 안")
