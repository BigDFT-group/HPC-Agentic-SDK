from .bridge import BridgeBackend

_backend = BridgeBackend()

render_script = _backend.render_script
submit = _backend.submit
get_statuses = _backend.get_statuses
get_recent_statuses = _backend.get_recent_statuses
cancel = _backend.cancel
