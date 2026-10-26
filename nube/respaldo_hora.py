"""Respaldo temporizado de cualquier pieza ya aprobada; no publica ni conoce el token de Instagram."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

CHILE=ZoneInfo('America/Santiago')
TIPOS=('carrusel','publicacion','reel','historia','historia-telegram')


def elegible(cola, pieza, hora, ahora):
    matches=[p for p in cola if p.get('id')==pieza]
    if len(matches)!=1:
        return False
    p=matches[0]
    inicio=dt.datetime.strptime(hora,'%Y-%m-%d %H:%M').replace(tzinfo=CHILE)
    # Si la pieza se reprogramo, la hora ya no coincide y este temporizador no hace nada.
    return (p.get('estado')=='pendiente' and p.get('tipo') in TIPOS
            and p.get('hora')==hora
            and inicio <= ahora <= inicio+dt.timedelta(hours=36))


def main():
    pieza,hora=os.environ['PIEZA'],os.environ['HORA']
    ahora=dt.datetime.now(CHILE)
    cola=json.loads((Path(__file__).parent/'cola.json').read_text(encoding='utf-8'))
    ok=elegible(cola,pieza,hora,ahora)
    print(f'Temporizador de {pieza} ({hora}) finalizado: {ahora.isoformat()}; elegible={ok}')
    if os.environ.get('AUDITORIA','true').lower()=='true':
        print('Auditoria del temporizador sin llamar a Instagram ni activar publicador.')
        return
    if not ok:
        print('No hace falta activar el publicador: antes de hora, reprogramada, finalizada o requiere revision.')
        return
    # El mismo workflow serializado relee main y reserva la pieza antes de enviar.
    subprocess.run(['gh','workflow','run','publicar.yml','--repo',os.environ['GITHUB_REPOSITORY'],
                    '--ref','main','-f','prueba=false','-f','auditoria=false'],check=True)
    print('Publicador activado para revisar la pieza aprobada a su hora.')


if __name__=='__main__':
    main()
