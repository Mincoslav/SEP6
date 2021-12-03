import requests
import json
import pyodbc

def fix_movie_id(movie_id: int, add_tt: bool):
    movie_id_mod = str(movie_id)

    if len(movie_id_mod) < 8:
        difference = 7 - len(movie_id_mod)
        movie_id_mod = ('0' * difference) + movie_id_mod
    if 'tt' not in movie_id_mod and add_tt is True:
        movie_id_mod = 'tt' + movie_id_mod
    return movie_id_mod

tmdb_api_key = '66ade9da9e0ff7f75853209b4f0b504c'

external_search_URL = 'https://api.themoviedb.org/3/find/{external_id}?api_key={api_key}&external_source=imdb_id'

def get_movie_from_tmdb(imdb_id: int):
    external_id = fix_movie_id(imdb_id, True)
    URL = external_search_URL.format(external_id= external_id, api_key= tmdb_api_key)
    response = requests.get(url = URL)
    content = json.loads(response._content)
    if response.status_code == 200:
        content['movie_results'][0]['id'] = imdb_id
    return response, content


def get_db_cursor():
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=tcp:sep-6.database.windows.net,1433;"
        "Database=movieDatabase;"
        "Uid=michal;"
        "Pwd=sb2Kr7TCzVZM5dF;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    connection = pyodbc.connect(connection_string)
    connection.autocommit = True

    cursor = connection.cursor()
    return cursor


def get_movie_list_from_email(email: str):
    movie_ids = []
    db_cursor = get_db_cursor()
    try:
        db_cursor.execute("SELECT user_id FROM users WHERE email = '{email}'".format(email = email))
        user_id = db_cursor.fetchone().user_id
    except Exception as e:
        return "no email"
    try:
        db_cursor.execute(
            "SELECT movie_lists.movie_id FROM ((users INNER JOIN user_list_lookup ON users.user_id = {user_id}) INNER JOIN movie_lists ON movie_lists.list_id = user_list_lookup.movie_list_id and user_list_lookup.user_id = {user_id});"
            .format(
                user_id = user_id
            )
        )
        result = db_cursor.fetchall()
        for row in result:
            movie_ids.append(row.movie_id)
    except Exception as e:
        return "no movies for email"
    else:
        return movie_ids


def get_movie(movie_id: str):
    try:        
        db_cursor = get_db_cursor()
        db_cursor.execute("SELECT * FROM movies WHERE movie_id = {}".format(movie_id))
        result = db_cursor.fetchone()
    except Exception as e:
        return "no movie found"
    else:
        return result