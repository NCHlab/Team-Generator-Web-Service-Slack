import threading
import logging

from flask_restful import Resource, reqparse
from flask import Flask, request, Response

from config import post_slack_data, parse_player, format_user
import config


logger = logging.getLogger(__name__)
mutex = threading.Lock()


class SlackAddToBalance(Resource):
    def post(self):
        data = dict(request.form)

        response_url = data["response_url"]
        players_text = data["text"]
        user_data = format_user(data)

        logger.info(f"Req from slack to add to balance, Names: {players_text}")
        logger.info(user_data)

        thread = threading.Thread(
            target=process_data, args=(response_url, players_text)
        )
        thread.start()

        return Response(status=200)


def process_data(response_url, players_text):

    players_list = parse_player(players_text)
    player_status = process_players(players_list)
    positive_result, player_names = process_output(player_status)
    player_names = ", ".join(player_names)

    if positive_result:
        post_slack_data(response_url, "Players added to balance", player_names)

    else:
        post_slack_data(response_url, "Following players do not exist", player_names)


def process_players(players_list):

    mutex.acquire()

    player_status = []
    for player in players_list:
        resp = config.obj.add_to_balance(player)
        player_status.append(resp)

    mutex.release()

    return player_status


def process_output(player_status):

    players_ok = list(
        filter(lambda x: x["status"] == "ok" or x["status"] == "ok_2", player_status)
    )

    if len(player_status) == len(players_ok):
        players_ok = list(map(lambda x: x["name"], players_ok))

        return (True, players_ok)
    else:
        players_error = list(filter(lambda x: x["status"] == "error", player_status))
        players_error = list(map(lambda x: x["name"], players_error))

        return (False, players_error)
