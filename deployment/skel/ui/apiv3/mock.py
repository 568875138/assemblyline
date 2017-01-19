from assemblyline.al.common import forge
from al_ui.apiv3 import core
from al_ui.api_base import api_login, make_api_response

SUB_API = 'myapi'

Classification = forge.get_classification()

myapi_api = core.make_subapi_blueprint(SUB_API)
myapi_api._doc = "My custom API"


@myapi_api.route("/<value>/", methods=["GET"])
@api_login()
def replay_value(value, **kwargs):
    """
    Make your own API here
    """
    return make_api_response({"success": True, "value": value})

