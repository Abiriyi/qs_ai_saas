from contextvars import ContextVar

_current_org = ContextVar("current_org", default=None)


def set_current_org(org):
    return _current_org.set(org)


def reset_current_org(token):
    _current_org.reset(token)


def get_current_org():
    return _current_org.get()