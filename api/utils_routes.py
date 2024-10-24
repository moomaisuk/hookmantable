from flask import Blueprint, jsonify
import json, math, env
import os
import requests

# Create a Blueprint instance for the 'ok' API
utils_blueprint = Blueprint('utils_blueprint', __name__)


@utils_blueprint.route('/hello', methods=['GET'])
def utils_hello():
    """
        http://{HOST_NAME}/api?ACCESS_TOKEN={ACCESS_TOKEN}
    """
    ac_token = request.args.get('ACCESS_TOKEN')

    if ac_token is None or ac_token != env.THIS_API_KEY:
        return jsonify({"message": 'Access denial'})

    return jsonify({"message": "not Implement yet"})

