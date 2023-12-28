from flask import Flask, request
from flask_cors import CORS
from ffci.config import FFCONFIG
from ffci.exception import Hub2LabException
from ffci.api.handlers.errors import render_error
from ffci.api.handlers.request_logging import before_request_log, after_request_log
from ffci.api.flaskapp import FlaskApp


def getvalues():
    jsonbody = request.get_json(force=True, silent=True)
    values = request.values.to_dict()
    if jsonbody:
        values.update(jsonbody)
    return values


class FailfastApp(FlaskApp):
    from ffci.api.hook import ffapi_app
    from ffci.api.info import info_app

    blueprints = [(ffapi_app, ""), (info_app, "")]
    before_request_funcs = [before_request_log]
    after_request_funcs = [after_request_log]
    error_handler_funcs = [(Exception, render_error), (Hub2LabException,
                                                       render_error)]


def create_app():
    app = Flask(__name__)
    CORS(app)
    ffapp = FailfastApp(app)
    # app.logger.addHandler(logging.StreamHandler(sys.stdout))
    # app.logger.setLevel(logging.INFO)
    if FFCONFIG.failfast['env'] != 'production':
        ffapp.app.config.from_object(
            'ffci.api.config.DevelopmentConfig')
    else:
        ffapp.app.config.from_object('ffci.api.config.ProductionConfig')

    ffapp.app.logger.info("Start service")
    return ffapp


if __name__ == "__main__":
    application = create_app().app
    application.run(host='0.0.0.0')
