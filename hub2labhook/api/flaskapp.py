from typing import Tuple, List, Any, Callable, Type  # noqa
import flask  # noqa
from hub2labhook.exception import Hub2LabException  # noqa


class FlaskApp(object):
    blueprints = []  # type: List[Tuple[flask.Blueprint, str]]
    after_request_funcs = []  # type: List[Callable[[flask.Response], None]]
    before_request_funcs = []  # type: List[Callable[[], None]]
    teardown_request_funcs = []  # type: List[Callable[[flask.Response], None]]
    error_handler_funcs = [
    ]  # type: List[Tuple[Type[Exception], Callable[[Exception], flask.Response]]]

    def __init__(self, app) -> None:
        self._app = app
        self.register_blueprints()
        self.register_before_requests()
        self.register_after_requests()
        self.register_teardowns()
        self.register_error_handlers()

    @property
    def app(self):
        return self._app

    def register_blueprints(self):
        for blueprint, prefix in self.blueprints:
            self.app.register_blueprint(blueprint, url_prefix=prefix)

    def register_after_requests(self):
        """ Register all after requests handlers """
        for func in self.after_request_funcs:
            self.app.after_request(func)

    def register_before_requests(self):
        for func in self.before_request_funcs:
            self.app.before_request(func)

    def register_teardowns(self):
        for func in self.teardown_request_funcs:
            self.app.teardown_request(func)

    def register_error_handlers(self):
        for exception, handler in self.error_handler_funcs:
            self.app.register_error_handler(exception, handler)
