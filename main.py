#Tarea: Desarrollo API REST con FastAPI integrando base de datos MYSQL y Api externa Spotify

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Header
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from configuration.conections import DatabaseConnection
import mysql.connector
import os
from service.spotify import get_auth_url, get_token,get_user_profile,refresh_token, get_top_tracks

app = FastAPI()

# Endpoint para obtener URL de autenticación de Spotify
@app.get("/login")
async def login():
    auth_url = get_auth_url()
    return {"auth_url": auth_url}

# Endpoint para manejar el callback de Spotify
@app.get("/callback")
async def callback(code: str):
    try:
        token_info = get_token(code)
        if not token_info:
            raise HTTPException(status_code=400, detail="Error obtaining token")
        return token_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en callback: {str(e)}")
    

@app.get("/profile")
async def profile(authorization: str = Header()):
    token = authorization.replace("Bearer ", "")
    user_profile = get_user_profile(token)
    if user_profile:
        return user_profile
    else:
        raise HTTPException(status_code=400, detail="Error fetching user profile")

# Endpoint para refrescar el token de Spotify
@app.get("/refresh_token")
async def refresh_access_token(refresh_token_param: str):
    new_token_info = refresh_token(refresh_token_param)
    if new_token_info:
        return new_token_info
    else:
        raise HTTPException(status_code=400, detail="Error refreshing token")
    

# GET Obtener Usuarios
@app.get("/users")
async def get_users():
    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM usuarios")
    users = mycursor.fetchall()
    return JSONResponse(content=users)

# POST Crear Usuario
class User(BaseModel):
    spotify_id: str
    nombre: str
    email: str
    pais: str

@app.post("/users")
async def create_user(request: Request):
    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()

    # Obtener datos de la petición o fallback a los del modelo User 
    body = await request.json()
    access_token = body.get("access_token")
    user_profile = get_user_profile(access_token) 
    spotify_id = body.get("id") 
    nombre = body.get("display_name") 
    email = body("email") 
    pais = body.get("pais")

    if user_profile:
        spotify_id = user_profile.get("id")
        nombre = user_profile.get("display_name")
        pais = user_profile.get("country")
    else:
        raise HTTPException(status_code=400, detail="Error fetching user profile with provided access token")

    mycursor = mydb.cursor()
    mycursor.execute( f"INSERT INTO usuarios (spotify_id, nombre, email, pais) VALUES ('{spotify_id}', '{nombre}', '{email}', '{pais}')")
    mydb.commit()
    return JSONResponse(content={"message": "Usuario creado exitosamente"}, status_code=201)



#PUT Actualizar Usuario
@app.put("/users/{user_id}")
async def update_user(user_id: int, user: User):
    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()
    spotify_id= user.spotify_id
    nombre= user.nombre
    email= user.email
    pais= user.pais
    mycursor = mydb.cursor()
    mycursor.execute( f"UPDATE usuarios SET spotify_id='{spotify_id}', nombre='{nombre}', email='{email}', pais='{pais}' WHERE id={user_id}")
    mydb.commit()
    return JSONResponse(content={"message": "Usuario actualizado exitosamente"})

#DELETE Eliminar Usuario
@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()
    mycursor = mydb.cursor()
    mycursor.execute(f"DELETE FROM usuarios WHERE id={user_id}")
    mydb.commit()
    return JSONResponse(content={"message": "Usuario eliminado exitosamente"})

#GET Preferencias Musicales de Usuario desde Spotify
@app.get("/preferences")
async def get_user_preferences(authorization: str = Header()):
    token = authorization.replace("Bearer ", "")
    
    preferencias = get_top_tracks(token)
    if not preferencias:
        raise HTTPException(
            status_code=401,
            detail=f"Token inválido o no se pudieron obtener preferencias"
        )

    if "items" not in preferencias or len(preferencias["items"]) == 0:
        raise HTTPException(
            status_code=404,
            detail="No hay canciones disponibles para este usuario"
        )

    top_tracks = [
        {"track_name": t["name"], "artist": t["artists"][0]["name"]}
        for t in preferencias["items"]
    ]

    return {"top_tracks": top_tracks}

#Almacenar Preferencias Musicales en la Base de Datos
@app.post("/preferences")
async def store_user_preferences(authorization: str = Header()):
    token = authorization.replace("Bearer ", "")
    
    preferencias = get_top_tracks(token)
    if not preferencias:
        raise HTTPException(
            status_code=401,
            detail=f"Token inválido o no se pudieron obtener preferencias"
        )

    if "items" not in preferencias or len(preferencias["items"]) == 0:
        raise HTTPException(
            status_code=404,
            detail="No hay canciones disponibles para este usuario"
        )

    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()
    mycursor = mydb.cursor()

    for track in preferencias["items"]:
        track_name = track["name"]
        artist_name = track["artists"][0]["name"]
        mycursor.execute(
            "INSERT INTO preferencias (track_name, artist) VALUES (%s, %s)",
            (track_name, artist_name)
        )

    mydb.commit()

    return JSONResponse(content={"message": "Preferencias almacenadas exitosamente"})

# Get Preferencias Musicales desde la Base de Datos
@app.get("/preferences/db")
async def get_stored_preferences():
    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM preferencias")
    preferencias = mycursor.fetchall()
    return JSONResponse(content=preferencias)        