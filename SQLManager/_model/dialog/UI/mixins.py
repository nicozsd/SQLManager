from abc import ABC, abstractmethod

class ComponentMixin(ABC):
    """
    Mixin base para automatizar a renderização e ciclo de vida
    dos componentes de UI na janela principal.
    """
    def __init__(self):
        self.widget = None

    def render(self, parent, **pack_kwargs):
        """
        Renderiza o componente no parent especificado e aplica os argumentos de layout.
        """
        self.widget = self._build(parent)
        self.widget.pack(**pack_kwargs)
        self._bind_events()
        return self.widget

    @abstractmethod
    def _build(self, parent):
        pass

    def _bind_events(self):
        """Hook opcional para registrar eventos após a renderização."""
        pass