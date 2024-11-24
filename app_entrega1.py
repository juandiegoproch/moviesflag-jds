from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)
apikey = "bf1d07b7"

searchfilms_cache = {}
moviedetails_cache = {}
country_flags_cache = {}

def cacheLookup_getMovieDetails(imdbID):
    if imdbID in moviedetails_cache:
        print(f"Cache hit on movie: {imdbID}")
        return moviedetails_cache[imdbID]
    return None

def cacheUpdate_getMovieDetails(imdbID, moviedetails):
    moviedetails_cache[imdbID] = moviedetails

def cacheLookup_get_country_flag(country_name):
    if country_name in country_flags_cache:
        print(f"Cache hit on country: {country_name}")
        return country_flags_cache[country_name]
    return None

def cacheUpdate_get_country_flag(country_name, flag_svg):
    country_flags_cache[country_name] = flag_svg

def searchfilms(search_text, page, pageSize):
    # Check if search results for this text and page are cached
    cache_key = f"{search_text}_{page}"
    if cache_key in searchfilms_cache:
        print(f"Cache hit on search: {cache_key}")
        return searchfilms_cache[cache_key]
    
    url = f"https://www.omdbapi.com/?s={search_text}&apikey={apikey}&page={page}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        searchfilms_cache[cache_key] = data
        return data
    else:
        print("Failed to retrieve search results.")
        return None

def getmoviedetails(movie):
    imdbID = movie["imdbID"]
    cached_result = cacheLookup_getMovieDetails(imdbID)
    if cached_result:
        return cached_result
    
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
    cached_flag = cacheLookup_get_country_flag(fullname)
    if cached_flag:
        return cached_flag
    
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

def merge_data_with_flags(filter, page, pageSize):
    filmssearch = searchfilms(filter, page, pageSize)
    moviesdetailswithflags = []
    if filmssearch and "Search" in filmssearch:
        for movie in filmssearch["Search"]:
            moviedetails = getmoviedetails(movie)
            if moviedetails:
                countriesNames = moviedetails["Country"].split(",")
                countries = []
                for country in countriesNames:
                    country_name = country.strip()
                    countrywithflag = {
                        "name": country_name,
                        "flag": get_country_flag(country_name)
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
    page = int(request.args.get("page", 1))  # Default to first page if not provided
    pageSize = int(request.args.get("pageSize", 10))  # Default to 10 items per page
    movies = merge_data_with_flags(filter, page, pageSize)
    return render_template("index.html", movies=movies, page=page, pageSize=pageSize)

@app.route("/api/movies")
def api_movies():
    filter = request.args.get("filter", "")
    page = int(request.args.get("page", 1))
    pageSize = int(request.args.get("pageSize", 10))
    movies = merge_data_with_flags(filter, page, pageSize)
    return jsonify(movies)

if __name__ == "__main__":
    app.run(debug=True)
