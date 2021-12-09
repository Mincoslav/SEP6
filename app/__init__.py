import azure.functions as func
import pyodbc
from azure.functions import AsgiMiddleware
from fastapi import status, HTTPException
from starlette import responses
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_418_IM_A_TEAPOT,
)

from api_app import app
from tmdb_api import get_movie_from_tmdb
from database_api import (
    get_movies_from_email_db,
    get_movie_db,
    sign_up_sign_in_db,
    create_list_for_user_db,
    add_movie_into_list_db,
    remove_movie_from_list_db,
    get_user_id_db,
    get_users_lists_db,
    get_movies_from_list_db,
)


tags_metadata = [
    {
        "name": "Get movie by ID",
        "description": "Get details about a movie from TMDb API using IMDb id __without__ 'tt*******' format",
    },
    {
        "name": "items",
        "description": "Manage items. So _fancy_ they have their own docs.",
        "externalDocs": {
            "description": "Items external docs",
            "url": "https://fastapi.tiangolo.com/",
        },
    },
]


@app.get("/", status_code=HTTP_200_OK)
def read_root():
    return {"Hello": "Movies"}


@app.get("/movie/{movie_id}", status_code=status.HTTP_200_OK, tags=["Get movie by ID"])
def get_movie_by_id(movie_id: str):
    result = get_movie_db(movie_id)
    if result != "no movie found":
        response, content = get_movie_from_tmdb(result.imdb_id)
    else:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Movie with id: {} not found database".format(movie_id),
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Movie with id: {} not found in TMDB".format(movie_id),
        )
    else:
        return content


@app.get("/movie_list/{list_id}", status_code=status.HTTP_200_OK)
def get_movie_list_content(list_id: int):
    # TODO
    movies_in_list = get_movies_from_list_db(list_id)
    if movies_in_list == "no movies in list":
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="No movies found in list with id:{}".format(list_id),
        )
    else:
        return {"status": HTTP_200_OK, "list_id": list_id, "movies": movies_in_list}


@app.get("/user/{user_email}/movies", status_code=HTTP_200_OK)
def get_users_movies(user_email: str):
    tmdb_movies = []
    movie_list = get_movies_from_email_db(user_email)
    if movie_list == "no email":
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="No known user found for email: {}".format(user_email),
        )
    elif movie_list == "no movies for email":
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="No movies found for email: {}".format(user_email),
        )
    else:
        for movie in movie_list:
            resp, json = get_movie_from_tmdb(movie)
            tmdb_movies.append(json)

        return {"response": HTTP_200_OK, "movies": tmdb_movies}


@app.get("/user/{user_email}/lists", status_code=HTTP_200_OK)
def get_users_lists(user_email: str):
    users_list_ids = get_users_lists_db(user_email)
    if users_list_ids == "no lists found":
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="No movie lists found for email:{}".format(user_email),
        )
    else:
        return {
            "response": HTTP_200_OK,
            "user_email": user_email,
            "list_ids": users_list_ids,
        }


@app.get("/user/{user_email}/id", status_code=HTTP_200_OK)
def get_user_id(user_email: str):
    user = get_user_id_db(user_email)
    if user == None or user == "get_user_id failed":
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="User not found for email: {}".format(user_email),
        )
    else:
        return {
            "response": HTTP_200_OK,
            "user_id": user.user_id,
            "user_email": user_email,
        }


@app.post("/user/{user_email}/register", status_code=HTTP_201_CREATED)
def sign_up_sign_in(user_email: str):
    response = ""
    try:
        status, user_id = sign_up_sign_in_db(user_email)
    except pyodbc.Error as e:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="User couldn't be created for email: {}".format(user_email),
        )
    else:
        if status == "user created":
            response = HTTP_201_CREATED
        elif status == "user retrieved":
            response = HTTP_200_OK

        return {
            "response": response,
            "status": status,
            "user_email": user_email,
            "user_id": user_id,
        }


@app.post("/user/{user_email}/create_list", status_code=HTTP_201_CREATED)
def create_list_for_user(user_email: str):
    user_id = get_user_id_db(user_email)[0]
    user_list = create_list_for_user_db(user_id)
    if user_list == "list not created":
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="List couldn't be created for user: {}".format(user_email),
        )
    else:
        return {
            "response": HTTP_201_CREATED,
            "user_email": user_email,
            "movie_list_id": user_list,
        }


@app.post("/add_to_list/{list_id}/movie/{movie_id}")
def add_movie_to_list(list_id: int, movie_id: int):
    response = add_movie_into_list_db(movie_list_id=list_id, movie_id=movie_id)

    if response == "movie not added":
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Movie couldn't be added. Possible reasons: list doesn't exist",
        )
    else:
        return {
            "response": HTTP_201_CREATED,
            "list_id": list_id,
            "movie_id": movie_id,
        }


@app.post("/remove_from_list/{list_id}/movie/{movie_id}")
def remove_movie_from_list(list_id: int, movie_id: int):
    response = remove_movie_from_list_db(movie_list_id=list_id, movie_id=movie_id)

    if response == "movie not removed":
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Movie couldn't be removed. Possible reasons: List with id: {list_id} doesn't exist or Movie with id: {movie_id} isn't in the list".format(
                list_id=list_id, movie_id=movie_id
            ),
        )
    else:
        return {
            "response": HTTP_200_OK,
            "message": response,
            "list_id": list_id,
            "movie_id": movie_id,
        }


def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return AsgiMiddleware(app).handle(req, context)
