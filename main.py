"""API de FastAPI que gestiona OAuth de Spotify y la persistencia en MySQL."""

# Tarea: Desarrollo API REST con FastAPI integrando base de datos MYSQL y Api externa Spotify

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
    """Devuelve la URL de autorización de Spotify para iniciar el flujo OAuth."""
    auth_url = get_auth_url()
    return {"auth_url": auth_url}

# Endpoint para manejar el callback de Spotify
@app.get("/callback")
async def callback(code: str):
    """Procesa el callback de Spotify e intercambia el código por tokens."""
    try:
        token_info = get_token(code)
        if not token_info:
            raise HTTPException(status_code=400, detail="Error obteniendo token")
        return token_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en callback: {str(e)}")
    

@app.get("/profile")
async def profile(authorization: str = Header()):
    """Obtiene el perfil de Spotify para el usuario autenticado."""
    token = authorization.replace("Bearer ", "")
    user_profile = get_user_profile(token)
    if user_profile:
        return user_profile
    else:
        raise HTTPException(status_code=400, detail="Error obteniendo perfil de usuario")

# Endpoint para refrescar el token de Spotify
@app.get("/refresh_token")
async def refresh_access_token(refresh_token_param: str):
    """Renueva un token de acceso usando el refresh token proporcionado."""
    new_token_info = refresh_token(refresh_token_param)
    if new_token_info:
        return new_token_info
    else:
        raise HTTPException(status_code=400, detail="Error renovando token")
    

# GET Obtener Usuarios
@app.get("/users")
async def get_users():
    """Recupera todos los usuarios almacenados en la base de datos MySQL."""
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
    """Modelo con los datos mínimos de usuario de Spotify almacenados localmente."""

    spotify_id: str
    nombre: str
    email: str
    pais: str

@app.post("/users")
async def create_user(request: Request):
    """Crea un usuario con datos de Spotify y lo guarda en MySQL."""
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
    email = body["email"]
    pais = body.get("pais")
 
    if user_profile:
        spotify_id = user_profile.get("id")
        nombre = user_profile.get("display_name")
        pais = user_profile.get("country")
    else:
        raise HTTPException(status_code=400, detail="Error obteniendo perfil de usuario con el token de acceso proporcionado")
    
    if not spotify_id or not nombre or not email or not pais:
        raise HTTPException(status_code=400, detail="Faltan datos obligatorios para crear el usuario")
    
    #Usuario existe en base de datos
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute(f"SELECT * FROM usuarios WHERE spotify_id='{spotify_id}'")
    existing_user = mycursor.fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario con este Spotify ID o email ya existe")
    else:
        mycursor = mydb.cursor()
        mycursor.execute( f"INSERT INTO usuarios (spotify_id, nombre, email, pais) VALUES ('{spotify_id}', '{nombre}', '{email}', '{pais}')")
        mydb.commit()
    return JSONResponse(content={"message": "Usuario creado exitosamente"}, status_code=201)



#PUT Actualizar Usuario
@app.put("/users/{user_id}")
async def update_user(user_id: int, user: User):
    """Actualiza un usuario existente con la información recibida."""
    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    
    if not user.spotify_id or not user.nombre or not user.email or not user.pais:
        raise HTTPException(status_code=400, detail="Faltan datos obligatorios para actualizar el usuario")
    else:
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
    """Elimina un usuario de MySQL según su identificador."""
    db_connection = DatabaseConnection(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    mydb = await db_connection.get_connection()

    if user_id <= 0:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Falta el ID de usuario para eliminar")
    
    mycursor = mydb.cursor()
    mycursor.execute(f"DELETE FROM usuarios WHERE id={user_id}")
    mydb.commit()
    return JSONResponse(content={"message": "Usuario eliminado exitosamente"})

#GET Preferencias Musicales de Usuario desde Spotify
@app.get("/preferences")
async def get_user_preferences(authorization: str = Header()):
    """Devuelve las canciones principales del usuario autenticado en Spotify."""
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
    """Almacena en MySQL las canciones principales del usuario autenticado."""
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
    """Recupera todas las preferencias musicales almacenadas en MySQL."""
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