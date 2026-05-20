from __future__ import annotations

import importlib
import inspect

from typing import Any, Dict, List, Optional

from ...CoreConfig import CoreConfig
from ..materialization import MaterializationScheduler
from ..query.executor import DatasetExecutor
from ..registry import AnalyticsRegistry, analytics_registry

try:
    from starlette.concurrency import run_in_threadpool
except ImportError:  # pragma: no cover - dependencia opcional
    run_in_threadpool = None

try:
    from starlette.requests import Request as StarletteRequest
except ImportError:  # pragma: no cover - dependencia opcional
    class StarletteRequest:
        pass

try:
    _flask_module = importlib.import_module('flask')
    request = _flask_module.request
    jsonify = _flask_module.jsonify
    FLASK_AVAILABLE = True
except ImportError:  # pragma: no cover - dependencia opcional
    request = None
    jsonify = None
    FLASK_AVAILABLE = False


_UI_TEMPLATE = """<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>SQLManager Analytics 5.0</title>
    <style>
        :root {
            --bg: #f6f1e8;
            --panel: #fffaf2;
            --ink: #13212f;
            --muted: #6a7682;
            --accent: #0b6e4f;
            --accent-2: #d95d39;
            --line: #d9cdbd;
            --shadow: 0 16px 40px rgba(19, 33, 47, 0.08);
        }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: Georgia, 'Times New Roman', serif; background: linear-gradient(180deg, #efe4d2 0%, var(--bg) 100%); color: var(--ink); }
        .shell { max-width: 1200px; margin: 0 auto; padding: 32px 20px 48px; }
        .hero { display: grid; gap: 12px; margin-bottom: 24px; }
        .hero h1 { margin: 0; font-size: clamp(2rem, 4vw, 3.6rem); line-height: 0.95; }
        .hero p { margin: 0; max-width: 720px; color: var(--muted); font-size: 1.05rem; }
        .grid { display: grid; grid-template-columns: 320px 1fr; gap: 20px; }
        .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 24px; box-shadow: var(--shadow); padding: 20px; }
        .panel h2 { margin: 0 0 12px; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.08em; }
        .dataset-list { display: grid; gap: 10px; max-height: 70vh; overflow: auto; }
        .dataset-card { border: 1px solid var(--line); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); cursor: pointer; transition: transform 160ms ease, border-color 160ms ease; }
        .dataset-card:hover, .dataset-card.active { transform: translateY(-2px); border-color: var(--accent); }
        .dataset-card strong { display: block; margin-bottom: 6px; }
        .dataset-card span { color: var(--muted); font-size: 0.92rem; }
        textarea, input, select, button { width: 100%; font: inherit; }
        textarea, input { border: 1px solid var(--line); border-radius: 14px; padding: 12px; background: #fff; color: var(--ink); }
        button { border: 0; border-radius: 14px; padding: 12px 14px; background: var(--accent); color: white; cursor: pointer; }
        button.secondary { background: var(--accent-2); }
        .actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }
        pre { margin: 0; padding: 16px; border-radius: 16px; background: #101820; color: #d7e4f2; overflow: auto; min-height: 320px; }
        .meta { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; color: var(--muted); }
        .tag { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 999px; background: rgba(11, 110, 79, 0.1); color: var(--accent); font-size: 0.8rem; }
        @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class=\"shell\">
        <section class=\"hero\">
            <span class=\"tag\">SQLManager 5.0</span>
            <h1>Analytics Workbench</h1>
            <p>Catálogo, execução ad hoc e materialização básica no próprio SQLManager. Ideal para BI operacional e validação de datasets semânticos.</p>
        </section>
        <section class=\"grid\">
            <aside class=\"panel\">
                <h2>Datasets</h2>
                <input id=\"search\" type=\"search\" placeholder=\"Buscar dataset\" />
                <div id=\"datasets\" class=\"dataset-list\"></div>
            </aside>
            <main class=\"panel\">
                <div class=\"meta\" id=\"meta\"></div>
                <h2 id=\"title\">Selecione um dataset</h2>
                <textarea id=\"payload\" rows=\"12\">{\n  \"dimensions\": [],\n  \"measures\": [],\n  \"filters\": {},\n  \"include_total\": true\n}</textarea>
                <div class=\"actions\">
                    <button id=\"run-query\">Executar Query</button>
                    <button id=\"run-materialization\" class=\"secondary\">Materializar</button>
                </div>
                <div style=\"height:16px\"></div>
                <pre id=\"result\">Aguardando consulta...</pre>
            </main>
        </section>
    </div>
    <script>
        const prefix = '__PREFIX__';
        let selectedDataset = null;
        let datasets = [];

        async function loadDatasets(query = '') {
            const response = await fetch(`${prefix}/catalog${query ? `?q=${encodeURIComponent(query)}` : ''}`);
            const payload = await response.json();
            datasets = payload.data || [];
            renderDatasets();
        }

        function renderDatasets() {
            const list = document.getElementById('datasets');
            list.innerHTML = '';
            for (const dataset of datasets) {
                const card = document.createElement('button');
                card.type = 'button';
                card.className = 'dataset-card' + (selectedDataset && selectedDataset.name === dataset.name ? ' active' : '');
                card.innerHTML = `<strong>${dataset.name}</strong><span>${dataset.description || 'Sem descrição'}</span>`;
                card.addEventListener('click', () => selectDataset(dataset));
                list.appendChild(card);
            }
        }

        function selectDataset(dataset) {
            selectedDataset = dataset;
            document.getElementById('title').textContent = dataset.name;
            document.getElementById('meta').innerHTML = [
                ...(dataset.tags || []).map(tag => `<span class=\"tag\">${tag}</span>`),
                `<span>${(dataset.dimensions || []).length} dimensões</span>`,
                `<span>${(dataset.measures || []).length} measures</span>`
            ].join('');
            document.getElementById('payload').value = JSON.stringify({
                dimensions: dataset.dimensions || [],
                measures: (dataset.measures || []).map(item => item.name),
                filters: {},
                include_total: true
            }, null, 2);
            renderDatasets();
        }

        async function runQuery() {
            if (!selectedDataset) return;
            const payload = JSON.parse(document.getElementById('payload').value || '{}');
            const response = await fetch(`${prefix}/query/${selectedDataset.name}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            document.getElementById('result').textContent = JSON.stringify(result, null, 2);
        }

        async function runMaterialization() {
            if (!selectedDataset) return;
            const response = await fetch(`${prefix}/materializations/${selectedDataset.name}/run`, { method: 'POST' });
            const result = await response.json();
            document.getElementById('result').textContent = JSON.stringify(result, null, 2);
        }

        document.getElementById('search').addEventListener('input', event => loadDatasets(event.target.value));
        document.getElementById('run-query').addEventListener('click', runQuery);
        document.getElementById('run-materialization').addEventListener('click', runMaterialization);
        loadDatasets();
    </script>
</body>
</html>"""


