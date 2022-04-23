#!/usr/bin/python3

import requests
import re
from datetime import datetime


def tmdb_lookup(tmdb_url, tmdb_headers, movie, year=None):

    movie = re.sub('[^a-zA-Z.\d\s]', '', movie)
    tmdb_params = {
        "language": "en-US",
        "query": movie,
        "page": 1,
        "include_adult": False
    }

    if year:
        tmdb_params["primary_release_year"] = year

    tmdb_search = requests.get(f"{tmdb_url}/search/movie", params=tmdb_params,
                               headers=tmdb_headers)

    if tmdb_search.status_code == 401:
        return "401", "401", "401", "401"
    
    tmdb_search = tmdb_search.json()

    if not tmdb_search["results"]:
        return "404", "404", "404", "404"

    movie_id = tmdb_search['results'][0]['id']
    movie_title = tmdb_search['results'][0]['title']
    movie_release_check = tmdb_search['results'][0]['release_date']

    if movie_release_check:
        movie_release = datetime.strptime(
            tmdb_search['results'][0]['release_date'], "%Y-%m-%d")
        movie_year = movie_release.year
    else:
        movie_year = "???"

    movie_rating = tmdb_search['results'][0]['vote_average']

    return movie_id, movie_title, movie_year, movie_rating


def sa_lookup(sa_url, sa_headers, movie_id):
    sa_params = {
        "country": "us",
        "tmdb_id": f"movie/{movie_id}",
        "output_language": "en"
        }

    sa_request = requests.request("GET", sa_url, headers=sa_headers,
                                  params=sa_params)

    if sa_request.status_code == 401:
        sa_response = "401"
    elif sa_request.status_code == 404:
        sa_response = "404"
    else:
        sa_response = sa_request.json()
        services = sa_response["streamingInfo"]

    return sa_response, services


def services_speller(service):
    if service == "hbo":
        service_proper = "HBO Max"
    elif service == "hulu":
        service_proper = "Hulu"
    elif service == "prime":
        service_proper = "Amazon Prime"
    elif service == "netflix":
        service_proper = "Netflix"
    elif service == "disney":
        service_proper = "Disney\+"
    elif service == "apple":
        service_proper = "Apple TV\+"
    elif service == "paramount":
        service_proper = "Paramount\+"
    elif service == "starz":
        service_proper = "STARZ"
    elif service == "showtime":
        service_proper = "Showtime"
    elif service == "peacock":
        service_proper = "Peacock"
    else:
        return service
    return service_proper


def char_cleanup(variable):
    variable = str(variable).replace('-', '\-')
    variable = str(variable).replace('(', '\(')
    variable = str(variable).replace(')', '\)')
    variable = str(variable).replace('+', '\+')
    variable = str(variable).replace('.', '\.')

    return variable
