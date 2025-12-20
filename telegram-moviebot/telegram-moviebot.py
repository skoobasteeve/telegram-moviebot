import difflib
import logging
import os
from datetime import datetime

import movie_check
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

tmdb_api_token = os.environ.get("TMDB_API_TOKEN")
sa_api_token = os.environ.get("SA_API_TOKEN")
bot_token = os.environ.get("TG_BOT_TOKEN")

country = os.environ.get("STREAMING_COUNTRY") or "us"
filter_user = os.environ.get("TG_BOT_USER")
logging_debug = os.environ.get("TG_DEBUG")

tmdb_url = "https://api.themoviedb.org/3"
tmdb_headers = {
    "Authorization": f"Bearer {tmdb_api_token}",
    "Content-Type": "application/json;charset=utf-8",
    "Accept": "application/json;charset=utf-8",
}

sa_url = "https://streaming-availability.p.rapidapi.com/get/basic"
sa_headers = {
    "x-rapidapi-host": "streaming-availability.p.rapidapi.com",
    "x-rapidapi-key": sa_api_token,
}


if logging_debug and logging_debug == "True":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )
else:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_firstname = update.message.from_user["first_name"]
    user_id = update.message.from_user["id"]
    username = update.message.from_user["username"] or "empty"
    logger.info(f"Session initiated by user: {user_firstname} ({username}, {user_id})")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a movie streaming bot! Type in a "
        + "movie and I'll tell you where to stream it.",
    )


def movie_lookup(movie, user_firstname):
    if "-Year" in movie:
        year = movie.split("-Year")[1].strip()
        movie = movie.split("-Year")[0].strip()
        logger.info(f'{user_firstname}: Looking up movie: "{movie}" ({year})')
        movie_id, movie_title, movie_year, movie_rating = movie_check.tmdb_lookup(
            tmdb_url, tmdb_headers, movie, year
        )
    else:
        logger.info(f'{user_firstname}: Looking up movie: "{movie}"')
        movie_id, movie_title, movie_year, movie_rating = movie_check.tmdb_lookup(
            tmdb_url, tmdb_headers, movie
        )

    tmdb_page = "https://themoviedb.org/movie/"

    if movie_id == "404":
        tg_reply = (
            f"{user_firstname}: I'm having trouble finding that movie\\. "
            + "Check your spelling and try again\\."
        )
        logger.warning(f'{user_firstname}: Movie "{movie}" not found in TMDB.')
        similarity = 0
        error_response = False
        return tg_reply, similarity, error_response

    if movie_id == "401":
        tg_reply = (
            "Invalid TMDB API token\\. " + "Bot shutting down until restarted\\.\\.\\."
        )
        logger.error("Invalid TMDB API token. Exiting...")
        similarity = 0
        error_response = True
        return tg_reply, similarity, error_response

    sa_response, services = movie_check.sa_lookup(sa_url, sa_headers, movie_id, country)
    if sa_response == "404":
        logger.warning(
            f'{user_firstname}: Movie "{movie}" not found by the Streaming Availability API.'
        )

    if sa_response == "401":
        tg_reply = (
            "Invalid Streaming Availability API token\\. "
            + "Bot shutting down until restarted\\.\\.\\."
        )
        logger.error(
            f"{user_firstname}: Invalid Streaming Availability API token. Exiting..."
        )
        similarity = 0
        error_response = True
        return tg_reply, similarity, error_response

    similarity = difflib.SequenceMatcher(None, movie, movie_title).ratio()
    sim_percent = "{0:.0f}%".format(similarity * 100)

    logger.info(f"{user_firstname}: Result was a {sim_percent} match.")

    movie_title = movie_check.char_cleanup(movie_title)
    movie_year = movie_check.char_cleanup(movie_year)
    movie_rating = movie_check.char_cleanup(movie_rating)

    tg_reply = (
        f"{movie_title} \\({movie_year}\\)\nRating: {movie_rating}"
        + f"\n[TMDB]({tmdb_page}{movie_id})"
    )
    logger.info(f'{user_firstname}: Returning movie: "{movie_title}: ({movie_year})"')

    if not services or sa_response == "404":
        tg_reply = tg_reply + "\n\nStreaming not available :\\("
        logger.info(
            f'{user_firstname}: No streaming available for "{movie_title}: ({movie_year})"'
        )
    else:
        for s in services:
            leaving_epoch = sa_response["streamingInfo"][s]["us"]["leaving"]
            leaving_date = datetime.fromtimestamp(int(leaving_epoch)).strftime(
                "%Y\\-%m\\-%d"
            )
            link = sa_response["streamingInfo"][s]["us"]["link"]

            s_pretty = movie_check.services_speller(s)
            tg_reply = tg_reply + f"\n\nAvailable on *{s_pretty}*"

            if leaving_epoch != 0:
                tg_reply = tg_reply + f"\nWill be leaving on {leaving_date}"

            tg_reply = tg_reply + f"\n[Watch here]({link})"

    error_response = False
    return tg_reply, similarity, error_response


async def input_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_firstname = update.message.from_user["first_name"]
    movie = update.message.text.title()
    movie_info, similarity, error_response = movie_lookup(movie, user_firstname)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=movie_info,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    if error_response:
        # In v20+, we can't easily stop the application from within a handler
        # The application will need to be stopped externally or we raise an exception
        logger.error("Critical error occurred. Application should be restarted.")
        return
    if similarity < 0.80 and similarity != 0:
        logger.info(
            f"{user_firstname}: Result accuracy was below the threshold. Sending follow-up message."
        )
        followup_msg = (
            "Not the movie you're looking for? "
            + "Try adding '\\-year' followed by the release year after the title\\."
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=followup_msg,
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command.",
    )


def main():
    if not tmdb_api_token:
        logger.error("ERROR: TMDB API token not provided. Exiting...")
        exit()

    if not sa_api_token:
        logger.error("ERROR: Streaming Availability API token not provided. Exiting...")
        exit()

    if not bot_token:
        logger.error("ERROR: Telegram bot token not provided. Exiting...")
        exit()

    # Build the Application
    application = Application.builder().token(bot_token).build()

    # Add start handler with optional user filter
    if filter_user:
        start_handler = CommandHandler(
            "start", start, filters.User(username=filter_user)
        )
    else:
        start_handler = CommandHandler("start", start)

    application.add_handler(start_handler)

    # Add movie input handler (text messages that are not commands)
    movie_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), input_movie)
    application.add_handler(movie_handler)

    # Add unknown command handler
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
