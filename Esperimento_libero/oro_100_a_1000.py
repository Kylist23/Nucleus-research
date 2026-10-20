# Esperimento (non decisionale per Nucleus): 100 euro -> 1000 sull'oro.
# Leva costante ribilanciata ogni giorno; costo di tenuta (swap) come % annua del valore mosso.
# Successo = x10 prima di perdere il 90%, entro N anni. Dati fino al 2022-12-30 (cassaforte intatta).
import csv, sys, collections
rows=[r for r in csv.DictReader(open(sys.argv[1])) if "1971-01-01"<=r["Date"]<="2022-12-30"]
d=[r["Date"] for r in rows]; c=[float(r["Close"]) for r in rows]; lo=[float(r["Low"]) for r in rows]
def run(start,end,L,years,swap):
    hit=ruin=n=0; dec=collections.Counter()
    for i0 in range(len(d)):
        if not(start<=d[i0]<=end): continue
        n+=1; eq=1.0
        for j in range(i0+1,min(i0+1+years*252,len(c))):
            if eq*(1+L*(lo[j]/c[j-1]-1))<=0.1: ruin+=1; break
            eq*=1+L*(c[j]/c[j-1]-1)-L*swap/252
            if eq>=10: hit+=1; dec[d[i0][:3]+"0"]+=1; break
    return n,hit,ruin,dict(dec)
for swap in [0.0,0.03]:
  for years in [3,10]:
    for (a,b) in [("1971-01-01","2012-12-31"),("1981-01-01","2012-12-31")]:
      if years==3 and b=="2012-12-31": b="2019-12-31"
      for L in [1,2,3,5,10,20]:
        n,h,r,dec=run(a,b,L,years,swap)
        print(f"swap {swap:.0%} | {years} anni | partenze {a[:4]}-{b[:4]} ({n}) | leva {L:>2}: x10 {100*h/n:5.1f}%  rovina {100*r/n:5.1f}%  x10 per decennio {dec}")
