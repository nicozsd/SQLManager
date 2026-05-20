from __future__ import annotations

import importlib
import inspect

from typing import Dict, Iterable, List, Optional

from .metadata import Dataset, build_default_dataset, filter_public_names


class AnalyticsRegistry:
    def __init__(self):
        self._datasets: Dict[str, Dataset] = {}

    def register(self, dataset: Dataset, overwrite: bool = True) -> Dataset:
        key = dataset.name.strip().lower()
        if not key:
            raise ValueError('Dataset precisa ter um nome valido')
        if not overwrite and key in self._datasets:
            return self._datasets[key]
        dataset.ensure_default_measure()
        self._datasets[key] = dataset
        return dataset

    def get(self, dataset_name: str) -> Optional[Dataset]:
        return self._datasets.get(str(dataset_name or '').strip().lower())

    def require(self, dataset_name: str) -> Dataset:
        dataset = self.get(dataset_name)
        if dataset is None:
            raise KeyError(f"Dataset '{dataset_name}' nao encontrado")
        return dataset

    def list(self) -> List[Dataset]:
        return [self._datasets[key] for key in sorted(self._datasets.keys())]

    def search(self, query: str = '', tags: Optional[Iterable[str]] = None) -> List[Dataset]:
        normalized_query = str(query or '').strip().lower()
        normalized_tags = {str(tag).strip().upper() for tag in tags or [] if str(tag).strip()}
        results = []
        for dataset in self.list():
            dataset_tags = {str(tag).strip().upper() for tag in dataset.tags}
            if normalized_tags and not normalized_tags.issubset(dataset_tags):
                continue
            if normalized_query:
                haystack = ' '.join([
                    dataset.name,
                    dataset.description,
                    dataset.source.name,
                    ' '.join(dataset.dimensions),
                    ' '.join(dataset.measures.keys()),
                ]).lower()
                if normalized_query not in haystack:
                    continue
            results.append(dataset)
        return results

    def catalog_summary(self) -> Dict[str, object]:
        datasets = self.list()
        tags: Dict[str, int] = {}
        for dataset in datasets:
            for tag in dataset.tags:
                tags[tag] = tags.get(tag, 0) + 1
        return {
            'datasets': len(datasets),
            'measures': sum(len(dataset.measures) for dataset in datasets),
            'hierarchies': sum(len(dataset.hierarchies) for dataset in datasets),
            'tags': tags,
        }

    def autodiscover(self, modules: Optional[Iterable[str]] = None, overwrite: bool = False) -> List[Dataset]:
        discovered: List[Dataset] = []
        for module_name in modules or ():
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            public_names = filter_public_names(getattr(module, '__all__', dir(module)))
            for name in public_names:
                attr = getattr(module, name, None)
                if not inspect.isclass(attr):
                    continue
                if getattr(attr, '__module__', None) != module.__name__:
                    continue
                dataset_key = name.strip().lower()
                if dataset_key in self._datasets and not overwrite:
                    continue
                discovered.append(self.register(build_default_dataset(name, attr, module.__name__), overwrite=True))
        return discovered

    def ensure(self, dataset_name: str, modules: Optional[Iterable[str]] = None) -> Optional[Dataset]:
        dataset = self.get(dataset_name)
        if dataset is not None:
            return dataset
        if modules:
            self.autodiscover(modules=modules, overwrite=False)
            return self.get(dataset_name)
        return None


analytics_registry = AnalyticsRegistry()