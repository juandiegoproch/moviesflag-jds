from flask import Flask, render_template, request, jsonify
import requests
import sqlite3
import json

app = Flask(__name__)
apikey = "bf1d07b7"

def get_db_connection():
    conn = sqlite3.connect('cache.db')
    conn.row_factory = sqlite3.Row  # Optional: Makes rows behave like dictionaries
    return conn, conn.cursor()

def db_init():
    conn, cursor = get_db_connection()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS searchfilms_cache (
        search_text TEXT PRIMARY KEY,
        response TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS moviedetails_cache (
        imdbID TEXT PRIMARY KEY,
        response TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS country_flags_cache (
        country_name TEXT PRIMARY KEY,
        flag_svg TEXT
    )
    ''')
    conn.commit()

def cacheLookup_getMovieDetails(imdbID):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT response FROM moviedetails_cache WHERE imdbID = ?', (imdbID,))
    row = cursor.fetchone()
    if row:
        print(f"cache hit on movie:{imdbID}")
    return json.loads(row[0]) if row else None

def cacheUpdate_getMovieDetails(imdbID, moviedetails):
    conn, cursor = get_db_connection()
    cursor.execute('REPLACE INTO moviedetails_cache (imdbID, response) VALUES (?, ?)', (imdbID, json.dumps(moviedetails)))
    conn.commit()

def cacheLookup_get_country_flag(country_name):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT flag_svg FROM country_flags_cache WHERE country_name = ?', (country_name,))
    row = cursor.fetchone()
    if (row):
        print(f"Cache hit on country:{country_name}")
    return row[0] if row else None

def cacheUpdate_get_country_flag(country_name, flag_svg):
    conn, cursor = get_db_connection()
    cursor.execute('REPLACE INTO country_flags_cache (country_name, flag_svg) VALUES (?, ?)', (country_name, flag_svg))
    conn.commit()

def searchfilms(search_text):
    # No pint on caching this
    
    url = f"https://www.omdbapi.com/?s={search_text}&apikey={apikey}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print("Failed to retrieve search results.")
        return None

def getmoviedetails(movie):
    # Check cache first
    imdbID = movie["imdbID"]
    cached_result = cacheLookup_getMovieDetails(imdbID)
    if cached_result:
        return cached_result
    
    # If not in cache, fetch from API
    url = f"https://www.omdbapi.com/?i={imdbID}&apikey={apikey}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        cacheUpdate_getMovieDetails(imdbID, data)
        return data
    else:
        print("Failed to retrieve movie details.")
        return None

def get_country_flag(fullname):
    # Check cache first
    cached_flag = cacheLookup_get_country_flag(fullname)
    if cached_flag:
        return cached_flag
    
    # If not in cache, fetch from API
    url = f"https://restcountries.com/v3.1/name/{fullname}?fullText=true"
    response = requests.get(url)
    if response.status_code == 200:
        country_data = response.json()
        if country_data:
            flag_svg = country_data[0].get("flags", {}).get("svg", None)
            if flag_svg:
                cacheUpdate_get_country_flag(fullname, flag_svg)
            return flag_svg
    print(f"Failed to retrieve flag for country: {fullname}")
    return None

def merge_data_with_flags(filter):
    filmssearch = searchfilms(filter)
    moviesdetailswithflags = []
    for movie in filmssearch["Search"]:
         moviedetails = getmoviedetails(movie)
         countriesNames = moviedetails["Country"].split(",")
         countries = []
         for country in countriesNames:
            countrywithflag = {
                "name": country.strip(),
                "flag": get_country_flag(country.strip())
            }
            countries.append(countrywithflag)
         moviewithflags = {
            "title": moviedetails["Title"],
            "year": moviedetails["Year"],
            "countries": countries
         }
         moviesdetailswithflags.append(moviewithflags)

    return moviesdetailswithflags

@app.route("/")
def index():
    filter = request.args.get("filter", "").upper()
    return render_template("index.html", movies = merge_data_with_flags(filter))

@app.route("/api/movies")
def api_movies():
    filter = request.args.get("filter", "")
    return jsonify(merge_data_with_flags(filter))    

if __name__ == "__main__":
    db_init()
    app.run(debug=True)

