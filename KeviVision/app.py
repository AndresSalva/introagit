from flask import Flask, render_template, request, redirect, url_for, session  # For flask implementation
from werkzeug.utils import secure_filename
from bson import ObjectId  # For ObjectId to work
from pymongo import MongoClient
from functools import wraps
import random
import os
import datetime


app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_unicaysecreta'  # importante para las sesiones
title = "KeviVision"
heading = "../static/images/logo.jpeg"


# Comment out when running locally
client = MongoClient("mongodb://localhost:27017/")
db = client.MyDB  # Select the database
#  db.authenticate(name=os.getenv("MONGO_USERNAME"),password=os.getenv("MONGO_PASSWORD"))


users = db.users  # Select the collection from users
lists = db.lists  # Select the collection from lists
media = db.media  # Select the collection movies and series

# Configuración para la subida de archivos
UPLOAD_FOLDER = 'KeviVision/static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Asegúrate de que la carpeta de subida existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Función para verificar si el archivo está permitido
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# PRINCIPAL PAGE RENDER
@app.route('/')
def index():
    return redirect(url_for('listMoviesSeries'))

def check_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get('username')
        admin = False
        if username:
            user_document_cursor = users.find({"_id": username})
            for user_document in user_document_cursor:
                if user_document and user_document.get("type") == 'admin':
                    admin = True
                    print("Usuario administrador encontrado:", user_document)
                    break
        session['admin'] = admin
        return f(*args, **kwargs)
    return decorated_function

