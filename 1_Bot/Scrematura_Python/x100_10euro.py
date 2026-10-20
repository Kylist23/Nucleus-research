# Quante partenze storiche arrivano a x100 prima di perdere il 90%? Oro giornaliero, leva costante
# ribilanciata ogni giorno, NESSUN costo (ipotesi ottimista). Dati fino al 2022-12-30 (cassaforte intatta).
import csv, sys, math
rows=[r for r in csv.DictReader(open(sys.argv[1])) if "1971-01-01"<=r["Date"]<="2022-12-30"]
d=[r["Date"] for r in rows]; c=[float(r["Close"]) for r in rows]; lo=[float(r["Low"]) for r in rows]
def run(start,end,L,horizon=5*252):
    s=[i for i in range(len(d)) if start<=d[i]<=end]
    hit=ruin=0; days=[]
    for i0 in s:
        eq=1.0
        for j in range(i0+1,min(i0+1+horizon,len(c))):
            # perdita peggiore dentro il giorno (minimo) per lo stop di margine
            worst=eq*(1+L*(lo[j]/c[j-1]-1))
            if worst<=0.1: ruin+=1; break
            eq*=1+L*(c[j]/c[j-1]-1)
            if eq>=100: hit+=1; days.append(j-i0); break
    n=len(s); return n,hit,ruin
for (a,b) in [("1971-01-01","2017-12-31"),("2016-01-01","2017-12-31")]:
    for L in [1,2,5,10,20]:
        n,h,r=run(a,b,L)
        print(f"{a[:4]}-{b[:4]} leva {L:>2}: partenze {n}, x100 entro 5 anni {h} ({100*h/n:.1f}%), rovina (-90%) {r} ({100*r/n:.1f}%)")
