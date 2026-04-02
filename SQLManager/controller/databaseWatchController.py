import threading
import hashlib
import json
import time

class DatabaseWatcher:
    def __init__(self, db, socketio):
        self.db       = db
        self.socketio = socketio
        self._tables  = {}
        self._running = False
        self._thread  = None
        
        # Detecta se gevent está ativo (monkey patched)
        self._use_gevent = False
        try:
            import gevent
            # Se threading.Thread foi patchado por gevent, use gevent.spawn
            if hasattr(threading, '_gevent_monkey_patched'):
                self._use_gevent = True
                self._gevent = gevent
        except ImportError:
            pass

    def watch(self, table_name: str, interval: int = 5, query: str = None):
        self._tables[table_name] = {
            'interval':   interval,
            'last_hash':  None,
            'last_check': 0,
            'query':      query or f"SELECT * FROM {table_name}"
        }

    def _get_hash(self, table_name: str, conn) -> str | None:
        cfg = self._tables[table_name]
        try:
            cursor = conn.cursor()
            cursor.execute(cfg['query'])
            rows = cursor.fetchall()
            cursor.close()
            content = json.dumps([list(r) for r in rows], default=str)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            print(f'[Watcher] Erro ao verificar {table_name}: {e}', flush=True)
            return None

    def _loop(self):
        time.sleep(0.5)
        
        conn = None
        try:
            conn = self.db._get_connection()
            conn.autocommit = True
            print('[Watcher] Conexão dedicada obtida', flush=True)
        except Exception as e:
            print(f'[Watcher] Falha ao obter conexão: {e}', flush=True)
            return

        while self._running:
            now = time.time()
            for table_name, cfg in self._tables.items():
                if now - cfg['last_check'] < cfg['interval']:
                    continue
                cfg['last_check'] = now
                current_hash = self._get_hash(table_name, conn)
                if current_hash is None:
                    continue
                if cfg['last_hash'] is None:
                    cfg['last_hash'] = current_hash
                    continue
                if current_hash != cfg['last_hash']:
                    cfg['last_hash'] = current_hash
                    print(f'[Watcher] Mudança detectada em {table_name}', flush=True)
                    self.socketio.emit(
                        'db_notification',
                        {'action': 'external_change', 'table': table_name},
                        room=table_name.upper()
                    )

            time.sleep(1)  # com gevent patchado, isso cede o event loop

        if conn:
            self.db._return_connection(conn)

    def start(self):
        if self._running:
            return
        if not self._tables:
            print('[Watcher] Nenhuma tabela registrada para monitorar', flush=True)
            return
        
        self._running = True
        
        import gevent
        self._greenlet = gevent.spawn(self._loop)
        
        print(f'[Watcher] Iniciado monitorando {len(self._tables)} tabela(s)', flush=True)

    def stop(self):
        self._running = False
        if self._greenlet:
            self._greenlet.join(timeout=5)