def check_cashier(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get('username')
        is_cashier = False
        if username:
            user_document_cursor = users.find({"_id": username})
            for user_document in user_document_cursor:
                if user_document and user_document.get("type") == 'cajero':
                    is_cashier = True
                    print("Usuario cajero encontrado:", user_document)
                    break
        session['cajero'] = is_cashier
        return f(*args, **kwargs)
    return decorated_function

@app.route('/adminpage')
def admin():
    return render_template('admin.html',t=title, h=heading)


@app.route('/cajeropage')
def cajero():
    return render_template('cajero.html',t=title, h=heading)

@app.route('/mediaPage')
def mediaPage():
    element = media.find_one({"_id": request.args.get('id')})
    return render_template('media.html', element=element, t=title, h=heading)

@app.route('/enviar_calificacion', methods=['POST'])
def enviar_calificacion():
    elemento_id = int(request.args.get('id'))
    nueva_calificacion = int(request.form.get('estrellas'))
    elemento = media.find_one({"_id": elemento_id})
    rating_actual = elemento.get('Rating', 0)  # Si no hay Rating, se asume 0
    # Calcular el nuevo rating como el promedio
    nuevo_rating = (rating_actual + nueva_calificacion) / 2
    # Actualizar el rating en la base de datos
    media.update_one({"_id": elemento_id}, {"$set": {"Rating": nuevo_rating}})
    return redirect(url_for('mediaPage', id=elemento_id))  # Redirigir a la página del elemento

@app.route("/listMoviesSeries", methods=['GET'])
@check_admin
@check_cashier
def listMoviesSeries():
    # Display the all media
    movies = media.find({'format': 'movie'}, {'format': 1, 'title': 1, 'Rating': 1})
    series = media.find({'format': 'series'}, {'format': 1, 'title': 1, 'Rating': 1})
    
    random_genres_1, random_genres_2 = random.sample(media.distinct('genres'), 2)

    random_movies_1 = media.find({'genres': {'$in': [random_genres_1]}}, {'format': 1, 'title': 1, 'Rating': 1})
    random_movies_2 = media.find({'genres': {'$in': [random_genres_2]}}, {'format': 1, 'title': 1, 'Rating': 1})

    return render_template('index.html', movies=movies, series=series, random_movies_1=random_movies_1, random_movies_2=random_movies_2, random_genres_1=random_genres_1, random_genres_2=random_genres_2, t=title, h=heading,admin=admin)


# LOGIN REQUIREMENTS
@app.route('/login')
def login():
    session.pop('username', None)
    return render_template('userLogin.html', t=title, h=heading)


@app.route('/logout')
def logout():
    # Elimina la clave 'username' de la sesión
    session.pop('username', None)
    return redirect(url_for('listMoviesSeries'))


@app.route('/verifyFirstAccess', methods=['POST'])
def verifyFirst():
    user_name = request.form['username']
    user_document = users.find_one({"_id": user_name})
    if user_document:
        user_password = request.form['password']
        if user_password == user_document.get('password'):
            # Autenticación exitosa, establece la sesión y redirige
            session['username'] = user_name
            return redirect(url_for('listMoviesSeries'))
        else:
            # Contraseña incorrecta
            result = "La contraseña no es válida."
    else:
        # Usuario no encontrado
        result = "El usuario no existe."
    return render_template('userLogin.html', result=result, t=title, h=heading)


# REGISTER PARAMETERS
@app.route('/sigin')
def sigin():
    session.pop('username', None)
    return render_template('userSignin.html', result="Ingrese un usuario", is_registered=False, t=title, h=heading)


@app.route('/insertUser', methods=['POST'])
def insertUser():
    is_register = request.args.get('is_register')
    if is_register != True:
        username = request.form['username']
        if not users.find_one({"_id": username}):
            session['username'] = username
            password = request.form['password']
            session['password'] = password
            users.insert_one({"_id": username, "password": password})
            return render_template('userSignin.html', result="Ingrese sus datos", is_registered=True, t=title, h=heading)
    return render_template('userSignin.html', result="Usuario no valido, ingrese otro", is_registered=False, t=title, h=heading)


@app.route('/insertDataUser', methods=['POST'])
def insertDataUser():
    users.update_one({"_id": session.get('username')},
                     {"$set": {"name": request.form['name'], "email": request.form['email'],"type":"user"}})
    session.pop('password', None)
    return redirect(url_for('listMoviesSeries'))

@app.route("/searchMedia", methods=['GET'])
def searchMedia():
    query = request.args.get('query', '')
    genre = request.args.get('genre', '')
    year = request.args.get('year', '')
    format = request.args.get('format', '')

    # Construir el filtro para la consulta en MongoDB
    filter_query = {'title': {'$regex': query, '$options': 'i'}}

    if genre:
        filter_query['genres'] = genre

    if year:
        filter_query['year'] = int(year)

    if format:
        filter_query['format'] = format

    # Realizar la consulta a MongoDB
    results = media.find(filter_query)

    return render_template('searchMedia.html', results=results, t=title, h=heading)

@app.route('/insertMedia', methods=['POST'])
def insertMedia():
    titleMedia = request.form['title']
    synopsis = request.form['synopsis']
    format = request.form['format']
    year = request.form['year']
    selectedGenres = request.form.getlist('genres')
    rate = request.form['rate']

    # Manejar la subida de archivos
    if 'image' not in request.files:
        return "No image part", 400
    file = request.files['image']
    if file.filename == '':
        return "No selected file", 400
    if file and allowed_file(file.filename):
        now = datetime.datetime.now()
        filename_without_ext = secure_filename(os.path.splitext(file.filename)[0])
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{filename_without_ext}{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        filename_only = os.path.basename(file_path)

        # Insertar en la base de datos
        media.insert_one({
            "_id": filename_only,
            "format": format,
            "title": titleMedia,
            "sinopsis": synopsis,
            "genres": selectedGenres,
            "year": year,
            "Rating": rate,
        })
        return redirect(url_for('admin'))
    else:
        return "File not allowed", 400
@app.route('/compra', methods=['POST'])
def compra():
    nombre = request.form.get('nombre')
    nit = request.form.get('nit')
    elemento_id = str(request.args.get('id'))
    media.update_one(
            {"_id": elemento_id},
            {
                "$inc": {"ventas": 1},
                "$push": {"ventas_detalle": {"nombre": nombre, "nit": nit}}
            }
        )
    return render_template('cajero.html',t=title, h=heading)

wsgi_app = app.wsgi_app

if __name__ == "__main__":
    app.run(debug=True, port=5000)