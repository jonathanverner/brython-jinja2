from . import events

@events.emits('change')
class DelayedUpdater(events.EventMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dirty_self = False
        self.__dirty_children = False

    def update_if_needed(self):
        if self.__dirty_self:
            self._update()
            self._mark_clean()
        if self.__dirty_children:
            self._update_children()
            self._mark_children_clean()

    @property
    def is_dirty(self):
        return self.__dirty_self or self.__dirty_children

    @property
    def is_clean(self):
        return not self.__dirty_self and not self.__dirty_children

    def _child_change_handler(self, evt):
        if self.__dirty_self or self.__dirty_children:
            return
        self.__dirty_children = True
        self.emit('change', {})

    def _change_handler(self, evt):
        if self.__dirty_self:
            return
        self.__dirty_self = True
        if not self.__dirty_children:
            self.emit('change', {})

    def _mark_dirty(self):
        self.__dirty_self = True

    def _mark_clean(self):
        self.__dirty_self = False

    def _mark_children_dirty(self):
        self.__dirty_children = True

    def _mark_children_clean(self):
        self.__dirty_children = False

    def _update(self):
        pass

    def _update_children(self):
        children = getattr(self, '_children', [])
        for ch in children:
            ch.update_if_needed()


