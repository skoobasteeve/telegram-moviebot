#!/usr/bin/python3

import telegram
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    MessageHandler,
    Filters)
import logging
from telegram import Update, ParseMode
import os
from datetime import datetime
import movie_check


tmdb_api_token = os.environ.get("TMDB_API_TOKEN")
sa_api_token = os.environ.get("SA_API_TOKEN")
bot_token = os.environ.get("TG_BOT_TOKEN")

filter_user = "@skoobasteeve"

tmdb_url = "https://api.themoviedb.org/3"
tmdb_headers = {
    'Authorization': f'Bearer {tmdb_api_token}',
    'Content-Type': 'application/json;charset=utf-8',
    'Accept': 'application/json;charset=utf-8'
}

sa_url = "https://streaming-availability.p.rapidapi.com/get/basic"
sa_headers = {
    'x-rapidapi-host': "streaming-availability.p.rapidapi.com",
    'x-rapidapi-key': sa_api_token
    }

updater = Updater(token=bot_token, use_context=True)
dispatcher = updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext):
    movie_handler = MessageHandler(Filters.text & (~Filters.command),
                                   input_movie)
    dispatcher.add_handler(movie_handler)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="I'm a movie streaming bot! Type in a " +
                             "movie and I'll tell you where to stream it.")


def movie_lookup(movie):
    logger.info(f'Looking up movie: "{movie}"')
    tmdb_page = "https://themoviedb.org/movie/"
    movie_id, movie_title, movie_year, movie_rating = (
        movie_check.tmdb_lookup(tmdb_url, tmdb_headers, movie))

    movie_rating = str(movie_rating).replace('.', '\.')
    sa_response, services = movie_check.sa_lookup(sa_url, sa_headers, movie_id)
    tg_reply = (f"{movie_title} \({movie_year}\)\nRating: {movie_rating}" +
                f"\n[TMDB]({tmdb_page}{movie_id})")
    logger.info(f'Returning movie: "{movie_title}: ({movie_year})"')

    if not services:
        tg_reply = tg_reply + "\n\nStreaming not available :\("
    else:
        for s in services:
            leaving_epoch = sa_response["streamingInfo"][s]["us"]["leaving"]
            leaving_date = datetime.fromtimestamp(
                int(leaving_epoch)).strftime('%Y\-%m\-%d')
            link = sa_response["streamingInfo"][s]["us"]["link"]

            s_pretty = movie_check.services_speller(s)
            tg_reply = tg_reply + f"\n\nAvailable on *{s_pretty}*"

            if leaving_epoch != 0:
                tg_reply = tg_reply + f"Will be leaving on {leaving_date}"

            tg_reply = tg_reply + f"\n[Watch here]({link})"
    return tg_reply


def input_movie(update: Update, context: CallbackContext):
    movie = update.message.text
    movie_info = movie_lookup(movie)
    context.bot.send_message(chat_id=update.effective_chat.id, text=movie_info, parse_mode=telegram.ParseMode.MARKDOWN_V2)


def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Sorry, I didn't understand that command.")


def main():

    start_handler = CommandHandler('start', start,
                                   Filters.user(username=filter_user))
    dispatcher.add_handler(start_handler)

    unknown_handler = MessageHandler(Filters.command, unknown)

    dispatcher.add_handler(unknown_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
