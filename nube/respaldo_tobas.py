"""Respaldo de una pieza ya aprobada; no publica ni conoce el token de Instagram."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

CHILE=ZoneInfo('America/Santiago')
HORA=dt.datetime(2026,10,19,12,0,tzinfo=CHILE)


def elegible(cola, ahora):
    matches=[p for p in cola if p.get('id')=='carrusel-tobas-3']
    if len(matches)!=1:
        return False
    p=matches[0]
    return (p.get('estado')=='pendiente' and p.get('tipo')=='carrusel'
            and p.get('hora')=='2026-10-19 12:00'
            and HORA <= ahora <= HORA+dt.timedelta(hours=36))


def main():
    ahora=dt.datetime.now(CHILE)
    cola=json.loads((Path(__file__).parent/'cola.json').read_text(encoding='utf-8'))
    print(f'Temporizador finalizado: {ahora.isoformat()}; elegible={elegible(cola,ahora)}')
    if os.environ.get('AUDITORIA','true').lower()=='true':
        print('Auditoria del temporizador sin llamar a Instagram ni activar publicador.')
        return
    if not elegible(cola,ahora):
        print('No hace falta activar el publicador: antes de hora, finalizada o requiere revision.')
        return
    # El mismo workflow serializado relee main y reserva la pieza antes de enviar.
    subprocess.run(['gh','workflow','run','publicar.yml','--repo',os.environ['GITHUB_REPOSITORY'],
                    '--ref','main','-f','prueba=false','-f','auditoria=false'],check=True)
    print('Publicador activado para revisar la pieza aprobada a su hora.')


if __name__=='__main__':
    main()