class AnalyticsRouter:
    def __init__(self, db, app: Optional[Any] = None, registry: Optional[AnalyticsRegistry] = None):
        self.db = db
        self.app = app
        self.registry = registry or analytics_registry
        self.config = CoreConfig.get_analytics_config()
        self.enabled = bool(self.config.get('enabled', False))
        self.executor = DatasetExecutor(db, self.registry)
        self.scheduler = MaterializationScheduler(self.executor, self.registry)

        if self.config.get('auto_discover_datasets', True):
            self.registry.autodiscover(self.config.get('datasets_modules'))

        self.scheduler.load_from_config(self.config.get('materializations', []))
        if self.config.get('auto_start_materialization', bool(self.config.get('materializations'))):
            self.scheduler.start()

        if self.app is not None and self.enabled:
            self._register_routes()

    def _detect_app_adapter(self) -> str:
        if self.app is None:
            return 'none'
        if hasattr(self.app, 'add_api_route'):
            return 'fastapi'
        if hasattr(self.app, 'add_route'):
            return 'starlette'
        if hasattr(self.app, 'route'):
            return 'flask'
        if hasattr(self.app, 'register_route'):
            return 'generic'
        return 'unsupported'

    def _get_json_response_class(self):
        for module_name in ('fastapi.responses', 'starlette.responses'):
            try:
                module = importlib.import_module(module_name)
                return getattr(module, 'JSONResponse')
            except (ImportError, AttributeError):
                continue
        return None

    def _get_html_response_class(self):
        for module_name in ('fastapi.responses', 'starlette.responses'):
            try:
                module = importlib.import_module(module_name)
                return getattr(module, 'HTMLResponse')
            except (ImportError, AttributeError):
                continue
        return None

    def _normalize_query_params(self, query_params: Any) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        if not query_params:
            return normalized
        if hasattr(query_params, 'lists'):
            for key, values in query_params.lists():
                if len(values) == 1:
                    normalized[key] = values[0]
                else:
                    normalized[key] = list(values)
            return normalized
        if hasattr(query_params, 'multi_items'):
            for key, value in query_params.multi_items():
                if key in normalized:
                    existing = normalized[key]
                    normalized[key] = existing + [value] if isinstance(existing, list) else [existing, value]
                else:
                    normalized[key] = value
            return normalized
        if hasattr(query_params, 'items'):
            for key, value in query_params.items():
                normalized[key] = value
            return normalized
        if isinstance(query_params, dict):
            return dict(query_params)
        return normalized

    def _build_response(self, payload: Dict[str, Any], adapter: str):
        status_code = int(payload.get('status', 200))
        response_payload = dict(payload)
        response_payload.pop('status', None)

        if adapter == 'flask':
            if not FLASK_AVAILABLE or jsonify is None:
                raise ImportError('Flask nao esta disponivel')
            return jsonify(response_payload), status_code

        response_class = self._get_json_response_class()
        if response_class is not None:
            return response_class(content=response_payload, status_code=status_code)

        return response_payload, status_code

    def _build_html_response(self, html: str, adapter: str):
        if adapter == 'flask':
            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

        response_class = self._get_html_response_class()
        if response_class is not None:
            return response_class(content=html, status_code=200)

        return html, 200

    async def _run_executor(self, dataset_name: str, payload: Dict[str, Any]):
        if run_in_threadpool is not None:
            return await run_in_threadpool(self.executor.execute, dataset_name, payload)
        return self.executor.execute(dataset_name, payload)

    def get_route_definitions(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        prefix = '/' + str(self.config.get('url_prefix', 'analytics')).strip('/')
        adapter = self._detect_app_adapter()
        return [
            {
                'path': f'{prefix}/catalog',
                'methods': ['GET'],
                'endpoint': 'analytics_catalog',
                'handler': self._make_catalog_handler(adapter),
                'tag': 'Analytics',
            },
            {
                'path': f'{prefix}/datasets',
                'methods': ['GET'],
                'endpoint': 'analytics_datasets',
                'handler': self._make_list_handler(adapter),
                'tag': 'Analytics',
            },
            {
                'path': f'{prefix}/datasets/{{dataset_name}}' if adapter != 'flask' else f'{prefix}/datasets/<dataset_name>',
                'methods': ['GET'],
                'endpoint': 'analytics_dataset_detail',
                'handler': self._make_detail_handler(adapter),
                'tag': 'Analytics',
            },
            {
                'path': f'{prefix}/query/{{dataset_name}}' if adapter != 'flask' else f'{prefix}/query/<dataset_name>',
                'methods': ['POST'],
                'endpoint': 'analytics_query',
                'handler': self._make_query_handler(adapter),
                'tag': 'Analytics',
            },
            {
                'path': f'{prefix}/materializations',
                'methods': ['GET'],
                'endpoint': 'analytics_materializations',
                'handler': self._make_materializations_handler(adapter),
                'tag': 'Analytics',
            },
            {
                'path': f'{prefix}/materializations/{{job_name}}/run' if adapter != 'flask' else f'{prefix}/materializations/<job_name>/run',
                'methods': ['POST'],
                'endpoint': 'analytics_materialization_run',
                'handler': self._make_materialization_run_handler(adapter),
                'tag': 'Analytics',
            },
            {
                'path': f'{prefix}/ui',
                'methods': ['GET'],
                'endpoint': 'analytics_ui',
                'handler': self._make_ui_handler(adapter),
                'tag': 'Analytics',
            },
        ]

    def _catalog_payload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = str(params.get('q') or '').strip()
        raw_tags = params.get('tag') or []
        tags = raw_tags if isinstance(raw_tags, list) else [raw_tags]
        datasets = self.registry.search(query=query, tags=tags)
        return {
            'status': 200,
            'data': [dataset.to_dict() for dataset in datasets],
            'meta': self.registry.catalog_summary(),
        }

    def _make_catalog_handler(self, adapter: str):
        if adapter == 'flask':
            def handler():
                return self._build_response(self._catalog_payload(self._normalize_query_params(request.args)), adapter)

            return handler

        async def handler(request_obj: StarletteRequest = None):
            params = self._normalize_query_params(getattr(request_obj, 'query_params', {}))
            return self._build_response(self._catalog_payload(params), adapter)

        return handler

    def _make_list_handler(self, adapter: str):
        if adapter == 'flask':
            def handler():
                payload = {'status': 200, 'data': [dataset.to_dict() for dataset in self.registry.list()]}
                return self._build_response(payload, adapter)

            return handler

        async def handler(request_obj: StarletteRequest = None):
            payload = {'status': 200, 'data': [dataset.to_dict() for dataset in self.registry.list()]}
            return self._build_response(payload, adapter)

        return handler

    def _make_detail_handler(self, adapter: str):
        if adapter == 'flask':
            def handler(dataset_name: str):
                dataset = self.registry.get(dataset_name)
                payload = {'status': 200, 'data': dataset.to_dict()} if dataset else {'status': 404, 'error': f"Dataset '{dataset_name}' nao encontrado"}
                return self._build_response(payload, adapter)

            return handler

        async def handler(dataset_name: str, request_obj: StarletteRequest = None):
            dataset = self.registry.get(dataset_name)
            payload = {'status': 200, 'data': dataset.to_dict()} if dataset else {'status': 404, 'error': f"Dataset '{dataset_name}' nao encontrado"}
            return self._build_response(payload, adapter)

        return handler

    def _make_query_handler(self, adapter: str):
        if adapter == 'flask':
            def handler(dataset_name: str):
                body = request.get_json(force=True, silent=True) or {}
                payload = self.executor.execute(dataset_name, body)
                return self._build_response(payload, adapter)

            return handler

        async def handler(dataset_name: str, request_obj: StarletteRequest = None):
            body = {}
            if request_obj is not None and hasattr(request_obj, 'json'):
                body = request_obj.json()
                if inspect.isawaitable(body):
                    body = await body
            payload = await self._run_executor(dataset_name, body or {})
            return self._build_response(payload, adapter)

        return handler

    def _make_materializations_handler(self, adapter: str):
        if adapter == 'flask':
            def handler():
                payload = {
                    'status': 200,
                    'data': [job.to_dict() for job in self.scheduler.list_jobs()],
                }
                return self._build_response(payload, adapter)

            return handler

        async def handler(request_obj: StarletteRequest = None):
            payload = {
                'status': 200,
                'data': [job.to_dict() for job in self.scheduler.list_jobs()],
            }
            return self._build_response(payload, adapter)

        return handler

    def _make_materialization_run_handler(self, adapter: str):
        if adapter == 'flask':
            def handler(job_name: str):
                job = self.scheduler.get_job(job_name)
                if job is None:
                    from ..materialization import MaterializationJob
                    dataset = self.registry.get(job_name)
                    if dataset is not None:
                        job = self.scheduler.register_job(MaterializationJob(name=job_name, dataset_name=dataset.name, payload={'include_total': True}), overwrite=False)
                payload = self.scheduler.run_job(job.name if job else job_name)
                return self._build_response(payload, adapter)

            return handler

        async def handler(job_name: str, request_obj: StarletteRequest = None):
            job = self.scheduler.get_job(job_name)
            if job is None:
                from ..materialization import MaterializationJob
                dataset = self.registry.get(job_name)
                if dataset is not None:
                    job = self.scheduler.register_job(MaterializationJob(name=job_name, dataset_name=dataset.name, payload={'include_total': True}), overwrite=False)
            payload = self.scheduler.run_job(job.name if job else job_name)
            return self._build_response(payload, adapter)

        return handler

    def _make_ui_handler(self, adapter: str):
        html = _UI_TEMPLATE.replace('__PREFIX__', '/' + str(self.config.get('url_prefix', 'analytics')).strip('/'))
        if adapter == 'flask':
            def handler():
                return self._build_html_response(html, adapter)

            return handler

        async def handler(request_obj: StarletteRequest = None):
            return self._build_html_response(html, adapter)

        return handler

    def _register_route_definition(self, route_definition: Dict[str, Any], adapter: str):
        path = route_definition['path']
        methods = route_definition['methods']
        endpoint = route_definition['endpoint']
        handler = route_definition['handler']
        handler.__name__ = endpoint

        if adapter == 'flask':
            self.app.route(path, methods=methods, endpoint=endpoint)(handler)
            return
        if adapter == 'fastapi':
            self.app.add_api_route(path, handler, methods=methods, name=endpoint, tags=[route_definition.get('tag', 'Analytics')])
            return
        if adapter == 'starlette':
            self.app.add_route(path, handler, methods=methods, name=endpoint)
            return
        if adapter == 'generic':
            self.app.register_route(**route_definition)
            return
        raise TypeError('App nao suportado para AnalyticsRouter')

    def _register_routes(self):
        adapter = self._detect_app_adapter()
        for route_definition in self.get_route_definitions():
            self._register_route_definition(route_definition, adapter)