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
        self._greenlet = None  # era self._thread

    # ... watch() e _get_hash() sem mudança ...

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