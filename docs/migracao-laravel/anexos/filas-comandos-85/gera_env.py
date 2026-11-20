# .env de teste: copia do ecidade/.env.example (versionado) com estas trocas; chave, token e enderecos ficticios
import sys,re,base64
src,dst=sys.argv[1:]
over={'APP_ENV':'testing','APP_KEY':'base64:'+base64.b64encode(b'chave-de-teste-fixa-32-bytes-ok!').decode(),'APP_DEBUG':'true',
 'APP_URL':'http://localhost','DB_HOST':'banco-inexistente.invalid','DB_PASSWORD':'x',
 'MAIL_DRIVER':'array','QUEUE_DRIVER':'sync','CACHE_DRIVER':'array','SESSION_DRIVER':'array','BROADCAST_DRIVER':'log',
 'API_DATA_AVAILABLE_TOKEN':'token-de-teste','API_DATA_AVAILABLE_URL':'http://api.invalid/'}
out=[];seen=set()
for l in open(src,encoding='latin-1'):
    m=re.match(r'([A-Z0-9_]+)=',l)
    if m and m.group(1) in over:
        if m.group(1) in seen: continue
        l=f'{m.group(1)}={over[m.group(1)]}\n'; seen.add(m.group(1))
    out.append(l)
out+= [f'{k}={v}\n' for k,v in over.items() if k not in seen]
open(dst,'w',encoding='latin-1').write(''.join(out))
